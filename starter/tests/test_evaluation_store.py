from pathlib import Path

import pytest

from src.evaluation import evaluate_query, summarize
from src.models import Chunk
from src.store import ChromaVectorStore


def chunk(chunk_id: str, page: int, category: str) -> Chunk:
    return Chunk(chunk_id, "doc", "source.pdf", page, f"evidence text {chunk_id}", {"category": category})


def test_store_upsert_search_filter_and_no_duplicates(tmp_path: Path) -> None:
    store = ChromaVectorStore(tmp_path / "chroma", dimensions=3)
    chunks = [chunk("c1", 1, "one"), chunk("c2", 2, "two")]
    vectors = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]
    store.upsert("A", chunks, vectors)
    store.upsert("A", chunks, vectors)
    assert store.count("A") == 2
    assert store.search("A", [1.0, 0.0, 0.0], top_k=1)[0]["chunk_id"] == "c1"
    assert store.search("A", [1.0, 0.0, 0.0], filters={"category": "two"})[0]["chunk_id"] == "c2"
    with pytest.raises(ValueError):
        store.search("A", [1.0, 0.0, 0.0], filters={"gold_page": 1})


def test_evidence_metrics_keep_numerators() -> None:
    question = {
        "id": "q",
        "split": "dev",
        "question": "question",
        "gold_source_id": "doc",
        "gold_page": 2,
        "evidence_quote": "target evidence",
        "filter": None,
    }
    hits = [
        {"chunk_id": "x", "text": "irrelevant", "score": 0.8, "metadata": {"document_id": "doc", "page": 1}},
        {"chunk_id": "y", "text": "Target   evidence is here", "score": 0.7, "metadata": {"document_id": "doc", "page": 2}},
    ]
    trace = evaluate_query(question, hits)
    trace["strategy"] = "A"
    assert trace["hit_at_1"] is False
    assert trace["evidence_hit_at_3"] is True
    summary = summarize([trace])
    assert summary["A"]["dev"]["hit_at_1"]["hits"] == 0
    assert summary["A"]["dev"]["evidence_hit_at_3"]["hits"] == 1
