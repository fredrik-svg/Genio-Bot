# Migration från Wyoming till Piper/Whisper

Detta dokument beskriver migreringen från Wyoming STT till det nya systemet med lokal Whisper eller audio upload.

## Vad har ändrats?

### Tidigare (Wyoming)
- Krävde separat Wyoming STT-server (rhasspy/wyoming-faster-whisper)
- Satelliten anslöt till servern via TCP på port 10300
- Beroende på wyoming Python-paketet

### Nu (Piper/Whisper)
- **Läge 1 (local)**: Lokal STT med faster-whisper direkt i satelliten
- **Läge 2 (upload)**: Skicka ljudfiler direkt till n8n för processering
- Inget behov av separat STT-server
- Använder faster-whisper Python-paketet istället för wyoming

## Migreringssteg

### 1. Uppdatera dependencies
```bash
pip uninstall wyoming
pip install faster-whisper
```

### 2. Uppdatera config.yaml

**Gamla inställningar:**
```yaml
stt:
  backend: wyoming
  wyoming:
    host: 127.0.0.1
    port: 10300
    max_retries: 3
    retry_delay: 1.0
    timeout: 10.0
  language: sv

backend:
  n8n_url: "http://server:5678/webhook/wyoming-input"
```

**Nya inställningar (lokal STT):**
```yaml
stt:
  mode: local              # Använd lokal Whisper
  language: sv
  piper:
    model: base            # tiny, base, small, medium, large
    device: cpu            # cpu eller cuda

backend:
  n8n_url: "https://ai.genio-bot.com/webhook/text-input"
  audio_url: "https://ai.genio-bot.com/webhook/audio-input"  # för upload-läge
```

**Nya inställningar (audio upload):**
```yaml
stt:
  mode: upload             # Skicka ljud till n8n
  language: sv

backend:
  n8n_url: "https://ai.genio-bot.com/webhook/text-input"
  audio_url: "https://ai.genio-bot.com/webhook/audio-input"
```

### 3. Ta bort Wyoming-server

Om du körde Wyoming STT-server i Docker:
```bash
# Stoppa och ta bort Wyoming-containern
docker stop wyoming-whisper
docker rm wyoming-whisper
docker volume rm genio-bot_whisper-data  # Ta bort gamla data
```

### 4. Uppdatera Docker Compose

Den nya `docker-compose.yml` kräver inte längre Wyoming-servern. Starta om:
```bash
docker-compose down
docker-compose up -d
```

## Fördelar med nya systemet

### Lokal STT (mode: local)
- ✅ Ingen separat server behövs
- ✅ Fungerar offline
- ✅ Snabbare för små modeller
- ✅ Lättare att underhålla
- ⚠️ Kräver mer CPU/GPU på enheten

### Audio Upload (mode: upload)
- ✅ Minimal CPU-användning på enheten
- ✅ STT-processering sker på servern
- ✅ Lättare att uppdatera STT-modeller centralt
- ✅ Stödjer mer avancerad processering på servern
- ⚠️ Kräver internetanslutning
- ⚠️ Lite långsammare på grund av uppladdning

## Val av läge

### Välj "local" om:
- Du vill ha offline-stöd
- Du har tillräckligt med CPU/GPU-resurser
- Du vill ha lägsta möjliga latens

### Välj "upload" om:
- Du vill minimera belastning på enheten
- Du har god internetanslutning
- Du vill ha centraliserad STT-processering

## Felsökning

### "Neither faster-whisper nor whisper is installed"
```bash
pip install faster-whisper
```

### "audio_url not configured"
Lägg till audio_url i config.yaml:
```yaml
backend:
  audio_url: "https://ai.genio-bot.com/webhook/audio-input"
```

### Långsam STT
1. Använd mindre modell (tiny eller base)
2. Byt till audio upload-läge
3. Aktivera GPU-stöd: `device: cuda`

## n8n Webhook-ändringar

Tidigare webhook: `/webhook/wyoming-input`

Nya webhooks:
- **Text**: `/webhook/text-input` (för textfrågor)
- **Audio**: `/webhook/audio-input` (för ljudfiler i upload-läge)

Uppdatera dina n8n-flöden att använda de nya webhook-adresserna.
