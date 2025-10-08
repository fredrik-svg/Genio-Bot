import asyncio
import logging
from typing import Optional

# Wyoming-klientbibliotek (PyPI: wyoming)
# Docs/APIs kan variera med version; denna implementering förutsätter grundläggande Transcribe/Transcript-ramar.
from wyoming.client import AsyncTcpClient
from wyoming.asr import Transcribe, Transcript
from wyoming.audio import AudioChunk, AudioStart, AudioStop

logger = logging.getLogger(__name__)

class WyomingSTT:
    def __init__(self, host: str = "127.0.0.1", port: int = 10300, language: str = "sv", 
                 max_retries: int = 3, retry_delay: float = 1.0, timeout: float = 10.0):
        self.host = host
        self.port = port
        self.language = language
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout

    async def _transcribe_async(self, pcm_bytes: bytes, sample_rate=16000) -> str:
        # PCM16 bytes (mono, 16kHz) - no conversion needed, Wyoming expects raw PCM
        
        last_error: Optional[Exception] = None
        
        for attempt in range(self.max_retries):
            try:
                client = AsyncTcpClient(self.host, self.port)
                
                # Add timeout to connection attempt
                await asyncio.wait_for(client.connect(), timeout=self.timeout)
                
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
                        msg = await asyncio.wait_for(client.read_event(), timeout=self.timeout)
                        if msg is None:
                            break
                        if msg.type == Transcript.type:
                            transcript = Transcript.from_event(msg)
                            text = (transcript.text or "").strip()
                            break
                    return text
                finally:
                    await client.disconnect()
                    
            except (ConnectionRefusedError, OSError) as e:
                last_error = e
                logger.warning(
                    f"Wyoming STT connection failed (attempt {attempt + 1}/{self.max_retries}): "
                    f"Cannot connect to {self.host}:{self.port}. "
                    f"Please ensure Wyoming STT server is running."
                )
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
            except asyncio.TimeoutError as e:
                last_error = e
                logger.warning(
                    f"Wyoming STT timeout (attempt {attempt + 1}/{self.max_retries}): "
                    f"Connection to {self.host}:{self.port} timed out after {self.timeout}s."
                )
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
            except Exception as e:
                last_error = e
                logger.error(f"Unexpected error during Wyoming STT transcription: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
        
        # All retries exhausted
        error_msg = (
            f"Failed to connect to Wyoming STT server at {self.host}:{self.port} "
            f"after {self.max_retries} attempts. "
            f"Please check that:\n"
            f"  1. The Wyoming STT server is running\n"
            f"  2. The server is accessible at {self.host}:{self.port}\n"
            f"  3. There are no firewall issues\n"
            f"Last error: {last_error}"
        )
        raise ConnectionError(error_msg) from last_error

    def transcribe_pcm16(self, pcm_bytes: bytes, sample_rate=16000) -> str:
        return asyncio.run(self._transcribe_async(pcm_bytes, sample_rate))
