"""Pydantic request / response schemas for the API."""

from __future__ import annotations

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------


class DocumentResponse(BaseModel):
    document_id: str
    filename: str
    file_type: str
    total_pages: int
    total_chunks: int
    status: str
    created_at: str
    file_size_bytes: int


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]
    total: int


# ---------------------------------------------------------------------------
# Query
# ---------------------------------------------------------------------------


class QueryRequest(BaseModel):
    query: str = Field(
        ..., min_length=1, max_length=2000, description="Natural language question"
    )
    document_id: str | None = Field(
        None, description="Restrict search to a specific document"
    )
    stream: bool = Field(False, description="Stream the response via SSE")


class SourceChunk(BaseModel):
    chunk_id: str
    text: str
    filename: str
    page_number: int
    section: str
    score: float
    retrieval_method: str


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceChunk]
    confidence: float
    query: str
    latency_ms: float
    refused: bool


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    status: str = "ok"
    qdrant: str = "unknown"
