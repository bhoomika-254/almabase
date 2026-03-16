from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy import select
from sqlalchemy.orm import Session
import os
import re

from app.db import get_db
from app.dependencies import get_current_user
from app.models import Project, Questionnaire, User
from app.schemas import QuestionnaireResponse
from app.services.documents import parse_questionnaire

router = APIRouter()

ALLOWED_EXTENSIONS = {".csv", ".pdf", ".txt", ".md"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


@router.post("/{project_id}/questionnaire", response_model=QuestionnaireResponse, status_code=status.HTTP_201_CREATED)
def upload_questionnaire(
    project_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _assert_project_owned(db, project_id, current_user.id)

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported questionnaire format '{ext}'. Allowed: csv, pdf, txt, md",
        )

    file_bytes = file.file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large (max 10 MB)")

    questions = parse_questionnaire(file_bytes, file.filename or "questionnaire")
    if not questions:
        raise HTTPException(
            status_code=422,
            detail="Could not parse any questions from this file. Make sure questions are numbered.",
        )

    safe_name = _safe_filename(file.filename or "questionnaire")

    # Replace existing questionnaire for this project (one per project)
    existing = db.execute(
        select(Questionnaire).where(Questionnaire.project_id == project_id)
    )
    old = existing.scalar_one_or_none()
    if old:
        db.delete(old)
        db.flush()

    questionnaire = Questionnaire(
        project_id=project_id,
        filename=safe_name,
        original_filename=file.filename or safe_name,
        questions=questions,
    )
    db.add(questionnaire)
    db.commit()
    db.refresh(questionnaire)
    return questionnaire


@router.get("/{project_id}/questionnaire", response_model=QuestionnaireResponse)
def get_questionnaire(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _assert_project_owned(db, project_id, current_user.id)
    result = db.execute(
        select(Questionnaire).where(Questionnaire.project_id == project_id)
    )
    q = result.scalar_one_or_none()
    if not q:
        raise HTTPException(status_code=404, detail="No questionnaire uploaded for this project")
    return q


# ─── Helpers ─────────────────────────────────────────────────────────────────

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
