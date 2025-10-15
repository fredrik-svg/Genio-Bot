"""Interactive configuration flow for the Genio Bot application."""
from __future__ import annotations

from pathlib import Path
from typing import Callable

from app_config import AppConfig


class ConfigurationFlow:
    """Simple terminal based configuration wizard."""

    def __init__(self, config_path: Path, input_func: Callable[[str], str] | None = None):
        self.config_path = config_path
        self.input = input_func or input
        self.config = AppConfig.load(config_path)

    def run(self) -> AppConfig:
        print("\n🛠️  Konfigurationsflöde – Genio Bot")
        print("-----------------------------------")
        self._step_server()
        self._step_webhook()
        self._step_summary()
        self.config.save(self.config_path)
        return self.config

    def _ask(self, prompt: str, default: str) -> str:
        value = self.input(f"{prompt} [{default}]: ").strip()
        return value or default

    def _step_server(self) -> None:
        print("\nSteg 1 – n8n-server")
        print(
            "Ange adressen till din n8n-instans. Den förifyllda adressen är "
            "Genio Bot-servern som driftas av Genio."
        )
        server = self._ask("n8n serveradress", self.config.n8n.server_url)
        self.config.n8n.server_url = server

    def _step_webhook(self) -> None:
        print("\nSteg 2 – Inkommande text-webhook")
        print("Här väljer du vilken webhook på n8n som ska ta emot transkriberad text.")
        print("Ange endast sökvägen om du använder serveradressen ovan. Du kan också klistra in en komplett URL.")
        path = self._ask("Sökväg eller URL till n8n-webhook", self.config.n8n.text_webhook_path)
        self.config.n8n.text_webhook_path = path

    def _step_summary(self) -> None:
        print("\nSteg 3 – Instruktioner för n8n")
        question_url = self.config.n8n.question_url()
        reply_url = self.config.app.reply_webhook_url()
        print("Så här kopplar du ihop allt:")
        print("\n1. I din n8n-workflow skapar du en *Webhook* nod för inkommande frågor.")
        print(f"   • Metod: POST\n   • URL: {question_url}\n   • Förväntad body (JSON):")
        print("     {\"text\": \"Hej!\", \"conversation_id\": \"<uuid>\", \"callback_url\": \"" + reply_url + "\"}")
        print("   Denna nod ansvarar för att starta din automation och skicka frågan vidare.")
        print(
            "\n2. När du har genererat ett svar i n8n skickar du det tillbaka till appen "
            "via en *HTTP Request* eller *Webhook*-nod:"
        )
        print(f"   • Metod: POST\n   • URL: {reply_url}\n   • Body (JSON): {{\"conversation_id\": \"<samma uuid>\", \"reply\": \"<svaret>\"}}")
        print("   Sätt Content-Type till application/json. Appen läser upp svaret automatiskt.")
        print(
            "\n3. Se till att svaret från n8n returneras så snart det är klart. Appen "
            f"väntar max {self.config.app.reply_timeout_s} sekunder innan den ger upp."
        )
        print("\nKonfigurationen sparas nu till", self.config_path)
