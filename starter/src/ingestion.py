"""Read PDF pages while preserving source and physical-page traceability."""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import pymupdf

from .models import DocumentPage


def load_pdf(
    path: Path,
    document_id: str,
    source: str,
    page_metadata: dict[int, dict[str, object]] | None = None,
) -> list[DocumentPage]:
    """Extract every physical page and retain empty-page/error information.

    PyMuPDF blocks preserve paragraph boundaries more reliably than flattening the
    complete page. OCR is intentionally not attempted because the selected PDF
    contains a text layer.
    """
    if not path.exists():
        raise FileNotFoundError(path)

    metadata_by_page = page_metadata or {}
    pages: list[DocumentPage] = []
    with pymupdf.open(path) as document:
        for index, pdf_page in enumerate(document):
            page_number = index + 1
            metadata = dict(metadata_by_page.get(page_number, {}))
            try:
                blocks = pdf_page.get_text("blocks", sort=True)
                paragraphs = [normalize_text(block[4]) for block in blocks]
                paragraphs = [
                    paragraph
                    for paragraph in paragraphs
                    if paragraph and not _is_running_matter(paragraph)
                ]
                text = "\n\n".join(paragraphs)
                metadata["extraction_status"] = "ok" if text else "empty"
            except Exception as exc:  # preserve the page and make the failure auditable
                text = ""
                metadata["extraction_status"] = "error"
                metadata["extraction_error"] = f"{type(exc).__name__}: {exc}"
            pages.append(
                DocumentPage(
                    document_id=document_id,
                    source=source,
                    page=page_number,
                    text=text,
                    metadata=metadata,
                )
            )
    return pages


def normalize_text(text: str) -> str:
    """Normalize Unicode and layout whitespace while retaining paragraphs."""
    text = unicodedata.normalize("NFKC", text.replace("\u00ad", ""))
    text = re.sub(r"-\n(?=[a-z])", "", text)
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    text = "\n".join(line for line in lines if line)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _is_running_matter(text: str) -> bool:
    """Drop repeated PDF headers and folio/footer blocks, not source content."""
    if text.startswith("Python Tutorial, Release 3.13.7"):
        return True
    if re.fullmatch(r"\d+", text):
        return True
    return bool(re.match(r"^\d+\n(?:Chapter|Appendix)\b", text))
