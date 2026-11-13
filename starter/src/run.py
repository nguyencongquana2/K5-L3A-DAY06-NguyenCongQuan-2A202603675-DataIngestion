"""Reproducible Day 06 ingestion and retrieval experiment entry point."""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv

from .chunking import by_paragraph, fixed_size
from .embeddings import MyEmbedder
from .evaluation import evaluate_query, summarize
from .ingestion import load_pdf
from .store import ChromaVectorStore


ROOT = Path(__file__).resolve().parents[2]
STARTER = ROOT / "starter"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reindex", action="store_true", help="re-embed and upsert all strategies")
    parser.add_argument("--skip-test", action="store_true", help="run dev only while tuning")
    args = parser.parse_args()

    load_dotenv(STARTER / ".env")
    manifest = _read_json(ROOT / "data" / "manifest.json")
    questions = _read_json(ROOT / "benchmark" / "questions.json")
    if manifest["counting_rule"]["content_page_count"] < 30:
        raise RuntimeError("corpus does not satisfy the 30-content-page requirement")

    inventory = {
        item["page"]: {"category": item["category"], "release": manifest["snapshot"]["release"]}
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
    errors = [page for page in pages if page.metadata["extraction_status"] != "ok"]
    if errors:
        raise RuntimeError(f"extraction failed for pages: {[page.page for page in errors]}")

    strategies = {
        "A": [chunk for page in pages for chunk in fixed_size(page, 800, 120)],
        "B": [chunk for page in pages for chunk in by_paragraph(page, 1000)],
    }
    strategies["C"] = strategies["B"]

    model_name = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    chroma_setting = os.getenv("CHROMA_PATH", ".chroma")
    chroma_path = Path(chroma_setting)
    if not chroma_path.is_absolute():
        chroma_path = STARTER / chroma_path
    embedder = MyEmbedder(model_name)
    store = ChromaVectorStore(chroma_path, embedder.dimensions)
    store.create_schema()

    ingest_stats: dict[str, object] = {
        "model": model_name,
        "dimensions": embedder.dimensions,
        "vector_store": f"Chroma {__import__('chromadb').__version__}",
        "metric": "cosine",
        "cost_usd": 0,
        "strategies": {},
    }
    vectors_b = None
    for strategy, chunks in strategies.items():
        started = time.perf_counter()
        if args.reindex or store.count(strategy) != len(chunks):
            if strategy == "C" and vectors_b is not None:
                vectors = vectors_b
            else:
                vectors = embedder.embed_documents([chunk.text for chunk in chunks])
                if strategy == "B":
                    vectors_b = vectors
            store.upsert(strategy, chunks, vectors)
        elapsed = time.perf_counter() - started
        ingest_stats["strategies"][strategy] = {
            "chunk_count": len(chunks),
            "stored_count": store.count(strategy),
            "elapsed_seconds": round(elapsed, 3),
            "chunking": "fixed size=800 overlap=120" if strategy == "A" else "paragraph max_size=1000",
            "filter": strategy == "C",
        }

    selected_questions = [q for q in questions if not args.skip_test or q["split"] == "dev"]
    traces = []
    for strategy in strategies:
        for question in selected_questions:
            query_vector = embedder.embed_query(question["question"])
            filters = question.get("filter") if strategy == "C" else None
            hits = store.search(strategy, query_vector, top_k=3, filters=filters)
            trace = evaluate_query(question, hits)
            trace["strategy"] = strategy
            traces.append(trace)

    results_dir = ROOT / "results"
    results_dir.mkdir(exist_ok=True)
    _write_json(results_dir / "ingestion_stats.json", ingest_stats)
    _write_json(results_dir / "metrics.json", summarize(traces))
    with (results_dir / "traces.jsonl").open("w", encoding="utf-8") as stream:
        for trace in traces:
            stream.write(json.dumps(trace, ensure_ascii=False) + "\n")

    print(json.dumps(summarize(traces), indent=2))
    print(f"Saved {len(traces)} traces to {results_dir}")


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
