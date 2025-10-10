# n8n Workflow Diagram - Audio Input with OpenAI Whisper

## Översikt
Detta är visualisering av flödet i `audio_input_llm_reply.json` som hanterar audio upload från Raspberry PI.

## Flödesdiagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Raspberry PI (Genio-Bot)                              │
│  ┌──────────────────────────────────────────────────────────────┐       │
│  │ 1. Spelar in ljud via mikrofon                                │       │
│  │ 2. VAD (Voice Activity Detection) upptäcker tal               │       │
│  │ 3. Konverterar PCM16 till WAV-fil                             │       │
│  └──────────────────────────────────────────────────────────────┘       │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │ HTTP POST multipart/form-data
                                │ {device: "raspi-5", audio: wav-file}
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                              n8n Workflow                                 │
│                                                                           │
│  ┌────────────────────────────────────────────────────────────┐         │
│  │ 📥 HTTP Webhook (Audio Input)                              │         │
│  │    Webhook: /webhook/audio-input                           │         │
│  │    Tar emot: {device, audio}                               │         │
│  └───────────────────────────┬────────────────────────────────┘         │
│                              │                                           │
│                              ▼                                           │
│  ┌────────────────────────────────────────────────────────────┐         │
│  │ ⚙️  Function: Prepare for OpenAI                           │         │
│  │    Byter namn: binary.audio → binary.file                  │         │
│  │    (OpenAI kräver att filen heter 'file')                  │         │
│  └───────────────────────────┬────────────────────────────────┘         │
│                              │                                           │
│                              ▼                                           │
│  ┌────────────────────────────────────────────────────────────┐         │
│  │ 🎙️  HTTP Request → OpenAI Whisper                          │         │
│  │    POST: https://api.openai.com/v1/audio/transcriptions    │         │
│  │    Body: {model: "whisper-1", language: "sv", file: wav}   │         │
│  │    Auth: Bearer token (OpenAI API Key)                     │         │
│  └───────────────────────────┬────────────────────────────────┘         │
│                              │                                           │
│                              ▼                                           │
│  ┌────────────────────────────────────────────────────────────┐         │
│  │ 📝 Function: Extract Text from OpenAI                      │         │
│  │    Input: {text: "transkriberad text"}                     │         │
│  │    Output: {text: "...", device: "raspi-5"}                │         │
│  └───────────────────────────┬────────────────────────────────┘         │
│                              │                                           │
│                              ▼                                           │
│  ┌────────────────────────────────────────────────────────────┐         │
│  │ 🤖 HTTP Request → AI Agent (LLM)                           │         │
│  │    POST: https://your-llm-server.com/api/generate          │         │
│  │    Body: {prompt: "Svara kort... [text]"}                  │         │
│  └───────────────────────────┬────────────────────────────────┘         │
│                              │                                           │
│                              ▼                                           │
│  ┌────────────────────────────────────────────────────────────┐         │
│  │ 💬 Function: Format Reply                                  │         │
│  │    Extraherar svar från LLM-respons                        │         │
│  │    Output: {reply: "svar från AI"}                         │         │
│  └───────────────────────────┬────────────────────────────────┘         │
│                              │                                           │
│                              ▼                                           │
│  ┌────────────────────────────────────────────────────────────┐         │
│  │ 📤 Respond to Webhook                                      │         │
│  │    Returnerar: {reply: "svar från AI"}                     │         │
│  └────────────────────────────────────────────────────────────┘         │
│                                                                           │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │ HTTP Response JSON
                                │ {reply: "svar från AI"}
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    Raspberry PI (Genio-Bot)                              │
│  ┌──────────────────────────────────────────────────────────────┐       │
│  │ 1. Tar emot svar från n8n                                     │       │
│  │ 2. Skickar text till Piper TTS                                │       │
│  │ 3. Genererar WAV-fil                                          │       │
│  │ 4. Spelar upp svaret via högtalare                            │       │
│  └──────────────────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────────────────┘
```

## Node-detaljer

### 1. HTTP Webhook (Audio Input)
- **Typ**: Webhook Trigger
- **Path**: `/webhook/audio-input`
- **Input**: `multipart/form-data` med `device` och `audio` (WAV-fil)
- **Syfte**: Ta emot ljudfiler från Raspberry PI

### 2. Function: Prepare for OpenAI
- **Typ**: Function Node
- **Syfte**: Byta namn på binary property från `audio` till `file`
- **Kod**: 
  ```javascript
  const item = items[0];
  if (item.binary && item.binary.audio) {
    item.binary.file = item.binary.audio;
    delete item.binary.audio;
  }
  return items;
  ```
- **Varför**: OpenAI API förväntar sig att filen heter `file`, inte `audio`

### 3. HTTP Request → OpenAI Whisper
- **Typ**: HTTP Request Node
- **Method**: POST
- **URL**: `https://api.openai.com/v1/audio/transcriptions`
- **Auth**: HTTP Header Auth (Bearer token)
- **Body**: 
  - `model`: `whisper-1`
  - `language`: `sv`
  - `file`: WAV-fil (binary)
- **Response**: `{"text": "transkriberad text"}`
- **Syfte**: Transkribera ljudfil till text med OpenAI Whisper

### 4. Function: Extract Text from OpenAI
- **Typ**: Function Node
- **Input**: OpenAI Whisper response
- **Output**: `{text: "...", device: "..."}`
- **Kod**:
  ```javascript
  const d = items[0].json || {};
  let text = d.text || "";
  if (!text) {
    throw new Error("Ingen text från OpenAI Whisper");
  }
  const device = $('HTTP Webhook (Audio Input)').first().json.device || 'unknown';
  return [{ json: { text, device } }];
  ```
- **Syfte**: Extrahera text och bevara device-information

### 5. HTTP Request → AI Agent (LLM)
- **Typ**: HTTP Request Node
- **Method**: POST
- **URL**: `https://your-llm-server.com/api/generate` (konfigurerbar)
- **Body**: `{prompt: "Svara kort... [text]"}`
- **Response**: Varierar beroende på LLM (vLLM, Ollama, OpenAI, etc.)
- **Syfte**: Hantera frågan och generera svar med AI Agent

### 6. Function: Format Reply
- **Typ**: Function Node
- **Syfte**: Extrahera svar från olika LLM-format
- **Output**: `{reply: "svar"}`
- **Kod**:
  ```javascript
  const d = items[0].json || {};
  let reply = d.reply || d.text || d.choices?.[0]?.message?.content || 
              d.choices?.[0]?.text || "Jag är osäker, kan du omformulera?";
  return [{ json: { reply } }];
  ```

### 7. Respond to Webhook
- **Typ**: Respond to Webhook Node
- **Response**: `{reply: "svar från AI"}`
- **Syfte**: Skicka tillbaka svaret till Raspberry PI

## Datablöde

### Input (från Raspberry PI)
```json
{
  "device": "raspi-5-vardagsrum",
  "audio": "<binary WAV data>"
}
```

### Efter PrepareForOpenAI
```json
{
  "device": "raspi-5-vardagsrum",
  "file": "<binary WAV data>"
}
```

### Efter OpenAI Whisper
```json
{
  "text": "Vad är klockan?"
}
```

### Efter Extract Text
```json
{
  "text": "Vad är klockan?",
  "device": "raspi-5-vardagsrum"
}
```

### Efter AI Agent (LLM)
```json
{
  "reply": "Klockan är 14:30"
}
```

### Output (till Raspberry PI)
```json
{
  "reply": "Klockan är 14:30"
}
```

## Tidsflöde (Uppskattad latens)

```
Total tid: ~2-5 sekunder (beroende på ljudlängd och LLM)

├─ Raspberry PI → n8n:           ~100-300ms (nätverkslatens)
├─ OpenAI Whisper transkribering: ~500-2000ms (beroende på ljudlängd)
├─ AI Agent (LLM) processering:   ~500-2000ms (beroende på modell)
└─ n8n → Raspberry PI:           ~100-300ms (nätverkslatens)
```

## Felhantering

Varje nod har inbyggd felhantering:
- **OpenAI Whisper**: Kastar fel om ingen text returneras
- **Extract Text**: Validerar att text finns
- **Format Reply**: Fallback till standardsvar om inget svar från LLM

## Säkerhet

- ✅ OpenAI API-nyckel lagras säkert i n8n credentials
- ✅ HTTPS för all kommunikation
- ⚠️  Ljuddata skickas till OpenAI (integritetsöverväganden)

## Kostnadsuppskattning

### OpenAI Whisper API
- **Pris**: $0.006 per minut audio
- **Exempel**: 
  - 5 sekunders fråga = $0.0005
  - 1 minuts inspelning = $0.006
  - 100 frågor/dag (5s vardera) = $0.05/dag = $1.50/månad

Se [OPENAI_SETUP.md](../OPENAI_SETUP.md) för mer information om kostnader.
