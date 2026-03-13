"""Vector similarity search using Qdrant."""

from __future__ import annotations

from qdrant_client.models import FieldCondition, Filter, MatchValue

from src.api.middleware.logging import get_logger
from src.config import settings
from src.ingestion.embedder import embed_texts, get_qdrant_client
from src.models import Chunk, RetrievedChunk

logger = get_logger(__name__)


def vector_search(
    query: str,
    top_k: int | None = None,
    document_id: str | None = None,
) -> list[RetrievedChunk]:
    """Search Qdrant for the most semantically similar chunks.

    Parameters
    ----------
    query:
        Natural language query string.
    top_k:
        Number of results to return (default from settings).
    document_id:
        If provided, restrict search to chunks from this document.
    """
    top_k = top_k or settings.retrieval_top_k

    query_vector = embed_texts([query])[0]
    client = get_qdrant_client()

    query_filter = None
    if document_id:
        query_filter = Filter(
            must=[
                FieldCondition(
                    key="document_id",
                    match=MatchValue(value=document_id),
                )
            ]
        )

    results = client.search(
        collection_name=settings.qdrant_collection,
        query_vector=query_vector,
        limit=top_k,
        query_filter=query_filter,
        with_payload=True,
    )

    retrieved: list[RetrievedChunk] = []
    for hit in results:
        payload = hit.payload or {}
        chunk = Chunk(
            chunk_id=str(hit.id),
            document_id=payload.get("document_id", ""),
            text=payload.get("text", ""),
            page_number=payload.get("page_number", 0),
            section=payload.get("section", ""),
            chunk_index=payload.get("chunk_index", 0),
            token_count=payload.get("token_count", 0),
            metadata={
                "filename": payload.get("filename", ""),
                "file_type": payload.get("file_type", ""),
            },
        )
        retrieved.append(
            RetrievedChunk(
                chunk=chunk,
                score=hit.score,
                retrieval_method="vector",
            )
        )

    logger.info("vector_search_complete", query_length=len(query), results=len(retrieved))
    return retrieved
