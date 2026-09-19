"""
workers/embed_worker.py
RQ worker: generates embeddings for uploaded documents and policy clauses.
Writes vectors to:
  - document_embeddings (for evidence docs: hospital bills, discharge summaries, etc.)
  - policy_clauses.embedding (for policy PDF chunks)

Triggered by: n8n webhook after OCR completes.
Run as: rq worker embed --url redis://...
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from uuid import UUID

from app.ai.provider import llm
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)
settings = get_settings()

# Chunk parameters
CHUNK_SIZE = 400       # target tokens per chunk
CHUNK_OVERLAP = 50     # token overlap between chunks


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """
    Split text into overlapping chunks by word count (approximate token proxy).
    Real production would use tiktoken for exact token counting.
    """
    words = text.split()
    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start += chunk_size - overlap
    return chunks


async def embed_document(document_id: str) -> dict:
    """
    RQ job: embed an evidence document (hospital bill, discharge summary, etc.)
    into document_embeddings.
    Called after OCR has completed and document_extractions row exists.
    """
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    engine = create_async_engine(settings.DATABASE_URL)
    AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    async with AsyncSessionLocal() as db:
        # Load the extraction text
        from app.documents.models import Document, DocumentExtraction
        result = await db.execute(
            select(DocumentExtraction)
            .where(DocumentExtraction.document_id == UUID(document_id))
            .where(DocumentExtraction.extraction_status == "completed")
        )
        extraction = result.scalar_one_or_none()
        if not extraction or not extraction.extracted_json:
            logger.warning("embed_document_no_extraction", document_id=document_id)
            return {"status": "skipped", "reason": "no completed extraction"}

        # Extract text field from the extraction JSON
        raw_text = extraction.extracted_json.get("raw_text") or extraction.extracted_json.get("text") or ""
        if not raw_text:
            return {"status": "skipped", "reason": "no text in extraction"}

        # Chunk the text
        chunks = chunk_text(raw_text)
        logger.info("embed_document_chunks", document_id=document_id, chunk_count=len(chunks))

        # Generate embeddings in batches
        batch_size = 20
        embeddings: list[list[float]] = []
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            batch_embeddings = await llm().embed(batch)
            embeddings.extend(batch_embeddings)

        # Write to document_embeddings
        from sqlalchemy import text as sql_text
        for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            await db.execute(
                sql_text("""
                    INSERT INTO document_embeddings (id, document_id, chunk_index, text, embedding, created_at)
                    VALUES (gen_random_uuid(), :doc_id, :idx, :text, :embedding::vector, NOW())
                """),
                {
                    "doc_id": document_id,
                    "idx": idx,
                    "text": chunk,
                    "embedding": f"[{','.join(str(x) for x in embedding)}]",
                },
            )

        # Update document status
        result2 = await db.execute(select(Document).where(Document.id == UUID(document_id)))
        doc = result2.scalar_one_or_none()
        if doc:
            doc.status = "completed"

        await db.commit()
        logger.info("embed_document_complete", document_id=document_id, chunks=len(chunks))
        return {"status": "success", "document_id": document_id, "chunks": len(chunks)}


async def embed_policy_version(policy_version_id: str) -> dict:
    """
    RQ job: embed a policy document (PDF chunks) into policy_clauses.embedding.
    Called after policy PDF is parsed.
    """
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from sqlalchemy import text as sql_text

    engine = create_async_engine(settings.DATABASE_URL)
    AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    async with AsyncSessionLocal() as db:
        # Load all policy_clauses for this version that have no embedding yet
        result = await db.execute(
            sql_text("""
                SELECT id, text, chunk_index
                FROM policy_clauses
                WHERE policy_version_id = :pvid AND embedding IS NULL
            """),
            {"pvid": policy_version_id},
        )
        clauses = result.fetchall()
        if not clauses:
            return {"status": "skipped", "reason": "no clauses without embeddings"}

        texts = [c.text for c in clauses]
        batch_size = 20
        all_embeddings: list[list[float]] = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            all_embeddings.extend(await llm().embed(batch))

        for clause, embedding in zip(clauses, all_embeddings):
            await db.execute(
                sql_text("""
                    UPDATE policy_clauses
                    SET embedding = :embedding::vector
                    WHERE id = :clause_id
                """),
                {
                    "clause_id": str(clause.id),
                    "embedding": f"[{','.join(str(x) for x in embedding)}]",
                },
            )

        await db.commit()
        logger.info("embed_policy_complete", policy_version_id=policy_version_id, clauses=len(clauses))
        return {"status": "success", "policy_version_id": policy_version_id, "clauses": len(clauses)}
