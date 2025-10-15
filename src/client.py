import requests
import tempfile
import subprocess
import os

class BackendClient:
    def __init__(self, url: str, response_key: str = "reply", timeout_s: int = 30, headers: dict | None = None, audio_url: str = None):
        self.url = url
        self.audio_url = audio_url  # Separate URL for audio uploads
        self.response_key = response_key
        self.timeout_s = timeout_s
        self.headers = headers or {}

    def ask(self, device: str, text: str) -> str:
        """Send text query to backend"""
        payload = {"device": device, "text": text}
        try:
            r = requests.post(self.url, json=payload, timeout=self.timeout_s, headers=self.headers)
            r.raise_for_status()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                # Check if using test webhook URL
                url_warning = ""
                if "/webhook-test/" in self.url:
                    url_warning = (
                        f"\n"
                        f"⚠️  VARNING: Du använder n8n's TEST-URL (/webhook-test/...)\n"
                        f"   Test-URL fungerar ENDAST vid testning i n8n UI!\n"
                        f"   Lösning: Använd production URL '/webhook/text-input' istället\n"
                        f"   och aktivera workflow i n8n.\n"
                    )
                
                response_hint = ""
                if e.response.text:
                    body = e.response.text.strip()
                    if body:
                        response_hint = f"\nServer-svar: {body}"

                error_msg = (
                    f"❌ 404 Not Found: {self.url}\n"
                    f"{url_warning}"
                    f"\n"
                    f"Möjliga orsaker:\n"
                    f"1. n8n-workflow inte importerat/aktiverat\n"
                    f"   → Importera 'n8n/wyoming_satellite_llm_reply.json' i n8n\n"
                    f"   → AKTIVERA workflow i n8n (klicka 'Active' toggle)\n"
                    f"2. Använder test-URL istället för production-URL\n"
                    f"   → Använd '/webhook/text-input' (INTE '/webhook-test/text-input')\n"
                    f"   → Test-URL fungerar endast vid testning i n8n UI\n"
                    f"3. Fel URL i config.yaml\n"
                    f"   → Kontrollera att 'backend.n8n_url' är korrekt\n"
                    f"4. Gammal workflow används\n"
                    f"   → Den nya webhook-path är '/webhook/text-input'\n"
                    f"\n"
                    f"Se README.md avsnitt '404-fel' för mer hjälp."
                    f"{response_hint}"
                )
                raise requests.exceptions.HTTPError(error_msg, response=e.response) from e
            raise
        data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {"reply": r.text}
        return data.get(self.response_key, "(ingen respons)")
    
    def ask_audio(self, device: str, pcm_bytes: bytes, sample_rate: int = 16000) -> str:
        """Send audio to backend for processing"""
        if not self.audio_url:
            raise ValueError("audio_url not configured in backend settings")
        
        # Convert PCM to WAV
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
            tmp_path = tmp_file.name
        
        try:
            self._pcm_to_wav(pcm_bytes, tmp_path, sample_rate)
            
            # Send as multipart/form-data
            with open(tmp_path, 'rb') as audio_file:
                files = {'audio': ('audio.wav', audio_file, 'audio/wav')}
                data = {'device': device}
                try:
                    r = requests.post(
                        self.audio_url,
                        files=files,
                        data=data,
                        timeout=self.timeout_s,
                        headers=self.headers
                    )
                    r.raise_for_status()
                except requests.exceptions.HTTPError as e:
                    if e.response.status_code == 404:
                        # Check if using test webhook URL
                        url_warning = ""
                        if "/webhook-test/" in self.audio_url:
                            url_warning = (
                                f"\n"
                                f"⚠️  VARNING: Du använder n8n's TEST-URL (/webhook-test/...)\n"
                                f"   Test-URL fungerar ENDAST vid testning i n8n UI!\n"
                                f"   Lösning: Använd production URL '/webhook/audio-input' istället\n"
                                f"   och aktivera workflow i n8n.\n"
                            )
                        
                        response_hint = ""
                        if e.response.text:
                            body = e.response.text.strip()
                            if body:
                                response_hint = f"\nServer-svar: {body}"

                        error_msg = (
                            f"❌ 404 Not Found: {self.audio_url}\n"
                            f"{url_warning}"
                            f"\n"
                            f"Möjliga orsaker:\n"
                            f"1. n8n audio workflow inte importerat/aktiverat\n"
                            f"   → Importera 'n8n/audio_input_llm_reply.json' i n8n\n"
                            f"   → AKTIVERA workflow i n8n (klicka 'Active' toggle)\n"
                            f"   → Konfigurera OpenAI API-nyckel för Whisper\n"
                            f"2. Använder test-URL istället för production-URL\n"
                            f"   → Använd '/webhook/audio-input' (INTE '/webhook-test/audio-input')\n"
                            f"   → Test-URL fungerar endast vid testning i n8n UI\n"
                            f"3. Fel URL i config.yaml\n"
                            f"   → Kontrollera att 'backend.audio_url' är korrekt\n"
                            f"4. mode: upload kräver audio workflow\n"
                            f"   → Den nya webhook-path är '/webhook/audio-input'\n"
                            f"\n"
                            f"Se README.md och MIGRATION.md för mer hjälp."
                            f"{response_hint}"
                        )
                        raise requests.exceptions.HTTPError(error_msg, response=e.response) from e
                    raise
                
            response_data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {"reply": r.text}
            return response_data.get(self.response_key, "(ingen respons)")
            
        finally:
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
