"""Command-line entrypoint for Actual Budget transaction classification."""

import argparse
import logging
import sys
from typing import TypedDict

from actual_classifier.actual_service import ActualBudgetService
from actual_classifier.classifier import TransactionClassifier
from actual_classifier.config import Settings
from actual_classifier.models import (
    CategoryEnum,
    ClassificationResult,
    TagEnum,
    TransactionInput,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("actual_classifier")


class BenchmarkCase(TypedDict):
    input: TransactionInput
    expected_category: CategoryEnum
    expected_tag: TagEnum | None


# Curated benchmark suite covering all household spending domains
BENCHMARK_CASES: list[BenchmarkCase] = [
    {
        "input": TransactionInput(
            id="bench-1",
            date="2026-09-01",
            amount_cents=-3440,
            imported_payee="TST*IDLY EXPRESS - MOUNT",
            account_name="[Sudhanva] Amex Gold Card",
        ),
        "expected_category": CategoryEnum.Food,
        "expected_tag": None,
    },
    {
        "input": TransactionInput(
            id="bench-2",
            date="2026-09-02",
            amount_cents=-1999,
            imported_payee="DISNEY PLUS 500 SOUTH BUENA VISTA 8889057888 CA",
            account_name="[Maanasa] Apple Card",
        ),
        "expected_category": CategoryEnum.Bills,
        "expected_tag": TagEnum.Subscription,
    },
    {
        "input": TransactionInput(
            id="bench-3",
            date="2026-09-03",
            amount_cents=-528912,
            imported_payee="IRONWORKS APARTMENTS ACH DEBIT",
            account_name="[Maanasa] Discover Cashback Debit",
        ),
        "expected_category": CategoryEnum.Rent,
        "expected_tag": TagEnum.Rent,
    },
    {
        "input": TransactionInput(
            id="bench-4",
            date="2026-09-04",
            amount_cents=-4250,
            imported_payee="LYFT *RIDE 09-04 SAN FRANCISCO CA",
            account_name="[Sudhanva] Robinhood Credit Card",
        ),
        "expected_category": CategoryEnum.Transit,
        "expected_tag": TagEnum.Transit,
    },
    {
        "input": TransactionInput(
            id="bench-5",
            date="2026-09-05",
            amount_cents=453362,
            imported_payee="GOOGLE LLC PAYROLL DIRECT DEP",
            account_name="[Maanasa] Discover Cashback Debit",
        ),
        "expected_category": CategoryEnum.Income,
        "expected_tag": TagEnum.Income,
    },
    {
        "input": TransactionInput(
            id="bench-6",
            date="2026-09-06",
            amount_cents=-22500,
            imported_payee="INSTANT URGENT CARE SANTA CLARA CA",
            account_name="[Maanasa] Chase Sapphire Reserve",
        ),
        "expected_category": CategoryEnum.Medical,
        "expected_tag": TagEnum.Medical,
    },
    {
        "input": TransactionInput(
            id="bench-7",
            date="2026-09-07",
            amount_cents=-69072,
            imported_payee="USI TRAVEL INSURANCE SERVICES",
            account_name="[Sudhanva] Chase Amazon Prime Visa",
        ),
        "expected_category": CategoryEnum.Travel,
        "expected_tag": TagEnum.Travel,
    },
    {
        "input": TransactionInput(
            id="bench-8",
            date="2026-09-08",
            amount_cents=-4859,
            imported_payee="AMZN Mktp US*2K7Y904 AMZN.COM/BILL",
            account_name="[Sudhanva] Chase Amazon Prime Visa",
        ),
        "expected_category": CategoryEnum.Shopping,
        "expected_tag": None,
    },
    {
        "input": TransactionInput(
            id="bench-9",
            date="2026-09-09",
            amount_cents=-5147,
            imported_payee="ACH Withdrawal COMCAST-XFINITY CABLE SVCS",
            account_name="[Maanasa] Discover Cashback Debit",
        ),
        "expected_category": CategoryEnum.Bills,
        "expected_tag": TagEnum.Subscription,
    },
    {
        "input": TransactionInput(
            id="bench-10",
            date="2026-09-10",
            amount_cents=-75000,
            imported_payee="AUTOPAY PAYMENT - THANK YOU",
            account_name="[Sudhanva] Chase Total Checking",
        ),
        "expected_category": CategoryEnum.Transfer,
        "expected_tag": TagEnum.Transfer,
    },
]


def run_benchmark(classifier: TransactionClassifier) -> float:
    """Evaluate classifier against golden benchmark vectors and print report."""
    logger.info("Starting classifier benchmark suite across 10 core domains...")

    correct_categories = 0
    correct_tags = 0
    total = len(BENCHMARK_CASES)

    print("\n" + "=" * 80)
    print(f"{'BENCHMARK EVALUATION REPORT':^80}")
    print("=" * 80)

    for idx, case in enumerate(BENCHMARK_CASES, start=1):
        tx: TransactionInput = case["input"]
        exp_cat: CategoryEnum = case["expected_category"]
        exp_tag: TagEnum | None = case["expected_tag"]

        result: ClassificationResult = classifier.classify(tx)

        cat_match = result.category == exp_cat
        # Treat None and Unknown as matching when no specific tag is expected
        tag_match = (result.tag == exp_tag) or (
            exp_tag is None and result.tag in (None, TagEnum.Unknown)
        )

        if cat_match:
            correct_categories += 1
        if tag_match:
            correct_tags += 1

        status_cat = "PASS" if cat_match else f"FAIL (got {result.category.value})"
        actual_tag_val = result.tag.value if result.tag else "None"
        status_tag = "PASS" if tag_match else f"FAIL (got {actual_tag_val})"

        print(
            f"[{idx:2d}/{total}] {tx.imported_payee[:30]:<30} | "
            f"Cat: {status_cat:<18} | Tag: {status_tag}"
        )
        print(
            f"      Normalized: '{result.clean_payee}' | "
            f"Conf: {result.confidence:.2f} | Rationale: {result.reasoning}"
        )

    cat_accuracy = (correct_categories / total) * 100.0
    tag_accuracy = (correct_tags / total) * 100.0

    print("-" * 80)
    print(f"Category Accuracy: {cat_accuracy:.1f}% ({correct_categories}/{total})")
    print(f"Tag Accuracy:      {tag_accuracy:.1f}% ({correct_tags}/{total})")
    print("=" * 80 + "\n")

    return (cat_accuracy + tag_accuracy) / 2.0


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Actual Budget AI Transaction Classifier")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview classifications without updating database",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=25,
        help="Maximum transactions to process",
    )
    parser.add_argument(
        "--benchmark",
        action="store_true",
        help="Run benchmark suite and compute accuracy score",
    )
    return parser.parse_args()


def main() -> None:
    """Main execution workflow."""
    args = parse_args()
    settings = Settings()

    classifier = TransactionClassifier(settings)

    if args.benchmark:
        score = run_benchmark(classifier)
        sys.exit(0 if score >= 80.0 else 1)

    service = ActualBudgetService(settings, classifier)
    results = service.run_classification_cycle(limit=args.limit, dry_run=args.dry_run)

    print(f"\nProcessed {len(results)} transactions:")
    for r in results:
        print(
            f" - {r['date']} | {r['imported_payee'][:25]:<25} -> {r['assigned_category']:<10} "
            f"| Tag: #{r['assigned_tag'] or 'None'} | Conf: {r['confidence']} | {r['clean_payee']}"
        )


if __name__ == "__main__":
    main()
