"""BM25 keyword search over the Qdrant payload texts."""

from __future__ import annotations

from qdrant_client.models import FieldCondition, Filter, MatchValue
from rank_bm25 import BM25Okapi

from src.api.middleware.logging import get_logger
from src.config import settings
from src.ingestion.embedder import get_qdrant_client
from src.models import Chunk, RetrievedChunk

logger = get_logger(__name__)


def _fetch_all_chunks(document_id: str | None = None) -> list[dict]:
    """Scroll through Qdrant and return all stored payloads."""
    client = get_qdrant_client()

    scroll_filter = None
    if document_id:
        scroll_filter = Filter(
            must=[
                FieldCondition(
                    key="document_id",
                    match=MatchValue(value=document_id),
                )
            ]
        )

    all_records: list[dict] = []
    offset = None
    while True:
        records, next_offset = client.scroll(
            collection_name=settings.qdrant_collection,
            scroll_filter=scroll_filter,
            limit=256,
            offset=offset,
            with_payload=True,
        )
        for r in records:
            payload = r.payload or {}
            payload["_point_id"] = str(r.id)
            all_records.append(payload)
        if next_offset is None:
            break
        offset = next_offset

    return all_records


def bm25_search(
    query: str,
    top_k: int | None = None,
    document_id: str | None = None,
) -> list[RetrievedChunk]:
    """Run BM25 keyword search over all stored chunks.

    This is intentionally simple — for a production system with millions of
    chunks you would use Elasticsearch or a dedicated BM25 index.  For a
    portfolio project with thousands of chunks this is perfectly adequate.
    """
    top_k = top_k or settings.retrieval_top_k

    records = _fetch_all_chunks(document_id)
    if not records:
        return []

    # Tokenize corpus (lowercased whitespace split)
    corpus_texts = [r.get("text", "") for r in records]
    tokenized_corpus = [doc.lower().split() for doc in corpus_texts]

    bm25 = BM25Okapi(tokenized_corpus)
    tokenized_query = query.lower().split()
    scores = bm25.get_scores(tokenized_query)

    # Pair scores with records and sort descending
    scored = sorted(
        zip(scores, records),
        key=lambda x: x[0],
        reverse=True,
    )[:top_k]

    retrieved: list[RetrievedChunk] = []
    for score, payload in scored:
        if score <= 0:
            continue
        chunk = Chunk(
            chunk_id=payload.get("_point_id", ""),
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
        retrieved.append(RetrievedChunk(chunk=chunk, score=float(score), retrieval_method="bm25"))

    logger.info("bm25_search_complete", query_length=len(query), results=len(retrieved))
    return retrieved
