"""Tests for the BM25 tokenizer."""

from src.retrieval.bm25_search import tokenize


def test_punctuation_does_not_stick_to_words():
    assert tokenize("Raise HTTPException(status_code=404), then") == [
        "raise",
        "httpexception",
        "status_code",
        "404",
        "then",
    ]


def test_query_and_document_tokens_match():
    doc = tokenize("Use `HTTPException`, not a return value.")
    assert "httpexception" in doc
    assert tokenize("HTTPException") == ["httpexception"]
