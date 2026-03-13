"""POST /api/v1/documents/upload — ingest a document into the RAG pipeline."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile

from src.api import document_store
from src.api.middleware.logging import get_logger
from src.api.schemas import DocumentResponse
from src.ingestion.chunker import chunk_document
from src.ingestion.embedder import embed_and_store
from src.ingestion.parser import SUPPORTED_TYPES, parse_document
from src.models import DocumentMetadata, DocumentStatus

logger = get_logger(__name__)
router = APIRouter()

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(file: UploadFile) -> DocumentResponse:
    """Upload and ingest a document.

    The file is parsed → chunked → embedded → stored in Qdrant in a single
    synchronous pipeline.  For very large files a background task queue
    (e.g. Celery) would be appropriate, but for the portfolio scope this
    works well.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required.")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in SUPPORTED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{suffix}'. Supported: {', '.join(SUPPORTED_TYPES)}",
        )

    # Read into a temp file
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File exceeds 50 MB limit.")

    doc_meta = DocumentMetadata(
        filename=file.filename,
        file_type=SUPPORTED_TYPES[suffix],
        file_size_bytes=len(content),
        status=DocumentStatus.PROCESSING,
    )
    document_store.save(doc_meta)

    tmp_dir = tempfile.mkdtemp()
    tmp_path = Path(tmp_dir) / file.filename
    try:
        tmp_path.write_bytes(content)

        # 1. Parse
        parsed = parse_document(tmp_path)
        doc_meta.total_pages = parsed.total_pages

        # 2. Chunk
        chunks = chunk_document(parsed, doc_meta.document_id)
        doc_meta.total_chunks = len(chunks)

        # 3. Embed & store
        embed_and_store(chunks)

        doc_meta.status = DocumentStatus.COMPLETED
        document_store.save(doc_meta)

        logger.info(
            "document_ingested",
            document_id=doc_meta.document_id,
            filename=file.filename,
            pages=parsed.total_pages,
            chunks=len(chunks),
        )

    except Exception as exc:
        doc_meta.status = DocumentStatus.FAILED
        document_store.save(doc_meta)
        logger.error("ingestion_failed", error=str(exc), document_id=doc_meta.document_id)
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {exc}") from exc

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    return DocumentResponse(**doc_meta.to_dict())
