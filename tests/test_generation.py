"""Tests for prompt formatting and generation helpers."""

from src.generation.prompts import build_query_prompt, format_context


class TestFormatContext:
    def test_single_chunk(self):
        chunks = [
            {
                "text": "Hello world",
                "filename": "doc.pdf",
                "page_number": 1,
                "section": "Intro",
            }
        ]
        ctx = format_context(chunks)
        assert "Source 1" in ctx
        assert "doc.pdf" in ctx
        assert "Page 1" in ctx
        assert "Section: Intro" in ctx
        assert "Hello world" in ctx

    def test_multiple_chunks(self):
        chunks = [
            {"text": "First chunk", "filename": "a.pdf", "page_number": 1, "section": ""},
            {"text": "Second chunk", "filename": "b.pdf", "page_number": 3, "section": "Methods"},
        ]
        ctx = format_context(chunks)
        assert "Source 1" in ctx
        assert "Source 2" in ctx
        assert "First chunk" in ctx
        assert "Second chunk" in ctx

    def test_empty_chunks(self):
        assert format_context([]) == ""


class TestBuildQueryPrompt:
    def test_contains_query(self):
        prompt = build_query_prompt(
            "What is RAG?",
            [{"text": "RAG info", "filename": "x.pdf", "page_number": 1, "section": ""}],
        )
        assert "What is RAG?" in prompt

    def test_contains_context(self):
        prompt = build_query_prompt(
            "test",
            [{"text": "context text", "filename": "f.md", "page_number": 2, "section": ""}],
        )
        assert "context text" in prompt
