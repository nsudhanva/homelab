"""Data models for transaction classification and schema validation."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class CategoryEnum(StrEnum):
    """Allowed single-word categories in Actual Budget."""

    Food = "Food"
    Bills = "Bills"
    Rent = "Rent"
    Transit = "Transit"
    Shopping = "Shopping"
    Travel = "Travel"
    Medical = "Medical"
    Income = "Income"
    Savings = "Savings"
    Transfer = "Transfer"


class TagEnum(StrEnum):
    """Allowed single-word tags in Actual Budget."""

    Subscription = "Subscription"
    Transit = "Transit"
    Medical = "Medical"
    Travel = "Travel"
    Income = "Income"
    Bills = "Bills"
    Rent = "Rent"
    Transfer = "Transfer"
    Unknown = "Unknown"


class TransactionInput(BaseModel):
    """Raw transaction data from Actual Budget."""

    model_config = ConfigDict(frozen=True)

    id: str
    date: str
    amount_cents: int
    imported_payee: str
    account_name: str
    current_notes: str = ""
    current_category: str | None = None

    @property
    def amount_dollars(self) -> float:
        """Return amount formatted as floating dollar value."""
        return round(self.amount_cents / 100.0, 2)


class ClassificationResult(BaseModel):
    """Strictly constrained output model for the LLM classifier."""

    model_config = ConfigDict(extra="forbid")

    category: CategoryEnum = Field(description="Strict single-word category from the allowed enum")
    tag: TagEnum | None = Field(
        default=None, description="Strict single-word tag from the allowed enum, or null"
    )
    clean_payee: str = Field(
        description="Clean, human-readable standardized merchant or payee name"
    )
    confidence: float = Field(
        ge=0.0, le=1.0, description="Confidence score of classification between 0.0 and 1.0"
    )
    reasoning: str = Field(description="Concise one-sentence rationale for the classification")
