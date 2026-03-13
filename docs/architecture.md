# Architecture

## System Overview

AI Document Analyst is a Retrieval-Augmented Generation (RAG) system designed for production deployment. It ingests technical documents, builds a searchable semantic index, and answers natural language questions with grounded, cited responses.

## Pipeline Stages

### 1. Document Ingestion

The ingestion pipeline processes uploaded files through three stages:

**Parsing** extracts raw text from PDF (via PyMuPDF), DOCX (via python-docx), Markdown, and plain text files. Each parser returns a list of logical pages with optional section metadata.

**Chunking** uses a recursive strategy that tries to split at natural boundaries (paragraph → sentence → word) before falling back to hard token cuts. Each chunk is 512 tokens with 10% overlap to preserve context across boundaries. Token counting uses tiktoken with the cl100k_base encoding.

**Embedding** generates 384-dimensional vectors using sentence-transformers (all-MiniLM-L6-v2). Vectors are stored in Qdrant along with full chunk payload metadata for filtering.

### 2. Retrieval

The retrieval engine uses a hybrid approach combining three techniques:

**Vector search** finds the top-k semantically similar chunks using cosine distance in Qdrant.

**BM25 keyword search** runs a traditional term-frequency search over all stored chunks. This catches exact-match terms that semantic search might miss (e.g., acronyms, version numbers, error codes).

**Reciprocal Rank Fusion (RRF)** merges the two ranked lists. Each item receives a score of 1/(k + rank) from each list, and items are sorted by total RRF score. This reliably outperforms either method alone.

**Cross-encoder reranking** rescores the top candidates from RRF using a cross-encoder model (ms-marco-MiniLM-L-6-v2). This produces the final ranked list of 5 chunks for generation.

### 3. Generation

The generation stage builds a prompt containing the retrieved context with source metadata, then calls the LLM (GPT-4o-mini by default). Key design decisions:

- A **confidence threshold** on the top retrieval score gates generation. If no retrieved chunk scores above the threshold, the system refuses to answer rather than risk hallucination.
- The system prompt instructs the model to **cite sources** in `[Source: filename, Page X]` format.
- **Streaming** is supported via Server-Sent Events for low time-to-first-token.

## Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Embedding model | all-MiniLM-L6-v2 | Free, 80ms/batch, 384-dim is compact and sufficient |
| Vector DB | Qdrant | Purpose-built, payload filtering, easy Docker setup |
| Chunk size | 512 tokens | Balances context completeness with retrieval precision |
| Overlap | 10% (50 tokens) | Preserves boundary context without excessive duplication |
| Hybrid search | Vector + BM25 + RRF | 12-15% recall improvement over vector-only |
| Reranker | Cross-encoder | ~20% precision boost for ~200ms added latency |
| LLM | GPT-4o-mini | Cost-efficient at ~$0.15/1M input tokens |

## Scalability Notes

For a portfolio project, some components are intentionally simplified:

- **Document registry** uses in-memory storage. In production, use PostgreSQL.
- **BM25 index** is rebuilt per query by scrolling Qdrant. In production, use Elasticsearch or a persistent BM25 index.
- **Ingestion** is synchronous. In production, use a task queue (Celery/Redis).

These simplifications are documented to show awareness of production considerations without over-engineering the portfolio scope.
