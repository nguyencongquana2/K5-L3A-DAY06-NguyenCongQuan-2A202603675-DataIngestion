"""Validate split, filters and exact evidence against the selected source PDF."""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

import pymupdf


ROOT = Path(__file__).resolve().parents[2]
QUESTIONS_PATH = ROOT / "benchmark" / "questions.json"
PDF_PATH = ROOT / "data" / "source" / "tutorial.pdf"


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"-\n(?=[a-z])", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def main() -> None:
    questions = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    assert len(questions) >= 20, "at least 20 questions are required"
    assert len({item["id"] for item in questions}) == len(questions), "question IDs must be unique"
    dev = [item for item in questions if item["split"] == "dev"]
    test = [item for item in questions if item["split"] == "test"]
    filtered = [item for item in questions if item.get("filter")]
    assert len(dev) >= 15 and len(test) >= 5, "split must contain at least 15 dev and 5 test"
    assert len(filtered) >= 3, "at least three questions must contain filters"
    assert any(item["split"] == "test" for item in filtered), "at least one filter question must be test"

    with pymupdf.open(PDF_PATH) as document:
        for item in questions:
            page = item["gold_page"]
            assert 1 <= page <= document.page_count, f"{item['id']}: invalid page {page}"
            text = normalize(document[page - 1].get_text())
            evidence = normalize(item["evidence_quote"])
            assert evidence in text, f"{item['id']}: evidence not found on page {page}"

    print(
        f"Benchmark OK: {len(questions)} questions | "
        f"dev={len(dev)} test={len(test)} | filters={len(filtered)}"
    )


if __name__ == "__main__":
    main()
