"""Create the reproducible corpus manifest for the selected Python Tutorial PDF."""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path

import pymupdf


ROOT = Path(__file__).resolve().parents[2]
PDF_PATH = ROOT / "data" / "source" / "tutorial.pdf"
MANIFEST_PATH = ROOT / "data" / "manifest.json"
TUTORIAL_FIRST_PAGE = 9
TUTORIAL_LAST_PAGE = 122
MIN_CONTENT_CHARS = 500


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"-\n(?=[a-z])", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def category_for(page: int) -> str:
    ranges = [
        (9, 10, "appetite"),
        (11, 12, "interpreter"),
        (13, 22, "basics"),
        (23, 38, "control_flow"),
        (39, 48, "data_structures"),
        (49, 58, "modules"),
        (59, 66, "input_output"),
        (67, 78, "exceptions"),
        (79, 92, "classes"),
        (93, 98, "standard_library"),
        (99, 106, "standard_library_advanced"),
        (107, 110, "virtual_environments"),
        (111, 114, "next_steps"),
        (115, 120, "floating_point"),
        (121, 122, "appendix"),
    ]
    return next(name for start, end, name in ranges if start <= page <= end)


def main() -> None:
    digest = hashlib.sha256(PDF_PATH.read_bytes()).hexdigest()
    pages: list[dict[str, object]] = []
    with pymupdf.open(PDF_PATH) as document:
        physical_pages = document.page_count
        for page_number in range(1, physical_pages + 1):
            text = normalize(document[page_number - 1].get_text())
            in_tutorial = TUTORIAL_FIRST_PAGE <= page_number <= TUTORIAL_LAST_PAGE
            counted = in_tutorial and len(text) >= MIN_CONTENT_CHARS
            pages.append(
                {
                    "page": page_number,
                    "normalized_characters": len(text),
                    "counted_as_content": counted,
                    "category": category_for(page_number) if in_tutorial else None,
                }
            )

    counted_pages = [item["page"] for item in pages if item["counted_as_content"]]
    manifest = {
        "manifest_version": 1,
        "generated_at": "2026-11-13",
        "source_id": "python-tutorial-3.13.7",
        "title": "Python Tutorial, Release 3.13.7",
        "source_path_or_url": {
            "local": "data/source/tutorial.pdf",
            "download_page": "https://docs.python.org/3.13/download.html",
            "archive": "https://docs.python.org/3.13/archives/python-3.13-docs-pdf-a4.zip",
        },
        "license_or_permission": {
            "name": "Python Software Foundation License Version 2",
            "url": "https://docs.python.org/3.13/license.html",
            "note": "Documentation may be used, modified and distributed under the stated license; code examples are additionally Zero-Clause BSD licensed.",
        },
        "accessed_at": "2026-11-13",
        "snapshot": {
            "release": "3.13.7",
            "pdf_creation_date": "2025-10-01",
            "sha256": digest,
        },
        "counting_rule": {
            "physical_pages": physical_pages,
            "candidate_tutorial_pages": [TUTORIAL_FIRST_PAGE, TUTORIAL_LAST_PAGE],
            "minimum_normalized_characters": MIN_CONTENT_CHARS,
            "excluded_sections": ["cover", "contents", "glossary", "license appendices", "index"],
            "content_page_count": len(counted_pages),
            "content_pages": counted_pages,
        },
        "page_inventory": pages,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {MANIFEST_PATH}")
    print(f"Physical pages: {physical_pages}; counted content pages: {len(counted_pages)}")


if __name__ == "__main__":
    main()
