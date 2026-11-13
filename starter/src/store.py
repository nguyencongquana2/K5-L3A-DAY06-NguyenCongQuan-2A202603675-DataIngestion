"""Persistent Chroma vector store with cosine search and metadata filtering."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import chromadb

from .models import Chunk


class ChromaVectorStore:
    ALLOWED_FILTERS = {"category", "document_id", "page", "source"}

    def __init__(self, persist_path: str | Path, dimensions: int) -> None:
        if dimensions <= 0:
            raise ValueError("dimensions must be positive")
        self.persist_path = Path(persist_path)
        self.persist_path.mkdir(parents=True, exist_ok=True)
        self.dimensions = dimensions
        self.client = chromadb.PersistentClient(path=str(self.persist_path))

    def create_schema(self) -> None:
        """Chroma creates its local schema lazily; verify the directory is writable."""
        probe = self.persist_path / ".write_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()

    def upsert(self, strategy: str, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        """Validate and replace one strategy's current set using stable chunk IDs.

        When re-ingesting changed source documents, remove obsolete chunks too.
        """
        if len(chunks) != len(vectors):
            raise ValueError("chunks and vectors must have equal lengths")
        if len({chunk.chunk_id for chunk in chunks}) != len(chunks):
            raise ValueError("chunk IDs must be unique")
        if any(len(vector) != self.dimensions for vector in vectors):
            raise ValueError(f"every vector must have {self.dimensions} dimensions")

        collection = self._collection(strategy)
        current_ids = set(collection.get(include=[])["ids"])
        desired_ids = {chunk.chunk_id for chunk in chunks}
        obsolete = sorted(current_ids - desired_ids)
        if obsolete:
            collection.delete(ids=obsolete)
        if not chunks:
            return

        collection.upsert(
            ids=[chunk.chunk_id for chunk in chunks],
            documents=[chunk.text for chunk in chunks],
            embeddings=vectors,
            metadatas=[self._metadata(chunk) for chunk in chunks],
        )

    def search(self, strategy: str, query_vector: list[float], top_k: int = 3,
               filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Filter trusted fields, rank by cosine distance and return trace-ready hits.

        Chroma binds values through its API; no user value is interpolated into SQL.
        """
        if len(query_vector) != self.dimensions:
            raise ValueError(f"query vector must have {self.dimensions} dimensions")
        if top_k <= 0:
            raise ValueError("top_k must be positive")
        where = None
        if filters:
            unknown = set(filters) - self.ALLOWED_FILTERS
            if unknown:
                raise ValueError(f"unsupported filter fields: {sorted(unknown)}")
            where = filters

        result = self._collection(strategy).query(
            query_embeddings=[query_vector],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        ids = result["ids"][0]
        documents = result["documents"][0]
        metadatas = result["metadatas"][0]
        distances = result["distances"][0]
        return [
            {
                "chunk_id": chunk_id,
                "text": text,
                "score": round(1.0 - float(distance), 8),
                "metadata": metadata,
            }
            for chunk_id, text, metadata, distance in zip(ids, documents, metadatas, distances)
        ]

    def count(self, strategy: str) -> int:
        return self._collection(strategy).count()

    def _collection(self, strategy: str):
        name = f"day6_{strategy.lower()}"
        return self.client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine", "dimensions": self.dimensions},
        )

    @staticmethod
    def _metadata(chunk: Chunk) -> dict[str, str | int | float | bool]:
        metadata: dict[str, str | int | float | bool] = {
            "document_id": chunk.document_id,
            "source": chunk.source,
            "page": chunk.page,
        }
        for key, value in chunk.metadata.items():
            if isinstance(value, (str, int, float, bool)):
                metadata[key] = value
        return metadata


# Backward-compatible name for code based on the original starter contract.
PgVectorStore = ChromaVectorStore
