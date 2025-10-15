# n8n-integration för nya Genio Bot

Den nya versionen av Genio Bot använder ett mycket enklare webhook-flöde:

```
┌─────────────┐       ┌──────────────┐        ┌────────────┐
│ Genio Bot   │ ─────▶│ n8n-webhook  │ ──────▶│ Din logik  │
│ (STT/TTS)   │       └──────────────┘        └────────────┘
│             │◀───── webhook-svar ◀──────────────┘
└─────────────┘
```

1. Appen spelar in ljud och omvandlar det till text.
2. Texten POST:as till ett n8n-webhookflöde tillsammans med ett `conversation_id` och den URL där appen väntar på svaret.
3. n8n bearbetar frågan (LLM, API, etc.) och postar svaret till appens webhook.
4. Svaret läses upp av Piper TTS.

## Konfiguration i n8n

Utgå från informationen som visas i applikationens konfigurationsflöde (steg 3). Sammanfattning:

### Fråge-webhook

| Inställning | Värde |
|-------------|-------|
| Metod | `POST` |
| URL | `<n8n-server>/<text_webhook_path>` (ex. `https://ai.genio-bot.com/webhook/text-input`) |
| Förväntad body | ```json
{ "text": "Hej!", "conversation_id": "<uuid>", "callback_url": "https://ai.genio-bot.com/api/v1/webhooks/genio-bot-reply" }
``` |

Din workflow bör svara med status 200 så fort frågan tagits emot.

### Skicka svar till appen

När svaret är klart lägger du in en **HTTP Request**-nod med:

| Inställning | Värde |
|-------------|-------|
| Metod | `POST` |
| URL | `https://ai.genio-bot.com/api/v1/webhooks/genio-bot-reply` (eller den URL du har ställt in) |
| Body (JSON) | ```json
{ "conversation_id": "{{$json.conversation_id}}", "reply": "<ditt svar>" }
``` |

Se till att `conversation_id` matchar det värde som kom in via fråge-webhooken.

## Timeout och felhantering

- Appen väntar det antal sekunder som anges i `app.reply_timeout_s` innan den ger upp.
- Skicka gärna felmeddelanden tillbaka i `reply` om något går snett – appen läser även upp dessa.

## Tips

- Om du behöver debugga kan du logga inkommande JSON i n8n för att se exakt vilken payload som skickas.
- `callback_url` skickas alltid med från appen och kan användas om du vill svara till olika instanser av appen.
- För produktion rekommenderas att säkra dina webhooks med autentisering (t.ex. API-nyckel) och uppdatera appens n8n-URL till att inkludera nödvändiga headers.
