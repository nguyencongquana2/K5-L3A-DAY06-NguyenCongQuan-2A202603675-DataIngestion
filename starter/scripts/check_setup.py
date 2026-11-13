"""Validate local dependencies and the selected corpus without modifying data."""
from pathlib import Path

import chromadb
import pymupdf
import sentence_transformers


ROOT = Path(__file__).resolve().parents[2]
PDF_PATH = ROOT / "data" / "source" / "tutorial.pdf"

if not PDF_PATH.exists():
    raise SystemExit(f"Corpus missing: {PDF_PATH}")

with pymupdf.open(PDF_PATH) as document:
    if document.page_count < 30:
        raise SystemExit(f"Corpus has only {document.page_count} physical pages")
    sample = document[8].get_text().strip()
    if not sample:
        raise SystemExit("PDF opens but page 9 has no extractable text")
    print(f"Corpus: {PDF_PATH.name} | physical pages: {document.page_count}")

print(
    "Dependencies: "
    f"PyMuPDF {pymupdf.__version__} | "
    f"Chroma {chromadb.__version__} | "
    f"sentence-transformers {sentence_transformers.__version__}"
)
print("Setup OK")
