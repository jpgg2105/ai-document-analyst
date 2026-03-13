"""Cross-encoder reranker — rescores query-chunk pairs for higher precision."""

from __future__ import annotations

from sentence_transformers import CrossEncoder

from src.api.middleware.logging import get_logger
from src.config import settings
from src.models import RetrievedChunk

logger = get_logger(__name__)

_reranker: CrossEncoder | None = None
_RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"


def _get_reranker() -> CrossEncoder:
    global _reranker
    if _reranker is None:
        logger.info("loading_reranker_model", model=_RERANKER_MODEL)
        _reranker = CrossEncoder(_RERANKER_MODEL)
    return _reranker


def rerank(
    query: str,
    chunks: list[RetrievedChunk],
    top_k: int | None = None,
) -> list[RetrievedChunk]:
    """Rerank retrieved chunks using a cross-encoder model.

    The cross-encoder scores each (query, chunk.text) pair directly,
    which is more accurate than bi-encoder cosine similarity but too
    slow to run on the full corpus — hence we rerank only the top
    candidates from the fusion stage.

    Parameters
    ----------
    query:
        The user's natural language query.
    chunks:
        Pre-filtered candidate chunks (typically 15-20).
    top_k:
        How many chunks to return after reranking (default from settings).
    """
    top_k = top_k or settings.rerank_top_k

    if not chunks:
        return []

    reranker = _get_reranker()
    pairs = [(query, rc.chunk.text) for rc in chunks]
    scores = reranker.predict(pairs).tolist()

    # Attach new scores and sort
    scored = sorted(
        zip(scores, chunks),
        key=lambda x: x[0],
        reverse=True,
    )

    results: list[RetrievedChunk] = []
    for score, rc in scored[:top_k]:
        results.append(
            RetrievedChunk(
                chunk=rc.chunk,
                score=float(score),
                retrieval_method="reranked",
            )
        )

    logger.info(
        "reranking_complete",
        input_chunks=len(chunks),
        output_chunks=len(results),
        top_score=round(results[0].score, 4) if results else 0,
    )
    return results
