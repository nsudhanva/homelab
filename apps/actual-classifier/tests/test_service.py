"""Unit tests for ActualBudgetService."""

import datetime
from unittest.mock import MagicMock, patch

from actual_classifier.actual_service import ActualBudgetService
from actual_classifier.classifier import TransactionClassifier
from actual_classifier.config import Settings
from actual_classifier.models import CategoryEnum, ClassificationResult, TagEnum


class MockCategory:
    def __init__(self, id: str, name: str) -> None:
        self.id = id
        self.name = name


class MockAccount:
    def __init__(self, id: str, name: str, offbudget: int = 0) -> None:
        self.id = id
        self.name = name
        self.offbudget = offbudget


class MockPayee:
    def __init__(self, id: str, name: str) -> None:
        self.id = id
        self.name = name


class MockTransaction:
    def __init__(
        self,
        id: str,
        date: int,
        amount: int,
        acct: str,
        payee_id: str | None,
        imported_description: str | None = None,
        notes: str | None = None,
        category: MockCategory | None = None,
        is_parent: int = 0,
        starting_balance_flag: int = 0,
        transferred_id: str | None = None,
    ) -> None:
        self.id = id
        self.date = date
        self.amount = amount
        self.acct = acct
        self.payee_id = payee_id
        self.imported_description = imported_description
        self.notes = notes
        self.category = category
        self.category_id = category.id if category else None
        self.is_parent = is_parent
        self.starting_balance_flag = starting_balance_flag
        self.transferred_id = transferred_id

    def get_date(self) -> datetime.date:
        return datetime.datetime.strptime(str(self.date), "%Y%m%d").date()


@patch("actual_classifier.actual_service.q")
@patch("actual_classifier.actual_service.Actual")
def test_run_classification_cycle_dry_run(mock_actual_cls: MagicMock, mock_q: MagicMock) -> None:
    """Test classification cycle in dry-run mode."""
    # Setup mock session and Actual context manager
    mock_actual_instance = MagicMock()
    mock_session = MagicMock()
    mock_actual_instance.session = mock_session
    mock_actual_cls.return_value.__enter__.return_value = mock_actual_instance

    mock_q.get_categories.return_value = [
        MockCategory("cat-food", "Food"),
        MockCategory("cat-bills", "Bills"),
    ]
    mock_q.get_accounts.return_value = [
        MockAccount("acc-amex", "[Sudhanva] Amex Gold Card"),
    ]
    mock_q.get_payees.return_value = [
        MockPayee("payee-safeway", "Safeway"),
    ]
    mock_q.get_transactions.return_value = [
        MockTransaction(
            id="tx-1",
            date=20260921,
            amount=-2500,
            acct="acc-amex",
            payee_id="payee-safeway",
            notes=None,
            category=None,
        ),
    ]

    settings = Settings()
    mock_classifier = MagicMock(spec=TransactionClassifier)
    mock_classifier.classify.return_value = ClassificationResult(
        category=CategoryEnum.Food,
        tag=None,
        clean_payee="Safeway",
        confidence=0.98,
        reasoning="Grocery supermarket",
    )

    service = ActualBudgetService(settings, mock_classifier)
    results = service.run_classification_cycle(limit=10, dry_run=True)

    assert len(results) == 1
    assert results[0]["id"] == "tx-1"
    assert results[0]["assigned_category"] == "Food"
    assert results[0]["clean_payee"] == "Safeway"
    assert results[0]["date"] == "2026-09-21"
    mock_actual_instance.commit.assert_not_called()


@patch("actual_classifier.actual_service.q")
@patch("actual_classifier.actual_service.Actual")
def test_run_classification_cycle_write_and_sync(
    mock_actual_cls: MagicMock, mock_q: MagicMock
) -> None:
    """Test classification cycle with database commit and sync."""
    mock_actual_instance = MagicMock()
    mock_session = MagicMock()
    mock_actual_instance.session = mock_session
    mock_actual_cls.return_value.__enter__.return_value = mock_actual_instance

    mock_q.get_categories.return_value = [
        MockCategory("cat-transit", "Transit"),
    ]
    mock_q.get_accounts.return_value = [
        MockAccount("acc-chase", "[Sudhanva] Chase Sapphire Reserve"),
    ]
    mock_q.get_payees.return_value = []
    tx = MockTransaction(
        id="tx-2",
        date=20260922,
        amount=-3500,
        acct="acc-chase",
        payee_id=None,
        imported_description="LYFT *RIDE",
        notes="#Unknown",
        category=None,
    )
    mock_q.get_transactions.return_value = [tx]

    settings = Settings()
    mock_classifier = MagicMock(spec=TransactionClassifier)
    mock_classifier.classify.return_value = ClassificationResult(
        category=CategoryEnum.Transit,
        tag=TagEnum.Transit,
        clean_payee="Lyft",
        confidence=0.99,
        reasoning="Rideshare transit trip",
    )

    service = ActualBudgetService(settings, mock_classifier)
    results = service.run_classification_cycle(limit=10, dry_run=False)

    assert len(results) == 1
    assert tx.category_id == "cat-transit"
    assert tx.notes == "#Transit"
    mock_session.add.assert_called_once_with(tx)
    mock_actual_instance.commit.assert_called_once()


@patch("actual_classifier.actual_service.q")
@patch("actual_classifier.actual_service.Actual")
def test_run_classification_cycle_skips_transfers_and_offbudget(
    mock_actual_cls: MagicMock, mock_q: MagicMock
) -> None:
    """Transfers and off-budget tracking accounts are never categorized."""
    mock_actual_instance = MagicMock()
    mock_actual_instance.session = MagicMock()
    mock_actual_cls.return_value.__enter__.return_value = mock_actual_instance

    mock_q.get_categories.return_value = [MockCategory("cat-food", "Food")]
    mock_q.get_accounts.return_value = [
        MockAccount("acc-checking", "Checking"),
        MockAccount("acc-brokerage", "Brokerage", offbudget=1),
    ]
    mock_q.get_payees.return_value = []
    mock_q.get_transactions.return_value = [
        MockTransaction(
            id="tx-transfer",
            date=20260923,
            amount=-10000,
            acct="acc-checking",
            payee_id=None,
            transferred_id="tx-other",
        ),
        MockTransaction(
            id="tx-offbudget",
            date=20260923,
            amount=5000,
            acct="acc-brokerage",
            payee_id=None,
            imported_description="DIVIDEND",
        ),
    ]

    mock_classifier = MagicMock(spec=TransactionClassifier)
    service = ActualBudgetService(Settings(), mock_classifier)
    results = service.run_classification_cycle(limit=10, dry_run=False)

    assert results == []
    mock_classifier.classify.assert_not_called()
    mock_actual_instance.commit.assert_not_called()
