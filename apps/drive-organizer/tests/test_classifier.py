from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    ToolCallPart,
    UserPromptPart,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel

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

    # 5. Books structure: Books/[Topic]
    cls_book = DocumentClassification(
        person="Sudhanva",
        jurisdiction="Global",
        category="Books",
        subcategory="Computer Science",
        clean_filename="The Algorithm Design Manual.pdf",
        confidence=0.95,
        summary="Skiena algorithms textbook",
        reasoning="Technical book",
    )
    assert DriveClassifier.resolve_target_folder(cls_book) == "Books/Computer Science"

    # 6. CVs structure: CVs/
    cls_cv = DocumentClassification(
        person="Unknown",
        jurisdiction="Global",
        category="CVs",
        clean_filename="Kimberly Do - CV.pdf",
        confidence=0.95,
        summary="Candidate resume",
        reasoning="External candidate CV",
    )
    assert DriveClassifier.resolve_target_folder(cls_cv) == "CVs"

    # 7. Colab Notebooks structure: Colab Notebooks/
    cls_nb = DocumentClassification(
        person="Sudhanva",
        jurisdiction="Global",
        category="Notebooks",
        clean_filename="fine-tuning-llama-2.ipynb",
        confidence=0.98,
        summary="Jupyter notebook for Llama 2 fine-tuning",
        reasoning="Colab notebook",
    )
    assert DriveClassifier.resolve_target_folder(cls_nb) == "Colab Notebooks"

    # 8. Google AI Studio structure: Google AI Studio/
    cls_ais = DocumentClassification(
        person="Sudhanva",
        jurisdiction="Global",
        category="AI Studio",
        clean_filename="Doc-Generator.prompt",
        confidence=0.98,
        summary="AI prompt experiment",
        reasoning="MakerSuite prompt",
    )
    assert DriveClassifier.resolve_target_folder(cls_ais) == "Google AI Studio"

    # 9. ML Models structure: Models/
    cls_model = DocumentClassification(
        person="Sudhanva",
        jurisdiction="Global",
        category="Models",
        clean_filename="WeatherMesh3.pt",
        confidence=0.98,
        summary="PyTorch model weights",
        reasoning="Model checkpoint",
    )
    assert DriveClassifier.resolve_target_folder(cls_model) == "Models"


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


def test_classify_sync_feeds_extracted_text_to_llm(make_task):
    mock_output = DocumentClassification(
        person="Sudhanva",
        jurisdiction="USA",
        category="Career",
        subcategory="Interview Prep",
        clean_filename="LeetCode Solutions.pdf",
        is_joint=False,
        confidence=0.92,
        summary="Sudhanva's coding challenge practice",
        search_tags=["leetcode", "interview", "algorithms"],
        reasoning="Document contains dynamic programming solutions",
    )

    prompts: list[str] = []

    def capture(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        request = messages[-1]
        assert isinstance(request, ModelRequest)
        prompts.extend(str(p.content) for p in request.parts if isinstance(p, UserPromptPart))
        return ModelResponse(
            parts=[ToolCallPart(info.output_tools[0].name, mock_output.model_dump())]
        )

    classifier = DriveClassifier(
        document_task=make_task(DocumentClassification, FunctionModel(capture))
    )

    res = classifier.classify_sync(
        filename="LeetCode Progress Notes.pdf",
        extracted_text="Two Sum, 3Sum, LRU Cache implementation details and runtime analysis",
        mime_type="application/pdf",
    )

    assert "Two Sum, 3Sum, LRU Cache" in prompts[0]
    assert "--- EXTRACTED DOCUMENT TEXT ---" in prompts[0]
    assert res.clean_filename == "LeetCode Solutions.pdf"
    assert res.category == "Career"
    assert res.subcategory == "Interview Prep"
    assert res.confidence == 0.92
