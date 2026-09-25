"""Transaction classifier powered by local LLM and homelab-ai routing."""

import logging

from pydantic_ai import Agent

from actual_classifier.config import Settings
from actual_classifier.models import (
    CategoryEnum,
    ClassificationResult,
    TagEnum,
    TransactionInput,
)
from homelab_ai import ModelRouter

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert personal finance classifier for Sudhanva and Maanasa.
Given a raw financial transaction, classify it accurately according to the household rules below.

### 1. Categories (Strict Single-Word Choice)
- Food: Supermarkets, groceries, farmers markets, bakeries, cafes, restaurants, dining out
  (e.g. Apni Mandi, Whole Foods, Murugan Cafe, Safeway, Chipotle, Idly Express, Starbucks).
- Transit: Rideshares (Lyft, Uber, Waymo), car rentals (Flexcar, Avis), parking (SFO, street),
  transit cards (Clipper, MTA), gas (Chevron, Speedway).
- Shopping: Retail goods, apparel, tech devices, online orders (Amazon, Target, Costco, Uniqlo,
  Google Store hardware purchases).
- Bills: Utilities, home internet (Comcast), phone (T-Mobile), electricity/gas (PG&E, Eversource),
  and software subscriptions.
- Rent: Apartment lease payments to property management (Ironworks).
- Travel: Vacations, flights, hotels, tourist attractions (Summit One Vanderbilt, Niagara Falls,
  Maid of the Mist), travel insurance.
- Medical: Urgent care, clinics, doctors, therapy (Gfit Googler Sessions, physical therapy),
  prescriptions and pharmacies (CVS, Walgreens).
- Income: Salary/payroll deposits (Google LLC, Montai Therapeutics), HYSA interest, stock dividends.
- Savings: Investment purchases, transfers to brokerage.
- Transfer: Credit card statement payments, inter-account transfers, Zelle, Wise, checks.

### Amount Sign
- Negative amounts are money leaving the account (purchases, bills, payments).
- Positive amounts are money entering the account (salary, interest, refunds, incoming transfers).
- A positive amount from a merchant is a refund or credit: use that merchant's category,
  not Income.

### 2. Tags (Strict Single-Word Choice, or Null)
- Subscription: Any recurring software, streaming, telecom, or membership service
  (Disney+, Paramount+, Cloudflare, LeetCode, Pikapods, Apple Services, Oracle Cloud, Comcast,
  T-Mobile, Fox One, Amex Gold Annual Fee, Robinhood Gold).
- Transit: Applied to all transit and mobility expenses.
- Medical: Applied to healthcare, therapy, and pharmacy.
- Travel: Applied to tourism, attractions, and vacation expenses.
- Income: Applied to salary, interest, and dividend inflows.
- Bills: Applied to non-subscription utilities (PG&E, Eversource).
- Rent: Applied to Ironworks apartment payments.
- Transfer: Applied to credit card payments and bank transfers.
- Unknown: Only use when you cannot determine the category itself.
- Use null when none of the tags above apply. Groceries, restaurants, and general shopping
  normally have a null tag. Never use Unknown just because no tag fits.

### 3. Clean Payee Normalization
- Strip out terminal codes, POS prefixes (e.g., TST*, SQ *, CL *), transaction locations,
  and zip codes.
- Examples:
  - "TST*IDLY EXPRESS - MOUNT" -> "Idly Express"
  - "SQ *ANDERSEN BAKERY - GRE" -> "Andersen Bakery"
  - "ACH Withdrawal COMCAST-XFINITY CABLE SVCS" -> "Comcast"
  - "DISNEY PLUS 500 SOUTH BUENA VISTA 8889057888 CA" -> "Disney+"
  - "60775 - SFO PARKING IT-G" -> "Park SFO"
  - "AVIS.COM PREPAY" -> "Avis"
  - "PAYAL BROW ARC BEAUTY SA" -> "Brow Arc"

Return strict JSON matching the schema with category, tag, clean_payee, confidence, and reasoning.
"""


class TransactionClassifier:
    """Classifies transactions using local LLM inference with fallback routing."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.router = ModelRouter(settings.to_llm_client_config())
        self.agent: Agent[None, ClassificationResult] = self.router.create_agent(
            output_type=ClassificationResult,
            system_prompt=SYSTEM_PROMPT,
        )

    def classify(self, tx: TransactionInput) -> ClassificationResult:
        """Classify a single transaction with guardrails."""
        prompt = (
            f"Account: {tx.account_name}\n"
            f"Amount: ${tx.amount_dollars:.2f}\n"
            f"Raw Description: {tx.imported_payee}\n"
            f"Current Notes: {tx.current_notes}"
        )

        try:
            result = self.agent.run_sync(prompt)
            output = result.output

            # Guardrail: Check confidence threshold
            if output.confidence < self.settings.confidence_threshold:
                logger.warning(
                    f"Low confidence ({output.confidence:.2f}) for '{tx.imported_payee}'; "
                    f"marking tag as Unknown."
                )
                output = ClassificationResult(
                    category=output.category,
                    tag=TagEnum.Unknown,
                    clean_payee=output.clean_payee,
                    confidence=output.confidence,
                    reasoning=(
                        f"Low confidence fallback ({output.confidence:.2f}): {output.reasoning}"
                    ),
                )

            return output

        except Exception as e:
            logger.error(f"Inference error classifying '{tx.imported_payee}': {e}")
            # Safe deterministic fallback
            return ClassificationResult(
                category=self._fallback_category(tx),
                tag=TagEnum.Unknown,
                clean_payee=tx.imported_payee.strip() or "Unknown Payee",
                confidence=0.0,
                reasoning=f"Classification exception fallback: {e}",
            )

    @staticmethod
    def _fallback_category(tx: TransactionInput) -> CategoryEnum:
        """Fallback category when LLM is unavailable."""
        p = tx.imported_payee.lower()
        if "ironworks" in p:
            return CategoryEnum.Rent
        if "payroll" in p or "interest" in p or "dividend" in p:
            return CategoryEnum.Income
        if "payment" in p or "transfer" in p or "zelle" in p:
            return CategoryEnum.Transfer
        return CategoryEnum.Shopping
