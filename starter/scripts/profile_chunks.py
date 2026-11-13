"""Profile the two chunking strategies before embeddings are generated."""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

STARTER = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STARTER))

from src.chunking import by_paragraph, fixed_size
from src.ingestion import load_pdf


ROOT = Path(__file__).resolve().parents[2]


def describe(lengths: list[int]) -> dict[str, float | int]:
    return {
        "count": len(lengths),
        "total_characters": sum(lengths),
        "minimum": min(lengths),
        "median": statistics.median(lengths),
        "mean": round(statistics.mean(lengths), 2),
        "maximum": max(lengths),
    }


def main() -> None:
    manifest = json.loads((ROOT / "data" / "manifest.json").read_text(encoding="utf-8"))
    inventory = {
        item["page"]: {"category": item["category"]}
        for item in manifest["page_inventory"]
        if item["counted_as_content"]
    }
    pages = load_pdf(
        ROOT / manifest["source_path_or_url"]["local"],
        manifest["source_id"],
        manifest["source_path_or_url"]["local"],
        inventory,
    )
    pages = [page for page in pages if page.page in inventory]
    fixed = [chunk for page in pages for chunk in fixed_size(page, size=800, overlap=120)]
    paragraph = [chunk for page in pages for chunk in by_paragraph(page, max_size=1000)]
    output = {
        "corpus_pages": len(pages),
        "empty_or_error_pages": [
            page.page for page in pages if page.metadata["extraction_status"] != "ok"
        ],
        "A_fixed_800_overlap_120": describe([len(chunk.text) for chunk in fixed]),
        "B_paragraph_max_1000": describe([len(chunk.text) for chunk in paragraph]),
        "C_paragraph_max_1000_with_filter": describe([len(chunk.text) for chunk in paragraph]),
    }
    path = ROOT / "results" / "chunk_profile.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
