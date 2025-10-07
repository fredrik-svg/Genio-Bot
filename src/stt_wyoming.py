import io
import asyncio
import numpy as np
import soundfile as sf

# Wyoming-klientbibliotek (PyPI: wyoming)
# Docs/APIs kan variera med version; denna implementering förutsätter grundläggande Transcribe/Transcript-ramar.
from wyoming.client import Client
from wyoming.speech import Transcribe, Transcript
from wyoming.audio import AudioChunk

class WyomingSTT:
    def __init__(self, host: str = "127.0.0.1", port: int = 10300, language: str = "sv"):
        self.host = host
        self.port = port
        self.language = language

    async def _transcribe_async(self, pcm_bytes: bytes, sample_rate=16000):
        # Konvertera PCM16 till WAV-bytes (mono, 16kHz)
        pcm = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        buf = io.BytesIO()
        sf.write(buf, pcm, sample_rate, format="WAV")
        buf.seek(0)
        wav_bytes = buf.read()

        client = await Client.connect(self.host, self.port)
        try:
            # Begär transkribering (språk-hint kan ignoreras av vissa servrar)
            await client.write(Transcribe(language=self.language))

            # Skicka hela yttrandet som en enda ljudchunk (WAV)
            await client.write(AudioChunk(wav_bytes))

            # Vänta på Transcript
            text = ""
            while True:
                msg = await client.read()
                if msg is None:
                    break
                if isinstance(msg, Transcript):
                    text = (msg.text or "").strip()
                    break
            return text
        finally:
            await client.close()

    def transcribe_pcm16(self, pcm_bytes: bytes, sample_rate=16000) -> str:
        return asyncio.run(self._transcribe_async(pcm_bytes, sample_rate))
