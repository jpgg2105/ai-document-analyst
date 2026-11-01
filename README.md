# AI Document Analyst

> A production-style RAG (Retrieval-Augmented Generation) service for Q&A over technical documents, with an evaluation harness to measure it honestly instead of asserting it.

## What it does

AI Document Analyst ingests documents, builds a semantic search index, and answers natural-language questions with source citations. Retrieval combines dense vector search (Qdrant), BM25 keyword search, and cross-encoder reranking; generation is grounded in the retrieved chunks so answers cite where they came from.

## Results

**Retrieval, measured.** [retrieval-ablation](https://github.com/jpgg2105/retrieval-ablation) rebuilds this
service's retrieval in memory with the same settings (512-token chunks, 20 candidates per retriever,
RRF with k = 60, cross-encoder reranking, 5 results) and measures each stage on 60 labelled questions over
FastAPI's documentation and on two BEIR benchmarks. Recall@5 = the answer is in the 5 chunks returned.

| Pipeline | FastAPI docs (60) | SciFact (300) | FiQA (648) |
|---|---|---|---|
| BM25, old tokenizer (`text.lower().split()`) | 55% | 62% | 16% |
| BM25, word tokens (current) | 78% | 73% | 22% |
| Dense vectors (all-MiniLM-L6-v2) | 77% | 74% | 37% |
| Hybrid, old tokenizer | 78% | 72% | 34% |
| Hybrid + reranker, old tokenizer | 87% | 74% | 38% |
| **Hybrid + reranker, word-token BM25** | **90%** | **74%** | **38%** |

What the measurements changed in this code ([full write-up](https://github.com/jpgg2105/retrieval-ablation/blob/main/RESULTS.md),
[PR #2](https://github.com/jpgg2105/ai-document-analyst/pull/2)):

- **BM25 now tokenizes on word characters.** Splitting on whitespace kept punctuation attached
  (`HTTPException,` vs `HTTPException`); with word tokens BM25 answers all 30 exact-term questions.
  With the old tokenizer, hybrid fusion added nothing significant over dense search.
- **The reranker now gets 10 candidates instead of 20.** It mostly improves ordering (nDCG@10 +4 to
  +12 points) and takes over 95% of query time on CPU; 10 candidates kept the quality of 20 (within
  2 points) at about half the time. The table's reranked rows were measured with 20.
- **The BM25 index is built once** and rebuilt only when the stored point count changes, instead of
  on every query (24 ms at 358 chunks, growing with the corpus).
- **Not changed yet:** 512-token chunks exceed MiniLM's 256-token input (90% are truncated for the
  dense side). 256-token chunks scored higher with the reranker, but not significantly on 60 questions.

Generation quality (faithfulness, hallucination rate) isn't measured yet; the `evaluation/` harness is
there for it.

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Document    │────▶│  Processing  │────▶│  Vector DB  │
│  Upload API  │     │  Pipeline    │     │  (Qdrant)   │
└─────────────┘     │  - Parse     │     └──────┬──────┘
                    │  - Chunk     │            │
                    │  - Embed     │            ▼
┌─────────────┐     └──────────────┘     ┌─────────────┐
│  User Query  │────────────────────────▶│  Retrieval   │
│  API         │                         │  Engine      │
└─────────────┘                         │  - Vector    │
       │                                │  - BM25      │
       │                                │  - Rerank    │
       ▼                                └──────┬──────┘
┌─────────────┐     ┌──────────────┐           │
│  Response    │◀────│  LLM Gen     │◀──────────┘
│  + Sources   │     │  + Citations │
└─────────────┘     └──────────────┘
```

## Tech Stack

| Component | Technology | Why |
|---|---|---|
| Backend | FastAPI | Async-native, automatic OpenAPI docs, streaming support |
| Frontend | React + Vite | Component-based UI with streaming and drag-and-drop uploads |
| Vector DB | Qdrant | Purpose-built for vector search, metadata filtering, easy Docker setup |
| Embeddings | sentence-transformers (`all-MiniLM-L6-v2`) | Free, fast, good quality for general-purpose retrieval |
| LLM | OpenAI GPT-4o-mini | Cost-efficient, strong instruction following |
| Document Parsing | PyMuPDF | Fast PDF extraction with layout awareness |
| Reranking | Cross-encoder (`ms-marco-MiniLM-L-6-v2`) | Precision boost at low added latency |
| BM25 | rank-bm25 | Lightweight keyword search for hybrid retrieval |
| Evaluation | DeepEval + RAGAS | Standard RAG evaluation frameworks |

## Quick Start
```bash
git clone https://github.com/jpgg2105/ai-document-analyst.git
cd ai-document-analyst

cp .env.example .env
# Edit .env with your OpenAI API key

docker compose up --build

# Frontend at http://localhost:3000
# API at http://localhost:8000
# API docs at http://localhost:8000/docs
```

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/documents/upload` | Upload and ingest a document |
| GET | `/api/v1/documents` | List all ingested documents |
| DELETE | `/api/v1/documents/{id}` | Remove a document and its chunks |
| POST | `/api/v1/query` | Ask a question over ingested documents |
| GET | `/api/v1/health` | Health check |

## Evaluation

```bash
# Run evaluation suite against a running instance
python -m evaluation.run_eval

# Results are saved to evaluation/results/
```

Run this and commit the output before citing any specific number in interviews or on a resume.

## Design notes

- **Hybrid retrieval over pure vector search.** BM25 catches exact technical terms and identifiers that embedding similarity alone tends to miss.
- **Reranking as a separate stage.** A cross-encoder reranks the top candidates from vector+BM25 before they reach the LLM, trading a small amount of latency for higher precision.
- **Confidence thresholds on retrieval scores** are used to return "I don't know" rather than force an answer from weak context.

(The specific quantified claims previously in this README — recall/precision percentages, hallucination rate — were not backed by a committed eval run and have been removed. Re-add them once `evaluation/run_eval.py` has actually been run against this system and the results are committed alongside this file.)

## License

MIT
