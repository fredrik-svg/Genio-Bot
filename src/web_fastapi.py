"""
FastAPI-based web frontend with n8n setup wizard.
Includes webhook notifications and configuration management.
"""
import os
import logging
import argparse
from typing import Optional
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import httpx

from util import load_config, setup_logging
from client import BackendClient
from n8n_config import N8nConfig

logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Genio-Bot Web Frontend", version="1.0.0")

# Global state
backend: Optional[BackendClient] = None
device_name: str = ""
n8n_config: Optional[N8nConfig] = None
config: dict = {}

# Templates
import os
template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
templates = Jinja2Templates(directory=template_dir)

# Pydantic models for request/response validation
class AskRequest(BaseModel):
    text: str

class AskResponse(BaseModel):
    reply: str

class SetupRequest(BaseModel):
    n8n_url: str
    text_webhook: Optional[str] = "/webhook/text-input"
    audio_webhook: Optional[str] = "/webhook/audio-input"
    api_key: Optional[str] = ""
    openai_api_key: Optional[str] = ""
    timeout_s: Optional[int] = 30

class WebhookNotification(BaseModel):
    """Model for incoming webhook notifications from n8n"""
    event: str
    device: str
    data: dict

class VerifyRequest(BaseModel):
    url: str
    webhook_path: Optional[str] = "/webhook/text-input"
    api_key: Optional[str] = ""

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Serve the main page or setup wizard based on configuration."""
    if n8n_config and not n8n_config.is_configured():
        return templates.TemplateResponse("setup_wizard.html", {"request": request})
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/setup", response_class=HTMLResponse)
async def setup_page(request: Request):
    """Serve the setup wizard page."""
    return templates.TemplateResponse("setup_wizard.html", {"request": request})

@app.get("/api/config")
async def get_config():
    """Get current n8n configuration (masked sensitive data)."""
    if not n8n_config:
        raise HTTPException(status_code=500, detail="Configuration not initialized")
    return n8n_config.to_dict()

@app.post("/api/setup")
async def save_setup(setup: SetupRequest):
    """Save n8n configuration from setup wizard."""
    if not n8n_config:
        raise HTTPException(status_code=500, detail="Configuration not initialized")
    
    try:
        n8n_config.update(
            n8n_url=setup.n8n_url.rstrip("/"),
            text_webhook=setup.text_webhook,
            audio_webhook=setup.audio_webhook,
            api_key=setup.api_key,
            openai_api_key=setup.openai_api_key,
            timeout_s=setup.timeout_s,
            configured=True
        )
        
        # Reinitialize backend client with new config
        global backend
        backend = BackendClient(
            url=n8n_config.get_text_url(),
            audio_url=n8n_config.get_audio_url(),
            response_key=config.get("backend", {}).get("response_key", "reply"),
            timeout_s=setup.timeout_s,
            headers={"Authorization": f"Bearer {setup.api_key}"} if setup.api_key else {}
        )
        
        logger.info("n8n configuration saved and applied")
        return {"success": True, "message": "Configuration saved successfully"}
    except Exception as e:
        logger.error(f"Failed to save setup: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/verify-connectivity")
async def verify_connectivity(verify: VerifyRequest):
    """Verify connectivity to n8n server."""
    try:
        full_url = verify.url.rstrip("/") + verify.webhook_path
        # Prepare headers with optional API key
        headers = {}
        if verify.api_key:
            headers["Authorization"] = f"Bearer {verify.api_key}"
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Try a HEAD request first, then GET if HEAD is not supported
            try:
                response = await client.head(full_url, headers=headers)
            except httpx.HTTPStatusError:
                response = await client.get(full_url, headers=headers)
            
            # Consider 404, 405 (Method Not Allowed), and 2xx as success
            # 404 means the server is reachable but webhook might not be configured yet
            # 405 means the endpoint exists but doesn't accept HEAD/GET (webhook might need POST)
            if response.status_code in [200, 404, 405] or (200 <= response.status_code < 300):
                return {
                    "success": True, 
                    "reachable": True,
                    "status_code": response.status_code,
                    "message": "n8n server is reachable"
                }
            else:
                return {
                    "success": False,
                    "reachable": True,
                    "status_code": response.status_code,
                    "message": f"Server returned status {response.status_code}"
                }
    except httpx.TimeoutException:
        return {
            "success": False,
            "reachable": False,
            "message": "Timeout: Kontrollera URL och nätverksanslutning"
        }
    except httpx.ConnectError as e:
        error_msg = str(e).lower()
        # Provide user-friendly error messages for common connection issues
        if "errno -5" in error_msg or "no address associated" in error_msg or "name or service not known" in error_msg:
            message = "Kan inte hitta server - kontrollera URL"
        elif "connection refused" in error_msg or "errno 111" in error_msg:
            message = "Anslutning nekad - kontrollera att servern är igång"
        elif "network is unreachable" in error_msg:
            message = "Nätverket är inte nåbart - kontrollera nätverksanslutning"
        else:
            message = f"Kan inte ansluta till server - kontrollera URL och nätverksanslutning"
        
        return {
            "success": False,
            "reachable": False,
            "message": message
        }
    except Exception as e:
        error_msg = str(e)
        # Provide more helpful error messages for common issues
        if "ssl" in error_msg.lower():
            message = f"SSL-certifikatfel - kontrollera att URL:en är korrekt"
        elif "name or service not known" in error_msg.lower() or "nodename nor servname" in error_msg.lower():
            message = "Kan inte hitta server - kontrollera URL"
        else:
            message = f"Anslutningsfel: {error_msg}"
        
        return {
            "success": False,
            "reachable": False,
            "message": message
        }

@app.post("/api/verify-webhook")
async def verify_webhook(verify: VerifyRequest):
    """Verify webhook is properly configured by sending a test request."""
    try:
        full_url = verify.url.rstrip("/") + verify.webhook_path
        test_payload = {
            "device": "setup-wizard",
            "text": "test"
        }
        
        # Prepare headers with optional API key
        headers = {}
        if verify.api_key:
            headers["Authorization"] = f"Bearer {verify.api_key}"
        
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(full_url, json=test_payload, headers=headers)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    # Check if response has expected structure
                    if "reply" in data or "response" in data:
                        return {
                            "success": True,
                            "message": "Webhook fungerar korrekt",
                            "response": data
                        }
                    else:
                        return {
                            "success": False,
                            "message": "Webhook svarade men formatet är oväntat",
                            "response": data
                        }
                except:
                    return {
                        "success": False,
                        "message": "Webhook svarade men inte med giltig JSON"
                    }
            elif response.status_code == 404:
                return {
                    "success": False,
                    "message": "Webhook finns inte (404). Importera workflow i n8n och aktivera det."
                }
            elif response.status_code == 401 or response.status_code == 403:
                return {
                    "success": False,
                    "message": f"Autentiseringsfel ({response.status_code}). Kontrollera API-nyckel."
                }
            else:
                return {
                    "success": False,
                    "message": f"Webhook returnerade status {response.status_code}"
                }
    except httpx.TimeoutException:
        return {
            "success": False,
            "message": "Timeout: Webhook svarar inte (kontrollera att workflow är aktiverat i n8n)"
        }
    except httpx.ConnectError as e:
        error_msg = str(e).lower()
        # Provide user-friendly error messages
        if "errno -5" in error_msg or "no address associated" in error_msg or "name or service not known" in error_msg:
            message = "Kan inte hitta server - kontrollera URL"
        elif "connection refused" in error_msg or "errno 111" in error_msg:
            message = "Anslutning nekad - kontrollera att n8n-servern är igång"
        else:
            message = "Kan inte ansluta till webhook - kontrollera URL och nätverksanslutning"
        
        return {
            "success": False,
            "message": message
        }
    except Exception as e:
        error_msg = str(e)
        if "ssl" in error_msg.lower():
            message = "SSL-certifikatfel - kontrollera att URL:en är korrekt"
        else:
            message = f"Webhook-verifiering misslyckades: {error_msg}"
        
        return {
            "success": False,
            "message": message
        }

@app.post("/api/verify-apikey")
async def verify_apikey(setup: SetupRequest):
    """Verify OpenAI API key (for audio workflow).
    
    Note: This endpoint only verifies the key is valid. The key must be configured
    separately in n8n Credentials. Genio-Bot does NOT send the OpenAI key to n8n;
    it only sends audio files, and n8n handles the OpenAI API communication.
    """
    if not setup.openai_api_key:
        return {
            "success": True,
            "message": "No API key provided - audio workflow will not be available",
            "optional": True
        }
    
    try:
        # Test OpenAI API key by making a simple request
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {setup.openai_api_key}"}
            )
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "message": "OpenAI API key is valid"
                }
            elif response.status_code == 401:
                return {
                    "success": False,
                    "message": "Invalid OpenAI API key"
                }
            else:
                return {
                    "success": False,
                    "message": f"API key verification returned status {response.status_code}"
                }
    except Exception as e:
        return {
            "success": False,
            "message": f"API key verification failed: {str(e)}"
        }

@app.post("/ask")
async def ask(ask_request: AskRequest):
    """Handle text questions."""
    if not backend:
        raise HTTPException(status_code=503, detail="Backend not configured")
    
    try:
        text = ask_request.text.strip()
        if not text:
            raise HTTPException(status_code=400, detail="Empty question")
        
        # Send to backend
        reply = backend.ask(device=device_name, text=text)
        return {"reply": reply}
    except Exception as e:
        logger.error(f"Error in ask endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/webhook/notification")
async def webhook_notification(notification: WebhookNotification):
    """
    Receive webhook notifications from n8n workflows.
    This allows n8n to send asynchronous notifications back to the app.
    """
    try:
        logger.info(f"Received webhook notification: {notification.event} from {notification.device}")
        
        # Handle different notification types
        if notification.event == "workflow_complete":
            logger.info(f"Workflow completed for device {notification.device}")
        elif notification.event == "workflow_error":
            logger.error(f"Workflow error for device {notification.device}: {notification.data}")
        else:
            logger.info(f"Unknown notification event: {notification.event}")
        
        return {"success": True, "message": "Notification received"}
    except Exception as e:
        logger.error(f"Error processing webhook notification: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "configured": n8n_config.is_configured() if n8n_config else False,
        "backend_url": n8n_config.get_text_url() if n8n_config else None
    }

def initialize_app(cfg_path: str):
    """Initialize the application with configuration."""
    global backend, device_name, n8n_config, config
    
    # Load main config
    config = load_config(cfg_path)
    setup_logging(config.get("logging", {}).get("level", "INFO"))
    
    # Initialize n8n configuration
    n8n_config = N8nConfig()
    
    # If n8n is already configured, initialize backend client
    if n8n_config.is_configured():
        backend = BackendClient(
            url=n8n_config.get_text_url(),
            audio_url=n8n_config.get_audio_url(),
            response_key=config.get("backend", {}).get("response_key", "reply"),
            timeout_s=n8n_config.get("timeout_s", 30),
            headers={"Authorization": f"Bearer {n8n_config.get('api_key')}"} if n8n_config.get("api_key") else {}
        )
        logger.info(f"Backend initialized with n8n URL: {n8n_config.get_text_url()}")
    else:
        # Try to use config from config.yaml if available
        be_cfg = config.get("backend", {})
        if be_cfg.get("n8n_url"):
            backend = BackendClient(
                url=be_cfg["n8n_url"],
                audio_url=be_cfg.get("audio_url"),
                response_key=be_cfg.get("response_key", "reply"),
                timeout_s=be_cfg.get("timeout_s", 30),
                headers=be_cfg.get("headers", {})
            )
            logger.info(f"Backend initialized from config.yaml: {be_cfg['n8n_url']}")
        else:
            logger.warning("n8n not configured - setup wizard will be displayed")
    
    device_name = os.uname().nodename

def main(cfg_path: str, host: str = '0.0.0.0', port: int = 5000):
    """Main entry point."""
    import uvicorn
    
    initialize_app(cfg_path)
    
    print(f"🌐 Web frontend (FastAPI) starting on http://{host}:{port}")
    if not n8n_config.is_configured():
        print(f"⚙️  Setup wizard available at http://{host}:{port}/setup")
    
    uvicorn.run(app, host=host, port=port, log_level="info")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='FastAPI web frontend for Genio-Bot')
    parser.add_argument("--config", default="config.yaml", help="Path to configuration file")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=5000, help="Port to listen on")
    args = parser.parse_args()
    main(args.config, args.host, args.port)
