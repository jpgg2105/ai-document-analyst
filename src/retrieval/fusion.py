"""Reciprocal Rank Fusion (RRF) — merges ranked lists from multiple retrievers."""

from __future__ import annotations

from src.api.middleware.logging import get_logger
from src.models import RetrievedChunk

logger = get_logger(__name__)

# Constant k recommended in the original RRF paper (Cormack et al., 2009)
RRF_K = 60


def reciprocal_rank_fusion(
    *ranked_lists: list[RetrievedChunk],
    top_k: int = 20,
) -> list[RetrievedChunk]:
    """Combine multiple ranked result lists using Reciprocal Rank Fusion.

    RRF score for a document d across N lists:
        RRF(d) = Σ  1 / (k + rank_i(d))

    where rank_i is the 1-based rank in list i.

    Parameters
    ----------
    *ranked_lists:
        One or more lists of RetrievedChunk, each sorted by their own score.
    top_k:
        Number of results to return after fusion.
    """
    # chunk_id → cumulative RRF score
    rrf_scores: dict[str, float] = {}
    # chunk_id → best RetrievedChunk object (for returning)
    chunk_map: dict[str, RetrievedChunk] = {}

    for ranked_list in ranked_lists:
        for rank, rc in enumerate(ranked_list, start=1):
            cid = rc.chunk.chunk_id
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + 1.0 / (RRF_K + rank)
            # Keep the entry with the highest individual score for tie-breaking
            if cid not in chunk_map or rc.score > chunk_map[cid].score:
                chunk_map[cid] = rc

    # Sort by RRF score descending
    sorted_ids = sorted(rrf_scores, key=lambda cid: rrf_scores[cid], reverse=True)

    results: list[RetrievedChunk] = []
    for cid in sorted_ids[:top_k]:
        rc = chunk_map[cid]
        results.append(
            RetrievedChunk(
                chunk=rc.chunk,
                score=rrf_scores[cid],
                retrieval_method="fusion",
            )
        )

    logger.info(
        "rrf_complete",
        input_lists=len(ranked_lists),
        unique_chunks=len(rrf_scores),
        output_size=len(results),
    )
    return results
