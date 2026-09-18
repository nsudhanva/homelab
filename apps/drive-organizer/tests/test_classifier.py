from drive_organizer.classifier import (
    DocumentClassification,
    DriveClassifier,
)


def test_resolve_target_folder_symmetry():
    # 1. Sudhanva USA Identity
    cls_sud = DocumentClassification(
        person="Sudhanva",
        jurisdiction="USA",
        category="Identity",
        clean_filename="Sudhanva - California Driver License.pdf",
        confidence=0.95,
        summary="California DL",
        reasoning="Valid DL",
    )
    assert DriveClassifier.resolve_target_folder(cls_sud) == "Sudhanva/USA/Identity"

    # 2. Maanasa USA Identity (Identical depth & names!)
    cls_maan = DocumentClassification(
        person="Maanasa",
        jurisdiction="USA",
        category="Identity",
        clean_filename="Maanasa - California Driver License.pdf",
        confidence=0.95,
        summary="California DL",
        reasoning="Valid DL",
    )
    assert DriveClassifier.resolve_target_folder(cls_maan) == "Maanasa/USA/Identity"

    # 3. Father Narayana USA Visas
    cls_dad = DocumentClassification(
        person="Narayana",
        jurisdiction="USA",
        category="Visas & Legal",
        clean_filename="Narayana - DS-160 Confirmation.pdf",
        confidence=0.95,
        summary="US Visa Confirmation",
        reasoning="Valid DS-160",
    )
    assert DriveClassifier.resolve_target_folder(cls_dad) == "Narayana/USA/Visas & Legal"

    # 4. Sudhanva Taxes with year
    cls_tax = DocumentClassification(
        person="Sudhanva",
        jurisdiction="USA",
        category="Taxes",
        subcategory="2024",
        clean_filename="2024 W-2 (Montai).pdf",
        confidence=0.95,
        summary="W-2 form",
        reasoning="Montai W-2",
    )
    assert DriveClassifier.resolve_target_folder(cls_tax) == "Sudhanva/USA/Taxes/2024"


def test_low_confidence_routes_to_review():
    cls_unknown = DocumentClassification(
        person="Unknown",
        jurisdiction="USA",
        category="Identity",
        clean_filename="Unknown.pdf",
        confidence=0.50,
        summary="Ambiguous document",
        reasoning="Could not identify owner",
    )
    assert DriveClassifier.resolve_target_folder(cls_unknown) == "Review/Needs Review"
