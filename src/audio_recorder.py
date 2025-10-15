"""Audio recording utilities for capturing utterances from the microphone."""
from __future__ import annotations

import queue
from dataclasses import dataclass

import numpy as np
import sounddevice as sd
import webrtcvad


@dataclass
class RecorderSettings:
    sample_rate: int = 16000
    channels: int = 1
    chunk_ms: int = 30
    vad_aggressiveness: int = 2
    min_voice_ms: int = 300
    max_record_ms: int = 10000
    silence_ms: int = 800


class AudioRecorder:
    """Continuously capture audio and cut on silence using WebRTC VAD."""

    def __init__(self, settings: RecorderSettings | None = None, device: int | None = None):
        self.settings = settings or RecorderSettings()
        self.device = device
        self._queue: "queue.Queue[bytes]" = queue.Queue()
        self._stream: sd.InputStream | None = None
        self._vad = webrtcvad.Vad(self.settings.vad_aggressiveness)

    @property
    def sample_rate(self) -> int:
        return self.settings.sample_rate

    def start(self) -> None:
        if self._stream is not None:
            return
        blocksize = int(self.settings.sample_rate * self.settings.chunk_ms / 1000)
        self._stream = sd.InputStream(
            samplerate=self.settings.sample_rate,
            channels=self.settings.channels,
            dtype="float32",
            device=self.device,
            callback=self._callback,
            blocksize=blocksize,
        )
        self._stream.start()

    def stop(self) -> None:
        if self._stream is None:
            return
        self._stream.stop()
        self._stream.close()
        self._stream = None

    def _callback(self, indata, frames, time, status):  # type: ignore[override]
        if status:
            # Ignore buffer warnings to keep the console clean.
            pass
        mono = indata[:, 0]
        audio = (mono * 32767).astype(np.int16).tobytes()
        self._queue.put(audio)

    def read_utterance(self) -> bytes:
        """Read audio until silence and return it as raw PCM16."""
        voiced = bytearray()
        voiced_ms = 0
        silence_ms = 0
        settings = self.settings
        while True:
            chunk = self._queue.get()
            is_speech = self._vad.is_speech(chunk, settings.sample_rate)
            ms = int(len(chunk) / 2 / settings.sample_rate * 1000)
            if is_speech:
                voiced.extend(chunk)
                voiced_ms += ms
                silence_ms = 0
            else:
                silence_ms += ms
            if voiced_ms >= settings.min_voice_ms and silence_ms >= settings.silence_ms:
                break
            if voiced_ms >= settings.max_record_ms:
                break
        return bytes(voiced)
