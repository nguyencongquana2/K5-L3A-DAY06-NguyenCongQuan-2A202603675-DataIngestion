# Experiment run log

- Run date: 2026-11-13 (Asia/Saigon)
- Command: `python -m src.run --reindex`
- Corpus extraction: 101 counted pages, zero empty/error pages in the counted set.
- Embedding: `sentence-transformers/all-MiniLM-L6-v2`, 384 dimensions, normalized vectors, local CPU, cost USD 0.
- Store: Chroma 1.5.9 persistent local store, cosine distance, HNSW implementation managed by Chroma.
- First model load downloaded public model weights from Hugging Face without authentication. Subsequent verified run used the cached model in Hugging Face offline mode.
- Windows reported that symlink caching was unavailable; Hugging Face used its degraded non-symlink cache. This affects disk use, not model output.
- Reindex counts equal persistent counts (A 381/381, B 308/308, C 308/308). Stable IDs and Chroma upsert prevent duplicate records; the automated store test repeats an upsert and asserts an unchanged count.
- No mock vectors, TF-IDF fallback or silent backend fallback was used.
