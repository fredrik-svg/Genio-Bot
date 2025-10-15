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
        response = httpx.post(
            self.config.n8n.question_url(),
            json=payload,
            timeout=self.config.app.reply_timeout_s,
            follow_redirects=True,
        )
        response.raise_for_status()
        reply = pending.wait(self.config.app.reply_timeout_s)
        if reply is None:
            raise TimeoutError(
                "Ingen respons mottagen från n8n-webhooken inom "
                f"{self.config.app.reply_timeout_s} sekunder."
            )
        return reply

    def handle_reply(self, conversation_id: str, reply: str) -> bool:
        return self.broker.resolve(conversation_id, reply)
