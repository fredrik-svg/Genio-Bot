# GitHub Copilot Instructions for Genio-Bot

## Project Overview

Genio-Bot is a Raspberry Pi 5 satellite voice control client that uses **Whisper STT** (Speech-to-Text) and **Piper TTS** (Text-to-Speech) to communicate with a central server (n8n webhook + LLM backend).

**Project Goal**: Record speech → transcribe to text (Whisper STT) → send to central LLM via n8n → receive text response → play response locally with Piper.

## Technology Stack

- **Language**: Python 3
- **STT**: faster-whisper (local) or OpenAI Whisper API (upload mode)
- **TTS**: Piper TTS
- **Web Framework**: FastAPI (new), Flask (legacy)
- **Audio**: sounddevice, webrtcvad-wheels
- **HTTP Client**: httpx (async), requests
- **Configuration**: YAML-based
- **Deployment**: Docker, systemd service

## Code Style Guidelines

### Python
- Follow PEP 8 conventions
- Use type hints where appropriate
- Use async/await for HTTP requests (prefer httpx over requests)
- Keep functions focused and modular
- Use logging instead of print statements

### Documentation
- All documentation is in Swedish (Svenska)
- Keep existing documentation style and language
- Use clear, concise language
- Include practical examples where relevant

### Configuration
- Configuration files use YAML format (config.yaml)
- Support both legacy config.yaml and new n8n_config.json
- Always validate configuration before use
- Provide example configuration files (*.example.yaml, *.example.json)

## Project Structure

```
/
├── src/                    # Python source code
│   ├── main.py            # Main entry point
│   ├── audio.py           # Audio stream handling
│   ├── stt_piper.py       # Speech-to-text (local and upload modes)
│   ├── tts.py             # Text-to-speech with Piper
│   ├── client.py          # Backend client (n8n communication)
│   ├── web_fastapi.py     # FastAPI web interface (new)
│   ├── web.py             # Flask web interface (legacy)
│   ├── n8n_config.py      # n8n configuration management
│   └── util.py            # Utilities
├── templates/             # HTML templates for web UI
├── n8n/                   # n8n workflow exports
├── systemd/               # systemd service files
├── *.md                   # Documentation files (in Swedish)
└── config files
```

## Key Features to Understand

### STT Modes
1. **Local Mode** (`mode: local`): Uses faster-whisper locally for offline operation
2. **Upload Mode** (`mode: upload`): Sends audio to n8n, which uses OpenAI Whisper API

### n8n Integration
- Two main workflows: text-input and audio-input
- Configuration via setup wizard at `/setup`
- API authentication via headers
- Webhook notifications support

### Configuration Management
- Primary: `n8n_config.json` (created by setup wizard)
- Legacy: `config.yaml` (backward compatibility)
- FastAPI app prefers n8n_config.json, falls back to config.yaml

## Development Guidelines

### Adding New Features
1. Maintain backward compatibility with existing configurations
2. Update both English and Swedish documentation
3. Support both STT modes (local and upload)
4. Add examples to USAGE_EXAMPLES.md if relevant
5. Update setup wizard if configuration changes are needed

### API Changes
- Always preserve existing API endpoints
- Add new endpoints rather than modifying existing ones
- Document API changes in N8N_INTEGRATION.md

### Error Handling
- Use appropriate logging levels (INFO, WARNING, ERROR)
- Provide clear, actionable error messages
- Include troubleshooting steps in documentation (Felsökning section)

### Testing
- Test both local and upload STT modes
- Verify Docker deployment works
- Test setup wizard functionality
- Validate n8n webhook integration

## Common Patterns

### Configuration Loading
```python
from util import load_config
cfg = load_config("config.yaml")
```

### HTTP Requests (prefer async)
```python
import httpx
async with httpx.AsyncClient() as client:
    response = await client.post(url, json=data, timeout=30)
```

### Logging
```python
import logging
logger = logging.getLogger(__name__)
logger.info("Message here")
```

## Important Notes

- **OpenAI API Key**: Configured in n8n credentials, NOT in Genio-Bot
- **n8n Communication**: Genio-Bot only sends data to n8n; n8n handles external API calls
- **Language**: All user-facing documentation must be in Swedish
- **Audio Processing**: Support both real-time streaming and file upload
- **Web UI**: FastAPI is the new standard, but Flask is kept for backward compatibility

## Security Considerations

- Never hardcode API keys
- Use environment variables or secure configuration files
- Validate all user inputs
- Use HTTPS for production n8n endpoints
- Implement proper authentication for webhooks
- Follow security best practices in N8N_INTEGRATION.md

## Documentation Files

- **README.md**: Main project overview (Swedish)
- **N8N_INTEGRATION.md**: n8n setup and integration guide
- **OPENAI_SETUP.md**: OpenAI Whisper API integration guide
- **MIGRATION.md**: Migration from Wyoming to Whisper
- **USAGE_EXAMPLES.md**: Practical usage examples

## When Making Changes

1. Consider impact on both Docker and manual deployment
2. Update relevant documentation files
3. Test with both STT modes if audio-related
4. Verify setup wizard still works for new configurations
5. Check backward compatibility with existing configs
6. Update example configuration files if needed
