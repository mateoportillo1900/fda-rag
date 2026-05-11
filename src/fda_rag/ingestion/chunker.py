"""Split parsed label sections into overlapping text chunks."""

from __future__ import annotations

from dataclasses import dataclass

from fda_rag.ingestion.parser import ParsedLabel

# ~1500 chars ≈ 375 tokens at 4 chars/token — sits in the retrieval sweet spot
CHUNK_SIZE = 1500
OVERLAP = 200


@dataclass
class Chunk:
    drug_name: str
    set_id: str
    section_code: str
    section_name: str
    chunk_index: int
    chunk_text: str


def _split_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Sliding-window split. Returns the original text as one chunk if it fits."""
    if len(text) <= chunk_size:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(text):
        window = text[start : start + chunk_size].strip()
        if window:
            chunks.append(window)
        if start + chunk_size >= len(text):
            break
        start += chunk_size - overlap

    return chunks


def chunk_label(
    label: ParsedLabel,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = OVERLAP,
) -> list[Chunk]:
    """Flatten all sections of a ParsedLabel into a list of Chunks."""
    chunks: list[Chunk] = []
    for section in label.sections:
        for idx, window in enumerate(_split_text(section.text, chunk_size, overlap)):
            chunks.append(
                Chunk(
                    drug_name=label.drug_name,
                    set_id=label.set_id,
                    section_code=section.code,
                    section_name=section.name,
                    chunk_index=idx,
                    chunk_text=window,
                )
            )
    return chunks
