import pytest

from drive_organizer.pre_router import PreRouter

CASES = [
    pytest.param(
        "form-MRG-10022025-0459358.pdf",
        "Registrar of Marriages Karnataka",
        {
            "is_joint": True,
            "person": "Sudhanva",
            "jurisdiction": "India",
            "category": "Identity",
            "clean_filename": "Marriage Certificate.pdf",
        },
        0.95,
        None,
        id="marriage-certificate-joint",
    ),
    pytest.param(
        "01-Form-Rental-agreement-Lease.pdf",
        "Ironworks Apartments Sunnyvale CA Residential Lease",
        {
            "is_joint": True,
            "person": "Sudhanva",
            "jurisdiction": "USA",
            "category": "Housing",
            "clean_filename": "Ironworks Lease.pdf",
        },
        0.0,
        None,
        id="ironworks-lease-joint",
    ),
    pytest.param(
        "Learners.pdf",
        "State of California Driver License Maanasa Narayan",
        {
            "person": "Maanasa",
            "jurisdiction": "USA",
            "category": "Identity",
            "clean_filename": "Maanasa - California Driver License.pdf",
        },
        0.0,
        None,
        id="maanasa-california-dl",
    ),
    pytest.param(
        "Aadhar - Sudhanvva Narayana.pdf",
        "Unique Identification Authority of India Government of India",
        {
            "person": "Sudhanva",
            "jurisdiction": "India",
            "category": "Identity",
            "clean_filename": "Sudhanva - Aadhaar Card.pdf",
        },
        0.0,
        None,
        id="sudhanva-aadhaar",
    ),
    pytest.param(
        "DS160 - Confirmation Page - Narayana.pdf",
        "Nonimmigrant Visa Application Confirmation",
        {
            "person": "Narayana",
            "jurisdiction": "USA",
            "category": "Visas & Legal",
            "clean_filename": "Narayana - DS-160 Visa Confirmation.pdf",
        },
        0.0,
        None,
        id="father-ds160-visa",
    ),
    pytest.param(
        "Statement for 2024 W2.pdf",
        "Form W-2 Wage and Tax Statement Montai Therapeutics",
        {"person": "Sudhanva", "jurisdiction": "USA", "category": "Taxes", "subcategory": "2024"},
        0.0,
        None,
        id="w2-tax-year",
    ),
    pytest.param(
        "Leetcode Progress",
        "",
        {"person": "Sudhanva", "category": "Career", "subcategory": "Interview Prep"},
        0.95,
        None,
        id="leetcode-interview-prep",
    ),
    pytest.param(
        "Lakshmi Stock Research Metaplan",
        "",
        {"person": "Sudhanva", "category": "Career", "subcategory": "Lakshmi"},
        0.95,
        None,
        id="lakshmi-career",
    ),
    pytest.param(
        "NEU Estimated Cost of Attendance (Archive)",
        "",
        {"person": "Sudhanva", "category": "Education", "subcategory": "Northeastern University"},
        0.0,
        None,
        id="neu-education",
    ),
    pytest.param(
        "NEU-Fall-2021-Housing (Archive)",
        "",
        {"person": "Sudhanva", "category": "Housing"},
        0.0,
        None,
        id="neu-housing",
    ),
    pytest.param(
        "KimberlyDo_CV.pdf",
        "Senior Machine Learning Engineer",
        {"category": "CVs", "clean_filename": "KimberlyDo - CV.pdf"},
        0.95,
        None,
        id="candidate-cv",
    ),
    pytest.param(
        "The Algorithm Design Manual (Texts in Computer Science) by Steven S. Skiena (z-lib.org).pdf",
        "",
        {"category": "Books", "subcategory": "Computer Science"},
        0.95,
        "(z-lib.org)",
        id="book-topic",
    ),
    pytest.param(
        "Learning NN.ipynb", "", {"category": "Notebooks"}, 0.95, None, id="colab-notebook"
    ),
    pytest.param("WeatherMesh3.pt", "", {"category": "Models"}, 0.95, None, id="model-weights"),
    pytest.param("data.zip", "", {"category": "Code"}, 0.95, None, id="data-archive"),
    pytest.param(
        "De-Slop Docs & Refactor.prompt",
        "",
        {"category": "AI Studio"},
        0.95,
        None,
        id="ai-studio-prompt",
    ),
]


@pytest.mark.parametrize(("filename", "text", "expected", "min_confidence", "name_lacks"), CASES)
def test_pre_router(filename, text, expected, min_confidence, name_lacks):
    suggestion = PreRouter.analyze(filename, text)
    for field, value in expected.items():
        assert getattr(suggestion, field) == value, field
    assert suggestion.confidence >= min_confidence
    if name_lacks:
        assert suggestion.clean_filename
        assert name_lacks not in suggestion.clean_filename
