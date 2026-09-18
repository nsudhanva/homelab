from drive_organizer.pre_router import PreRouter


def test_marriage_certificate_joint_routing():
    suggestion = PreRouter.analyze(
        "form-MRG-10022025-0459358.pdf", "Registrar of Marriages Karnataka"
    )
    assert suggestion.is_joint is True
    assert suggestion.person == "Sudhanva"
    assert suggestion.jurisdiction == "India"
    assert suggestion.category == "Identity"
    assert suggestion.clean_filename == "Marriage Certificate.pdf"
    assert suggestion.confidence >= 0.95


def test_ironworks_lease_joint_routing():
    suggestion = PreRouter.analyze(
        "01-Form-Rental-agreement-Lease.pdf",
        "Ironworks Apartments Sunnyvale CA Residential Lease",
    )
    assert suggestion.is_joint is True
    assert suggestion.person == "Sudhanva"
    assert suggestion.jurisdiction == "USA"
    assert suggestion.category == "Housing"
    assert suggestion.clean_filename == "Ironworks Lease.pdf"


def test_maanasa_california_dl():
    suggestion = PreRouter.analyze(
        "Learners.pdf",
        "State of California Driver License Maanasa Narayan",
    )
    assert suggestion.person == "Maanasa"
    assert suggestion.jurisdiction == "USA"
    assert suggestion.category == "Identity"
    assert (
        suggestion.clean_filename is not None
        and "California Driver License" in suggestion.clean_filename
    )


def test_sudhanva_aadhaar():
    suggestion = PreRouter.analyze(
        "Aadhar - Sudhanvva Narayana.pdf",
        "Unique Identification Authority of India Government of India",
    )
    assert suggestion.person == "Sudhanva"
    assert suggestion.jurisdiction == "India"
    assert suggestion.category == "Identity"
    assert suggestion.clean_filename == "Sudhanva - Aadhaar Card.pdf"


def test_father_ds160_visa():
    suggestion = PreRouter.analyze(
        "DS160 - Confirmation Page - Narayana.pdf",
        "Nonimmigrant Visa Application Confirmation",
    )
    assert suggestion.person == "Narayana"
    assert suggestion.jurisdiction == "USA"
    assert suggestion.category == "Visas & Legal"
    assert suggestion.clean_filename == "Narayana - DS-160 Visa Confirmation.pdf"


def test_w2_tax_routing():
    suggestion = PreRouter.analyze(
        "Statement for 2024 W2.pdf",
        "Form W-2 Wage and Tax Statement Montai Therapeutics",
    )
    assert suggestion.person == "Sudhanva"
    assert suggestion.jurisdiction == "USA"
    assert suggestion.category == "Taxes"
    assert suggestion.subcategory == "2024"


def test_leetcode_progress_routing():
    suggestion = PreRouter.analyze("Leetcode Progress", "")
    assert suggestion.person == "Sudhanva"
    assert suggestion.category == "Career"
    assert suggestion.subcategory == "Interview Prep"
    assert suggestion.confidence >= 0.95


def test_lakshmi_metaplan_routing():
    suggestion = PreRouter.analyze("Lakshmi Stock Research Metaplan", "")
    assert suggestion.person == "Sudhanva"
    assert suggestion.category == "Career"
    assert suggestion.subcategory == "Lakshmi"
    assert suggestion.confidence >= 0.95


def test_neu_education_and_housing():
    s_edu = PreRouter.analyze("NEU Estimated Cost of Attendance (Archive)", "")
    assert s_edu.person == "Sudhanva"
    assert s_edu.category == "Education"
    assert s_edu.subcategory == "Northeastern University"

    s_house = PreRouter.analyze("NEU-Fall-2021-Housing (Archive)", "")
    assert s_house.person == "Sudhanva"
    assert s_house.category == "Housing"


def test_candidate_resume_recruiting():
    suggestion = PreRouter.analyze("KimberlyDo_CV.pdf", "Senior Machine Learning Engineer")
    assert suggestion.person == "Sudhanva"
    assert suggestion.category == "Career"
    assert suggestion.subcategory == "Recruiting"
    assert "Candidate Resume" in (suggestion.clean_filename or "")
