# AI Document Analyst

> A production-style RAG (Retrieval-Augmented Generation) service for Q&A over technical documents, with an evaluation harness to measure it honestly instead of asserting it.

## What it does

AI Document Analyst ingests documents, builds a semantic search index, and answers natural-language questions with source citations. Retrieval combines dense vector search (Qdrant), BM25 keyword search, and cross-encoder reranking; generation is grounded in the retrieved chunks so answers cite where they came from.

## Results

*Pending a committed evaluation run.* The `evaluation/` harness (`run_eval.py` + `eval_dataset.json`) measures retrieval recall, faithfulness, and hallucination rate against a live instance. Numbers will be added here once a run has actually been executed and its output committed — see `evaluation/results/` for the latest run, if present. Until then, treat any specific metric as unverified.

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
