"""FastAPI application — entrypoint for the AI Document Analyst."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.middleware.logging import get_logger, setup_logging
from src.api.middleware.timing import RequestTimingMiddleware
from src.api.routes import documents, query, upload
from src.api.schemas import HealthResponse
from src.ingestion.embedder import ensure_collection, get_qdrant_client

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle events."""
    setup_logging()
    logger.info("starting_application")

    # Ensure Qdrant collection exists on startup
    try:
        client = get_qdrant_client()
        ensure_collection(client)
        logger.info("qdrant_connected")
    except Exception as exc:
        logger.warning("qdrant_connection_failed", error=str(exc))

    yield

    logger.info("shutting_down")


app = FastAPI(
    title="AI Document Analyst",
    description="Intelligent Q&A over technical documentation using RAG",
    version="0.1.0",
    lifespan=lifespan,
)

# Middleware
app.add_middleware(RequestTimingMiddleware)

# Routes
app.include_router(upload.router, prefix="/api/v1/documents", tags=["documents"])
app.include_router(documents.router, prefix="/api/v1/documents", tags=["documents"])
app.include_router(query.router, prefix="/api/v1", tags=["query"])


@app.get("/api/v1/health", response_model=HealthResponse, tags=["health"])
async def health_check() -> HealthResponse:
    """Check API and Qdrant connectivity."""
    qdrant_status = "unknown"
    try:
        client = get_qdrant_client()
        client.get_collections()
        qdrant_status = "connected"
    except Exception:
        qdrant_status = "disconnected"

    return HealthResponse(status="ok", qdrant=qdrant_status)
