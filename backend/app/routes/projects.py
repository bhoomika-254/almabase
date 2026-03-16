from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
import os

from app.db import get_db
from app.dependencies import get_current_user
from app.models import Project, User, ReferenceDocument, Questionnaire
from app.schemas import ProjectCreate, ProjectResponse
from app.services.documents import parse_document, parse_questionnaire

router = APIRouter()


@router.get("", response_model=list[ProjectResponse])
def list_projects(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = db.execute(
        select(Project)
        .where(Project.user_id == current_user.id)
        .order_by(Project.updated_at.desc())
    )
    return result.scalars().all()


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    body: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = Project(user_id=current_user.id, name=body.name, description=body.description)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.post("/sample", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_sample_project(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a project pre-loaded with sample data from mock_data/ folder."""
    project = Project(
        user_id=current_user.id,
        name="Sample Project - FERPA Compliance",
        description="Pre-loaded sample questionnaire and reference documents for testing"
    )
    db.add(project)
    db.flush()

    # Load reference documents from mock_data/reference_docs/
    mock_ref_dir = os.path.join(os.path.dirname(__file__), "../../../mock_data/reference_docs")
    if os.path.exists(mock_ref_dir):
        for filename in sorted(os.listdir(mock_ref_dir)):
            if not filename.endswith(('.md', '.txt', '.pdf')):
                continue
            filepath = os.path.join(mock_ref_dir, filename)
            with open(filepath, 'rb') as f:
                file_bytes = f.read()
            content, file_type = parse_document(file_bytes, filename)
            ref_doc = ReferenceDocument(
                project_id=project.id,
                filename=filename,
                original_filename=filename,
                content=content,
                file_type=file_type,
                file_size=len(file_bytes),
            )
            db.add(ref_doc)

    # Load questionnaire from mock_data/sample_questionnaire.csv
    mock_q_path = os.path.join(os.path.dirname(__file__), "../../../mock_data/sample_questionnaire.csv")
    if os.path.exists(mock_q_path):
        with open(mock_q_path, 'rb') as f:
            q_bytes = f.read()
        questions = parse_questionnaire(q_bytes, "sample_questionnaire.csv")
        questionnaire = Questionnaire(
            project_id=project.id,
            filename="sample_questionnaire.csv",
            original_filename="sample_questionnaire.csv",
            questions=questions,
        )
        db.add(questionnaire)

    db.commit()
    db.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = _get_owned_project(db, project_id, current_user.id)
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = _get_owned_project(db, project_id, current_user.id)
    db.delete(project)
    db.commit()


# ─── Helper ─────────────────────────────────────────────────────────────────

def _get_owned_project(db: Session, project_id: str, user_id: str) -> Project:
    result = db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == user_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project
