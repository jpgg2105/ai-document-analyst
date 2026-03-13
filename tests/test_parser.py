"""Tests for document parsing (markdown, text, error handling)."""

from pathlib import Path
import tempfile

import pytest

from src.ingestion.parser import parse_document, SUPPORTED_TYPES


class TestParseMarkdown:
    def test_parses_sections(self, sample_markdown_file: Path):
        result = parse_document(sample_markdown_file)
        assert result.filename == sample_markdown_file.name
        assert result.file_type == "markdown"
        assert result.total_pages > 0

    def test_extracts_section_names(self, sample_markdown_file: Path):
        result = parse_document(sample_markdown_file)
        sections = [p.section for p in result.pages if p.section]
        # The sample markdown has "## Deep Learning"
        assert any("Deep Learning" in s for s in sections)

    def test_page_text_not_empty(self, sample_markdown_file: Path):
        result = parse_document(sample_markdown_file)
        for page in result.pages:
            assert page.text.strip() != ""


class TestParseText:
    def test_parses_plain_text(self, sample_txt_file: Path):
        result = parse_document(sample_txt_file)
        assert result.file_type == "text"
        assert result.total_pages == 1
        assert "Machine learning" in result.pages[0].text

    def test_empty_text_file(self):
        tmp = tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w")
        tmp.write("")
        tmp.close()
        result = parse_document(Path(tmp.name))
        assert result.total_pages == 0


class TestParserErrors:
    def test_unsupported_file_type(self, tmp_path: Path):
        fake_file = tmp_path / "test.xyz"
        fake_file.write_text("content")
        with pytest.raises(ValueError, match="Unsupported file type"):
            parse_document(fake_file)

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            parse_document(Path("/nonexistent/file.pdf"))

    def test_supported_types_dict(self):
        assert ".pdf" in SUPPORTED_TYPES
        assert ".md" in SUPPORTED_TYPES
        assert ".txt" in SUPPORTED_TYPES
        assert ".docx" in SUPPORTED_TYPES
