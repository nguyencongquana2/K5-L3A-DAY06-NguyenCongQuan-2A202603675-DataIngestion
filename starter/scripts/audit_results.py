"""Build the declared manual audit artifact from inspected chunks and traces.

The numeric coherence and grounding labels below are explicit reviewer judgments,
not similarity-score thresholds or LLM-as-a-judge calls.
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

STARTER = Path(__file__).resolve().parents[1]
ROOT = STARTER.parent
sys.path.insert(0, str(STARTER))

from src.chunking import by_paragraph, fixed_size
from src.ingestion import load_pdf


PAGES = [9, 10, 11, 12, 13, 14, 15, 16, 17, 18]
A_LABELS = {
    9: (1, "Starts mid-sentence; the module paragraph is understandable but its preceding subject is missing."),
    10: (2, "All three paragraphs are complete and explain the tutorial progression independently."),
    11: (1, "Starts mid-word and ends mid-sentence, although the central line-editing explanation is usable."),
    12: (1, "Starts in a prior sentence and ends at an unfinished prompt, so both boundaries lose context."),
    13: (1, "Starts with a continuation from the comments explanation before reaching a coherent calculator section."),
    14: (1, "Starts mid-word in an error explanation; the later calculator example is understandable."),
    15: (1, "Starts inside a quoting example, so the initial subject and setup are missing."),
    16: (1, "Begins with a continuation from the previous page and cuts the final example."),
    17: (1, "Begins with the tail of a previous sentence before a coherent slice explanation."),
    18: (1, "Begins with the tail of a previous example before changing to list material."),
}
B_LABELS = {
    9: (1, "Contains complete prose paragraphs but ends with a colon before the promised reason list."),
    10: (2, "Complete, self-contained paragraphs describe what follows in the tutorial."),
    11: (2, "Two complete paragraphs explain interpreter exit and line editing."),
    12: (2, "The interactive-mode explanation and example are complete; the trailing heading is traceable."),
    13: (2, "The calculator subsection includes its setup, examples and numeric-type explanation."),
    14: (2, "The arithmetic and undefined-variable examples retain their explanations and outputs."),
    15: (2, "The print and raw-string discussion includes setup, examples and limitations."),
    16: (1, "The physical page begins as a continuation and the selected group ends inside an error example."),
    17: (2, "The slicing rule, diagram and bounds explanation form a self-contained unit."),
    18: (2, "String immutability is explained with the failing assignment and replacement approach."),
}
GROUNDING_REASONS = {
    "q16": "Top-3 states the class-versus-instance variable distinction and retains page 84.",
    "q17": "Top-3 explicitly states that __next__ raises StopIteration at exhaustion.",
    "q18": "Top-3 contains the exact venv command and surrounding environment-creation context.",
    "q19": "Top-3 explains the inexact binary representation behind the failed decimal equality.",
    "q20": "Top-3 states what doctest scans and validates in docstrings.",
}


def canonical(text: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", text)).strip()


def coherence_samples(manifest: dict, pages_by_number: dict) -> list[dict]:
    records = []
    for page_number in PAGES:
        page = pages_by_number[page_number]
        position = len(page.text) // 2
        chunks_a = fixed_size(page, 800, 120)
        chunk_a = next(
            chunk
            for chunk in chunks_a
            if chunk.metadata["char_start"] <= position < chunk.metadata["char_end"]
        )
        chunks_b = by_paragraph(page, 1000)
        chunk_b = next(
            (
                chunk
                for chunk in chunks_b
                if (start := page.text.find(chunk.text)) <= position < start + len(chunk.text)
            ),
            chunks_b[0],
        )
        for strategy, chunk, labels in (
            ("A", chunk_a, A_LABELS),
            ("B", chunk_b, B_LABELS),
            ("C", chunk_b, B_LABELS),
        ):
            score, reason = labels[page_number]
            records.append(
                {
                    "strategy": strategy,
                    "source_position": {"page": page_number, "normalized_character": position},
                    "chunk_id": chunk.chunk_id,
                    "chunk_text": chunk.text,
                    "score_0_to_2": score,
                    "reason": reason,
                }
            )
    return records


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
    pages_by_number = {page.page: page for page in pages}
    traces = [
        json.loads(line)
        for line in (ROOT / "results" / "traces.jsonl").read_text(encoding="utf-8").splitlines()
    ]

    coherence = coherence_samples(manifest, pages_by_number)
    metadata_records = []
    grounding_records = []
    for trace in traces:
        if trace["split"] != "test":
            continue
        filter_applied = trace["strategy"] == "C" and bool(trace["filter"])
        for hit in trace["hits"][:3]:
            metadata = hit["metadata"]
            expected_category = inventory[metadata["page"]]["category"]
            source_text = canonical(pages_by_number[metadata["page"]].text)
            record = {
                "strategy": trace["strategy"],
                "question_id": trace["question_id"],
                "rank": hit["rank"],
                "chunk_id": hit["chunk_id"],
                "source": metadata.get("source"),
                "page": metadata.get("page"),
                "category": metadata.get("category"),
                "document_id_correct": metadata.get("document_id") == manifest["source_id"],
                "source_correct": metadata.get("source") == manifest["source_path_or_url"]["local"],
                "page_and_text_correct": canonical(hit["text"]) in source_text,
                "category_correct": metadata.get("category") == expected_category,
                "filter_applied": filter_applied,
                "filter_compliant": (
                    metadata.get("category") == trace["filter"]["category"] if filter_applied else None
                ),
            }
            record["complete_and_correct"] = all(
                record[key]
                for key in (
                    "document_id_correct",
                    "source_correct",
                    "page_and_text_correct",
                    "category_correct",
                )
            )
            metadata_records.append(record)

        evidence_ranks = [hit["rank"] for hit in trace["hits"] if hit["evidence_match"]]
        grounding_records.append(
            {
                "strategy": trace["strategy"],
                "question_id": trace["question_id"],
                "score_0_to_2": 2,
                "evidence_ranks": evidence_ranks,
                "reason": GROUNDING_REASONS[trace["question_id"]],
            }
        )

    summary = {"coherence": {}, "metadata": {}, "grounding": {}, "filter": {}}
    for strategy in ("A", "B", "C"):
        coherence_items = [item for item in coherence if item["strategy"] == strategy]
        metadata_items = [item for item in metadata_records if item["strategy"] == strategy]
        grounding_items = [item for item in grounding_records if item["strategy"] == strategy]
        filtered_items = [item for item in metadata_items if item["filter_applied"]]
        summary["coherence"][strategy] = {
            "score_sum": sum(item["score_0_to_2"] for item in coherence_items),
            "samples": len(coherence_items),
            "average_out_of_2": sum(item["score_0_to_2"] for item in coherence_items)
            / len(coherence_items),
        }
        summary["metadata"][strategy] = {
            "complete_and_correct": sum(item["complete_and_correct"] for item in metadata_items),
            "records": len(metadata_items),
        }
        summary["grounding"][strategy] = {
            "score_counts": {
                str(score): sum(item["score_0_to_2"] == score for item in grounding_items)
                for score in (0, 1, 2)
            },
            "average_out_of_2": sum(item["score_0_to_2"] for item in grounding_items)
            / len(grounding_items),
        }
        summary["filter"][strategy] = (
            {
                "compliant_records": sum(item["filter_compliant"] for item in filtered_items),
                "checked_records": len(filtered_items),
                "compliant_questions": 1 if filtered_items and all(item["filter_compliant"] for item in filtered_items) else 0,
                "checked_questions": 1 if filtered_items else 0,
            }
            if filtered_items
            else "N/A (strategy does not apply metadata filters)"
        )

    output = {
        "audit_method": {
            "reviewer": "AI-assisted explicit review; student confirmation required before submission",
            "independence_limit": "The reviewer helped implement the pipeline, so labels are not independent and may be optimistic.",
            "coherence_sampling": "The midpoint of the first 10 sorted counted page IDs was fixed; the chunk containing that position was inspected for each strategy.",
            "metadata_sampling": "All 5 test questions x top-3 hits x 3 strategies (45 records).",
            "grounding_sampling": "All 5 test questions for each strategy; labels judge evidence sufficiency, not LLM answer correctness.",
        },
        "coherence_labels": coherence,
        "metadata_audit": metadata_records,
        "grounding_labels": grounding_records,
        "summary": summary,
    }
    path = ROOT / "results" / "manual_audit.json"
    path.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
