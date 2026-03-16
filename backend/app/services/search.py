"""
Reference document search & indexing service.
- Splits document content into paragraph-level chunks
- Stores chunks in ReferenceDocumentIndex
- Provides keyword search across a project's reference documents
"""
import re
from typing import List

from sqlalchemy import select, delete
from sqlalchemy.orm import Session

from app.models import ReferenceDocument, ReferenceDocumentIndex
from app.schemas import SearchResult


# ─── Chunking ────────────────────────────────────────────────────────────────

def _split_into_chunks(text: str, min_len: int = 40) -> List[str]:
    """
    Split document into paragraph-level chunks.
    Paragraphs are separated by blank lines or markdown headings.
    """
    # Split on blank lines first
    raw_chunks = re.split(r"\n{2,}", text)

    chunks = []
    for chunk in raw_chunks:
        chunk = chunk.strip()
        if len(chunk) >= min_len:
            chunks.append(chunk)
        elif chunks:
            # Append short chunks to the previous one
            chunks[-1] = chunks[-1] + "\n" + chunk

    return chunks or [text]


# ─── Index Build ─────────────────────────────────────────────────────────────

def build_index_for_document(
    db: Session,
    doc: ReferenceDocument,
) -> None:
    """
    Build the full-text index for a reference document.
    Deletes existing chunks first (for re-indexing).
    """
    # Remove existing index entries for this doc
    db.execute(
        delete(ReferenceDocumentIndex).where(
            ReferenceDocumentIndex.reference_doc_id == doc.id
        )
    )

    chunks = _split_into_chunks(doc.content)

    # Track line numbers approximately
    line_cursor = 1
    for position, chunk in enumerate(chunks):
        index_entry = ReferenceDocumentIndex(
            reference_doc_id=doc.id,
            content_chunk=chunk,
            chunk_position=position,
            line_number=line_cursor,
        )
        db.add(index_entry)
        line_cursor += chunk.count("\n") + 2  # +2 for blank line separator

    db.flush()


# ─── Search ──────────────────────────────────────────────────────────────────

def _search_score(chunk: str, query_terms: List[str]) -> int:
    """Simple term-frequency scoring (case-insensitive)."""
    chunk_lower = chunk.lower()
    return sum(chunk_lower.count(term.lower()) for term in query_terms)


def _make_snippet(chunk: str, query_terms: List[str], max_len: int = 200) -> str:
    """
    Extract a snippet from the chunk centered around the first query term match.
    """
    chunk_lower = chunk.lower()
    start = 0
    for term in query_terms:
        idx = chunk_lower.find(term.lower())
        if idx != -1:
            start = max(0, idx - 60)
            break

    snippet = chunk[start : start + max_len]
    if start > 0:
        snippet = "..." + snippet
    if start + max_len < len(chunk):
        snippet = snippet + "..."
    return snippet.strip()


def search_references(
    db: Session,
    project_id: str,
    query: str,
    limit: int = 10,
) -> List[SearchResult]:
    """
    Search across all reference document index chunks for a project.
    Returns ranked results with snippet previews.
    """
    if not query.strip():
        return []

    query_terms = [t for t in re.split(r"\s+", query.strip()) if len(t) >= 2]
    if not query_terms:
        return []

    # Load all index chunks for the project's reference docs
    stmt = (
        select(ReferenceDocumentIndex, ReferenceDocument.original_filename, ReferenceDocument.id.label("rdoc_id"))
        .join(ReferenceDocument, ReferenceDocumentIndex.reference_doc_id == ReferenceDocument.id)
        .where(ReferenceDocument.project_id == project_id)
    )
    rows = db.execute(stmt).all()

    results = []
    for chunk_obj, doc_name, doc_id in rows:
        score = _search_score(chunk_obj.content_chunk, query_terms)
        if score > 0:
            results.append((score, chunk_obj, doc_name, doc_id))

    # Sort by score descending
    results.sort(key=lambda x: x[0], reverse=True)

    return [
        SearchResult(
            doc_id=doc_id,
            doc_name=doc_name,
            snippet=_make_snippet(chunk_obj.content_chunk, query_terms),
            chunk_position=chunk_obj.chunk_position,
        )
        for _, chunk_obj, doc_name, doc_id in results[:limit]
    ]
