"""Shared data models for the AI Document Analyst."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4


class DocumentStatus(StrEnum):
    """Processing status of a document."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class DocumentMetadata:
    """Metadata attached to an ingested document."""

    document_id: str = field(default_factory=lambda: str(uuid4()))
    filename: str = ""
    file_type: str = ""
    total_pages: int = 0
    total_chunks: int = 0
    status: DocumentStatus = DocumentStatus.PENDING
    created_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )
    file_size_bytes: int = 0

    def to_dict(self) -> dict:
        return {
            "document_id": self.document_id,
            "filename": self.filename,
            "file_type": self.file_type,
            "total_pages": self.total_pages,
            "total_chunks": self.total_chunks,
            "status": self.status.value,
            "created_at": self.created_at,
            "file_size_bytes": self.file_size_bytes,
        }


@dataclass
class Chunk:
    """A single text chunk produced by the chunking pipeline."""

    chunk_id: str = field(default_factory=lambda: str(uuid4()))
    document_id: str = ""
    text: str = ""
    page_number: int = 0
    section: str = ""
    chunk_index: int = 0
    token_count: int = 0
    metadata: dict = field(default_factory=dict)

    def to_qdrant_payload(self) -> dict:
        """Return the payload dict stored alongside the vector in Qdrant."""
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "text": self.text,
            "page_number": self.page_number,
            "section": self.section,
            "chunk_index": self.chunk_index,
            "token_count": self.token_count,
            **self.metadata,
        }


@dataclass
class RetrievedChunk:
    """A chunk returned from the retrieval engine with a relevance score."""

    chunk: Chunk
    score: float = 0.0
    retrieval_method: str = ""  # "vector", "bm25", "fusion", "reranked"


@dataclass
class QueryResult:
    """Final result returned to the user."""

    answer: str = ""
    sources: list[RetrievedChunk] = field(default_factory=list)
    confidence: float = 0.0
    query: str = ""
    latency_ms: float = 0.0
    refused: bool = False
