"""Evidence-aware retrieval evaluation and aggregation."""
from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from typing import Any


def evaluate_query(question: dict[str, Any], hits: list[dict[str, Any]]) -> dict[str, Any]:
    """Check source/page and evidence containment; preserve the complete top-k trace.

    Accept any documented alternative gold evidence. Do not infer human grounding
    or chunk coherence labels from exact string match.
    """
    golds = question.get("gold_evidence") or [
        {
            "source_id": question["gold_source_id"],
            "page": question["gold_page"],
            "evidence_quote": question["evidence_quote"],
        }
    ]

    evaluated_hits = []
    for rank, hit in enumerate(hits, start=1):
        metadata = hit.get("metadata", {})
        text = _canonical(hit.get("text", ""))
        matched = any(
            metadata.get("document_id") == gold["source_id"]
            and metadata.get("page") == gold["page"]
            and _canonical(gold["evidence_quote"]) in text
            for gold in golds
        )
        evaluated_hits.append({**hit, "rank": rank, "evidence_match": matched})

    return {
        "question_id": question["id"],
        "split": question["split"],
        "question": question["question"],
        "filter": question.get("filter"),
        "gold_source_id": question["gold_source_id"],
        "gold_page": question["gold_page"],
        "evidence_quote": question["evidence_quote"],
        "hit_at_1": bool(evaluated_hits and evaluated_hits[0]["evidence_match"]),
        "evidence_hit_at_3": any(hit["evidence_match"] for hit in evaluated_hits[:3]),
        "hits": evaluated_hits,
    }


def summarize(traces: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate Hit@1 and Evidence Hit@3 by strategy and split."""
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for trace in traces:
        groups[(trace["strategy"], trace["split"])].append(trace)

    output: dict[str, Any] = {}
    for (strategy, split), items in sorted(groups.items()):
        hit1 = sum(bool(item["hit_at_1"]) for item in items)
        hit3 = sum(bool(item["evidence_hit_at_3"]) for item in items)
        total = len(items)
        output.setdefault(strategy, {})[split] = {
            "questions": total,
            "hit_at_1": {"hits": hit1, "total": total, "rate": hit1 / total},
            "evidence_hit_at_3": {"hits": hit3, "total": total, "rate": hit3 / total},
        }
    return output


def _canonical(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).casefold()
    text = re.sub(r"\s+", " ", text)
    return text.strip()
