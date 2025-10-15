"""Application configuration models and helpers."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict
import yaml


def _join_url(base: str, path: str) -> str:
    base = base.rstrip("/")
    if not path:
        return base
    if path.startswith("http://") or path.startswith("https://"):
        return path.rstrip("/")
    if not path.startswith("/"):
        path = "/" + path
    return f"{base}{path}".rstrip("/")


@dataclass
class N8nSettings:
    """Settings for talking to the n8n server."""

    server_url: str = "https://ai.genio-bot.com"
    text_webhook_path: str = "/webhook/genio-bot-question"
    response_webhook_path: str = "/webhook/genio-bot-response"

    def question_url(self) -> str:
        return _join_url(self.server_url, self.text_webhook_path)

    def response_url(self) -> str:
        return _join_url(self.server_url, self.response_webhook_path)


@dataclass
class AppRuntimeSettings:
    """Runtime settings for this application."""

    public_base_url: str = "https://ai.genio-bot.com"
    reply_webhook_path: str = "/api/v1/webhooks/genio-bot-reply"
    listen_host: str = "0.0.0.0"
    listen_port: int = 8010
    reply_timeout_s: int = 45

    def reply_webhook_url(self) -> str:
        return _join_url(self.public_base_url, self.reply_webhook_path)


@dataclass
class SpeechSettings:
    """Settings for speech recognition."""

    model_size: str = "small"
    language: str = "sv"
    device: str = "cpu"
    compute_type: str = "int8"


@dataclass
class VoiceSettings:
    """Settings for the Piper text-to-speech backend."""

    model_path: str = "./piper/models/sv-se_nst-medium.onnx"
    config_path: str = "./piper/models/sv-se_nst-medium.onnx.json"
    output_wav: str = "/tmp/genio-bot-tts.wav"
    playback_cmd: list[str] = field(default_factory=lambda: ["aplay", "-q", "/tmp/genio-bot-tts.wav"])


@dataclass
class AppConfig:
    """Top-level configuration dataclass."""

    n8n: N8nSettings = field(default_factory=N8nSettings)
    app: AppRuntimeSettings = field(default_factory=AppRuntimeSettings)
    stt: SpeechSettings = field(default_factory=SpeechSettings)
    tts: VoiceSettings = field(default_factory=VoiceSettings)

    @classmethod
    def load(cls, path: Path) -> "AppConfig":
        if not path.exists():
            return cls()
        data = yaml.safe_load(path.read_text()) or {}
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AppConfig":
        n8n = N8nSettings(**data.get("n8n", {}))
        app = AppRuntimeSettings(**data.get("app", {}))
        stt = SpeechSettings(**data.get("stt", {}))
        tts_data = data.get("tts", {})
        # allow playback_cmd to be provided as string or list
        if isinstance(tts_data.get("playback_cmd"), str):
            tts_data = dict(tts_data)
            tts_data["playback_cmd"] = tts_data["playback_cmd"].split()
        tts = VoiceSettings(**tts_data)
        return cls(n8n=n8n, app=app, stt=stt, tts=tts)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "n8n": {
                "server_url": self.n8n.server_url,
                "text_webhook_path": self.n8n.text_webhook_path,
                "response_webhook_path": self.n8n.response_webhook_path,
            },
            "app": {
                "public_base_url": self.app.public_base_url,
                "reply_webhook_path": self.app.reply_webhook_path,
                "listen_host": self.app.listen_host,
                "listen_port": self.app.listen_port,
                "reply_timeout_s": self.app.reply_timeout_s,
            },
            "stt": {
                "model_size": self.stt.model_size,
                "language": self.stt.language,
                "device": self.stt.device,
                "compute_type": self.stt.compute_type,
            },
            "tts": {
                "model_path": self.tts.model_path,
                "config_path": self.tts.config_path,
                "output_wav": self.tts.output_wav,
                "playback_cmd": self.tts.playback_cmd,
            },
        }

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w") as f:
            yaml.safe_dump(self.to_dict(), f, sort_keys=False)
