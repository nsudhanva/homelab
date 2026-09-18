import re
from dataclasses import dataclass


@dataclass
class PreRouteSuggestion:
    person: str | None = None
    jurisdiction: str | None = None
    category: str | None = None
    subcategory: str | None = None
    clean_filename: str | None = None
    is_joint: bool = False
    confidence: float = 0.0
    reason: str = ""


class PreRouter:
    """Performs deterministic pattern matching and rule-based pre-routing."""

    @classmethod
    def analyze(cls, filename: str, extracted_text: str = "") -> PreRouteSuggestion:
        combined = f"{filename} {extracted_text}".lower()

        # 1. Joint Documents (Marriage cert, joint lease, joint taxes)
        if any(term in combined for term in ["marriage cert", "marriage certificate", "form-mrg"]):
            return PreRouteSuggestion(
                person="Sudhanva",
                jurisdiction="India",
                category="Identity",
                clean_filename="Marriage Certificate.pdf",
                is_joint=True,
                confidence=0.98,
                reason="Marriage certificate is a joint identity document.",
            )

        if "ironworks" in combined or ("lease" in combined and "sunnyvale" in combined):
            return PreRouteSuggestion(
                person="Sudhanva",
                jurisdiction="USA",
                category="Housing",
                clean_filename="Ironworks Lease.pdf",
                is_joint=True,
                confidence=0.98,
                reason="Ironworks residential lease agreement.",
            )

        if "jvue" in combined or ("lease" in combined and "lma" in combined):
            return PreRouteSuggestion(
                person="Sudhanva",
                jurisdiction="USA",
                category="Housing",
                clean_filename="JVue Apartment Lease.pdf",
                is_joint=False,
                confidence=0.95,
                reason="JVue at the LMA apartment lease.",
            )

        # 2. Person Identification
        if "sudhanva" in combined or "sudhanvva" in combined:
            person = "Sudhanva"
        elif any(
            alias in combined
            for alias in [
                "maanasa narayan",
                "maanasa naryana",
                "maanasa",
                "maansi",
                "kayak",
                "momo",
            ]
        ):
            person = "Maanasa"
        elif any(
            alias in combined
            for alias in [
                "narayana chandran",
                "chandran narayana",
                "narayana",
                "bank of baroda",
                "bob ",
            ]
        ):
            person = "Narayana"
        elif any(alias in combined for alias in ["narmada m p", "narmada mp", "narmada"]):
            person = "Narmada"
        elif "rashmi narayana" in combined or "rashmi" in filename.lower():
            person = "Rashmi"
        else:
            person = "Sudhanva"

        # 3. Category & Jurisdiction Resolution
        # Colab / Jupyter Notebooks
        if filename.lower().endswith(".ipynb") or "colaboratory" in combined:
            return PreRouteSuggestion(
                person=person or "Sudhanva",
                jurisdiction="Global",
                category="Notebooks",
                clean_filename=filename,
                is_joint=False,
                confidence=0.98,
                reason="Google Colaboratory or Jupyter notebook.",
            )

        # Google AI Studio / MakerSuite Prompts
        if (
            filename.lower().endswith((".prompt", ".applet", ".applet+zip"))
            or "makersuite" in combined
            or "google ai studio" in combined
        ):
            return PreRouteSuggestion(
                person=person or "Sudhanva",
                jurisdiction="Global",
                category="AI Studio",
                clean_filename=filename,
                is_joint=False,
                confidence=0.98,
                reason="Google AI Studio / MakerSuite prompt experiment.",
            )

        # Machine Learning Model Weights
        if filename.lower().endswith(
            (".pt", ".pth", ".safetensors", ".onnx", ".bin", ".ckpt", ".h5")
        ):
            return PreRouteSuggestion(
                person=person or "Sudhanva",
                jurisdiction="Global",
                category="Models",
                clean_filename=filename,
                is_joint=False,
                confidence=0.98,
                reason="Machine learning model weights / checkpoint.",
            )

        # Code archives and datasets
        if filename.lower() in ["data.zip", "code.zip", "dataset.zip"] or (
            filename.lower().endswith(".zip")
            and any(k in filename.lower() for k in ["data", "code", "model", "repo"])
        ):
            return PreRouteSuggestion(
                person=person or "Sudhanva",
                jurisdiction="Global",
                category="Code",
                clean_filename=filename,
                is_joint=False,
                confidence=0.95,
                reason="Code archive or ML dataset.",
            )

        # Books (E-books, textbooks, z-lib downloads, epubs, mobi)
        if (
            filename.lower().endswith((".epub", ".mobi", ".azw3"))
            or "(z-lib.org)" in combined
            or "textbook" in combined
            or "texts in computer science" in combined
        ):
            clean_bname = filename.replace("(z-lib.org)", "").strip()
            if any(
                k in combined for k in ["algorithm", "computer science", "programming", "python"]
            ):
                topic = "Computer Science"
            elif any(k in combined for k in ["data science", "machine learning"]):
                topic = "Data Science"
            elif any(k in combined for k in ["algebra", "calculus", "mathematics", "linear"]):
                topic = "Mathematics"
            else:
                topic = "General"

            return PreRouteSuggestion(
                person=person or "Sudhanva",
                jurisdiction="Global",
                category="Books",
                subcategory=topic,
                clean_filename=clean_bname,
                is_joint=False,
                confidence=0.95,
                reason=f"Published book or technical literature in {topic}.",
            )

        # India Identity
        if "aadhaar" in combined or "aadhar" in combined:
            p = person or "Sudhanva"
            return PreRouteSuggestion(
                person=p,
                jurisdiction="India",
                category="Identity",
                clean_filename=f"{p} - Aadhaar Card.pdf",
                is_joint=False,
                confidence=0.95,
                reason="Indian national Aadhaar identity card.",
            )

        if "pan card" in combined or "permanent account number" in combined:
            p = person or "Sudhanva"
            return PreRouteSuggestion(
                person=p,
                jurisdiction="India",
                category="Identity",
                clean_filename=f"{p} - PAN Card.pdf",
                is_joint=False,
                confidence=0.95,
                reason="Indian income tax PAN card.",
            )

        # USA Identity: Driver License / Mass ID
        if any(
            term in combined
            for term in ["driver license", "driver's license", "california dl", "learners"]
        ):
            p = person or (
                "Maanasa" if "california" in combined and "maanasa" in combined else "Sudhanva"
            )
            return PreRouteSuggestion(
                person=p,
                jurisdiction="USA",
                category="Identity",
                clean_filename=f"{p} - California Driver License.pdf"
                if "california" in combined
                else f"{p} - Driver License.pdf",
                is_joint=False,
                confidence=0.95,
                reason="US state driver license or permit.",
            )

        if "mass id" in combined:
            p = person or "Sudhanva"
            return PreRouteSuggestion(
                person=p,
                jurisdiction="USA",
                category="Identity",
                clean_filename=f"{p} - Mass ID.pdf",
                is_joint=False,
                confidence=0.95,
                reason="Massachusetts state identification card.",
            )

        if "ssn" in combined or "social security" in combined:
            p = person or "Sudhanva"
            return PreRouteSuggestion(
                person=p,
                jurisdiction="USA",
                category="Identity",
                clean_filename=f"{p} - SSN Card.pdf",
                is_joint=False,
                confidence=0.95,
                reason="US Social Security card.",
            )

        # USA Immigration: H-1B, Visas, DS-160
        if any(term in combined for term in ["i-797", "i-129", "notice of action", "h-1b", "h1b"]):
            p = person or ("Maanasa" if "kayak" in combined else "Sudhanva")
            company = "KAYAK" if "kayak" in combined else ("Montai" if "montai" in combined else "")
            title = (
                f"{p} - H1B Approval Notice ({company}).pdf"
                if company
                else f"{p} - H1B Approval Notice.pdf"
            )
            return PreRouteSuggestion(
                person=p,
                jurisdiction="USA",
                category="Visas & Legal",
                clean_filename=title,
                is_joint=False,
                confidence=0.95,
                reason="USCIS H-1B visa petition or approval notice.",
            )

        if "ds-160" in combined or "ds160" in combined or "visa appointment" in combined:
            p = person or "Narayana"
            return PreRouteSuggestion(
                person=p,
                jurisdiction="USA",
                category="Visas & Legal",
                clean_filename=f"{p} - DS-160 Visa Confirmation.pdf",
                is_joint=False,
                confidence=0.95,
                reason="US consular nonimmigrant visa confirmation.",
            )

        if "i-94" in combined or "arrival/departure" in combined:
            p = person or "Sudhanva"
            return PreRouteSuggestion(
                person=p,
                jurisdiction="USA",
                category="Visas & Legal",
                clean_filename=f"{p} - I-94 Travel Record.pdf",
                is_joint=False,
                confidence=0.95,
                reason="US CBP I-94 arrival and departure record.",
            )

        # USA Taxes: W-2, 1040, 1099
        if "w-2" in combined or "w2" in combined or "wage and tax statement" in combined:
            p = person or "Sudhanva"
            # Attempt to extract year
            year_match = re.search(r"202[0-9]", combined)
            year = year_match.group(0) if year_match else "2024"
            return PreRouteSuggestion(
                person=p,
                jurisdiction="USA",
                category="Taxes",
                subcategory=year,
                clean_filename=f"{year} W-2 ({p}).pdf",
                is_joint=False,
                confidence=0.95,
                reason=f"Form W-2 wage and tax statement for year {year}.",
            )

        if "1099" in combined or "form 1040" in combined or "tax return" in combined:
            p = person or "Sudhanva"
            year_match = re.search(r"202[0-9]", combined)
            year = year_match.group(0) if year_match else "2024"
            is_j = "joint" in combined or "married filing" in combined
            return PreRouteSuggestion(
                person=p,
                jurisdiction="USA",
                category="Taxes",
                subcategory=year,
                clean_filename=f"{year} Tax Return ({p}).pdf",
                is_joint=is_j,
                confidence=0.90,
                reason=f"Tax return documentation for tax year {year}.",
            )

        # USA Vehicle: RMV, Car, Crash
        if any(
            term in combined
            for term in [
                "crash102",
                "motor vehicle crash",
                "rmv receipt",
                "rmv citation",
                "atfault",
            ]
        ):
            return PreRouteSuggestion(
                person="Sudhanva",
                jurisdiction="USA",
                category="Vehicle",
                clean_filename="Mass RMV Crash Operator Report.pdf"
                if "crash" in combined
                else "Mass RMV Vehicle Document.pdf",
                is_joint=False,
                confidence=0.95,
                reason="Massachusetts RMV motor vehicle or accident report.",
            )

        # USA Health: MRI, Medical, Surgery
        if any(
            term in combined
            for term in [
                "mr arthrogram",
                "fluoroscopy",
                "shields health",
                "shoulder",
                "patient portal",
            ]
        ):
            return PreRouteSuggestion(
                person="Sudhanva",
                jurisdiction="USA",
                category="Health",
                clean_filename="Sudhanva - Shoulder MRI Report.pdf",
                is_joint=False,
                confidence=0.95,
                reason="Clinical orthopedic MRI or diagnostic scan report.",
            )

        # Education: Northeastern University (NEU), PES University, Bangalore University
        if any(term in combined for term in ["neu", "northeastern"]):
            p = person or "Sudhanva"
            if "housing" in combined:
                return PreRouteSuggestion(
                    person=p,
                    jurisdiction="USA",
                    category="Housing",
                    clean_filename="Northeastern Fall 2021 Housing",
                    is_joint=False,
                    confidence=0.95,
                    reason="Northeastern University graduate student housing documentation.",
                )
            if any(term in combined for term in ["cost", "attendance", "tuition", "fee"]):
                return PreRouteSuggestion(
                    person=p,
                    jurisdiction="USA",
                    category="Education",
                    subcategory="Northeastern University",
                    clean_filename="Northeastern University - Cost of Attendance",
                    is_joint=False,
                    confidence=0.95,
                    reason="Northeastern University graduate tuition and cost of attendance estimate.",
                )
            return PreRouteSuggestion(
                person=p,
                jurisdiction="USA",
                category="Education",
                subcategory="Northeastern University",
                clean_filename=filename.replace(".pdf", ""),
                is_joint=False,
                confidence=0.92,
                reason="Northeastern University academic documentation.",
            )

        if any(term in combined for term in ["pesit", "pes university", "pes college"]):
            return PreRouteSuggestion(
                person=person or "Sudhanva",
                jurisdiction="India",
                category="Education",
                subcategory="PES University",
                clean_filename=filename.replace(".pdf", ""),
                is_joint=False,
                confidence=0.95,
                reason="PES University academic records.",
            )

        # Career: Leetcode, Coding Challenges, Lakshmi Research, Recruiting Resumes
        if "leetcode" in combined:
            return PreRouteSuggestion(
                person="Sudhanva",
                jurisdiction="Global",
                category="Career",
                subcategory="Interview Prep",
                clean_filename="Leetcode Progress",
                is_joint=False,
                confidence=0.98,
                reason="Technical interview preparation and coding challenge tracking.",
            )

        if "lakshmi" in combined:
            return PreRouteSuggestion(
                person="Sudhanva",
                jurisdiction="USA",
                category="Career",
                subcategory="Lakshmi",
                clean_filename="Lakshmi Stock Research Metaplan",
                is_joint=False,
                confidence=0.98,
                reason="Quantitative financial architecture and stock research project.",
            )

        # Candidate CV / Resumes (External applicants / referrals)
        if any(
            term in combined for term in ["_cv", "-cv", "cv.pdf", "resume.pdf", "curriculum vitae"]
        ):
            if not any(
                fam in combined for fam in ["sudhanva", "maanasa", "narayana", "narmada", "rashmi"]
            ):
                candidate_name = (
                    filename.replace(".pdf", "")
                    .replace("_CV", "")
                    .replace("-CV", "")
                    .replace("_cv", "")
                    .replace("-cv", "")
                    .replace("_resume", "")
                    .replace("_", " ")
                    .strip()
                )
                return PreRouteSuggestion(
                    person="Unknown",
                    jurisdiction="Global",
                    category="CVs",
                    subcategory=None,
                    clean_filename=f"{candidate_name} - CV.pdf",
                    is_joint=False,
                    confidence=0.95,
                    reason=f"External candidate CV / resume for {candidate_name}.",
                )

        # Default fallback
        return PreRouteSuggestion(
            person=person,
            confidence=0.0,
            reason="Ambiguous document, deferring to Pydantic AI agent.",
        )
