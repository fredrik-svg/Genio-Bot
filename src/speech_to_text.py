"""Speech-to-text implementation using faster-whisper."""
from __future__ import annotations

import numpy as np
from faster_whisper import WhisperModel


class SpeechToText:
    """Wrapper around the Whisper model for on-device transcription."""

    def __init__(self, model_size: str, device: str = "cpu", compute_type: str = "int8", language: str | None = None):
        self.model = WhisperModel(model_size, device=device, compute_type=compute_type)
        self.language = language

    def transcribe(self, pcm16: bytes, sample_rate: int) -> str:
        if not pcm16:
            return ""
        audio = np.frombuffer(pcm16, dtype=np.int16).astype(np.float32) / 32768.0
        segments, _ = self.model.transcribe(audio, language=self.language, beam_size=1)
        text = " ".join(segment.text.strip() for segment in segments if segment.text)
        return text.strip()
