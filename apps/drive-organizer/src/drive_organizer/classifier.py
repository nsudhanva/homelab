import logging
import os
import threading
import time
from typing import Any

from openai import AsyncOpenAI
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from .pre_router import PreRouter, PreRouteSuggestion

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")
logger = logging.getLogger(__name__)

VALID_PEOPLE = {"Sudhanva", "Maanasa", "Narayana", "Narmada", "Rashmi", "Unknown"}
VALID_JURISDICTIONS = {"USA", "India", "Global"}
VALID_CATEGORIES = {
    "Identity",
    "Visas & Legal",
    "Taxes",
    "Banking",
    "Housing",
    "Health",
    "Vehicle",
    "Career",
    "Education",
    "Books",
    "CVs",
    "Notebooks",
    "AI Studio",
    "Models",
    "Code",
    "Review",
}


class LLMConnectionError(RuntimeError):
    """Raised when the LLM server is unreachable or times out."""

    pass


class FolderTriageDecision(BaseModel):
    action: str = Field(
        description="Must be 'dismantle' for loose document/scan/receipt batches, or 'keep_intact' for code projects, repos, software environments, or datasets"
    )
    is_code: bool = Field(
        description="True if folder contains a software repository, code project, programming scripts, or dev environment"
    )
    target_folder: str | None = Field(
        default=None,
        description="Destination path if keep_intact (e.g. 'Code/<Folder_Name>' or 'Colab Notebooks/<Folder_Name>')",
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score between 0.0 and 1.0",
    )
    reasoning: str = Field(
        description="Brief 1-2 sentence explanation of whether this is code/project to preserve intact or a document batch to dismantle"
    )


class DocumentClassification(BaseModel):
    person: str = Field(
        description="The individual the document belongs to: 'Sudhanva', 'Maanasa', 'Narayana', 'Narmada', 'Rashmi', or 'Unknown'"
    )
    jurisdiction: str = Field(description="Applicable jurisdiction: 'USA', 'India', or 'Global'")
    category: str = Field(
        description="Document category: 'Identity', 'Visas & Legal', 'Taxes', 'Banking', 'Housing', 'Health', 'Vehicle', 'Career', 'Education', 'Books', 'Review'"
    )
    subcategory: str | None = Field(
        default=None,
        description="Subcategory: e.g. 4-digit tax year '2024', university 'Northeastern University', company name, or book topic 'Computer Science'",
    )
    clean_filename: str = Field(
        description="Clean, human-readable standardized filename without hashes or uuid"
    )
    is_joint: bool = Field(
        default=False,
        description="True if document belongs to or names both Sudhanva and Maanasa (e.g. lease, marriage cert, joint taxes)",
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score between 0.0 and 1.0",
    )
    summary: str = Field(
        description="1-2 sentence human summary for Drive description and search indexing"
    )
    search_tags: list[str] = Field(
        default_factory=list,
        description="3-5 search keywords for Drive search bar indexing",
    )
    reasoning: str = Field(description="Brief explanation of the classification decision")


class DriveClassifier:
    """Classifies Google Drive files using deterministic pre-routing and Pydantic AI."""

    def __init__(
        self,
        base_url: str = "http://llama-server.llama.svc.cluster.local:8080/v1",
        model_name: str = "gemma-4-e2b-it",
        confidence_threshold: float = 0.80,
        timeout_seconds: float = 120.0,
        agent: Any = None,
        triage_agent: Any = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self.confidence_threshold = confidence_threshold
        self.timeout = timeout_seconds
        self._explicit_agent = agent
        self._explicit_triage_agent = triage_agent
        self._local = threading.local()

    @property
    def triage_agent(self) -> Agent[None, FolderTriageDecision]:
        """Return the folder triage agent, isolated per thread."""
        if self._explicit_triage_agent is not None:
            return self._explicit_triage_agent

        if not hasattr(self._local, "triage_agent"):
            client = AsyncOpenAI(
                base_url=self.base_url,
                api_key="not-needed",
                timeout=self.timeout,
            )
            provider = OpenAIProvider(openai_client=client)
            model = OpenAIChatModel(self.model_name, provider=provider)
            self._local.triage_agent = Agent(
                model=model,
                output_type=FolderTriageDecision,
                system_prompt=(
                    "You are an automated file system classifier.\n"
                    "Determine whether the provided Google Drive folder should be:\n"
                    "1. KEPT INTACT ('keep_intact'): For software projects, code repositories, "
                    "development scripts, programming environments, Jupyter notebooks, or datasets.\n"
                    "CRITICAL: NEVER dismantle code projects, as separating scripts from configs/assets breaks the codebase.\n"
                    "If keep_intact, set target_folder='Code/<FolderName>' (or 'Colab Notebooks/<FolderName>' for Jupyter/Colab projects).\n"
                    "2. DISMANTLED ('dismantle'): For unstructured document batches, loose PDFs, "
                    "scanned receipts, tax records, medical files, invoices, or personal paperwork.\n"
                    "These files should be individually extracted, classified, and sorted into the personal taxonomy.\n"
                    "Provide confidence (0.0 to 1.0) and a concise 1-sentence reason."
                ),
            )
        return self._local.triage_agent

    def triage_folder_sync(
        self,
        folder_name: str,
        sample_files: list[str],
        tree_summary: str,
    ) -> FolderTriageDecision:
        """Determines whether a root folder is code/project (keep intact) or document batch (dismantle)."""
        code_exts = {
            ".py",
            ".ts",
            ".js",
            ".jsx",
            ".tsx",
            ".go",
            ".rs",
            ".java",
            ".cpp",
            ".c",
            ".h",
            ".cs",
            ".rb",
            ".php",
            ".sh",
            ".swift",
            ".kt",
            ".scala",
            ".lua",
            ".zig",
        }
        code_files = {
            "package.json",
            "pyproject.toml",
            "cargo.toml",
            "go.mod",
            "gemfile",
            "pom.xml",
            "build.gradle",
            "cmakelists.txt",
            "makefile",
            "dockerfile",
            ".gitignore",
        }
        has_code_signature = any(
            any(f.lower().endswith(ext) for ext in code_exts)
            or f.lower().split("/")[-1] in code_files
            for f in sample_files
        )
        has_notebook_signature = any(f.lower().endswith(".ipynb") for f in sample_files)

        prompt_content = (
            f"Please evaluate the following Google Drive folder to decide if it is code/project (keep intact) "
            f"or an unstructured document batch (dismantle):\n\n"
            f"Folder Name: {folder_name}\n"
            f"Sample Files: {', '.join(sample_files[:20]) if sample_files else 'None'}\n\n"
            f"Folder Manifest:\n{tree_summary}\n\n"
            "Decision Rules:\n"
            "- If it represents a software repo, code project, script collection, or dev environment, "
            f"choose 'keep_intact' and target_folder='Code/{folder_name}'.\n"
            "- If it represents Jupyter/Colab notebooks, choose 'keep_intact' and "
            f"target_folder='Colab Notebooks/{folder_name}'.\n"
            "- If it contains loose personal records, tax forms, receipts, scans, identity documents, bills, "
            "or miscellaneous PDFs/documents, choose 'dismantle'.\n"
        )

        max_attempts = 2
        for attempt in range(1, max_attempts + 1):
            try:
                run_result = self.triage_agent.run_sync(prompt_content)
                decision = run_result.output
                if decision.action not in ("dismantle", "keep_intact"):
                    decision.action = (
                        "keep_intact"
                        if (has_code_signature or has_notebook_signature)
                        else "dismantle"
                    )
                if decision.action == "keep_intact" and not decision.target_folder:
                    target_parent = "Colab Notebooks" if has_notebook_signature else "Code"
                    decision.target_folder = f"{target_parent}/{folder_name}"
                return decision
            except Exception as exc:
                logger.warning(f"LLM folder triage attempt {attempt} failed: {exc}")

        # Fallback to deterministic heuristics
        if has_notebook_signature:
            return FolderTriageDecision(
                action="keep_intact",
                is_code=True,
                target_folder=f"Colab Notebooks/{folder_name}",
                confidence=0.95,
                reasoning="Folder contains Jupyter notebooks; preserving intact in Colab Notebooks.",
            )
        if has_code_signature:
            return FolderTriageDecision(
                action="keep_intact",
                is_code=True,
                target_folder=f"Code/{folder_name}",
                confidence=0.95,
                reasoning="Folder contains programming code or build files; preserving intact in Code/.",
            )

        return FolderTriageDecision(
            action="dismantle",
            is_code=False,
            target_folder=None,
            confidence=0.90,
            reasoning="Folder contains personal files/documents; dismantling and organizing files individually.",
        )

    @property
    def agent(self) -> Agent[None, DocumentClassification]:
        """Return the classifier agent, isolated per thread."""
        if self._explicit_agent is not None:
            return self._explicit_agent

        if not hasattr(self._local, "agent"):
            client = AsyncOpenAI(
                base_url=self.base_url,
                api_key="not-needed",
                timeout=self.timeout,
            )
            provider = OpenAIProvider(openai_client=client)
            model = OpenAIChatModel(self.model_name, provider=provider)
            self._local.agent = Agent(
                model=model,
                output_type=DocumentClassification,
                system_prompt=(
                    "You are an expert personal document organizer for Sudhanva and Maanasa's household.\n\n"
                    "IMPORTANT CONTEXT:\n"
                    "- Primary Owner: Sudhanva (nsudhanva@gmail.com).\n"
                    "- Household: Sudhanva & Maanasa (wife).\n"
                    "- Extended Family: Narayana (father), Narmada (mother), Rashmi (sister).\n"
                    "- Primary Locations: USA (current residence - California / Massachusetts / Boston) and India (origin).\n\n"
                    "PERSON CLASSIFICATION RULES:\n"
                    "- 'Sudhanva': Default owner for all personal, career, work, tech, university, coding, and general documents unless another person is named.\n"
                    "- 'Maanasa': Wife (keywords: Maanasa, Maansi, Narayan).\n"
                    "- 'Narayana': Father (keywords: Narayana Chandran, BoB).\n"
                    "- 'Narmada': Mother (keywords: Narmada).\n"
                    "- 'Rashmi': Sister (keywords: Rashmi).\n"
                    "- 'Unknown': ONLY for external spam, third-party vendor noise, or unidentifiable files.\n\n"
                    "JOINT DOCUMENT RULE (CRITICAL):\n"
                    "- Set is_joint=true if the document mentions, pertains to, or belongs to BOTH Sudhanva and Maanasa.\n"
                    "- Examples of joint documents: Marriage certificates, apartment rental leases (Ironworks, JVue, etc.), joint bank accounts, joint tax filings, health/travel insurance covering both, wedding planning/invitations.\n\n"
                    "JURISDICTION RULES (Do NOT default to Global unless truly universal):\n"
                    "- 'USA': Any document tied to US residency, US universities (Northeastern University / NEU / Boston / Silicon Valley), US employers, US taxes (W-2, 1040), US leases, US visas/immigration (H-1B, I-797, I-94), US health insurance, US driver's licenses (MA, CA).\n"
                    "- 'India': Any document tied to India (Aadhaar, PAN, Indian passport, PES University, Bangalore, Indian banks like SBI/HDFC/BoB, Indian property, Indian taxes/ITR).\n"
                    "- 'Global': ONLY for completely borderless, generic files (e.g. open source code, theoretical computer science books, general philosophy notes).\n\n"
                    "CATEGORY & SUBCATEGORY RULES:\n"
                    "- 'Notebooks': Jupyter and Google Colab notebooks (.ipynb, application/vnd.google.colaboratory). (Routes to 'Colab Notebooks/'). Do NOT classify notebooks as Career or Education!\n"
                    "- 'AI Studio': Google AI Studio and MakerSuite prompts or applets (application/vnd.google-makersuite.*). (Routes to 'Google AI Studio/').\n"
                    "- 'Models': Machine learning model checkpoints and weights (.pt, .pth, .safetensors, .onnx, .bin). (Routes to 'Models/').\n"
                    "- 'Code': Code repositories, scripts, programming files, and dataset archives (.zip, .tar.gz, .py). (Routes to 'Code/').\n"
                    "- 'Books': Published ebooks, textbooks, epubs, technical literature, computer science books, reading books. (Subcategory should be the topic e.g. 'Computer Science', 'Mathematics', 'Machine Learning', 'Data Science', 'Fiction', 'Non-Fiction'). Books are organized into the shared library under Books/[Topic]/.\n"
                    "- 'CVs': Resumes, CVs, and portfolios belonging to OTHER people / external candidates / referrals / applicants (e.g. 'KimberlyDo_CV.pdf'). These do NOT belong to Sudhanva or household members. They route to the top-level shared folder CVs/ (e.g. 'CVs/Kimberly Do - CV.pdf'). Note: Sudhanva's or Maanasa's OWN personal resumes still go to {Person}/Career/Resumes/.\n"
                    "- 'Education': Academic degrees, university transcripts, course assignments, homework, worksheets, lecture notes, syllabus, course codes (e.g. 'CS 5170', 'CS 5800'), college applications, tuition fees, Northeastern University (NEU), PES University. Subcategory should be the institution e.g. 'Northeastern University'.\n"
                    "- 'Career': Job offers, employment agreements, compensation/equity, resumes/CVs, job applications, interview prep plans, LeetCode solutions, company project architectures (e.g. 'Lakshmi', 'Initiable', 'Montai', 'Autodesk', 'Pixxel'). Subcategory should be company name or area (e.g. 'Interview Prep', 'Lakshmi', 'Resumes', 'Startups').\n"
                    "- 'Identity': Passports, Driver's Licenses, State IDs, SSN, Aadhaar, PAN card, Birth Certificate, Marriage Certificate.\n"
                    "- 'Visas & Legal': H-1B, I-797, I-94, Global Entry (GEP), DS-160, US visas, visitor visas.\n"
                    "- 'Taxes': W-2, 1040, 1099, Indian ITR, tax forms. Subcategory MUST be the 4-digit tax year (e.g. '2024', '2023').\n"
                    "- 'Banking': Checking, savings, credit cards, investment statements, fixed deposits.\n"
                    "- 'Housing': Apartment leases, landlord agreements, utility bills (Xfinity, National Grid, Eversource), rent receipts.\n"
                    "- 'Health': Health insurance cards, medical tests, doctor visits, vaccination records, visitor medical insurance.\n"
                    "- 'Vehicle': Auto title, registration, car insurance, RMV records.\n"
                    "- 'Review': Scratch to-do lists, temporary shopping lists, corrupted files, or items with no permanent value.\n\n"
                    "NAMING RULES:\n"
                    "- Standardized, human-readable names without numbers or hashes. Strip annoying tags like '(z-lib.org)' or 'Copy of '."
                ),
            )
        return self._local.agent

    def classify_sync(
        self,
        filename: str,
        extracted_text: str = "",
        mime_type: str = "application/pdf",
        folder_breadcrumbs: list[str] | None = None,
    ) -> DocumentClassification:
        """Classifies a document by reading its content with the local LLM."""
        # 1. Preliminary heuristic scan for contextual hints (non-binding)
        pre_route: PreRouteSuggestion = PreRouter.analyze(
            filename, extracted_text, folder_breadcrumbs=folder_breadcrumbs
        )

        # 2. Construct LLM prompt with actual extracted document text
        text_section = (
            f"--- EXTRACTED DOCUMENT TEXT ---\n{extracted_text[:3500]}\n--- END DOCUMENT TEXT ---"
            if extracted_text.strip()
            else "[No extractable text found in document stream/header - rely on filename and metadata]"
        )

        folder_context = (
            f"Original Folder Path: {' / '.join(folder_breadcrumbs)}\n"
            if folder_breadcrumbs
            else ""
        )

        prompt_content = (
            f"Please inspect and classify the following document:\n"
            f"Filename: {filename}\n"
            f"MIME Type: {mime_type}\n"
            f"{folder_context}"
            f"Preliminary Scan Hint: suggested_person={pre_route.person or 'Sudhanva (default)'}, "
            f"suggested_category={pre_route.category or 'unspecified'}\n\n"
            f"{text_section}\n\n"
            "Instructions:\n"
            "1. Read the document text carefully to identify who it belongs to, what type of document it is, and its jurisdiction.\n"
            "2. Follow the symmetrical family filing schema strictly.\n"
            "3. If the document does not name anyone else, default person to 'Sudhanva'.\n"
            "4. Generate a clean, descriptive human filename, a 1-2 sentence summary, and 3-5 search keywords."
        )

        max_attempts = 3
        backoff_seconds = 10.0
        last_exc: Exception | None = None

        for attempt in range(1, max_attempts + 1):
            try:
                logger.info(
                    f"Submitting '{filename}' to LLM for content analysis (attempt {attempt}/{max_attempts})..."
                )
                run_result = self.agent.run_sync(prompt_content)
                result = run_result.output

                # Normalize and validate outputs
                if result.person not in VALID_PEOPLE or result.person == "Unknown":
                    if (
                        result.category != "Review"
                        and result.confidence >= self.confidence_threshold
                    ):
                        result.person = "Sudhanva"
                    else:
                        result.person = "Unknown"

                if result.jurisdiction not in VALID_JURISDICTIONS:
                    result.jurisdiction = "USA"
                if result.category not in VALID_CATEGORIES:
                    result.category = "Review"

                if result.confidence < self.confidence_threshold:
                    logger.warning(
                        f"Low confidence ({result.confidence:.2f}) for '{filename}'. "
                        "Routing to Review."
                    )
                    result.category = "Review"

                return result

            except Exception as exc:
                last_exc = exc
                err_msg = str(exc)
                logger.warning(
                    f"LLM classify attempt {attempt}/{max_attempts} failed for '{filename}': {err_msg}"
                )
                if attempt < max_attempts:
                    time.sleep(backoff_seconds)

        # Fallback to pre-routing ONLY if LLM completely failed and pre-route is confident
        if (
            pre_route.confidence >= 0.90
            and pre_route.person
            and pre_route.jurisdiction
            and pre_route.category
            and pre_route.clean_filename
        ):
            logger.warning(
                f"LLM call failed; using pre-routing fallback for '{filename}' -> "
                f"{pre_route.person}/{pre_route.jurisdiction}/{pre_route.category}"
            )
            return DocumentClassification(
                person=pre_route.person,
                jurisdiction=pre_route.jurisdiction,
                category=pre_route.category,
                subcategory=pre_route.subcategory,
                clean_filename=pre_route.clean_filename,
                is_joint=pre_route.is_joint,
                confidence=pre_route.confidence,
                summary=pre_route.reason,
                search_tags=[
                    pre_route.person.lower(),
                    pre_route.jurisdiction.lower(),
                    pre_route.category.lower(),
                ],
                reasoning=f"LLM unreachable; pre-routing fallback: {pre_route.reason}",
            )

        raise LLMConnectionError(f"LLM classification failed: {last_exc}")

    @staticmethod
    def resolve_target_folder(cls: DocumentClassification) -> str:
        """Resolves the exact relative destination folder path in Google Drive."""
        if cls.confidence < 0.80 or cls.category == "Review":
            return "Review/Needs Review"

        # Books structure: shared digital library under Books/[Topic]
        if cls.category == "Books":
            topic = cls.subcategory or "General"
            return f"Books/{topic}"

        # External CVs & Resumes: shared top-level folder CVs/
        if cls.category == "CVs":
            if cls.subcategory:
                return f"CVs/{cls.subcategory}"
            return "CVs"

        # Colab / Jupyter Notebooks: Colab Notebooks/
        if cls.category == "Notebooks":
            if cls.subcategory:
                return f"Colab Notebooks/{cls.subcategory}"
            return "Colab Notebooks"

        # Google AI Studio / MakerSuite prompts: Google AI Studio/
        if cls.category == "AI Studio":
            return "Google AI Studio"

        # Machine Learning Model Checkpoints: Models/
        if cls.category == "Models":
            if cls.subcategory:
                return f"Models/{cls.subcategory}"
            return "Models"

        # Code repositories & dataset archives: Code/
        if cls.category == "Code":
            if cls.subcategory:
                return f"Code/{cls.subcategory}"
            return "Code"

        if cls.person == "Unknown":
            return "Review/Needs Review"

        # Education & Career structures
        if cls.category in {"Career", "Education"}:
            if cls.subcategory:
                return f"{cls.person}/{cls.category}/{cls.subcategory}"
            return f"{cls.person}/{cls.category}"

        # Standard symmetrical path: [Person]/[Jurisdiction]/[Category]
        path = f"{cls.person}/{cls.jurisdiction}/{cls.category}"
        if cls.category == "Taxes" and cls.subcategory:
            path = f"{path}/{cls.subcategory}"
        return path
