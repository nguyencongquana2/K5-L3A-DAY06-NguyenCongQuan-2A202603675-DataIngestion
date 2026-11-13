from pathlib import Path

from src.chunking import by_paragraph, fixed_size
from src.ingestion import load_pdf, normalize_text
from src.models import DocumentPage


def test_normalize_text_repairs_line_hyphen_and_unicode() -> None:
    assert normalize_text("Ａ test-\ning\n\n\nnext") == "A testing\nnext"


def test_load_pdf_preserves_physical_pages() -> None:
    root = Path(__file__).resolve().parents[2]
    pages = load_pdf(root / "data" / "source" / "tutorial.pdf", "python", "tutorial.pdf")
    assert len(pages) == 167
    assert pages[8].page == 9
    assert "WHETTING YOUR APPETITE" in pages[8].text
    assert pages[8].metadata["extraction_status"] == "ok"


def sample_page() -> DocumentPage:
    return DocumentPage(
        document_id="doc",
        source="source.pdf",
        page=7,
        text="First complete paragraph.\n\nSecond paragraph has several words.\n\nThird paragraph.",
        metadata={"category": "sample"},
    )


def test_fixed_size_is_bounded_traceable_and_overlapping() -> None:
    chunks = fixed_size(sample_page(), size=45, overlap=10)
    assert len(chunks) >= 2
    assert all(len(chunk.text) <= 45 for chunk in chunks)
    assert all(chunk.page == 7 and chunk.metadata["category"] == "sample" for chunk in chunks)
    assert len({chunk.chunk_id for chunk in chunks}) == len(chunks)
    assert chunks[1].metadata["char_start"] < chunks[0].metadata["char_end"]


def test_paragraph_chunks_keep_boundaries_when_they_fit() -> None:
    chunks = by_paragraph(sample_page(), max_size=50)
    assert all(len(chunk.text) <= 50 for chunk in chunks)
    assert chunks[0].text == "First complete paragraph."
    assert chunks[1].text.startswith("Second paragraph")
    assert all(chunk.metadata["chunking"] == "paragraph" for chunk in chunks)
