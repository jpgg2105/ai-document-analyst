"""POST /api/v1/query — ask a question over ingested documents."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from src.api.middleware.logging import get_logger
from src.api.schemas import QueryRequest, QueryResponse, SourceChunk
from src.config import settings
from src.generation.generator import generate_answer, generate_answer_stream
from src.retrieval.bm25_search import bm25_search
from src.retrieval.fusion import reciprocal_rank_fusion
from src.retrieval.reranker import rerank
from src.retrieval.vector_search import vector_search

logger = get_logger(__name__)
router = APIRouter()


async def _retrieve(query: str, document_id: str | None = None):
    """Run the full hybrid retrieval pipeline: vector → BM25 → RRF → rerank."""
    # 1. Vector search
    vector_results = vector_search(query, top_k=settings.retrieval_top_k, document_id=document_id)

    # 2. BM25 keyword search
    bm25_results = bm25_search(query, top_k=settings.retrieval_top_k, document_id=document_id)

    # 3. Reciprocal Rank Fusion
    fused = reciprocal_rank_fusion(vector_results, bm25_results, top_k=settings.retrieval_top_k)

    # 4. Cross-encoder reranking
    reranked = rerank(query, fused, top_k=settings.rerank_top_k)

    return reranked


@router.post("/query", response_model=QueryResponse)
async def query_documents(body: QueryRequest) -> QueryResponse | StreamingResponse:
    """Ask a question and get a cited answer.

    When ``stream=true`` the response is sent as Server-Sent Events.
    """
    logger.info("query_received", query=body.query, stream=body.stream)

    retrieved = await _retrieve(body.query, body.document_id)

    # ---- Streaming path ----
    if body.stream:

        async def event_generator():
            async for token in generate_answer_stream(body.query, retrieved):
                yield f"data: {token}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    # ---- Standard path ----
    result = await generate_answer(body.query, retrieved)

    sources = [
        SourceChunk(
            chunk_id=rc.chunk.chunk_id,
            text=rc.chunk.text,
            filename=rc.chunk.metadata.get("filename", ""),
            page_number=rc.chunk.page_number,
            section=rc.chunk.section,
            score=round(rc.score, 4),
            retrieval_method=rc.retrieval_method,
        )
        for rc in result.sources
    ]

    return QueryResponse(
        answer=result.answer,
        sources=sources,
        confidence=round(result.confidence, 4),
        query=result.query,
        latency_ms=round(result.latency_ms, 2),
        refused=result.refused,
    )
