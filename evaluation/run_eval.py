"""Evaluation runner — measures retrieval quality and generation faithfulness.

Run with:
    python -m evaluation.run_eval

This script is designed to be run against a live instance of the API
(docker compose up) with documents already ingested.  It can also be
run in CI with mocked endpoints for regression testing.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path

import httpx

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

API_BASE = "http://localhost:8000/api/v1"
EVAL_DATASET = Path(__file__).parent / "eval_dataset.json"
RESULTS_DIR = Path(__file__).parent / "results"

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class EvalCase:
    id: str
    query: str
    expected_answer: str
    relevant_keywords: list[str]
    source_document: str
    difficulty: str


@dataclass
class EvalResult:
    id: str
    query: str
    answer: str
    expected_answer: str
    confidence: float
    latency_ms: float
    refused: bool
    keyword_recall: float  # fraction of expected keywords found in answer
    source_found: bool  # whether the expected source doc appears in sources
    sources_count: int
    difficulty: str


@dataclass
class EvalSummary:
    total: int = 0
    avg_keyword_recall: float = 0.0
    avg_confidence: float = 0.0
    avg_latency_ms: float = 0.0
    source_hit_rate: float = 0.0
    refusal_rate: float = 0.0
    results_by_difficulty: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Evaluation logic
# ---------------------------------------------------------------------------


def _keyword_recall(answer: str, keywords: list[str]) -> float:
    """Fraction of expected keywords that appear in the answer (case-insensitive)."""
    if not keywords:
        return 1.0
    answer_lower = answer.lower()
    hits = sum(1 for kw in keywords if kw.lower() in answer_lower)
    return hits / len(keywords)


def evaluate_case(case: EvalCase, client: httpx.Client) -> EvalResult:
    """Send a query to the live API and evaluate the response."""
    start = time.perf_counter()
    resp = client.post(
        f"{API_BASE}/query",
        json={"query": case.query},
        timeout=30.0,
    )
    wall_ms = (time.perf_counter() - start) * 1000

    if resp.status_code != 200:
        return EvalResult(
            id=case.id,
            query=case.query,
            answer=f"HTTP {resp.status_code}",
            expected_answer=case.expected_answer,
            confidence=0.0,
            latency_ms=wall_ms,
            refused=True,
            keyword_recall=0.0,
            source_found=False,
            sources_count=0,
            difficulty=case.difficulty,
        )

    data = resp.json()
    answer = data.get("answer", "")
    sources = data.get("sources", [])
    source_filenames = [s.get("filename", "") for s in sources]

    return EvalResult(
        id=case.id,
        query=case.query,
        answer=answer,
        expected_answer=case.expected_answer,
        confidence=data.get("confidence", 0.0),
        latency_ms=data.get("latency_ms", wall_ms),
        refused=data.get("refused", False),
        keyword_recall=_keyword_recall(answer, case.relevant_keywords),
        source_found=any(case.source_document in fn for fn in source_filenames),
        sources_count=len(sources),
        difficulty=case.difficulty,
    )


def summarize(results: list[EvalResult]) -> EvalSummary:
    """Compute aggregate evaluation metrics."""
    if not results:
        return EvalSummary()

    n = len(results)
    summary = EvalSummary(
        total=n,
        avg_keyword_recall=sum(r.keyword_recall for r in results) / n,
        avg_confidence=sum(r.confidence for r in results) / n,
        avg_latency_ms=sum(r.latency_ms for r in results) / n,
        source_hit_rate=sum(1 for r in results if r.source_found) / n,
        refusal_rate=sum(1 for r in results if r.refused) / n,
    )

    # Break down by difficulty
    for difficulty in ("easy", "medium", "hard"):
        subset = [r for r in results if r.difficulty == difficulty]
        if subset:
            summary.results_by_difficulty[difficulty] = {
                "count": len(subset),
                "avg_keyword_recall": sum(r.keyword_recall for r in subset) / len(subset),
                "avg_latency_ms": sum(r.latency_ms for r in subset) / len(subset),
            }

    return summary


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    # Load dataset
    with open(EVAL_DATASET) as f:
        raw = json.load(f)
    cases = [EvalCase(**item) for item in raw]
    print(f"Loaded {len(cases)} evaluation cases")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    results: list[EvalResult] = []
    with httpx.Client() as client:
        for i, case in enumerate(cases, start=1):
            print(f"[{i}/{len(cases)}] {case.id}: {case.query[:60]}...")
            result = evaluate_case(case, client)
            results.append(result)
            print(
                f"  → kw_recall={result.keyword_recall:.2f}  "
                f"confidence={result.confidence:.3f}  "
                f"latency={result.latency_ms:.0f}ms  "
                f"refused={result.refused}"
            )

    # Summarize
    summary = summarize(results)
    print("\n" + "=" * 60)
    print("EVALUATION SUMMARY")
    print("=" * 60)
    print(f"Total cases:         {summary.total}")
    print(f"Avg keyword recall:  {summary.avg_keyword_recall:.2%}")
    print(f"Avg confidence:      {summary.avg_confidence:.3f}")
    print(f"Avg latency:         {summary.avg_latency_ms:.0f} ms")
    print(f"Source hit rate:     {summary.source_hit_rate:.2%}")
    print(f"Refusal rate:        {summary.refusal_rate:.2%}")

    for diff, stats in summary.results_by_difficulty.items():
        print(f"\n  [{diff}] n={stats['count']}  "
              f"kw_recall={stats['avg_keyword_recall']:.2%}  "
              f"latency={stats['avg_latency_ms']:.0f}ms")

    # Save results
    output = {
        "summary": asdict(summary),
        "results": [asdict(r) for r in results],
    }
    out_path = RESULTS_DIR / "eval_results.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved to {out_path}")


if __name__ == "__main__":
    main()
