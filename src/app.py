"""Entry point for the new Genio Bot voice assistant."""
from __future__ import annotations

import argparse
import os
from pathlib import Path

from .app_config import AppConfig
from .audio_recorder import AudioRecorder
from .config_flow import ConfigurationFlow
from .n8n_webhook_client import N8nWebhookClient
from .reply_broker import ReplyBroker
from .reply_server import ReplyWebhookServer
from .speech_to_text import SpeechToText
from .text_to_speech import PiperTextToSpeech


def build_components(config: AppConfig):
    recorder = AudioRecorder()
    stt = SpeechToText(
        model_size=config.stt.model_size,
        device=config.stt.device,
        compute_type=config.stt.compute_type,
        language=config.stt.language,
    )
    tts = PiperTextToSpeech(
        model_path=config.tts.model_path,
        config_path=config.tts.config_path,
        output_wav=config.tts.output_wav,
        playback_cmd=config.tts.playback_cmd,
    )
    broker = ReplyBroker()
    client = N8nWebhookClient(config, broker)
    webhook_server = ReplyWebhookServer(config, client)
    return recorder, stt, tts, client, webhook_server


def main() -> None:
    parser = argparse.ArgumentParser(description="Genio Bot röstassistent")
    parser.add_argument("--config", default="config.yaml", help="Sökväg till konfigurationsfilen")
    args = parser.parse_args()

    config_path = Path(args.config)
    flow = ConfigurationFlow(config_path)
    config = flow.run()

    recorder, stt, tts, client, webhook_server = build_components(config)
    webhook_server.start()

    recorder.start()
    device_name = os.uname().nodename
    print("\n🎤  Tala när du är redo. Pausa för att skicka frågan till n8n. Ctrl+C för att avsluta.")

    try:
        while True:
            audio = recorder.read_utterance()
            if not audio:
                continue
            text = stt.transcribe(audio, recorder.sample_rate)
            if not text:
                print("(Ingen text uppfattades, försök igen)")
                continue
            print(f"→ Skickar till n8n: {text}")
            try:
                reply = client.ask(text, device=device_name)
            except TimeoutError as exc:
                print(f"⚠️  {exc}")
                continue
            print(f"← Svar från n8n: {reply}")
            tts.speak(reply)
    except KeyboardInterrupt:
        print("Avslutar…")
    finally:
        recorder.stop()
        webhook_server.stop()


if __name__ == "__main__":  # pragma: no cover
    main()
