from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session
import os
import re

from app.db import get_db
from app.dependencies import get_current_user
from app.models import Project, ReferenceDocument, User
from app.schemas import ReferenceDocumentResponse, SearchResult
from app.services.documents import parse_document
from app.services.search import build_index_for_document, search_references

router = APIRouter()

ALLOWED_EXTENSIONS = {".txt", ".md", ".pdf"}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB


@router.post("/{project_id}/references", response_model=ReferenceDocumentResponse, status_code=status.HTTP_201_CREATED)
def upload_reference(
    project_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _assert_project_owned(db, project_id, current_user.id)

    ext = _get_ext(file.filename or "")
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported file type '{ext}'. Allowed: txt, md, pdf",
        )

    file_bytes = file.file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large (max 20 MB)")

    content, file_type = parse_document(file_bytes, file.filename or "file")

    safe_name = _safe_filename(file.filename or "upload")
    doc = ReferenceDocument(
        project_id=project_id,
        filename=safe_name,
        original_filename=file.filename or safe_name,
        content=content,
        file_type=file_type,
        file_size=len(file_bytes),
    )
    db.add(doc)
    db.flush()

    build_index_for_document(db, doc)

    db.commit()
    db.refresh(doc)
    return doc


@router.get("/{project_id}/references", response_model=list[ReferenceDocumentResponse])
def list_references(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _assert_project_owned(db, project_id, current_user.id)
    result = db.execute(
        select(ReferenceDocument)
        .where(ReferenceDocument.project_id == project_id)
        .order_by(ReferenceDocument.uploaded_at.asc())
    )
    return result.scalars().all()


@router.delete("/{project_id}/references/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_reference(
    project_id: str,
    doc_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _assert_project_owned(db, project_id, current_user.id)
    result = db.execute(
        select(ReferenceDocument).where(
            ReferenceDocument.id == doc_id,
            ReferenceDocument.project_id == project_id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Reference document not found")
    db.delete(doc)
    db.commit()


@router.get("/{project_id}/references/search", response_model=list[SearchResult])
def search_reference_docs(
    project_id: str,
    q: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _assert_project_owned(db, project_id, current_user.id)
    return search_references(db, project_id, q, limit)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _get_ext(filename: str) -> str:
    return os.path.splitext(filename)[1].lower()


def _safe_filename(filename: str) -> str:
    name = os.path.basename(filename)
    name = re.sub(r"[^\w.\-]", "_", name)
    return name[:255]


def _assert_project_owned(db: Session, project_id: str, user_id: str) -> None:
    result = db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == user_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")
