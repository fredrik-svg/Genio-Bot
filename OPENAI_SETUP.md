# OpenAI Whisper Integration - Setup Guide

## Översikt

n8n-flödet för audio upload (`n8n/audio_input_llm_reply.json`) använder nu **OpenAI Whisper API** för att transkribera ljudfiler till text. Detta ger hög kvalitet och pålitlig transkribering utan att behöva hantera egen STT-server.

## Flödesdiagram

```
Raspberry PI → n8n Webhook → OpenAI Whisper API → AI Agent (LLM) → Svar tillbaka till PI
```

### Detaljerat flöde:

1. **HTTP Webhook (Audio Input)** - Tar emot ljudfil från Raspberry PI
2. **Function: Prepare for OpenAI** - Byter namn på binary property från 'audio' till 'file' (OpenAI krav)
3. **HTTP Request → OpenAI Whisper** - Skickar ljudfil till OpenAI för transkribering
4. **Function: Extract Text from OpenAI** - Extraherar transkriberad text från OpenAI-respons
5. **HTTP Request → AI Agent (LLM)** - Skickar text till din LLM för att hantera frågan
6. **Function: Format Reply** - Formaterar svar
7. **Respond to Webhook** - Skickar tillbaka svar till Raspberry PI

## Krav

- n8n installerat och igång
- OpenAI API-nyckel (https://platform.openai.com/api-keys)
- AI Agent/LLM-endpoint för att hantera frågor

## Installation

### 1. Skaffa OpenAI API-nyckel

1. Gå till https://platform.openai.com/api-keys
2. Skapa ett konto om du inte har ett
3. Generera en ny API-nyckel
4. Spara nyckeln säkert (den visas bara en gång)

### 2. Konfigurera n8n Credentials

1. Öppna n8n (t.ex. http://localhost:5678)
2. Gå till **Settings → Credentials**
3. Klicka på **+ Add Credential**
4. Välj **HTTP Header Auth**
5. Fyll i:
   - **Name**: `OpenAI API Key` (eller annat beskrivande namn)
   - **Header Name**: `Authorization`
   - **Header Value**: `Bearer sk-your-api-key-here` (ersätt med din riktiga nyckel)
6. Spara credentials

### 3. Importera workflow

1. I n8n, gå till **Menu → Import from File**
2. Välj filen `n8n/audio_input_llm_reply.json`
3. Klicka på **Import**

### 4. Konfigurera workflow

1. Öppna den importerade workflown
2. Klicka på noden **HTTP Request → OpenAI Whisper**
3. Under **Credentials**, välj din OpenAI API Key credential
4. Klicka på noden **HTTP Request → AI Agent (LLM)**
5. Ändra URL till din LLM-endpoint (t.ex. vLLM, Ollama, OpenAI, etc.)
6. Justera body-parametrar för din LLM om nödvändigt
7. Spara workflown
8. Aktivera workflown (toggle i övre högra hörnet)

### 5. Testa webhook

Webhook-URL kommer att vara: `https://your-n8n-server.com/webhook/audio-input`

Test med curl:
```bash
curl -X POST https://your-n8n-server.com/webhook/audio-input \
  -F "device=test-device" \
  -F "audio=@test_audio.wav"
```

## Konfiguration i config.yaml

För att använda audio upload-läget med OpenAI, konfigurera:

```yaml
stt:
  mode: upload
  language: sv

backend:
  n8n_url: "https://your-n8n-server.com/webhook/text-input"
  audio_url: "https://your-n8n-server.com/webhook/audio-input"
  timeout_s: 30
```

## Kostnad

OpenAI Whisper API tar betalt per sekund audio:
- **Pris**: $0.006 per minut (ca 6 cent per minut)
- Exempel: 10 minuter audio = $0.06

Se aktuella priser på: https://openai.com/api/pricing/

## Fördelar med OpenAI Whisper

✅ Hög transkriberingskvalitet  
✅ Stödjer många språk (inklusive svenska)  
✅ Ingen egen STT-server att underhålla  
✅ Skalbar och pålitlig  
✅ Snabb processering  

## Nackdelar

❌ Kostnad per minut audio  
❌ Kräver internetanslutning  
❌ Ljuddata skickas till OpenAI (integritetsöverväganden)  
❌ Beroende av tredjepartstjänst  

## Alternativ till OpenAI

Om du föredrar att inte använda OpenAI kan du ändra workflow:

1. **Lokal faster-whisper**: Använd `mode: local` istället (kräver ingen server)
2. **Egen Whisper-server**: Byt URL i OpenAI-noden till din egen Whisper-server
3. **Andra STT-tjänster**: Deepgram, AssemblyAI, Google Speech-to-Text, etc.

## Felsökning

### "Unauthorized" fel från OpenAI

- Kontrollera att API-nyckeln är korrekt
- Verifiera att credentials är kopplade till HTTP-noden
- Se till att `Authorization` header används (inte API-Key header)

### "Invalid file format" fel

- OpenAI Whisper stödjer: mp3, mp4, mpeg, mpga, m4a, wav, webm
- Kontrollera att ljudfilen är i rätt format
- Verifiera att filen inte är skadad

### Timeout-fel

- Öka timeout i workflow-noden (default 30s)
- Kontrollera internetanslutning
- Verifiera att OpenAI API är tillgänglig

### Ingen text returneras

- Kontrollera att ljudfilen innehåller tal
- Verifiera att rätt språk är konfigurerat (language: sv)
- Se n8n-loggar för detaljerad felsökning

## Support

- OpenAI API Docs: https://platform.openai.com/docs/guides/speech-to-text
- n8n Documentation: https://docs.n8n.io/
- GitHub Issues: https://github.com/fredrik-svg/Genio-Bot/issues
