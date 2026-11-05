"""Runtime settings loaded from environment variables."""

from pathlib import Path
from zoneinfo import ZoneInfo

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_CATALOG = Path(__file__).resolve().parents[2] / "catalog.yaml"


class Settings(BaseSettings):
    """Settings for the sync job and the web dashboard."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    actual_server_url: str = Field(
        default="http://actual-budget.actual-budget.svc.cluster.local:5006",
        validation_alias="ACTUAL_SERVER_URL",
    )
    actual_password: str = Field(default="", validation_alias="ACTUAL_PASSWORD")
    actual_budget_name: str = Field(default="My Finances", validation_alias="ACTUAL_BUDGET_NAME")
    bank_sync: bool = Field(
        default=False,
        validation_alias="OFFERS_BANK_SYNC",
        description="Run the Actual bank sync before reading transactions",
    )
    lookback_days: int | None = Field(
        default=None,
        ge=1,
        validation_alias="OFFERS_LOOKBACK_DAYS",
        description="Days of history to read. Empty reads every transaction in Actual",
    )

    catalog_path: Path = Field(default=DEFAULT_CATALOG, validation_alias="OFFERS_CATALOG_PATH")
    db_path: Path = Field(default=Path("offers.db"), validation_alias="OFFERS_DB_PATH")
    timezone: str = Field(default="America/Los_Angeles", validation_alias="OFFERS_TIMEZONE")
    public_url: str = Field(
        default="https://offers.sudhanva.me", validation_alias="OFFERS_PUBLIC_URL"
    )

    ai_enabled: bool = Field(default=True, validation_alias="OFFERS_AI_ENABLED")
    ai_confidence_threshold: float = Field(
        default=0.85, ge=0.0, le=1.0, validation_alias="OFFERS_AI_CONFIDENCE_THRESHOLD"
    )
    ai_max_calls: int = Field(default=40, ge=0, validation_alias="OFFERS_AI_MAX_CALLS")
    ai_max_merchants: int = Field(default=200, ge=0, validation_alias="OFFERS_AI_MAX_MERCHANTS")

    telegram_bot_token: str = Field(default="", validation_alias="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: str = Field(default="", validation_alias="TELEGRAM_CHAT_ID")
    reminder_days: int = Field(default=5, ge=1, validation_alias="OFFERS_REMINDER_DAYS")

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)

    @property
    def telegram_enabled(self) -> bool:
        return bool(self.telegram_bot_token and self.telegram_chat_id)
