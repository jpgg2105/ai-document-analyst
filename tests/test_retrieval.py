"""Tests for the Reciprocal Rank Fusion module."""

from src.models import Chunk, RetrievedChunk
from src.retrieval.fusion import reciprocal_rank_fusion


def _make_rc(chunk_id: str, score: float, method: str = "test") -> RetrievedChunk:
    return RetrievedChunk(
        chunk=Chunk(chunk_id=chunk_id, text=f"text-{chunk_id}"),
        score=score,
        retrieval_method=method,
    )


class TestReciprocalRankFusion:
    def test_single_list(self):
        results = [_make_rc("a", 0.9), _make_rc("b", 0.8)]
        fused = reciprocal_rank_fusion(results, top_k=5)
        assert len(fused) == 2
        # "a" was rank 1 so should still be first
        assert fused[0].chunk.chunk_id == "a"

    def test_merges_two_lists(self):
        list_a = [_make_rc("a", 0.9), _make_rc("b", 0.7)]
        list_b = [_make_rc("b", 0.95), _make_rc("c", 0.6)]
        fused = reciprocal_rank_fusion(list_a, list_b, top_k=5)
        ids = [rc.chunk.chunk_id for rc in fused]
        # "b" appears in both lists so should rank highest
        assert ids[0] == "b"
        assert set(ids) == {"a", "b", "c"}

    def test_top_k_limits_output(self):
        results = [_make_rc(str(i), 0.5) for i in range(20)]
        fused = reciprocal_rank_fusion(results, top_k=3)
        assert len(fused) == 3

    def test_empty_lists(self):
        fused = reciprocal_rank_fusion([], [], top_k=5)
        assert fused == []

    def test_retrieval_method_set_to_fusion(self):
        results = [_make_rc("a", 0.9, method="vector")]
        fused = reciprocal_rank_fusion(results, top_k=5)
        assert fused[0].retrieval_method == "fusion"
