"""Recursive text chunking with configurable size, overlap, and token counting."""

from __future__ import annotations

import tiktoken

from src.api.middleware.logging import get_logger
from src.config import settings
from src.ingestion.parser import ParsedDocument
from src.models import Chunk

logger = get_logger(__name__)

# Separators ordered from largest to smallest logical boundary
_SEPARATORS: list[str] = ["\n\n", "\n", ". ", " ", ""]


def _count_tokens(text: str, encoding_name: str = "cl100k_base") -> int:
    """Count tokens using tiktoken (cl100k_base covers GPT-4 / GPT-3.5)."""
    enc = tiktoken.get_encoding(encoding_name)
    return len(enc.encode(text))


def _recursive_split(
    text: str,
    max_tokens: int,
    separators: list[str] | None = None,
) -> list[str]:
    """Split *text* into pieces of at most *max_tokens* tokens.

    Tries the largest separator first; falls back to smaller ones when a
    segment is still too large.
    """
    if separators is None:
        separators = list(_SEPARATORS)

    if _count_tokens(text) <= max_tokens:
        return [text]

    if not separators:
        # Last resort: hard-cut by characters (shouldn't happen often)
        enc = tiktoken.get_encoding("cl100k_base")
        tokens = enc.encode(text)
        pieces: list[str] = []
        for i in range(0, len(tokens), max_tokens):
            pieces.append(enc.decode(tokens[i : i + max_tokens]))
        return pieces

    sep = separators[0]
    remaining_seps = separators[1:]
    parts = text.split(sep) if sep else list(text)

    chunks: list[str] = []
    current: list[str] = []
    current_tokens = 0

    for part in parts:
        part_tokens = _count_tokens(part)
        # If a single part exceeds max_tokens, recurse with smaller sep
        if part_tokens > max_tokens:
            # Flush accumulated text first
            if current:
                chunks.append(sep.join(current))
                current, current_tokens = [], 0
            chunks.extend(_recursive_split(part, max_tokens, remaining_seps))
            continue

        if current_tokens + part_tokens > max_tokens and current:
            chunks.append(sep.join(current))
            current, current_tokens = [], 0

        current.append(part)
        current_tokens += part_tokens

    if current:
        chunks.append(sep.join(current))

    return chunks


def _add_overlap(pieces: list[str], overlap_tokens: int) -> list[str]:
    """Re-create chunks so that each one includes *overlap_tokens* from the
    end of the previous chunk, giving the model continuity at boundaries."""
    if overlap_tokens <= 0 or len(pieces) <= 1:
        return pieces

    enc = tiktoken.get_encoding("cl100k_base")
    result: list[str] = [pieces[0]]

    for i in range(1, len(pieces)):
        prev_tokens = enc.encode(pieces[i - 1])
        overlap_part = enc.decode(prev_tokens[-overlap_tokens:])
        result.append(overlap_part + " " + pieces[i])

    return result


def chunk_document(
    parsed: ParsedDocument,
    document_id: str,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[Chunk]:
    """Split a parsed document into overlapping token-counted chunks.

    Parameters
    ----------
    parsed:
        Output of the parser.
    document_id:
        UUID linking chunks back to their source document.
    chunk_size:
        Max tokens per chunk (default from settings).
    chunk_overlap:
        Number of overlapping tokens between consecutive chunks (default from settings).
    """
    chunk_size = chunk_size or settings.chunk_size
    chunk_overlap = chunk_overlap or settings.chunk_overlap

    logger.info(
        "chunking_document",
        filename=parsed.filename,
        pages=parsed.total_pages,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    all_chunks: list[Chunk] = []
    chunk_index = 0

    for page in parsed.pages:
        raw_pieces = _recursive_split(page.text, chunk_size)
        pieces = _add_overlap(raw_pieces, chunk_overlap)

        for piece in pieces:
            text = piece.strip()
            if not text:
                continue
            all_chunks.append(
                Chunk(
                    document_id=document_id,
                    text=text,
                    page_number=page.page_number,
                    section=page.section,
                    chunk_index=chunk_index,
                    token_count=_count_tokens(text),
                    metadata={
                        "filename": parsed.filename,
                        "file_type": parsed.file_type,
                    },
                )
            )
            chunk_index += 1

    logger.info(
        "chunking_complete",
        filename=parsed.filename,
        total_chunks=len(all_chunks),
    )
    return all_chunks
