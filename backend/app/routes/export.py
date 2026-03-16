from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import get_current_user
from app.models import Answer, CoverageSummary, ExportFormat, Project, Questionnaire, User
from app.schemas import ExportRequest
from app.services.export import export_csv, export_docx, export_html, export_json, export_pdf

router = APIRouter()

CONTENT_TYPES = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "html": "text/html",
    "json": "application/json",
    "csv": "text/csv",
}


@router.post("/{project_id}/export")
def export_answers(
    project_id: str,
    body: ExportRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = _get_owned_project(db, project_id, current_user.id)

    q_res = db.execute(
        select(Questionnaire).where(Questionnaire.project_id == project_id)
    )
    questionnaire = q_res.scalar_one_or_none()
    if not questionnaire:
        raise HTTPException(status_code=404, detail="No questionnaire found")

    a_res = db.execute(
        select(Answer)
        .where(Answer.questionnaire_id == questionnaire.id)
        .order_by(Answer.question_number.asc())
    )
    answers = a_res.scalars().all()
    if not answers:
        raise HTTPException(status_code=400, detail="No answers to export. Generate answers first.")

    cov_res = db.execute(
        select(CoverageSummary)
        .where(CoverageSummary.questionnaire_id == questionnaire.id)
        .order_by(CoverageSummary.generated_at.desc())
    )
    coverage_orm = cov_res.scalar_one_or_none()

    answers_data = [
        {
            "question_number": a.question_number,
            "question_text": a.question_text,
            "generated_answer": a.generated_answer,
            "user_edited": a.user_edited,
            "edited_answer": a.edited_answer,
            "confidence_score": a.confidence_score,
            "not_found": a.not_found,
            "citations": a.citations or [],
            "evidence_snippets": a.evidence_snippets or [],
            "answer_candidates": a.answer_candidates or [],
        }
        for a in answers
    ]

    coverage_data = None
    if coverage_orm:
        coverage_data = {
            "total_questions": coverage_orm.total_questions,
            "answered_with_citations": coverage_orm.answered_with_citations,
            "not_found_count": coverage_orm.not_found_count,
            "average_confidence_score": coverage_orm.average_confidence_score,
        }

    fmt = body.format
    if fmt == "json":
        content = export_json(answers_data, coverage_data, project.name)
    elif fmt == "csv":
        content = export_csv(answers_data)
    elif fmt == "html":
        content = export_html(answers_data, project.name)
    elif fmt == "docx":
        content = export_docx(answers_data, project.name)
    elif fmt == "pdf":
        content = export_pdf(answers_data, project.name)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown format: {fmt}")

    export_record = ExportFormat(
        questionnaire_id=questionnaire.id,
        format=fmt,
        exported_by=current_user.id,
    )
    db.add(export_record)
    db.commit()

    return Response(
        content=content,
        media_type=CONTENT_TYPES[fmt],
        headers={
            "Content-Disposition": f'attachment; filename="answers.{fmt}"',
            "Content-Length": str(len(content)),
        },
    )


def _get_owned_project(db, project_id, user_id):
    result = db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == user_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project
