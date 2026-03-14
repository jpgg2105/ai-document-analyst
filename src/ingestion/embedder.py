"""Embedding pipeline — generates vectors with sentence-transformers and stores them in Qdrant."""

from __future__ import annotations

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)
from sentence_transformers import SentenceTransformer

from src.api.middleware.logging import get_logger
from src.config import settings
from src.models import Chunk

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Singleton-style model loader (avoids re-loading on every call)
# ---------------------------------------------------------------------------

_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        logger.info("loading_embedding_model", model=settings.embedding_model)
        _model = SentenceTransformer(settings.embedding_model)
    return _model


# ---------------------------------------------------------------------------
# Qdrant helpers
# ---------------------------------------------------------------------------


def get_qdrant_client() -> QdrantClient:
    """Return a Qdrant client connected to the configured host."""
    return QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)


def ensure_collection(client: QdrantClient) -> None:
    """Create the Qdrant collection if it does not already exist."""
    collections = [c.name for c in client.get_collections().collections]
    if settings.qdrant_collection not in collections:
        client.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config=VectorParams(
                size=settings.embedding_dimension,
                distance=Distance.COSINE,
            ),
        )
        logger.info("collection_created", name=settings.qdrant_collection)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Generate embedding vectors for a list of texts."""
    model = _get_model()
    embeddings = model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
    result: list[list[float]] = embeddings.tolist()
    return result


def embed_and_store(chunks: list[Chunk]) -> int:
    """Embed a batch of chunks and upsert them into Qdrant.

    Returns the number of points stored.
    """
    if not chunks:
        return 0

    client = get_qdrant_client()
    ensure_collection(client)

    texts = [c.text for c in chunks]
    vectors = embed_texts(texts)

    points = [
        PointStruct(
            id=c.chunk_id,
            vector=vec,
            payload=c.to_qdrant_payload(),
        )
        for c, vec in zip(chunks, vectors)
    ]

    # Upsert in batches of 100 to avoid memory spikes
    batch_size = 100
    for i in range(0, len(points), batch_size):
        batch = points[i : i + batch_size]
        client.upsert(
            collection_name=settings.qdrant_collection,
            points=batch,
        )

    logger.info(
        "embeddings_stored",
        total_chunks=len(chunks),
        document_id=chunks[0].document_id if chunks else "",
    )
    return len(points)


def delete_document_vectors(document_id: str) -> None:
    """Remove all vectors belonging to a document from Qdrant."""
    client = get_qdrant_client()
    client.delete(
        collection_name=settings.qdrant_collection,
        points_selector=Filter(
            must=[
                FieldCondition(
                    key="document_id",
                    match=MatchValue(value=document_id),
                )
            ]
        ),
    )
    logger.info("vectors_deleted", document_id=document_id)