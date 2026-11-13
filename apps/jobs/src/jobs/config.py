from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="JOBS_", env_file=".env", extra="ignore")

    db_path: Path = Path("jobs.db")
    lookback_years: int = 12
    overlap_days: int = 3
    no_reply_days: int = 14
    ignore_domains: str = "gmail.com,googlemail.com"
    workers: int = 8
    ai_max_calls: int | None = None

    gmail_client_id: str = Field("", validation_alias=AliasChoices("GMAIL_CLIENT_ID"))
    gmail_client_secret: str = Field("", validation_alias=AliasChoices("GMAIL_CLIENT_SECRET"))
    gmail_refresh_token: str = Field("", validation_alias=AliasChoices("GMAIL_REFRESH_TOKEN"))

    @property
    def ignored_domains(self) -> frozenset[str]:
        return frozenset(d.strip().lower() for d in self.ignore_domains.split(",") if d.strip())
