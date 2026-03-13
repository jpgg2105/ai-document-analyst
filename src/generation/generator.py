"""LLM generation — produces grounded answers with citations and streaming support."""

from __future__ import annotations

import time
from collections.abc import AsyncIterator

from openai import AsyncOpenAI

from src.api.middleware.logging import get_logger
from src.config import settings
from src.generation.prompts import _NO_INFO_MSG, SYSTEM_PROMPT, build_query_prompt
from src.models import QueryResult, RetrievedChunk

logger = get_logger(__name__)

_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _client


async def generate_answer(
    query: str,
    retrieved_chunks: list[RetrievedChunk],
) -> QueryResult:
    """Generate a cited answer using the LLM.

    If the top reranked score is below the confidence threshold the system
    refuses to answer rather than risk hallucination.
    """
    start = time.perf_counter()

    # ---- Confidence gate ----
    if not retrieved_chunks:
        return QueryResult(
            answer=_NO_INFO_MSG,
            sources=[],
            confidence=0.0,
            query=query,
            latency_ms=0,
            refused=True,
        )

    top_score = retrieved_chunks[0].score
    if top_score < settings.confidence_threshold:
        return QueryResult(
            answer=_NO_INFO_MSG,
            sources=retrieved_chunks,
            confidence=top_score,
            query=query,
            latency_ms=(time.perf_counter() - start) * 1000,
            refused=True,
        )

    # ---- Build prompt ----
    chunk_dicts = [
        {
            "text": rc.chunk.text,
            "filename": rc.chunk.metadata.get("filename", ""),
            "page_number": rc.chunk.page_number,
            "section": rc.chunk.section,
        }
        for rc in retrieved_chunks
    ]
    user_prompt = build_query_prompt(query, chunk_dicts)

    # ---- Call LLM ----
    client = _get_client()
    response = await client.chat.completions.create(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
    )

    answer = response.choices[0].message.content or ""
    latency = (time.perf_counter() - start) * 1000

    logger.info(
        "generation_complete",
        query_length=len(query),
        answer_length=len(answer),
        top_score=round(top_score, 4),
        latency_ms=round(latency, 2),
    )

    return QueryResult(
        answer=answer,
        sources=retrieved_chunks,
        confidence=top_score,
        query=query,
        latency_ms=latency,
        refused=False,
    )


async def generate_answer_stream(
    query: str,
    retrieved_chunks: list[RetrievedChunk],
) -> AsyncIterator[str]:
    """Stream the generated answer token-by-token via SSE.

    Yields plain-text chunks suitable for Server-Sent Events.
    """
    if not retrieved_chunks:
        yield _NO_INFO_MSG
        return

    top_score = retrieved_chunks[0].score
    if top_score < settings.confidence_threshold:
        yield _NO_INFO_MSG
        return

    chunk_dicts = [
        {
            "text": rc.chunk.text,
            "filename": rc.chunk.metadata.get("filename", ""),
            "page_number": rc.chunk.page_number,
            "section": rc.chunk.section,
        }
        for rc in retrieved_chunks
    ]
    user_prompt = build_query_prompt(query, chunk_dicts)

    client = _get_client()
    stream = await client.chat.completions.create(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
        stream=True,
    )

    async for event in stream:
        delta = event.choices[0].delta
        if delta.content:
            yield delta.content
