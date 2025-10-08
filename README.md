# raspi-satellite-1

Raspberry Pi 5 “satellit”-klient för röststyrning med **Wyoming STT (Rhasspy)** och **Piper TTS** som pratar med en central server (t.ex. n8n-webhook + LLM-backend).

> **Mål**: Spela in tal → transkribera till text (Wyoming STT) → skicka till central LLM via n8n → få textsvar → läsa upp svaret lokalt med Piper.

## 📁 Struktur
```
raspi-satellite-1/
├─ README.md
├─ LICENSE
├─ .env.example
├─ config.example.yaml
├─ requirements.txt
├─ docker-compose.yml            # valfritt
├─ Dockerfile                    # valfritt
├─ systemd/raspi-satellite.service
└─ src/
   ├─ main.py
   ├─ audio.py
   ├─ stt_wyoming.py
   ├─ tts.py
   ├─ client.py
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

### Wyoming STT-server
Kör en Wyoming STT-tjänst (t.ex. Rhasspy Whisper/DeepSpeech) och exponera `host:port` (standard 10300).

**Viktigt**: Se till att Wyoming STT-servern körs innan du startar satelliten. Om anslutning misslyckas kommer systemet att försöka igen enligt konfigurationen (standard: 3 försök med 1 sekunds mellanrum). Du kan anpassa detta i `config.yaml`:

```yaml
stt:
  wyoming:
    host: 127.0.0.1
    port: 10300
    max_retries: 3      # antal återförsök
    retry_delay: 1.0    # sekunder mellan försök
    timeout: 10.0       # timeout per försök
```

## ▶️ Kör
```bash
source .venv/bin/activate
python src/main.py
```

## 🧪 Flöde
1) Satelliten spelar in ljud, VAD upptäcker tal.
2) PCM16 skickas som yttrande till **Wyoming STT** → text.
3) Text POST:as till `backend.n8n_url` → LLM → svarstext tillbaka.
4) **Piper TTS** genererar WAV och spelar upp svaret.

## ❗ Obs om Python-biblioteket `wyoming`
Koden använder paketet **`wyoming`** (PyPI) som implementerar Wyoming-protokollet. Om paketet saknas:
```bash
pip install wyoming
```
Se Rhasspys/HA-communityns dokumentation om `wyoming` om API:et uppdaterats.

## 🔧 Felsökning

### ConnectionRefusedError / Wyoming STT-anslutning misslyckas

Om du får felmeddelandet `ConnectionRefusedError: [Errno 111] Connect call failed`, kontrollera:

1. **Wyoming STT-servern körs**: Starta din Wyoming STT-tjänst innan satelliten
2. **Rätt host och port**: Kontrollera `stt.wyoming.host` och `stt.wyoming.port` i `config.yaml`
3. **Brandväggsregler**: Se till att porten är öppen och tillgänglig
4. **Serverkonfiguration**: Verifiera att Wyoming-servern lyssnar på rätt adress/port

Systemet försöker automatiskt återansluta vid fel (standard: 3 försök). Du kan anpassa detta i konfigurationen.

---

## n8n-export
En färdig n8n-export finns i `n8n/wyoming_satellite_llm_reply.json`.
- Importera i n8n (Menu → Import from File).
- Ändra URL i noden **HTTP Request → LLM** till din LLM-endpoint.
- Flödet exponerar webhook på `/webhook/wyoming-input`.



### Extra n8n-flöden

- **`n8n/openai_realtime_websocket.json`** – OpenAI Realtime (WebSocket) med GPT-4o-mini. Använder din API-nyckel lagrad i n8n.
- **`n8n/home_assistant_mqtt.json`** – Enkel MQTT-styrning av Home Assistant (standard broker `mqtt://homeassistant.local`).

Importera i n8n (Menu → Import from File) och aktivera vid behov.
