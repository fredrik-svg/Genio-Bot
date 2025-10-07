#!/usr/bin/env python3

import argparse
import asyncio
import logging
import time
from dataclasses import dataclass
from functools import partial
from typing import List, Optional, Set

from .asr import Transcript
from .client import AsyncClient
from .event import Event
from .info import AsrModel, AsrProgram, Attribution, Describe, Info
from .server import AsyncEventHandler, AsyncServer

_LOGGER = logging.getLogger(__name__)


async def main() -> None:
    """Runs fallback ASR server."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--uri", required=True, help="unix:// or tcp://")
    parser.add_argument(
        "fallback_uri",
        nargs="+",
        help="Wyoming URI of ASR server (e.g., tcp://127.0.0.1:10300)",
    )
    parser.add_argument(
        "--debug", action="store_true", help="Print DEBUG messages to console"
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO)
    _LOGGER.debug(args)

    server = AsyncServer.from_uri(args.uri)
    _LOGGER.info("Ready")

    try:
        await server.run(partial(FallbackEventHandler, args.fallback_uri))
    except KeyboardInterrupt:
        pass


# -----------------------------------------------------------------------------


@dataclass
class FallbackClient:
    """Information about a Wyoming ASR client."""

    uri: str
    client: AsyncClient
    name: str
    info: Optional[Info] = None
    is_connected: bool = False
    is_enabled: bool = True

    async def ensure_connected_and_info(self) -> None:
        """Connect to client and get info if necessary."""
        if not self.is_connected:
            _LOGGER.debug("Connecting to %s", self.uri)
            await self.client.connect()
            self.is_connected = True

        if self.info is None:
            _LOGGER.debug("Getting info for %s", self.uri)
            await self.client.write_event(Describe().event())
            while True:
                event = await self.client.read_event()
                if event is None:
                    _LOGGER.warning("Disconnected from %s", self.name)
                    self.is_enabled = False
                    self.is_connected = False
                    break

                if not Info.is_type(event.type):
                    continue

                self.info = Info.from_event(event)
                if self.info.asr:
                    self.name = self.info.asr[0].name
                    self.is_enabled = True
                else:
                    _LOGGER.warning("Disabled %s (no ASR service)", self.name)
                    self.is_enabled = False

                break

            _LOGGER.info("Got info for %s (%s)", self.name, self.uri)


class FallbackEventHandler(AsyncEventHandler):
    """Event handler for clients."""

    def __init__(
        self,
        fallback_uris: List[str],
        *args,
        **kwargs,
    ) -> None:
        """Initialize event handler."""
        super().__init__(*args, **kwargs)

        if not fallback_uris:
            raise ValueError("At least one fallback URI is required")

        self.fallback_clients: List[FallbackClient] = [
            FallbackClient(uri=uri, client=AsyncClient.from_uri(uri), name=uri)
            for uri in fallback_uris
        ]
        self.client_id = str(time.monotonic_ns())

        self._target_idx = 0
        self._target_read_task: Optional[asyncio.Task] = None
        self._saved_events: List[Event] = []
        self._info_event: Optional[Event] = None

    async def handle_event(self, event: Event) -> bool:
        """Handle Wyoming event."""
        try:
            if Describe.is_type(event.type):
                await self._write_info()
                return True

            target_client = self.fallback_clients[self._target_idx]
            await target_client.ensure_connected_and_info()

            if self._target_read_task is None:
                await self._set_fallback_target(target_client)

            # Forward to current target
            await target_client.client.write_event(event)
            self._saved_events.append(event)
        except Exception:
            _LOGGER.exception("Error handling event")

        return True

    async def _set_fallback_target(self, fb_client: FallbackClient) -> None:
        """Create read task and send saved messages."""
        self._target_read_task = asyncio.create_task(self._read_from_client(fb_client))
        self._target_read_task.add_done_callback(lambda _: self._clear_read_task())

        for saved_event in self._saved_events:
            await fb_client.client.write_event(saved_event)

    async def _read_from_client(self, fb_client: FallbackClient) -> None:
        """Read events from a client until a transcript comes back."""
        try:
            while True:
                event = await fb_client.client.read_event()
                if event is None:
                    # TODO: fall back
                    _LOGGER.warning("Disconnected from %s", fb_client.name)
                    # self.is_connected = False
                    break

                if not Transcript.is_type(event.type):
                    continue

                transcript = Transcript.from_event(event)
                _LOGGER.debug("Received from '%s' from %s", transcript, fb_client.name)

                await fb_client.client.disconnect()
                fb_client.is_connected = False

                if transcript.text.strip():
                    # Got the final transcript
                    _LOGGER.debug(
                        "Final transcript: '%s' from %s",
                        transcript.text,
                        fb_client.name,
                    )
                    await self.write_event(event)
                    self._saved_events.clear()
                    self._target_idx = 0
                else:
                    # Fallback
                    self._target_idx += 1
                    while self._target_idx < len(self.fallback_clients):
                        next_client = self.fallback_clients[self._target_idx]
                        await next_client.ensure_connected_and_info()
                        if not next_client.is_enabled:
                            self._target_idx += 1
                            continue

                        _LOGGER.debug("Falling back to %s", next_client.name)
                        await self._set_fallback_target(next_client)
                        break

                    if self._target_idx >= len(self.fallback_clients):
                        # No more fallbacks
                        _LOGGER.debug("No more fallbacks. Sending empty transcript.")
                        await self.write_event(event)
                        self._saved_events.clear()
                        self._target_idx = 0

                break

        except Exception:
            _LOGGER.exception("Error reading event from client")

    def _clear_read_task(self) -> None:
        self._target_read_task = None

    async def _write_info(self) -> None:
        if self._info_event is not None:
            await self.write_event(self._info_event)
            return

        supported_langs: Set[str] = set()

        for fb_client in self.fallback_clients:
            await fb_client.ensure_connected_and_info()
            assert fb_client.info is not None
            for asr_prog in fb_client.info.asr:
                for asr_model in asr_prog.models:
                    if not asr_model.installed:
                        continue

                    supported_langs.update(asr_model.languages)

        info = Info(
            asr=[
                AsrProgram(
                    name="stt-fallback",
                    attribution=Attribution(
                        name="The Home Assistant Authors",
                        url="http://github.com/OHF-voice",
                    ),
                    description="Automatic fallback for Wyoming speech-to-text",
                    installed=True,
                    version="1.0.0",
                    models=[
                        AsrModel(
                            name="fallback",
                            attribution=Attribution(
                                name="The Home Assistant Authors",
                                url="http://github.com/OHF-voice",
                            ),
                            installed=True,
                            description="Fallback model",
                            version=None,
                            languages=list(sorted(supported_langs)),
                        )
                    ],
                )
            ]
        )

        self._info_event = info.event()
        await self.write_event(self._info_event)


# -----------------------------------------------------------------------------

if __name__ == "__main__":
    asyncio.run(main())
