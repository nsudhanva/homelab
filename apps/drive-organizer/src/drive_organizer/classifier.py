import logging
import os
import threading
import time

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
    "Review",
}


class LLMConnectionError(RuntimeError):
    """Raised when the LLM server is unreachable or times out."""

    pass


class DocumentClassification(BaseModel):
    person: str = Field(
        description="Whose document: Sudhanva, Maanasa, Narayana, Narmada, Rashmi, or Unknown"
    )
    jurisdiction: str = Field(description="Legal jurisdiction: USA, India, or Global")
    category: str = Field(
        description="Category: Identity, Visas & Legal, Taxes, Banking, Housing, Health, Vehicle, Career, Education, or Review"
    )
    subcategory: str | None = Field(
        default=None,
        description="Optional subfolder, e.g. '2024' or '2025' for Taxes, or company name for Career",
    )
    clean_filename: str = Field(
        description="Clean, human-readable filename, e.g. 'Maanasa - California Driver License.pdf'"
    )
    is_joint: bool = Field(
        default=False,
        description="True if document belongs jointly to both Sudhanva and Maanasa (e.g. Marriage cert, lease, joint 1040)",
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
        agent: Agent[None, DocumentClassification] | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self.confidence_threshold = confidence_threshold
        self.timeout = timeout_seconds
        self._explicit_agent = agent
        self._local = threading.local()

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
                    "You are an expert personal document organizer for Sudhanva's household.\n"
                    "IMPORTANT CONTEXT: This is SUDHANVA'S personal Google Drive (nsudhanva@gmail.com).\n"
                    "DEFAULT PERSON RULE: Sudhanva is the primary user and default owner of this Drive. "
                    "Unless a document specifically names or belongs to Maanasa (wife), Narayana (father), "
                    "Narmada (mother), or Rashmi (sister), always assign person='Sudhanva'. "
                    "Do NOT assign 'Unknown' simply because the document does not mention the name 'Sudhanva' - "
                    "personal projects, career files, coding notes, finances, and general receipts default to Sudhanva.\n\n"
                    "ALLOWED PEOPLE:\n"
                    "- 'Sudhanva': Default owner for all personal, career, education, finance, and household files\n"
                    "- 'Maanasa': Wife (keywords: Maanasa, Maansi)\n"
                    "- 'Narayana': Father (keywords: Narayana Chandran, Bank of Baroda)\n"
                    "- 'Narmada': Mother (keywords: Narmada)\n"
                    "- 'Rashmi': Sister (keywords: Rashmi)\n"
                    "- 'Unknown': Only for completely ambiguous, corrupt, or unidentifiable external files\n\n"
                    "ALLOWED JURISDICTIONS:\n"
                    "- 'USA'\n"
                    "- 'India'\n"
                    "- 'Global'\n\n"
                    "ALLOWED CATEGORIES:\n"
                    "- 'Identity': Passports, Driver Licenses, State IDs, SSN, Aadhaar, PAN card, Birth/Marriage certs\n"
                    "- 'Visas & Legal': H-1B, I-797, I-94, Global Entry (GEP), DS-160, visitor visas\n"
                    "- 'Taxes': W-2, Form 1040, 1099, Indian ITR, tax filings (subcategory should be the 4-digit tax year e.g. '2024')\n"
                    "- 'Banking': Checking/savings statements, fixed deposits, credit cards\n"
                    "- 'Housing': Leases (Ironworks, JVue), utility bills (Xfinity, Eversource, National Grid)\n"
                    "- 'Health': Medical records, MRI scans, health insurance cards, doctor reports\n"
                    "- 'Vehicle': Car registration, insurance, RMV crash reports\n"
                    "- 'Career': Resumes, employment contracts, offer letters, coding challenges, Leetcode, project architectures (e.g. Lakshmi)\n"
                    "- 'Education': University degrees, transcripts, marksheets, tuition, attendance costs (e.g. NEU, Northeastern, PES)\n"
                    "- 'Review': Fallback if ambiguous\n\n"
                    "JOINT RULES:\n"
                    "- Set is_joint=true if the document is shared equally between Sudhanva and Maanasa "
                    "(e.g. Marriage Certificate, Apartment Lease with co-tenants, Joint 1040 Tax Return).\n\n"
                    "NAMING RULES:\n"
                    "- Clean, human names without hashes or numbers. Examples: "
                    "'Maanasa - California Driver License.pdf', 'Sudhanva - Aadhaar Card.pdf', "
                    "'2024 W-2 (Montai).pdf', 'Marriage Certificate.pdf'."
                ),
            )
        return self._local.agent

    def classify_sync(
        self,
        filename: str,
        extracted_text: str = "",
        mime_type: str = "application/pdf",
    ) -> DocumentClassification:
        """Classifies a document with deterministic pre-routing and LLM fallback/validation."""
        # 1. Deterministic Pre-routing check
        pre_route: PreRouteSuggestion = PreRouter.analyze(filename, extracted_text)
        if (
            pre_route.confidence >= 0.95
            and pre_route.person
            and pre_route.jurisdiction
            and pre_route.category
            and pre_route.clean_filename
        ):
            logger.info(
                f"Deterministic pre-routing hit for '{filename}' -> "
                f"{pre_route.person}/{pre_route.jurisdiction}/{pre_route.category} ({pre_route.reason})"
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
                reasoning=pre_route.reason,
            )

        # 2. LLM Classification via Pydantic AI with retry
        prompt_content = (
            f"Filename: {filename}\n"
            f"MIME Type: {mime_type}\n"
            f"Pre-router hint: person={pre_route.person or 'unknown'}, "
            f"category={pre_route.category or 'unknown'}\n"
            f"Extracted First Page Text:\n"
            f"---\n{extracted_text[:1800]}\n---\n"
            "Classify this document following the symmetrical person and jurisdiction taxonomy."
        )

        max_attempts = 3
        backoff_seconds = 10.0
        last_exc: Exception | None = None

        for attempt in range(1, max_attempts + 1):
            try:
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
                else:
                    raise LLMConnectionError(
                        f"LLM endpoint unreachable after {max_attempts} attempts: {exc}"
                    ) from exc

        raise LLMConnectionError(f"LLM classification failed: {last_exc}")

    @staticmethod
    def resolve_target_folder(cls: DocumentClassification) -> str:
        """Resolves the exact relative destination folder path in Google Drive."""
        if cls.confidence < 0.80 or cls.category == "Review" or cls.person == "Unknown":
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
