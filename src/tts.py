import subprocess
from pathlib import Path

class PiperTTS:
    def __init__(self, model_path: str, config_path: str, output_wav: str, playback_cmd=None):
        self.model_path = model_path
        self.config_path = config_path
        self.output_wav = output_wav
        self.playback_cmd = playback_cmd or ["aplay", "-q", output_wav]

    def synth(self, text: str):
        Path(self.output_wav).parent.mkdir(parents=True, exist_ok=True)
        # piper -m <model.onnx> -c <config.json> -f out.wav -t "text"
        cmd = [
            "piper",
            "-m", self.model_path,
            "-c", self.config_path,
            "-f", self.output_wav,
            "-t", text,
        ]
        subprocess.run(cmd, check=True)
        subprocess.run(self.playback_cmd, check=True)
