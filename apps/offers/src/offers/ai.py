"""AI decisions for candidates that no rule can decide.

The AI answers one question: does this transaction count for this offer? It returns a
structured answer with a confidence. The engine applies every answer, and lists the answers
below the confidence threshold in the AI log. Answers are cached against the offer
fingerprint, so the AI sees each transaction once for each meaning of an offer.
"""

import logging
from typing import Protocol

from homelab_ai import AITask, HomelabAIError
from pydantic import BaseModel, Field

from offers.catalog import Card, MerchantType, Offer
from offers.models import AIDecision, Candidate, EvidenceKind, Txn

logger = logging.getLogger(__name__)

INSTRUCTIONS = """You decide whether one card transaction counts toward one credit card offer.

Rules:
- Answer only about the offer and the transaction given.
- A "credit" transaction is money into the card account. It counts only if the card issuer
  posted it for this offer. A merchant refund does not count.
- A "purchase" transaction is money out. It counts only if it is an eligible purchase for the
  offer, for example at a partner merchant, or through an app that the offer names.
- Bank descriptions are abbreviated and noisy, for example "SQ *", "TST*", "DD *", or a city
  and a store number. Look through the noise for the merchant.
- If the merchant is not certain, give a low confidence. Do not guess a match.
- Confidence is a number from 0 to 1.
- Keep the reason to one short sentence.
"""


class MatchDecision(BaseModel):
    match: bool
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str = Field(max_length=300)


def _offer_text(offer: Offer, card: Card) -> str:
    lines = [
        f"Card: {card.name} ({card.issuer})",
        f"Offer: {offer.name}",
        f"Value: ${offer.value:.2f} per {offer.period.value.replace('_', ' ')}",
    ]
    if offer.how_to_use:
        lines.append(f"How it works: {offer.how_to_use}")
    if offer.detect.ai_hint:
        lines.append(f"Eligibility: {offer.detect.ai_hint}")
    return "\n".join(lines)


class Matcher(Protocol):
    @property
    def model(self) -> str: ...

    def decide(self, candidate: Candidate, offer: Offer, card: Card) -> AIDecision | None: ...


class OfferMatcher:
    def __init__(self, task: AITask[MatchDecision] | None = None) -> None:
        self.task = task or AITask(
            name="offers-matcher", output_type=MatchDecision, instructions=INSTRUCTIONS
        )

    @property
    def model(self) -> str:
        return self.task.describe()

    def decide(self, candidate: Candidate, offer: Offer, card: Card) -> AIDecision | None:
        txn = candidate.txn
        kind = "credit" if candidate.kind is EvidenceKind.CREDIT else "purchase"
        prompt = (
            f"Transaction type: {kind}\n"
            f"Date: {txn.date.isoformat()}\n"
            f"Amount: ${abs(txn.amount):.2f}\n"
            f"Payee: {txn.payee}\n"
            f"Bank description: {txn.description}"
        )
        try:
            out = self.task.run_sync(prompt, stable_prefix=_offer_text(offer, card))
        except HomelabAIError as exc:
            logger.warning("AI decision failed for offer %s: %s", offer.id, exc)
            return None
        return AIDecision(out.match, out.confidence, out.reason.strip())


MERCHANT_INSTRUCTIONS = """You classify one merchant from a credit card statement into one type.

Types:
- dining: restaurants, cafes, bars, coffee shops, fast food, food delivery from restaurants
- groceries: supermarkets and grocery stores, farmers markets
- gas: gas stations and EV charging
- transit: public transit, trains, buses, subway, tolls, parking
- rideshare: Uber, Lyft, taxis
- airline: airlines
- hotel: hotels and lodging
- travel: travel agencies, car rental, cruises, other travel
- drugstore: pharmacies and drugstores
- streaming: video and music streaming services
- entertainment: events, tickets, theaters, museums, attractions
- online_retail: online marketplaces such as Amazon
- retail: stores for clothing, home, electronics, and general goods
- utilities: electricity, gas, water, internet, cable
- phone: mobile phone plans
- subscription: software and other recurring subscriptions
- health: doctors, clinics, therapy, fitness
- other: anything else

Rules:
- Bank descriptions are abbreviated and noisy. Look through prefixes such as "SQ *" or "TST*".
- Use the budget category only as a hint.
- If you are not sure, give a low confidence.
"""


class MerchantDecision(BaseModel):
    type: MerchantType
    confidence: float = Field(ge=0.0, le=1.0)


class MerchantClassifier:
    def __init__(self, task: AITask[MerchantDecision] | None = None) -> None:
        self.task = task or AITask(
            name="offers-merchant-type",
            output_type=MerchantDecision,
            instructions=MERCHANT_INSTRUCTIONS,
        )

    def classify(self, txn: Txn) -> MerchantDecision | None:
        prompt = (
            f"Payee: {txn.payee}\n"
            f"Bank description: {txn.description}\n"
            f"Budget category: {txn.category or 'none'}"
        )
        try:
            return self.task.run_sync(prompt)
        except HomelabAIError as exc:
            logger.warning("Merchant classification failed: %s", exc)
            return None
