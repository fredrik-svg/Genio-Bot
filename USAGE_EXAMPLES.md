# Användningsexempel för Genio-Bot

Detta dokument visar praktiska exempel på hur man använder Genio-Bot med de två olika STT-lägena.

## Läge 1: Lokal STT (Rekommenderat för offline-användning)

### Konfiguration
```yaml
# config.yaml
audio:
  sample_rate: 16000
  channels: 1
  vad:
    enabled: true
    aggressiveness: 2

stt:
  mode: local              # Använd lokal Whisper
  language: sv
  piper:
    model: base            # tiny för snabbast, base för balans, small/medium/large för bättre kvalitet
    device: cpu            # använd "cuda" om du har NVIDIA GPU

tts:
  piper:
    model_path: models/piper/sv-SE_piper.onnx
    config_path: models/piper/sv-SE_piper.onnx.json
    output_wav: /tmp/tts_out.wav

backend:
  n8n_url: "https://ai.genio-bot.com/webhook/text-input"
  timeout_s: 30
```

### Starta
```bash
# Installera dependencies
pip install -r requirements.txt

# Starta satelliten
python src/main.py --config config.yaml
```

### Vad händer
1. 🎤 Du pratar in mikrofonen
2. 🧠 Whisper transkriberar lokalt (på din enhet)
3. 📨 Texten skickas till n8n på `https://ai.genio-bot.com/webhook/text-input`
4. 🤖 n8n processerar med LLM och svarar
5. 🔊 Piper TTS läser upp svaret

### Fördelar
- Fungerar offline (utom n8n-anrop)
- Snabb respons för små modeller
- Inget ljud lämnar din enhet förrän det är transkriberat

### Nackdelar
- Kräver CPU/GPU-resurser
- Första körningen laddar ned modeller (kan ta tid)

---

## Läge 2: Audio Upload (Rekommenderat för låga resurser)

### Konfiguration
```yaml
# config.yaml
audio:
  sample_rate: 16000
  channels: 1
  vad:
    enabled: true
    aggressiveness: 2

stt:
  mode: upload             # Skicka ljud till n8n
  language: sv

tts:
  piper:
    model_path: models/piper/sv-SE_piper.onnx
    config_path: models/piper/sv-SE_piper.onnx.json
    output_wav: /tmp/tts_out.wav

backend:
  n8n_url: "https://ai.genio-bot.com/webhook/text-input"      # används inte i upload-läge
  audio_url: "https://ai.genio-bot.com/webhook/audio-input"   # viktigt!
  timeout_s: 30
```

### Starta
```bash
# Installera dependencies (faster-whisper INTE nödvändigt i detta läge)
pip install PyYAML sounddevice webrtcvad-wheels numpy soundfile requests flask

# Starta satelliten
python src/main.py --config config.yaml
```

### Vad händer
1. 🎤 Du pratar in mikrofonen
2. 📤 Ljudfilen (WAV) skickas direkt till n8n på `https://ai.genio-bot.com/webhook/audio-input`
3. 🧠 n8n kör STT på servern (t.ex. med Whisper, Deepgram, etc.)
4. 🤖 n8n processerar med LLM och svarar
5. 🔊 Piper TTS läser upp svaret

### Fördelar
- Minimal CPU-användning på enheten
- Ingen nedladdning av stora modeller
- Flexibel STT-motor på servern

### Nackdelar
- Kräver snabb internetanslutning
- Ljuddata skickas till servern
- Lite högre latens

---

## n8n Webhook-exempel

### Webhook för text-input (mode: local)
```json
{
  "device": "raspi-5-vardagsrum",
  "text": "Vad är klockan?"
}
```

**Förväntat svar:**
```json
{
  "reply": "Klockan är 14:30"
}
```

### Webhook för audio-input (mode: upload)
**Request:**
- Method: `POST`
- Content-Type: `multipart/form-data`
- Fields:
  - `device`: "raspi-5-vardagsrum"
  - `audio`: WAV-fil (16kHz, mono, 16-bit)

**Förväntat svar:**
```json
{
  "reply": "Klockan är 14:30"
}
```

---

## Docker Compose-exempel

### Med lokal STT
```yaml
version: "3.8"
services:
  satellite:
    build: .
    devices:
      - "/dev/snd:/dev/snd"
    volumes:
      - ./:/app
      - whisper-models:/root/.cache/huggingface
    environment:
      - PYTHONUNBUFFERED=1
      - STT_MODE=local
    command: ["python", "src/main.py", "--config", "config.docker.yaml"]
    restart: unless-stopped

volumes:
  whisper-models:
```

### Med audio upload
```yaml
version: "3.8"
services:
  satellite:
    build: .
    devices:
      - "/dev/snd:/dev/snd"
    volumes:
      - ./:/app
    environment:
      - PYTHONUNBUFFERED=1
      - STT_MODE=upload
    command: ["python", "src/main.py", "--config", "config.docker.yaml"]
    restart: unless-stopped
```

---

## Prestandajämförelse

### Raspberry Pi 4 (4GB RAM)
| Modell | Läge | Svarstid | CPU | RAM |
|--------|------|----------|-----|-----|
| tiny | local | ~1-2s | 25% | 200MB |
| base | local | ~2-3s | 40% | 300MB |
| small | local | ~5-6s | 60% | 500MB |
| - | upload | ~1-2s | 5% | 100MB |

### Raspberry Pi 5 (8GB RAM)
| Modell | Läge | Svarstid | CPU | RAM |
|--------|------|----------|-----|-----|
| tiny | local | ~0.5-1s | 20% | 200MB |
| base | local | ~1-2s | 30% | 300MB |
| small | local | ~2-3s | 45% | 500MB |
| medium | local | ~4-5s | 65% | 1GB |
| - | upload | ~0.5-1s | 5% | 100MB |

*Obs: Svarstiden inkluderar STT men inte n8n/LLM-processering*

---

## Felsökning

### "Modellen laddar inte"
```bash
# Töm cache och försök igen
rm -rf ~/.cache/huggingface
python src/main.py --config config.yaml
```

### "Connection refused till audio_url"
Kontrollera att n8n-servern är tillgänglig:
```bash
curl -X POST https://ai.genio-bot.com/webhook/audio-input
```

### "Långsam transkribering"
1. Byt till mindre modell: `model: tiny`
2. Eller byt till upload-läge: `mode: upload`

### "Inget ljud spelas upp"
```bash
# Testa högtalarna
aplay /usr/share/sounds/alsa/Front_Center.wav

# Kontrollera Piper-konfiguration
cat config.yaml | grep -A5 "tts:"
```

---

## Tips och tricks

### Spara bandwidth med lokal STT
Använd `mode: local` för att minska nätverkstrafik. Endast text skickas till n8n.

### Använd GPU för snabbare STT
```yaml
stt:
  piper:
    device: cuda  # Kräver NVIDIA GPU med CUDA
```

### Dynamisk modellväxling
Du kan byta modell utan omstart genom att ändra config och skicka SIGHUP:
```bash
pkill -HUP -f "python src/main.py"
```

### Blanda lokalt och remote
För maximal effektivitet:
- Använd lokal STT (billigare, snabbare)
- Låt n8n hantera LLM-processeringen
- Använd lokal TTS (Piper)

Detta ger bästa balansen mellan prestanda och kostnad.
