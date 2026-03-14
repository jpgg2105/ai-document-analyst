"""Tests for the recursive text chunker."""

from pathlib import Path

from src.ingestion.chunker import _count_tokens, _recursive_split, chunk_document
from src.ingestion.parser import parse_document


class TestTokenCounting:
    def test_empty_string(self):
        assert _count_tokens("") == 0

    def test_known_sentence(self):
        tokens = _count_tokens("Hello world")
        assert tokens > 0
        assert tokens < 10

    def test_longer_text(self):
        text = "This is a longer sentence that should have more tokens than a short one."
        assert _count_tokens(text) > _count_tokens("Hello")


class TestRecursiveSplit:
    def test_short_text_not_split(self):
        text = "Short text."
        pieces = _recursive_split(text, max_tokens=100)
        assert len(pieces) == 1
        assert pieces[0] == text

    def test_splits_at_paragraph_boundary(self):
        text = "Paragraph one has several words of content here.\n\nParagraph two also has several words of content here."
        pieces = _recursive_split(text, max_tokens=10)
        assert len(pieces) >= 2

    def test_all_pieces_under_limit(self):
        text = " ".join(["word"] * 500)
        pieces = _recursive_split(text, max_tokens=50)
        for piece in pieces:
            assert _count_tokens(piece) <= 50


class TestChunkDocument:
    def test_chunks_created(self, sample_markdown_file: Path):
        parsed = parse_document(sample_markdown_file)
        chunks = chunk_document(parsed, document_id="test-doc-1", chunk_size=64, chunk_overlap=5)
        assert len(chunks) > 0
        for chunk in chunks:
            assert chunk.document_id == "test-doc-1"
            assert chunk.text.strip() != ""
            assert chunk.token_count > 0

    def test_chunk_metadata(self, sample_markdown_file: Path):
        parsed = parse_document(sample_markdown_file)
        chunks = chunk_document(parsed, document_id="test-doc-2")
        for chunk in chunks:
            assert chunk.metadata.get("filename") == sample_markdown_file.name
            assert chunk.metadata.get("file_type") == "markdown"

    def test_empty_document(self):
        from src.ingestion.parser import ParsedDocument

        parsed = ParsedDocument(filename="empty.md", file_type="markdown", pages=[])
        chunks = chunk_document(parsed, document_id="empty")
        assert chunks == []
