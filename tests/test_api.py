"""Integration tests for the FastAPI application.

These tests cover the health endpoint and basic request validation.
Endpoints that require Qdrant or OpenAI are tested with mocks to keep
the test suite runnable without external services.
"""

import io
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


class TestHealthEndpoint:
    def test_health_returns_ok(self):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"


class TestDocumentsEndpoints:
    def test_list_documents_empty(self):
        resp = client.get("/api/v1/documents")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 0
        assert isinstance(data["documents"], list)

    def test_upload_unsupported_type(self):
        fake = io.BytesIO(b"not a real file")
        resp = client.post(
            "/api/v1/documents/upload",
            files={"file": ("test.xyz", fake, "application/octet-stream")},
        )
        assert resp.status_code == 400
        assert "Unsupported" in resp.json()["detail"]

    def test_delete_nonexistent(self):
        resp = client.delete("/api/v1/documents/nonexistent-id")
        assert resp.status_code == 404


class TestQueryEndpoint:
    def test_query_empty_string(self):
        resp = client.post("/api/v1/query", json={"query": ""})
        assert resp.status_code == 422  # Pydantic validation

    def test_query_too_long(self):
        resp = client.post("/api/v1/query", json={"query": "x" * 2001})
        assert resp.status_code == 422

    @patch("src.api.routes.query.vector_search")
    @patch("src.api.routes.query.bm25_search")
    @patch("src.api.routes.query.rerank")
    @patch("src.api.routes.query.generate_answer")
    def test_query_returns_answer(
        self,
        mock_generate,
        mock_rerank,
        mock_bm25,
        mock_vector,
    ):
        from src.models import QueryResult

        mock_vector.return_value = []
        mock_bm25.return_value = []
        mock_rerank.return_value = []
        mock_generate.return_value = QueryResult(
            answer="I don't have enough information in the provided documents to answer this question.",
            sources=[],
            confidence=0.0,
            query="What is Python?",
            latency_ms=50.0,
            refused=True,
        )

        resp = client.post("/api/v1/query", json={"query": "What is Python?"})
        assert resp.status_code == 200
        data = resp.json()
        assert "answer" in data
        assert data["refused"] is True


class TestUploadWithMocks:
    @patch("src.api.routes.upload.embed_and_store")
    @patch("src.api.routes.upload.chunk_document")
    @patch("src.api.routes.upload.parse_document")
    def test_upload_markdown_success(self, mock_parse, mock_chunk, mock_embed):
        from src.ingestion.parser import ParsedDocument, ParsedPage
        from src.models import Chunk

        mock_parse.return_value = ParsedDocument(
            filename="test.md",
            file_type="markdown",
            pages=[ParsedPage(page_number=1, text="Hello world")],
        )
        mock_chunk.return_value = [
            Chunk(document_id="test", text="Hello world", chunk_index=0, token_count=2)
        ]
        mock_embed.return_value = 1

        content = b"# Test\n\nHello world"
        resp = client.post(
            "/api/v1/documents/upload",
            files={"file": ("test.md", io.BytesIO(content), "text/markdown")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["filename"] == "test.md"
        assert data["status"] == "completed"
        assert data["total_pages"] == 1
        assert data["total_chunks"] == 1
