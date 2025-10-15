"""HTTP client that posts questions to n8n and awaits webhook replies."""
from __future__ import annotations

import uuid

import httpx

from .app_config import AppConfig
from .reply_broker import ReplyBroker


class N8nWebhookClient:
    def __init__(self, config: AppConfig, broker: ReplyBroker):
        self.config = config
        self.broker = broker

    def ask(self, text: str, device: str | None = None) -> str:
        conversation_id = str(uuid.uuid4())
        pending = self.broker.create(conversation_id)
        payload = {
            "text": text,
            "conversation_id": conversation_id,
            "callback_url": self.config.app.reply_webhook_url(),
        }
        if device:
            payload["device"] = device
        headers = {
            # Cloudflare sometimes blocks generic HTTP clients. Spoof a
            # mainstream browser user agent and keep the request behaviour
            # consistent with manual tests performed via the browser/curl.
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 "
                "Safari/605.1.15"
            ),
            # Accept JSON (n8n returns JSON here) while still allowing fallbacks
            # similar to the browser behaviour.
            "Accept": "application/json, */*;q=0.1",
        }
        try:
            response = httpx.post(
                self.config.n8n.question_url(),
                json=payload,
                timeout=self.config.app.reply_timeout_s,
                follow_redirects=True,
                headers=headers,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:  # pragma: no cover - network failure
            self.broker.discard(conversation_id)
            status = exc.response.status_code
            raise RuntimeError(
                "n8n-webhooken svarade med felkod "
                f"{status}. Kontrollera att URL och webhook-path stämmer."
            ) from exc
        except httpx.RequestError as exc:  # pragma: no cover - network failure
            self.broker.discard(conversation_id)
            raise RuntimeError(
                "Kunde inte kontakta n8n-webhooken. Kontrollera nätverk och URL."
            ) from exc
        reply = pending.wait(self.config.app.reply_timeout_s)
        if reply is None:
            self.broker.discard(conversation_id)
            raise TimeoutError(
                "Ingen respons mottagen från n8n-webhooken inom "
                f"{self.config.app.reply_timeout_s} sekunder."
            )
        return reply

    def handle_reply(self, conversation_id: str, reply: str) -> bool:
        return self.broker.resolve(conversation_id, reply)

    def diagnose_connection(self, test_text: str = "diagnostic ping", device: str | None = None) -> dict:
        """Perform basic connectivity checks against the n8n server.

        The diagnostics are split into two steps so that it is easier to
        understand where a failure occurs when the webhook responds with a
        404-status. The returned dictionary always contains two keys:

        ``server``
            Result of pinging the base server URL with a GET request.
        ``webhook``
            Result of posting a minimal payload to the question webhook.

        Both keys map to dictionaries containing ``ok`` (bool) as well as
        contextual data such as status codes or error messages.
        """

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 "
                "Safari/605.1.15"
            ),
            "Accept": "application/json, */*;q=0.1",
        }

        diagnostics: dict[str, dict[str, object]] = {
            "server": {"ok": False},
            "webhook": {"ok": False},
        }

        try:
            response = httpx.get(
                self.config.n8n.server_url,
                timeout=self.config.app.reply_timeout_s,
                follow_redirects=True,
                headers=headers,
            )
            diagnostics["server"].update(
                {
                    "ok": response.is_success,
                    "status_code": response.status_code,
                    "url": str(response.url),
                }
            )
        except httpx.RequestError as exc:  # pragma: no cover - network failure
            diagnostics["server"].update({"error": str(exc)})

        conversation_id = str(uuid.uuid4())
        payload = {
            "text": test_text,
            "conversation_id": conversation_id,
            "callback_url": self.config.app.reply_webhook_url(),
        }
        if device:
            payload["device"] = device

        _ = self.broker.create(conversation_id)
        try:
            try:
                response = httpx.post(
                    self.config.n8n.question_url(),
                    json=payload,
                    timeout=self.config.app.reply_timeout_s,
                    follow_redirects=True,
                    headers=headers,
                )
                diagnostics["webhook"].update(
                    {
                        "ok": response.is_success,
                        "status_code": response.status_code,
                        "url": str(response.url),
                        "response_body": response.text,
                    }
                )
            except httpx.RequestError as exc:  # pragma: no cover - network failure
                diagnostics["webhook"].update({"error": str(exc)})
        finally:
            self.broker.discard(conversation_id)

        return diagnostics
