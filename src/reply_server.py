"""FastAPI server that receives replies from n8n and resolves pending requests."""
from __future__ import annotations

import threading

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

from app_config import AppConfig
from n8n_webhook_client import N8nWebhookClient


class ReplyPayload(BaseModel):
    conversation_id: str
    reply: str


class ReplyWebhookServer:
    def __init__(self, config: AppConfig, client: N8nWebhookClient):
        self.config = config
        self.client = client
        self._thread: threading.Thread | None = None
        self._uvicorn: uvicorn.Server | None = None

    def _create_app(self) -> FastAPI:
        app = FastAPI(title="Genio Bot Webhook")

        @app.get("/health")
        async def health():  # pragma: no cover - simple health check
            return {"status": "ok"}

        @app.post(self.config.app.reply_webhook_path)
        async def handle(payload: ReplyPayload):
            if not self.client.handle_reply(payload.conversation_id, payload.reply):
                raise HTTPException(status_code=404, detail="Ingen pågående konversation hittades")
            return {"status": "received"}

        return app

    def start(self) -> None:
        if self._thread is not None:
            return
        app = self._create_app()
        config = uvicorn.Config(
            app,
            host=self.config.app.listen_host,
            port=self.config.app.listen_port,
            log_level="info",
        )
        server = uvicorn.Server(config)
        self._uvicorn = server
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()
        self._thread = thread

    def stop(self) -> None:
        if self._uvicorn:
            self._uvicorn.should_exit = True
        if self._thread:
            self._thread.join(timeout=1)
        self._thread = None
        self._uvicorn = None
