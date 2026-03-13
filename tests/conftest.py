"""Shared pytest fixtures."""

import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def sample_text() -> str:
    return (
        "Machine learning is a subset of artificial intelligence. "
        "It involves training algorithms on data to make predictions. "
        "Deep learning uses neural networks with multiple layers. "
        "Transformers are a type of neural network architecture. "
        "They use self-attention mechanisms to process sequential data. "
        "Large language models like GPT-4 are based on the transformer architecture. "
        "These models are pre-trained on massive text corpora. "
        "Fine-tuning adapts a pre-trained model to a specific task. "
        "Retrieval-augmented generation combines search with generation. "
        "RAG systems retrieve relevant documents before generating answers."
    )


@pytest.fixture
def sample_markdown_file(sample_text: str) -> Path:
    """Create a temporary markdown file for testing."""
    tmp = tempfile.NamedTemporaryFile(suffix=".md", delete=False, mode="w")
    content = (
        f"# Machine Learning Overview\n\n{sample_text}\n\n"
        "## Deep Learning\n\n"
        "Deep learning uses neural networks with many layers "
        "to learn representations of data."
    )
    tmp.write(content)
    tmp.close()
    return Path(tmp.name)


@pytest.fixture
def sample_txt_file(sample_text: str) -> Path:
    """Create a temporary text file for testing."""
    tmp = tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w")
    tmp.write(sample_text)
    tmp.close()
    return Path(tmp.name)
