"""Unit tests for ActualBudgetService."""

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
    def __init__(self, id: str, name: str) -> None:
        self.id = id
        self.name = name


class MockPayee:
    def __init__(self, id: str, name: str) -> None:
        self.id = id
        self.name = name


class MockTransaction:
    def __init__(
        self,
        id: str,
        date: str,
        amount: int,
        acct: str,
        description: str,
        imported_description: str | None = None,
        notes: str | None = None,
        category: str | None = None,
        is_parent: bool = False,
        starting_balance_flag: bool = False,
    ) -> None:
        self.id = id
        self.date = date
        self.amount = amount
        self.acct = acct
        self.description = description
        self.imported_description = imported_description
        self.notes = notes
        self.category = category
        self.is_parent = is_parent
        self.starting_balance_flag = starting_balance_flag


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
            date="2026-09-21",
            amount=-2500,
            acct="acc-amex",
            description="payee-safeway",
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
    # Ensure no db commit or sync in dry run
    mock_session.commit.assert_not_called()
    mock_actual_instance.sync.assert_not_called()


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
        date="2026-09-22",
        amount=-3500,
        acct="acc-chase",
        description="",
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
    assert tx.category == "cat-transit"
    assert tx.notes == "#Transit"
    mock_session.add.assert_called_once_with(tx)
    mock_session.commit.assert_called_once()
    mock_actual_instance.sync.assert_called_once()
