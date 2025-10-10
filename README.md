# raspi-satellite-1

Raspberry Pi 5 “satellit”-klient för röststyrning med **Whisper STT** och **Piper TTS** som pratar med en central server (t.ex. n8n-webhook + LLM-backend).

> **Mål**: Spela in tal → transkribera till text (Whisper STT) → skicka till central LLM via n8n → få textsvar → läsa upp svaret lokalt med Piper.

## 📁 Struktur
```
raspi-satellite-1/
├─ README.md
├─ LICENSE
├─ .env.example
├─ config.example.yaml                 # exempel på konfiguration
├─ config.docker.yaml                  # konfiguration för docker-compose
├─ requirements.txt
├─ docker-compose.yml                  # båda tjänsterna (STT + satellit)
├─ docker-compose.wyoming-only.yml     # endast STT-server
├─ Dockerfile                          # för satelliten
├─ systemd/raspi-satellite.service
└─ src/
   ├─ main.py
   ├─ audio.py
   ├─ stt_piper.py
   ├─ tts.py
   ├─ client.py
   ├─ web.py
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
| **Docker Compose (rekommenderat)** | `docker-compose up -d` | `config.docker.yaml` | Startar både STT-server och satellit |
| **Endast STT-server** | `docker-compose -f docker-compose.wyoming-only.yml up -d` | - | STT-server på port 10300 |
| **Manuellt** | `python src/main.py` | `config.yaml` | Kräver separat STT-server |
| **Web Frontend** | `python src/web.py` | `config.yaml` | Textbaserat gränssnitt (inget STT/TTS) |

### Med Docker Compose (rekommenderat)
```bash
docker-compose up -d
```

Detta startar både Whisper STT-servern och satelliten. Loggar kan visas med:
```bash
docker-compose logs -f
```

### Manuellt (Python)
```bash
# Starta Whisper STT-server först
docker-compose -f docker-compose.wyoming-only.yml up -d

# Sedan starta satelliten
source .venv/bin/activate
python src/main.py
```

### Web Frontend
Om du vill använda en textbaserad frontend istället för röstinmatning:

```bash
source .venv/bin/activate
python src/web.py --config config.yaml
```

Detta startar en webbserver på `http://localhost:5000` där du kan ställa frågor i textform direkt till backend-flödet. Perfekt för testning eller när du inte har tillgång till mikrofon/högtalare.

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

---

## n8n-export
En färdig n8n-export finns i `n8n/wyoming_satellite_llm_reply.json`.
- Importera i n8n (Menu → Import from File).
- Ändra URL i noden **HTTP Request → LLM** till din LLM-endpoint.
- Flödet exponerar webhooks:
  - `/webhook/text-input` för textfrågor
  - `/webhook/audio-input` för ljudfiler (om mode: upload)



### Extra n8n-flöden

- **`n8n/openai_realtime_websocket.json`** – OpenAI Realtime (WebSocket) med GPT-4o-mini. Använder din API-nyckel lagrad i n8n.
- **`n8n/home_assistant_mqtt.json`** – Enkel MQTT-styrning av Home Assistant (standard broker `mqtt://homeassistant.local`).

Importera i n8n (Menu → Import from File) och aktivera vid behov.
