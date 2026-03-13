"""Simple in-memory document registry.

In a production system this would be backed by PostgreSQL.  For this portfolio
project an in-memory dict is sufficient and keeps dependencies minimal.
"""

from __future__ import annotations

from src.models import DocumentMetadata

_store: dict[str, DocumentMetadata] = {}


def save(doc: DocumentMetadata) -> None:
    _store[doc.document_id] = doc


def get(document_id: str) -> DocumentMetadata | None:
    return _store.get(document_id)


def list_all() -> list[DocumentMetadata]:
    return list(_store.values())


def delete(document_id: str) -> bool:
    return _store.pop(document_id, None) is not None
