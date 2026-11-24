from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    bw_client_id: SecretStr = Field(
        validation_alias="BW_CLIENTID",
        description="Bitwarden personal API key client_id",
    )
    bw_client_secret: SecretStr = Field(
        validation_alias="BW_CLIENTSECRET",
        description="Bitwarden personal API key client_secret",
    )
    bw_password: SecretStr = Field(
        validation_alias="BW_PASSWORD",
        description="Bitwarden master password that unlocks the vault",
    )
    bw_server: str | None = Field(
        default=None,
        validation_alias="BW_SERVER",
        description="Bitwarden server URL. Unset uses the bw CLI default (bitwarden.com)",
    )
    bw_binary: str = Field(
        default="bw",
        validation_alias="BW_BINARY",
        description="Path or name of the Bitwarden CLI binary",
    )
    bw_appdata_dir: str = Field(
        default="/tmp/bitwarden",
        validation_alias="BITWARDENCLI_APPDATA_DIR",
        description="Writable directory for the Bitwarden CLI state",
    )
    bw_timeout_seconds: int = Field(
        default=180,
        gt=0,
        validation_alias="BW_TIMEOUT_SECONDS",
        description="Timeout for one Bitwarden CLI command",
    )
    examples_per_folder: int = Field(
        default=20,
        ge=0,
        validation_alias="EXAMPLES_PER_FOLDER",
        description="Filed items shown to the model as examples for each folder",
    )
    max_items: int = Field(
        default=200,
        gt=0,
        validation_alias="MAX_ITEMS",
        description="Maximum number of items without a folder to file in one run",
    )
    confidence_threshold: float = Field(
        default=0.80,
        ge=0.0,
        le=1.0,
        validation_alias="CONFIDENCE_THRESHOLD",
        description="Filed items below this confidence are listed for review in the summary",
    )
    telegram_bot_token: SecretStr | None = Field(
        default=None,
        validation_alias="TELEGRAM_BOT_TOKEN",
        description="Telegram bot token for the run summary",
    )
    telegram_chat_id: int = Field(
        default=7341944813,
        validation_alias="TELEGRAM_CHAT_ID",
        description="Telegram chat ID for the run summary",
    )
    telegram_topic_id: int | None = Field(
        default=None,
        validation_alias="TELEGRAM_TOPIC_ID",
        description="Optional Telegram forum topic ID",
    )
