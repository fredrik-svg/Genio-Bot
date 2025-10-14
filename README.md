# raspi-satellite-1

Raspberry Pi 5 “satellit”-klient för röststyrning med **Whisper STT** och **Piper TTS** som pratar med en central server (t.ex. n8n-webhook + LLM-backend).

> **Mål**: Spela in tal → transkribera till text (Whisper STT) → skicka till central LLM via n8n → få textsvar → läsa upp svaret lokalt med Piper.

📚 **Dokumentation:**
- [N8N_INTEGRATION.md](N8N_INTEGRATION.md) - **n8n integration guide med setup wizard** ⭐ **NY**
- [MIGRATION.md](MIGRATION.md) - Migrering från Wyoming till Whisper
- [USAGE_EXAMPLES.md](USAGE_EXAMPLES.md) - Praktiska användningsexempel
- [OPENAI_SETUP.md](OPENAI_SETUP.md) - OpenAI Whisper API integration (för audio upload)

## 📁 Struktur
```
raspi-satellite-1/
├─ README.md
├─ LICENSE
├─ .env.example
├─ config.example.yaml                 # exempel på konfiguration
├─ n8n_config.example.json             # exempel på n8n-konfiguration
├─ config.docker.yaml                  # konfiguration för docker-compose
├─ requirements.txt
├─ docker-compose.yml                  # satellit med lokal STT
├─ Dockerfile                          # för satelliten
├─ systemd/raspi-satellite.service
└─ src/
   ├─ main.py
   ├─ audio.py
   ├─ stt_piper.py
   ├─ tts.py
   ├─ client.py
   ├─ web.py                    # Flask-based web (legacy)
   ├─ web_fastapi.py            # FastAPI web with setup wizard (new)
   ├─ n8n_config.py             # n8n configuration management
   └─ util.py
```

## 🔧 Installation (Pi 5)

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv portaudio19-dev ffmpeg sox alsa-utils
```

```bash
git clone https://github.com/<ditt-konto>/raspi-satellite-1.git
cd raspi-satellite-1
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip wheel
pip install -r requirements.txt
cp .env.example .env
cp config.example.yaml config.yaml
```

### Piper röst (svenska)
Ladda ned en svensk Piper-modell (ONNX + JSON) till `models/piper/` och referera i `config.yaml`.

### STT-konfiguration

Systemet stödjer två lägen för tal-till-text:

#### Läge 1: Lokal STT (mode: local)
STT körs lokalt på enheten med faster-whisper. Detta kräver ingen extern server.

**Fördelar:**
- Ingen beroende på extern server
- Fungerar offline
- Snabbare för små modeller

**Nackdelar:**
- Kräver CPU/GPU-resurser på enheten
- Större modeller kan vara långsamma

**Konfiguration i config.yaml:**
```yaml
stt:
  mode: local
  language: sv
  piper:
    model: base          # tiny, base, small, medium, large
    device: cpu          # cpu eller cuda
```

#### Läge 2: Audio Upload (mode: upload)
Ljudfiler skickas direkt till n8n för STT-processering på servern.

**Fördelar:**
- Minimal CPU-användning på enheten
- STT-processering sker på servern
- Lättare att uppdatera STT-modeller

**Nackdelar:**
- Kräver internetanslutning
- Lite långsammare på grund av uppladdningstid

**Konfiguration i config.yaml:**
```yaml
stt:
  mode: upload
  language: sv

backend:
  audio_url: "https://ai.genio-bot.com/webhook/audio-input"
```

## ▶️ Kör

### Snabbstart

| Metod | Kommando | Konfig | Beskrivning |
|-------|----------|--------|-------------|
| **Docker Compose (rekommenderat)** | `docker-compose up -d` | `config.docker.yaml` | Startar satelliten med lokal STT |
| **Manuellt** | `python src/main.py` | `config.yaml` | Lokal STT eller audio upload |
| **Web Frontend** | `python src/web.py` | `config.yaml` | Textbaserat gränssnitt (inget STT/TTS) |

### Med Docker Compose (rekommenderat)
```bash
docker-compose up -d
```

Detta startar satelliten med lokal Whisper STT. Loggar kan visas med:
```bash
docker-compose logs -f
```

### Manuellt (Python)
```bash
source .venv/bin/activate
python src/main.py --config config.yaml
```

**Obs**: Första gången kan det ta lite tid när Whisper-modellen laddas ned.

### Web Frontend

#### Option 1: FastAPI with Setup Wizard (Rekommenderat)
```bash
source .venv/bin/activate
python src/web_fastapi.py --config config.yaml
```

**Ny funktionalitet:**
- 🚀 Browser-baserad installationsguide på `http://localhost:5000/setup`
- ✅ Automatisk verifiering av n8n-anslutning och webhooks
- 🔑 API-nyckel verifiering för OpenAI
- 📝 Persistent konfigurationshantering (`n8n_config.json`)
- 🔔 Webhook-notiser från n8n workflows
- ⚡ Async HTTP med httpx för bättre prestanda

Se [N8N_INTEGRATION.md](N8N_INTEGRATION.md) för fullständig guide.

#### Option 2: Flask (Legacy)
```bash
source .venv/bin/activate
python src/web.py --config config.yaml
```

Detta startar en enklare webbserver på `http://localhost:5000` där du kan ställa frågor i textform direkt till backend-flödet. Perfekt för testning eller när du inte har tillgång till mikrofon/högtalare.

**Observera**: Web-frontend kräver endast backend-konfiguration och hoppar över STT/TTS/audio-komponenterna.

## 🧪 Flöde

### Röstflöde (main.py)

**Läge 1: Lokal STT (mode: local)**
1) Satelliten spelar in ljud, VAD upptäcker tal.
2) PCM16 transkriberas lokalt med **Whisper** → text.
3) Text POST:as till `backend.n8n_url` → LLM → svarstext tillbaka.
4) **Piper TTS** genererar WAV och spelar upp svaret.

**Läge 2: Audio Upload (mode: upload)**
1) Satelliten spelar in ljud, VAD upptäcker tal.
2) Ljudfilen skickas direkt till `backend.audio_url` → n8n processar → text + LLM → svarstext tillbaka.
3) **Piper TTS** genererar WAV och spelar upp svaret.

### Web Frontend-flöde (web.py)
1) Användaren skriver text i webbgränssnittet.
2) Text POST:as direkt till `backend.n8n_url` → LLM → svarstext tillbaka.
3) Svaret visas i webbgränssnittet.

## ❗ Obs om Python-biblioteket `faster-whisper`
Koden använder paketet **`faster-whisper`** för lokal STT. Detta installeras automatiskt via requirements.txt:
```bash
pip install faster-whisper
```

För GPU-acceleration (CUDA), installera även:
```bash
pip install faster-whisper[gpu]
```

## 🔧 Felsökning

### STT-fel: "Neither faster-whisper nor whisper is installed"

**Fel**: Saknar STT-bibliotek för lokal transkribering.

**Lösning**: Installera faster-whisper:
```bash
pip install faster-whisper
```

Alternativt, använd audio upload-läge istället:
```yaml
stt:
  mode: upload
```

### Audio upload-fel: "audio_url not configured"

Om du använder `mode: upload` men får detta fel, lägg till audio_url i config.yaml:

```yaml
backend:
  audio_url: "https://ai.genio-bot.com/webhook/audio-input"
```

### Långsam STT med stora modeller

Om lokal STT är långsam, prova:
1. Använd en mindre modell (tiny eller base)
2. Byt till audio upload-läge
3. Aktivera GPU-stöd om tillgängligt (device: cuda)

### 404-fel: "Not Found for url: .../webhook/text-input"

**Fel**: n8n-servern returnerar 404 på webhook-endpoints.

**Möjliga orsaker och lösningar**:

1. **n8n-workflow inte importerat**
   - Importera `n8n/wyoming_satellite_llm_reply.json` i n8n (Menu → Import from File)
   - För `mode: upload`, importera även `n8n/audio_input_llm_reply.json`
   - Aktivera workflow i n8n

2. **Gammal workflow används**
   - Den gamla webhooks var `/webhook/wyoming-input`
   - Uppdatera till den nya workflown som använder `/webhook/text-input`
   - Se MIGRATION.md för mer information

3. **Fel URL i config.yaml**
   - Kontrollera att `backend.n8n_url` pekar på rätt server
   - Verifiera att servern är tillgänglig (testa med curl eller webbläsare)

---

## n8n-export

Färdiga n8n-exporter finns i `n8n/`-katalogen:

### 1. Text Input Workflow (Obligatorisk)
**Fil**: `n8n/wyoming_satellite_llm_reply.json`
- Importera i n8n (Menu → Import from File).
- Ändra URL i noden **HTTP Request → LLM** till din LLM-endpoint.
- Exponerar webhook: `/webhook/text-input` för textfrågor
- Används av både `main.py` (mode: local) och `web.py`

### 2. Audio Input Workflow (Valfri - endast för mode: upload)
**Fil**: `n8n/audio_input_llm_reply.json`
- Importera i n8n om du vill använda `mode: upload` i STT-konfigurationen.
- **Använder OpenAI Whisper API** för ljudtranskribering
- Konfigurera OpenAI API-nyckel i n8n credentials (HTTP Header Auth med `Authorization: Bearer sk-...`)
- Ändra URL för **HTTP Request → AI Agent (LLM)** till din LLM-endpoint.
- Exponerar webhook: `/webhook/audio-input` för ljuduppladdning
- Används av `main.py` när `stt.mode: upload`

**Flöde:**
1. Raspberry PI skickar ljudfil till n8n webhook
2. OpenAI Whisper API transkriberar ljudet till text
3. AI Agent (LLM) hanterar frågan
4. Svar skickas tillbaka till Raspberry PI

**OBS**: 
- Kräver OpenAI API-nyckel för Whisper transkribering
- Om du får 404-fel på webhook-endpoints, kontrollera att du har importerat rätt workflow(s) i n8n och att webhook-paths matchar.



### Extra n8n-flöden

- **`n8n/openai_realtime_websocket.json`** – OpenAI Realtime (WebSocket) med GPT-4o-mini. Använder din API-nyckel lagrad i n8n.
- **`n8n/home_assistant_mqtt.json`** – Enkel MQTT-styrning av Home Assistant (standard broker `mqtt://homeassistant.local`).

Importera i n8n (Menu → Import from File) och aktivera vid behov.
