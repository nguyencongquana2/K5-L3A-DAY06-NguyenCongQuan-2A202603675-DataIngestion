"""Local semantic embedding adapter used consistently for documents and queries."""
from __future__ import annotations

from typing import Protocol

from sentence_transformers import SentenceTransformer


class Embedder(Protocol):
    model_name: str
    dimensions: int

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Return one vector per input text, in the same order."""
        ...

    def embed_query(self, question: str) -> list[float]:
        """Return a query vector compatible with the stored document vectors."""
        ...


class MyEmbedder:
    """Sentence Transformers adapter; failures are surfaced without mock fallback."""

    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self._model = SentenceTransformer(model_name)
        dimension = self._model.get_embedding_dimension()
        if not dimension:
            raise RuntimeError(f"Could not determine dimensions for {model_name}")
        self.dimensions = int(dimension)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors = self._model.encode(
            texts,
            batch_size=32,
            show_progress_bar=False,
            normalize_embeddings=True,
        )
        return vectors.tolist()

    def embed_query(self, question: str) -> list[float]:
        if not question.strip():
            raise ValueError("question must not be empty")
        vector = self._model.encode(question, normalize_embeddings=True)
        return vector.tolist()
