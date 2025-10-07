import asyncio

# Wyoming-klientbibliotek (PyPI: wyoming)
# Docs/APIs kan variera med version; denna implementering förutsätter grundläggande Transcribe/Transcript-ramar.
from wyoming.client import AsyncTcpClient
from wyoming.asr import Transcribe, Transcript
from wyoming.audio import AudioChunk, AudioStart, AudioStop

class WyomingSTT:
    def __init__(self, host: str = "127.0.0.1", port: int = 10300, language: str = "sv"):
        self.host = host
        self.port = port
        self.language = language

    async def _transcribe_async(self, pcm_bytes: bytes, sample_rate=16000):
        # PCM16 bytes (mono, 16kHz) - no conversion needed, Wyoming expects raw PCM
        
        client = AsyncTcpClient(self.host, self.port)
        await client.connect()
        try:
            # Begär transkribering (språk-hint kan ignoreras av vissa servrar)
            await client.write_event(Transcribe(language=self.language).event())

            # Skicka AudioStart event
            await client.write_event(AudioStart(rate=sample_rate, width=2, channels=1).event())

            # Skicka hela yttrandet som en enda ljudchunk (raw PCM16)
            await client.write_event(AudioChunk(rate=sample_rate, width=2, channels=1, audio=pcm_bytes).event())

            # Skicka AudioStop event
            await client.write_event(AudioStop().event())

            # Vänta på Transcript
            text = ""
            while True:
                msg = await client.read_event()
                if msg is None:
                    break
                if msg.type == Transcript.type:
                    transcript = Transcript.from_event(msg)
                    text = (transcript.text or "").strip()
                    break
            return text
        finally:
            await client.disconnect()

    def transcribe_pcm16(self, pcm_bytes: bytes, sample_rate=16000) -> str:
        return asyncio.run(self._transcribe_async(pcm_bytes, sample_rate))
