import logging
import subprocess
import tempfile
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

class PiperSTT:
    """
    STT using local faster-whisper or whisper model for transcription.
    This replaces Wyoming STT with a direct local implementation.
    """
    def __init__(self, model: str = "base", language: str = "sv", device: str = "cpu"):
        self.model = model
        self.language = language
        self.device = device
        self._whisper_model = None
        
        try:
            # Try to use faster-whisper first (more efficient)
            from faster_whisper import WhisperModel
            self._whisper_model = WhisperModel(model, device=device, compute_type="int8")
            self._use_faster_whisper = True
            logger.info(f"Loaded faster-whisper model: {model}")
        except ImportError:
            # Fall back to openai-whisper
            try:
                import whisper
                self._whisper_model = whisper.load_model(model)
                self._use_faster_whisper = False
                logger.info(f"Loaded whisper model: {model}")
            except ImportError:
                raise ImportError(
                    "Neither faster-whisper nor whisper is installed. "
                    "Install one of them: pip install faster-whisper OR pip install openai-whisper"
                )
    
    def transcribe_pcm16(self, pcm_bytes: bytes, sample_rate: int = 16000) -> str:
        """
        Transcribe PCM16 audio bytes to text.
        
        Args:
            pcm_bytes: Raw PCM16 audio data (mono, 16-bit)
            sample_rate: Sample rate of the audio (default: 16000)
        
        Returns:
            Transcribed text
        """
        # Save PCM data to a temporary WAV file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
            tmp_path = tmp_file.name
            
        try:
            # Convert PCM16 to WAV using ffmpeg
            self._pcm_to_wav(pcm_bytes, tmp_path, sample_rate)
            
            # Transcribe using whisper
            if self._use_faster_whisper:
                segments, info = self._whisper_model.transcribe(
                    tmp_path,
                    language=self.language,
                    beam_size=5
                )
                text = " ".join([segment.text for segment in segments]).strip()
            else:
                result = self._whisper_model.transcribe(
                    tmp_path,
                    language=self.language
                )
                text = result["text"].strip()
            
            logger.debug(f"Transcribed: {text}")
            return text
            
        finally:
            # Clean up temporary file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    def _pcm_to_wav(self, pcm_bytes: bytes, output_path: str, sample_rate: int):
        """Convert raw PCM16 to WAV file using ffmpeg"""
        cmd = [
            "ffmpeg",
            "-f", "s16le",           # signed 16-bit little-endian
            "-ar", str(sample_rate), # sample rate
            "-ac", "1",              # mono
            "-i", "pipe:0",          # input from stdin
            "-y",                    # overwrite output file
            output_path
        ]
        
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = process.communicate(input=pcm_bytes)
        
        if process.returncode != 0:
            raise RuntimeError(f"ffmpeg failed: {stderr.decode()}")
