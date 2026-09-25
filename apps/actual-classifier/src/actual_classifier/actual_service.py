"""Service layer managing Actual Budget synchronization and transaction updates."""

import logging
from typing import Any

import actual.queries as q
from actual import Actual

from actual_classifier.classifier import TransactionClassifier
from actual_classifier.config import Settings
from actual_classifier.models import ClassificationResult, TransactionInput

logger = logging.getLogger(__name__)


class ActualBudgetService:
    """Interacts with Actual Budget to fetch and update transactions."""

    def __init__(self, settings: Settings, classifier: TransactionClassifier) -> None:
        self.settings = settings
        self.classifier = classifier

    def run_classification_cycle(
        self, limit: int = 50, dry_run: bool = False
    ) -> list[dict[str, Any]]:
        """Find pending transactions, classify them with the LLM, and apply updates."""
        logger.info(f"Connecting to Actual Budget at {self.settings.actual_server_url}...")

        results: list[dict[str, Any]] = []

        with Actual(
            base_url=self.settings.actual_server_url,
            password=self.settings.actual_password,
            file=self.settings.actual_budget_name,
        ) as actual:
            session = actual.session

            # 1. Fetch categories map
            categories = q.get_categories(session)
            cat_map = {c.name.lower(): c.id for c in categories if c.name}

            # 2. Fetch accounts map
            accounts = q.get_accounts(session)
            acc_map = {a.id: a.name for a in accounts}
            offbudget_accounts = {a.id for a in accounts if a.offbudget}

            # 3. Fetch payees map
            payees = q.get_payees(session)
            payee_map = {p.id: p.name for p in payees}

            # 4. Fetch all transactions
            transactions = q.get_transactions(session)

            # Filter for unclassified or #Unknown transactions
            pending: list[Any] = []
            for t in transactions:
                if t.is_parent or t.starting_balance_flag or t.transferred_id:
                    continue
                if t.acct in offbudget_accounts:
                    continue
                notes = (t.notes or "").strip()
                if t.category_id is None or "#Unknown" in notes:
                    pending.append(t)

            logger.info(f"Found {len(pending)} unclassified or review-pending transactions.")
            batch = pending[:limit]

            for tx in batch:
                acc_name = (acc_map.get(tx.acct) if tx.acct else None) or "Unknown Account"
                payee_name = (
                    (payee_map.get(tx.payee_id) if tx.payee_id else None)
                    or tx.imported_description
                    or "Unknown"
                )

                tx_input = TransactionInput(
                    id=tx.id,
                    date=tx.get_date().isoformat(),
                    amount_cents=tx.amount,
                    imported_payee=payee_name,
                    account_name=acc_name,
                    current_notes=tx.notes or "",
                    current_category=tx.category.name if tx.category else None,
                )

                classification: ClassificationResult = self.classifier.classify(tx_input)

                target_cat_name = classification.category.value
                target_cat_id = cat_map.get(target_cat_name.lower())

                # Prepare updated notes with strict single-word tag
                current_notes_clean = (tx.notes or "").replace("#Unknown", "").strip()
                if classification.tag:
                    tag_str = f"#{classification.tag.value}"
                    new_notes = (
                        f"{current_notes_clean} {tag_str}".strip()
                        if current_notes_clean
                        else tag_str
                    )
                else:
                    new_notes = current_notes_clean

                summary_entry = {
                    "id": tx.id,
                    "date": tx_input.date,
                    "imported_payee": payee_name,
                    "clean_payee": classification.clean_payee,
                    "amount": f"${tx_input.amount_dollars:.2f}",
                    "account": acc_name,
                    "assigned_category": target_cat_name,
                    "assigned_tag": classification.tag.value if classification.tag else None,
                    "confidence": f"{classification.confidence:.2f}",
                    "reasoning": classification.reasoning,
                }
                results.append(summary_entry)

                if not dry_run:
                    if target_cat_id:
                        tx.category_id = target_cat_id
                    tx.notes = new_notes
                    session.add(tx)

            if not dry_run and results:
                logger.info("Committing and syncing updates to Actual Budget...")
                actual.commit()
                logger.info(f"Successfully updated and synced {len(results)} transactions.")
            elif dry_run:
                logger.info(
                    f"DRY RUN: Evaluated {len(results)} transactions without writing to database."
                )

        return results
