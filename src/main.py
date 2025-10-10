import os
import argparse
from util import load_config, setup_logging
from audio import AudioStream
from tts import PiperTTS
from client import BackendClient

# STT - support both local Piper/Whisper and audio upload modes
from stt_piper import PiperSTT

def main(cfg_path: str):
    cfg = load_config(cfg_path)
    setup_logging(cfg.get("logging", {}).get("level", "INFO"))

    # Init moduler
    audio_cfg = cfg.get("audio", {})
    stt_cfg = cfg.get("stt", {})
    tts_cfg = cfg.get("tts", {}).get("piper", {})
    be_cfg = cfg.get("backend", {})

    stream = AudioStream(
        sample_rate=audio_cfg.get("sample_rate", 16000),
        channels=audio_cfg.get("channels", 1),
        chunk_ms=audio_cfg.get("chunk_ms", 30),
        device=audio_cfg.get("input_device"),
        vad_enabled=audio_cfg.get("vad", {}).get("enabled", True),
        vad_aggressiveness=audio_cfg.get("vad", {}).get("aggressiveness", 2),
    )

    # STT mode: "local" uses Piper/Whisper locally, "upload" sends audio to n8n
    stt_mode = stt_cfg.get("mode", "local")
    stt = None
    if stt_mode == "local":
        piper_cfg = stt_cfg.get("piper", {})
        stt = PiperSTT(
            model=piper_cfg.get("model", "base"),
            language=stt_cfg.get("language", "sv"),
            device=piper_cfg.get("device", "cpu"),
        )

    tts = PiperTTS(
        model_path=tts_cfg["model_path"],
        config_path=tts_cfg["config_path"],
        output_wav=tts_cfg.get("output_wav", "/tmp/tts_out.wav"),
        playback_cmd=tts_cfg.get("playback_cmd"),
    )

    backend = BackendClient(
        url=be_cfg["n8n_url"],
        audio_url=be_cfg.get("audio_url"),  # Optional audio upload endpoint
        response_key=be_cfg.get("response_key", "reply"),
        timeout_s=be_cfg.get("timeout_s", 30),
        headers=be_cfg.get("headers", {}),
    )

    device_name = os.uname().nodename
    print(f"🚀 Satellit startad (STT-läge: {stt_mode}) — Ctrl+C för att avsluta.")

    stream.start()
    try:
        while True:
            print("🎙️  Lyssnar… (prata, håll en paus för att skicka)")
            pcm = stream.read_frames_until_silence()
            
            # Process audio based on mode
            if stt_mode == "local":
                print("🧠  Lokal STT (Whisper)…")
                try:
                    text = stt.transcribe_pcm16(pcm)
                except Exception as e:
                    print(f"❌ STT-fel: {e}")
                    continue
                if not text:
                    print("(tom transkribering, försöker igen)")
                    continue
                print(f"📨 → Backend: {text}")
                reply = backend.ask(device=device_name, text=text)
            else:  # upload mode
                print("📤  Skickar ljud till n8n…")
                try:
                    reply = backend.ask_audio(device=device_name, pcm_bytes=pcm)
                except Exception as e:
                    print(f"❌ Upload-fel: {e}")
                    continue
            
            print(f"🗣️  ← Svar: {reply}")
            tts.synth(reply)
    except KeyboardInterrupt:
        print("Avslutar…")
    finally:
        stream.stop()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config.yaml")
    args = parser.parse_args()
    main(args.config)
