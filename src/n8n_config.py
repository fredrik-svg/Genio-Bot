"""
Persistent n8n configuration handling module.
Manages n8n server settings, webhook URLs, and API credentials.
"""
import json
import os
from pathlib import Path
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class N8nConfig:
    """Handles persistent n8n configuration storage and retrieval."""
    
    def __init__(self, config_path: str = "n8n_config.json"):
        """Initialize configuration handler.
        
        Args:
            config_path: Path to the n8n configuration file
        """
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or return default config."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    logger.info(f"Loaded n8n config from {self.config_path}")
                    return config
            except Exception as e:
                logger.error(f"Failed to load n8n config: {e}")
                return self._default_config()
        return self._default_config()
    
    def _default_config(self) -> Dict[str, Any]:
        """Return default configuration structure."""
        return {
            "n8n_url": "",
            "text_webhook": "/webhook/text-input",
            "audio_webhook": "/webhook/audio-input",
            "api_key": "",  # Used for n8n authentication
            "openai_api_key": "",  # Stored for verification only; must be configured in n8n separately
            "timeout_s": 30,
            "configured": False
        }
    
    def save(self) -> bool:
        """Save current configuration to file.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved n8n config to {self.config_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save n8n config: {e}")
            return False
    
    def update(self, **kwargs) -> bool:
        """Update configuration with new values.
        
        Args:
            **kwargs: Key-value pairs to update in the configuration
            
        Returns:
            True if successful, False otherwise
        """
        self.config.update(kwargs)
        return self.save()
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value.
        
        Args:
            key: Configuration key to retrieve
            default: Default value if key doesn't exist
            
        Returns:
            Configuration value or default
        """
        return self.config.get(key, default)
    
    def get_text_url(self) -> str:
        """Get full text webhook URL."""
        base = self.config.get("n8n_url", "").rstrip("/")
        path = self.config.get("text_webhook", "/webhook/text-input")
        return f"{base}{path}" if base else ""
    
    def get_audio_url(self) -> str:
        """Get full audio webhook URL."""
        base = self.config.get("n8n_url", "").rstrip("/")
        path = self.config.get("audio_webhook", "/webhook/audio-input")
        return f"{base}{path}" if base else ""
    
    def is_configured(self) -> bool:
        """Check if basic configuration is complete."""
        return (
            self.config.get("configured", False) and
            bool(self.config.get("n8n_url", "").strip())
        )
    
    def mark_configured(self, configured: bool = True):
        """Mark configuration as complete or incomplete."""
        self.config["configured"] = configured
        self.save()
    
    def to_dict(self) -> Dict[str, Any]:
        """Return configuration as dictionary (without sensitive data)."""
        safe_config = self.config.copy()
        # Mask sensitive fields
        if safe_config.get("api_key"):
            safe_config["api_key"] = "***" + safe_config["api_key"][-4:] if len(safe_config.get("api_key", "")) > 4 else "***"
        if safe_config.get("openai_api_key"):
            safe_config["openai_api_key"] = "***" + safe_config["openai_api_key"][-4:] if len(safe_config.get("openai_api_key", "")) > 4 else "***"
        return safe_config
