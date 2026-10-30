"""Configuration and environment settings for Actual Classifier."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Actual Budget Connection
    actual_server_url: str = Field(
        default="http://actual-budget.actual-budget.svc.cluster.local:5006",
        validation_alias="ACTUAL_SERVER_URL",
    )
    actual_password: str = Field(
        default="",
        validation_alias="ACTUAL_PASSWORD",
    )
    actual_budget_name: str = Field(
        default="My Finances",
        validation_alias="ACTUAL_BUDGET_NAME",
    )

    # Classification Behavior
    confidence_threshold: float = Field(
        default=0.6,
        validation_alias="CONFIDENCE_THRESHOLD",
        description=(
            "Minimum confidence score required to auto-classify; below this #Unknown is retained"
        ),
    )
    batch_size: int = Field(
        default=25,
        validation_alias="BATCH_SIZE",
        description="Maximum transactions to classify in one execution run",
    )
