"""Text-to-speech helpers built on top of the Piper command line interface."""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Iterable


class PiperTextToSpeech:
    """Run Piper locally and play the resulting waveform."""

    def __init__(self, model_path: str, config_path: str, output_wav: str, playback_cmd: Iterable[str]):
        self.model_path = model_path
        self.config_path = config_path
        self.output_wav = output_wav
        self.playback_cmd = list(playback_cmd)

    def speak(self, text: str) -> None:
        if not text:
            return
        Path(self.output_wav).parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            "piper",
            "-m",
            self.model_path,
            "-c",
            self.config_path,
            "-f",
            self.output_wav,
            "-t",
            text,
        ]
        subprocess.run(cmd, check=True)
        subprocess.run(self.playback_cmd, check=True)
