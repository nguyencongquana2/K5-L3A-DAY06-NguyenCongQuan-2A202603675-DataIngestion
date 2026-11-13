"""Fixed-window and paragraph-aware chunking with stable source IDs."""
from __future__ import annotations

from .models import Chunk, DocumentPage


def fixed_size(page: DocumentPage, size: int, overlap: int) -> list[Chunk]:
    """Split text into overlapping character windows without crossing pages."""
    if size <= 0:
        raise ValueError("size must be positive")
    if overlap < 0 or overlap >= size:
        raise ValueError("overlap must satisfy 0 <= overlap < size")
    if not page.text.strip():
        return []

    chunks: list[Chunk] = []
    start = 0
    index = 0
    while start < len(page.text):
        end = min(start + size, len(page.text))
        if end < len(page.text):
            boundary = page.text.rfind(" ", start + size // 2, end)
            if boundary > start:
                end = boundary
        text = page.text[start:end].strip()
        if text:
            metadata = dict(page.metadata)
            metadata.update({"chunking": "fixed", "char_start": start, "char_end": end})
            chunks.append(
                Chunk(
                    chunk_id=f"{page.document_id}:p{page.page:03d}:fixed:{index:03d}",
                    document_id=page.document_id,
                    source=page.source,
                    page=page.page,
                    text=text,
                    metadata=metadata,
                )
            )
            index += 1
        if end == len(page.text):
            break
        start = max(end - overlap, start + 1)
    return chunks


def by_paragraph(page: DocumentPage, max_size: int) -> list[Chunk]:
    """Group complete PDF text blocks up to max_size, splitting oversized blocks."""
    if max_size <= 0:
        raise ValueError("max_size must be positive")
    paragraphs = [item.strip() for item in page.text.split("\n\n") if item.strip()]
    if not paragraphs:
        return []

    groups: list[str] = []
    current = ""
    for paragraph in paragraphs:
        pieces = _split_oversized(paragraph, max_size)
        for piece in pieces:
            candidate = f"{current}\n\n{piece}" if current else piece
            if len(candidate) <= max_size:
                current = candidate
            else:
                if current:
                    groups.append(current)
                current = piece
    if current:
        groups.append(current)

    chunks: list[Chunk] = []
    for index, text in enumerate(groups):
        metadata = dict(page.metadata)
        metadata.update({"chunking": "paragraph", "paragraph_group": index})
        chunks.append(
            Chunk(
                chunk_id=f"{page.document_id}:p{page.page:03d}:paragraph:{index:03d}",
                document_id=page.document_id,
                source=page.source,
                page=page.page,
                text=text,
                metadata=metadata,
            )
        )
    return chunks


def _split_oversized(text: str, max_size: int) -> list[str]:
    pieces: list[str] = []
    remaining = text
    while len(remaining) > max_size:
        boundary = remaining.rfind(" ", max_size // 2, max_size + 1)
        if boundary < 1:
            boundary = max_size
        pieces.append(remaining[:boundary].strip())
        remaining = remaining[boundary:].strip()
    if remaining:
        pieces.append(remaining)
    return pieces
