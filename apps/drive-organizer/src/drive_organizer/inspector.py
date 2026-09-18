import io
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from PIL import ExifTags, Image
from pypdf import PdfReader

logger = logging.getLogger(__name__)


@dataclass
class DocumentInspection:
    is_media: bool
    media_date: datetime | None = None
    page_count: int = 1
    has_extractable_text: bool = False
    extracted_text: str = ""
    suggested_ext: str = ""


class FileInspector:
    """Inspects file streams using lightweight single-page extraction and EXIF analysis."""

    @staticmethod
    def inspect_bytes(
        filename: str, mime_type: str, file_bytes: bytes, created_time_str: str | None = None
    ) -> DocumentInspection:
        lower_name = filename.lower()
        lower_mime = mime_type.lower()

        # 1. Media handling (Image / Video)
        if (
            lower_mime.startswith("image/")
            or lower_mime.startswith("video/")
            or lower_name.endswith((".jpg", ".jpeg", ".png", ".heic", ".mp4", ".mov", ".m4v"))
        ):
            # Check if this is a document scan saved as an image (e.g. passport or license)
            doc_keywords = [
                "passport",
                "license",
                "aadhaar",
                "aadhar",
                "pan",
                "visa",
                "dl",
                "i-94",
                "w2",
                "tax",
            ]
            is_scan = any(kw in lower_name for kw in doc_keywords)

            if not is_scan:
                exif_date = FileInspector._extract_exif_date(file_bytes)
                if exif_date is None and created_time_str:
                    try:
                        exif_date = datetime.fromisoformat(created_time_str.replace("Z", "+00:00"))
                    except Exception:
                        exif_date = datetime.now()
                return DocumentInspection(
                    is_media=True,
                    media_date=exif_date or datetime.now(),
                    has_extractable_text=False,
                    extracted_text="",
                )

        # 2. PDF inspection (Firecrawl single-page pattern)
        if lower_mime == "application/pdf" or lower_name.endswith(".pdf"):
            return FileInspector._inspect_pdf(file_bytes)

        # 3. Plain text / CSV / Google Workspace exports
        if (
            lower_mime.startswith("text/")
            or lower_mime.startswith("application/vnd.google-apps.")
            or lower_name.endswith((".txt", ".csv", ".json", ".md"))
        ):
            try:
                text = file_bytes[:8000].decode("utf-8", errors="replace")
                return DocumentInspection(
                    is_media=False,
                    page_count=1,
                    has_extractable_text=bool(text.strip()),
                    extracted_text=text[:3500].strip(),
                )
            except Exception as e:
                logger.warning(f"Error decoding text for {filename}: {e}")

        # Fallback
        return DocumentInspection(
            is_media=False,
            has_extractable_text=False,
            extracted_text="",
        )

    @staticmethod
    def _inspect_pdf(file_bytes: bytes) -> DocumentInspection:
        """Inspects PDF, extracting up to the first 3 pages of text for LLM content analysis."""
        try:
            stream = io.BytesIO(file_bytes)
            reader = PdfReader(stream)
            num_pages = len(reader.pages)
            if num_pages == 0:
                return DocumentInspection(is_media=False, page_count=0, has_extractable_text=False)

            extracted_chunks: list[str] = []
            for p_idx in range(min(num_pages, 3)):
                page_text = reader.pages[p_idx].extract_text() or ""
                stripped = page_text.strip()
                if stripped:
                    extracted_chunks.append(f"[Page {p_idx + 1}]\n{stripped}")

            full_text = "\n\n".join(extracted_chunks)
            has_text = len(full_text.strip()) > 30
            truncated = full_text.strip()[:3500]

            return DocumentInspection(
                is_media=False,
                page_count=num_pages,
                has_extractable_text=has_text,
                extracted_text=truncated,
            )
        except Exception as e:
            logger.warning(f"Error reading PDF bytes: {e}")
            return DocumentInspection(is_media=False, has_extractable_text=False)

    @staticmethod
    def _extract_exif_date(file_bytes: bytes) -> datetime | None:
        """Extracts DateTimeOriginal or DateTimeDigitized from image bytes."""
        try:
            image = Image.open(io.BytesIO(file_bytes))
            exif_raw: Any = image.getexif()
            if not exif_raw:
                return None

            date_str = None
            for tag_id, val in exif_raw.items():
                tag_name = ExifTags.TAGS.get(tag_id, tag_id)
                if tag_name in ("DateTimeOriginal", "DateTimeDigitized", "DateTime") and isinstance(
                    val, str
                ):
                    date_str = val
                    break

            if date_str:
                for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y:%m:%d"):
                    try:
                        return datetime.strptime(date_str.strip(), fmt)
                    except ValueError:
                        continue
        except Exception:
            return None
        return None
