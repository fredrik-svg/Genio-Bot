"""Utilities for pairing outgoing questions with incoming webhook replies."""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class PendingReply:
    conversation_id: str
    reply: Optional[str] = None
    event: threading.Event = field(init=False, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "event", threading.Event())

    def set(self, reply: str) -> None:
        self.reply = reply
        self.event.set()

    def wait(self, timeout: float | None = None) -> Optional[str]:
        if self.event.wait(timeout):
            return self.reply
        return None


class ReplyBroker:
    """Maintain a registry of pending conversations."""

    def __init__(self) -> None:
        self._pending: Dict[str, PendingReply] = {}
        self._lock = threading.Lock()

    def create(self, conversation_id: str) -> PendingReply:
        pending = PendingReply(conversation_id)
        with self._lock:
            self._pending[conversation_id] = pending
        return pending

    def resolve(self, conversation_id: str, reply: str) -> bool:
        with self._lock:
            pending = self._pending.pop(conversation_id, None)
        if not pending:
            return False
        pending.set(reply)
        return True
