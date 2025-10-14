# n8n Integration Guide

This guide explains how to integrate Genio-Bot with n8n for workflow automation and LLM processing.

## Overview

Genio-Bot uses n8n webhooks to process text and audio queries through customizable workflows. The integration supports:

- **Text webhooks** - Process text queries from the web interface or voice commands
- **Audio webhooks** - Process audio files with OpenAI Whisper API (optional)
- **Webhook notifications** - Receive asynchronous notifications from n8n workflows
- **API key authentication** - Secure communication with n8n and external APIs

## Architecture

```
┌─────────────────┐         ┌──────────────┐         ┌─────────────┐
│   Genio-Bot     │ ─HTTP──>│   n8n        │ ─HTTP──>│  LLM/API    │
│   (FastAPI)     │<─JSON───│  Workflow    │<─JSON───│  Services   │
└─────────────────┘         └──────────────┘         └─────────────┘
       │                            │
       │ Webhook notifications      │
       │<───────────────────────────┘
       │
```

## Setup Wizard

Genio-Bot includes a browser-based installation wizard that guides you through:

1. **Basic Configuration** - Set n8n server URL and webhook paths
2. **Connectivity Verification** - Test connection to n8n server
3. **Webhook Testing** - Verify webhooks are properly configured
4. **API Key Configuration** - Set up authentication (optional)

### Accessing the Setup Wizard

1. Start the FastAPI web frontend:
   ```bash
   python src/web_fastapi.py --config config.yaml
   ```

2. Navigate to `http://localhost:5000/setup` in your browser

3. Follow the step-by-step wizard to configure your n8n integration

## Configuration Files

### n8n_config.json

The setup wizard creates a persistent configuration file:

```json
{
  "n8n_url": "https://ai.genio-bot.com",
  "text_webhook": "/webhook/text-input",
  "audio_webhook": "/webhook/audio-input",
  "api_key": "your-n8n-api-key",
  "openai_api_key": "sk-your-openai-key",
  "timeout_s": 30,
  "configured": true
}
```

**Important Notes**: 
- The `api_key` is used for authenticating with your n8n server
- The `openai_api_key` is stored for verification purposes only - **it is NOT sent to n8n**
- **OpenAI API key must be configured separately in n8n Credentials** (see [OPENAI_SETUP.md](OPENAI_SETUP.md))
- Genio-Bot only sends audio files to n8n; n8n handles the OpenAI Whisper API calls using its own credentials

### config.yaml (Legacy)

For backward compatibility, you can still use `config.yaml`:

```yaml
backend:
  n8n_url: "https://ai.genio-bot.com/webhook/text-input"
  audio_url: "https://ai.genio-bot.com/webhook/audio-input"
  response_key: reply
  timeout_s: 30
  headers:
    Authorization: "Bearer your-api-key"
```

The FastAPI app will use `n8n_config.json` if available, otherwise fall back to `config.yaml`.

## Webhook Endpoints

### 1. Text Input Webhook

**n8n Workflow**: `n8n/wyoming_satellite_llm_reply.json`

**Endpoint**: `/webhook/text-input`

**Request Format**:
```json
{
  "device": "device-name",
  "text": "User's question"
}
```

**Response Format**:
```json
{
  "reply": "LLM response text"
}
```

**Workflow Steps**:
1. Receive text query from Genio-Bot
2. Process query with LLM (OpenAI, local LLM, etc.)
3. Return response to Genio-Bot
4. (Optional) Send notification webhook back to Genio-Bot

### 2. Audio Input Webhook

**n8n Workflow**: `n8n/audio_input_llm_reply.json`

**Endpoint**: `/webhook/audio-input`

**Request Format**: Multipart form data with:
- `audio`: WAV audio file
- `device`: Device name

**Response Format**:
```json
{
  "reply": "LLM response after transcription"
}
```

**Workflow Steps**:
1. Receive audio file from Genio-Bot
2. Transcribe with OpenAI Whisper API
3. Process transcribed text with LLM
4. Return response to Genio-Bot

**Requirements**:
- OpenAI API key configured in n8n
- HTTP Header Auth credential: `Authorization: Bearer sk-...`

## Webhook Notifications (New Feature)

Genio-Bot can receive asynchronous notifications from n8n workflows.

**Endpoint**: `POST /webhook/notification`

**Request Format**:
```json
{
  "event": "workflow_complete",
  "device": "device-name",
  "data": {
    "workflow_id": "123",
    "status": "success",
    "additional_info": {}
  }
}
```

**Supported Events**:
- `workflow_complete` - Workflow finished successfully
- `workflow_error` - Workflow encountered an error
- Custom events defined by your workflows

**Use Cases**:
- Long-running workflow status updates
- Error notifications
- Multi-step workflow progress tracking
- Integration with external services

## API Endpoints

### Configuration Management

#### GET /api/config
Get current n8n configuration (sensitive data masked).

**Response**:
```json
{
  "n8n_url": "https://ai.genio-bot.com",
  "text_webhook": "/webhook/text-input",
  "configured": true,
  "api_key": "***1234"
}
```

#### POST /api/setup
Save new n8n configuration from setup wizard.

**Request**:
```json
{
  "n8n_url": "https://ai.genio-bot.com",
  "text_webhook": "/webhook/text-input",
  "audio_webhook": "/webhook/audio-input",
  "api_key": "optional",
  "openai_api_key": "sk-...",
  "timeout_s": 30
}
```

### Verification Endpoints

#### POST /api/verify-connectivity
Test connection to n8n server.

**Request**:
```json
{
  "url": "https://ai.genio-bot.com",
  "webhook_path": "/webhook/text-input"
}
```

**Response**:
```json
{
  "success": true,
  "reachable": true,
  "status_code": 404,
  "message": "n8n server is reachable"
}
```

#### POST /api/verify-webhook
Test webhook functionality with a real request.

**Request**:
```json
{
  "url": "https://ai.genio-bot.com",
  "webhook_path": "/webhook/text-input"
}
```

**Response**:
```json
{
  "success": true,
  "message": "Webhook is properly configured",
  "response": {"reply": "test response"}
}
```

#### POST /api/verify-apikey
Verify OpenAI API key validity.

**Request**:
```json
{
  "n8n_url": "",
  "openai_api_key": "sk-..."
}
```

**Response**:
```json
{
  "success": true,
  "message": "OpenAI API key is valid"
}
```

## n8n Workflow Configuration

### Text Workflow Setup

1. Import `n8n/wyoming_satellite_llm_reply.json` into n8n
2. Configure the LLM node with your endpoint
3. Activate the workflow
4. Note the webhook URL (e.g., `https://your-n8n.com/webhook/text-input`)

### Audio Workflow Setup (Optional)

1. Import `n8n/audio_input_llm_reply.json` into n8n
2. Create HTTP Header Auth credential in n8n:
   - Name: "OpenAI Whisper"
   - Header: `Authorization`
   - Value: `Bearer sk-your-openai-key`
3. Configure the credential in the Whisper API node
4. Configure the LLM node with your endpoint
5. Activate the workflow

### Adding Notification Webhooks

To send notifications from n8n back to Genio-Bot:

1. Add an HTTP Request node at the end of your workflow
2. Configure:
   - Method: POST
   - URL: `http://your-genio-bot:5000/webhook/notification`
   - Body:
     ```json
     {
       "event": "workflow_complete",
       "device": "{{ $json.device }}",
       "data": {
         "status": "success",
         "workflow_id": "{{ $workflow.id }}"
       }
     }
     ```

## Runtime HTTP Calls

Genio-Bot uses `httpx` for async HTTP communication:

```python
import httpx

async with httpx.AsyncClient(timeout=30.0) as client:
    response = await client.post(
        "https://n8n-server/webhook/text-input",
        json={"device": "device", "text": "query"},
        headers={"Authorization": "Bearer token"}
    )
```

**Benefits of httpx**:
- Async/await support for better performance
- HTTP/2 support
- Connection pooling
- Timeout handling

## Troubleshooting

### 404 Not Found Error

**Problem**: Webhook returns 404

**Solutions**:
1. Verify workflow is imported and activated in n8n
2. Check webhook path matches configuration
3. Ensure n8n is accessible from Genio-Bot server

### Connection Timeout

**Problem**: Requests timeout

**Solutions**:
1. Increase `timeout_s` in configuration
2. Check network connectivity
3. Verify n8n server is running
4. Check firewall rules

### Webhook Verification Failed

**Problem**: Webhook test fails in setup wizard

**Solutions**:
1. Import the correct workflow JSON file
2. Activate the workflow in n8n
3. Test webhook manually with curl:
   ```bash
   curl -X POST https://your-n8n/webhook/text-input \
     -H "Content-Type: application/json" \
     -d '{"device":"test","text":"hello"}'
   ```

### API Key Verification Failed

**Problem**: OpenAI API key verification fails

**Solutions**:
1. Verify key format starts with `sk-`
2. Check key is active in OpenAI dashboard
3. Ensure account has API access enabled
4. Check for billing issues

## Security Best Practices

1. **Use HTTPS** - Always use HTTPS for n8n endpoints in production
2. **API Key Security** - Store API keys securely, use environment variables
3. **Network Security** - Use firewall rules to restrict access
4. **Rate Limiting** - Configure rate limits in n8n
5. **Webhook Validation** - Validate webhook payloads in n8n workflows
6. **Audit Logging** - Enable logging in both n8n and Genio-Bot

## Migration from Flask to FastAPI

If you're upgrading from the Flask-based `web.py`:

1. Install new dependencies:
   ```bash
   pip install fastapi uvicorn httpx
   ```

2. Use the new web_fastapi.py:
   ```bash
   python src/web_fastapi.py --config config.yaml
   ```

3. Run the setup wizard to migrate configuration:
   - Navigate to `http://localhost:5000/setup`
   - Enter your existing n8n settings
   - Complete verification steps

4. Update systemd service if needed:
   ```ini
   ExecStart=/path/to/venv/bin/python src/web_fastapi.py --config config.yaml
   ```

## Example Workflows

### Basic Text Processing

```
Genio-Bot → n8n → OpenAI API → n8n → Genio-Bot
```

### Audio with Transcription

```
Genio-Bot → n8n → Whisper API → LLM → n8n → Genio-Bot
```

### With Notifications

```
Genio-Bot → n8n → LLM → n8n → Genio-Bot
                    ↓
              Notification
                    ↓
              Genio-Bot
```

## Additional Resources

- [n8n Documentation](https://docs.n8n.io/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [httpx Documentation](https://www.python-httpx.org/)
- [OpenAI Whisper API](https://platform.openai.com/docs/guides/speech-to-text)

## Support

For issues and questions:
- Check MIGRATION.md for common migration issues
- Review README.md for general setup
- Check n8n logs for workflow errors
- Review Genio-Bot logs for client errors
