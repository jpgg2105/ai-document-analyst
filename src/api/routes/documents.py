"""GET /api/v1/documents and DELETE /api/v1/documents/{id}."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from src.api import document_store
from src.api.schemas import DocumentListResponse, DocumentResponse
from src.ingestion.embedder import delete_document_vectors

router = APIRouter()


@router.get("", response_model=DocumentListResponse)
async def list_documents() -> DocumentListResponse:
    """Return all ingested documents."""
    docs = document_store.list_all()
    return DocumentListResponse(
        documents=[DocumentResponse(**d.to_dict()) for d in docs],
        total=len(docs),
    )


@router.delete("/{document_id}")
async def delete_document(document_id: str) -> dict:
    """Remove a document and all its vectors from Qdrant."""
    doc = document_store.get(document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found.")

    delete_document_vectors(document_id)
    document_store.delete(document_id)
    return {"status": "deleted", "document_id": document_id}
