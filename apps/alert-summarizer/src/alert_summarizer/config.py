from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ALERT_", env_file=".env", extra="ignore")

    # Cluster Settings
    cluster_name: str = "homelab-k3s"
    environment: str = "production"

    # LLM & Pydantic AI Settings
    llm_base_url: str = "http://llama-server.llama.svc.cluster.local:8080/v1"
    llm_model: str = "gemma-4-e2b-it"
    llm_timeout_seconds: float = 15.0
    llm_max_tokens: int = 400
    llm_temperature: float = 0.2
    llm_retries: int = 2
    pydantic_ai_no_banner: bool = True

    # Telegram Settings
    telegram_bot_token: SecretStr | None = None
    telegram_bot_token_file: Path | None = Path(
        "/etc/alertmanager/secrets/alertmanager-telegram/token"
    )
    telegram_chat_id: int = 7341944813
    telegram_timeout_seconds: float = 5.0
    telegram_api_url: str = "https://api.telegram.org"

    # Server Settings
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"

    def get_telegram_token(self) -> str:
        if self.telegram_bot_token:
            return self.telegram_bot_token.get_secret_value()
        if self.telegram_bot_token_file and self.telegram_bot_token_file.is_file():
            return self.telegram_bot_token_file.read_text().strip()
        raise ValueError("No Telegram bot token found in environment or secret file")
