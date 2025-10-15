# Genio Bot Voice Assistant

En helt ny version av Genio Bot-klienten som från grunden bygger upp flödet:

1. 🎙️ **Spela in tal** via lokal mikrofon
2. ✍️ **Transkribera** med Whisper (faster-whisper)
3. 🌐 **Skicka frågan** till ett n8n-webhookflöde
4. 🔁 **Ta emot svaret** via en webhook från n8n
5. 🔊 **Läs upp** svaret lokalt med Piper TTS

Applikationen körs på servern `https://ai.genio-bot.com` och innehåller ett interaktivt
konfigurationsflöde som guidar dig genom alla steg som krävs för att koppla upp mot n8n.

## 📦 Innehåll

```
Genio-Bot/
├─ README.md
├─ config.example.yaml
├─ requirements.txt
└─ src/
   ├─ app.py                     # huvudprogram med röstloop
   ├─ app_config.py              # dataklasser och hantering av config
   ├─ audio_recorder.py          # mikrofoninspelning + VAD
   ├─ config_flow.py             # interaktiv konfigurationsguide
   ├─ n8n_webhook_client.py      # klient som pratar med n8n-webhooken
   ├─ reply_broker.py            # kopplar ihop frågor och svar
   ├─ reply_server.py            # FastAPI-server för inkommande svar
   ├─ speech_to_text.py          # Whisper STT
   └─ text_to_speech.py          # Piper TTS
```

## 🚀 Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
cp config.example.yaml config.yaml
```

> **Tips:** Glöm inte att ladda ned en svensk Piper-modell och ange sökvägarna i `config.yaml`.

## ⚙️ Konfigurationsflöde

Kör applikationen första gången för att starta guiden:

```bash
python -m src.app --config config.yaml
```

Om `config.yaml` inte finns körs konfigurationsguiden automatiskt. Guiden består av tre steg:

1. Ange adressen till n8n-servern (förifylld med `https://ai.genio-bot.com`).
2. Välj vilken webhook-sökväg i n8n som ska ta emot texten.
3. Få en tydlig sammanställning över vilka inställningar som krävs i n8n:
   - URL och exempelpayload för fråge-webhooken.
   - URL och payload för svarkopplingen tillbaka till appen.
   - Timeout-information så att dina flöden svarar i tid.

Alla val sparas i `config.yaml`.

För att köra konfigurationsguiden igen, använd flaggan `--configure`:

```bash
python -m src.app --configure
```

## ▶️ Användning

Om du redan har en giltig konfiguration startar programmet direkt och lyssnar efter tal:

1. Tala i mikrofonen – röstaktiviteten klipper automatiskt ut ett yttrande.
2. Texten transkriberas lokalt.
3. Text + `conversation_id` skickas som JSON till din n8n-webhook.
4. n8n behandlar frågan och postar svaret till appens webhook (`/api/v1/webhooks/genio-bot-reply`).
5. Appen läser upp svaret med Piper så snart det har kommit fram.

## 🔗 n8n-integration i korthet

| Del | Inställning |
|-----|-------------|
| **Fråge-webhook i n8n** | `POST` mot URL: `<n8n-server>/<text_webhook_path>`<br> Body (JSON): `{ "text": "Hej", "conversation_id": "<uuid>", "callback_url": "https://ai.genio-bot.com/api/v1/webhooks/genio-bot-reply" }` |
| **Svar tillbaka till appen** | `POST` mot `https://ai.genio-bot.com/api/v1/webhooks/genio-bot-reply`<br> Body (JSON): `{ "conversation_id": "<samma uuid>", "reply": "<ditt svar>" }` |

Använd `conversation_id` för att hålla ihop frågan och svaret. Appen väntar upp till det antal sekunder som anges i `app.reply_timeout_s` innan den ger upp.

## 🧪 Testa lokalt

Det går bra att köra programmet i en utvecklingsmiljö. Tänk på att mikrofon, `piper`-kommando och faster-whisper-modellen måste finnas installerade för att hela flödet ska fungera.

## 🆘 Felsökning

- **Ingen text transkriberas:** kontrollera att mikrofonen fungerar och att `sounddevice` har behörighet.
- **Timeout mot n8n:** verifiera att webhook-URL:en stämmer och att n8n-flödet skickar tillbaka svaret till appens webhook.
- **Piper hittar inte modellen:** uppdatera `tts.model_path` och `tts.config_path` i `config.yaml`.

Lycka till med din nya Genio Bot-installation! 🎉
