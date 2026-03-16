from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy import select, delete
from sqlalchemy.orm import Session
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.db import get_db, SessionLocal
from app.dependencies import get_current_user
from app.models import (
    Answer, CoverageSummary, Project, Questionnaire,
    ReferenceDocument, User, VersionHistory
)
from app.schemas import (
    AnswerEditRequest, AnswerResponse, CoverageSummaryResponse,
    GenerateAnswersRequest, SelectCandidateRequest, VersionHistoryResponse
)
from app.services.citations import calculate_confidence, process_citations
from app.services.llm import generate_answers_from_raw, generate_batch_answer_candidates, generate_single_answer

router = APIRouter()


# ─── Generate Answers ─────────────────────────────────────────────────────────

@router.post("/{project_id}/generate-answers", status_code=status.HTTP_202_ACCEPTED)
def generate_answers(
    project_id: str,
    body: GenerateAnswersRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Trigger AI answer generation (runs in background)."""
    project = _get_owned_project(db, project_id, current_user.id)

    questionnaire = _get_questionnaire(db, project_id)
    if not questionnaire:
        raise HTTPException(status_code=404, detail="No questionnaire uploaded")

    refs = _get_references(db, project_id)
    if not refs:
        raise HTTPException(status_code=400, detail="No reference documents uploaded")

    background_tasks.add_task(
        _run_generation,
        project_id=project_id,
        questionnaire_id=questionnaire.id,
        questions=questionnaire.questions,
        refs=refs,
        question_ids=body.question_ids,
        user_id=current_user.id,
    )

    return {"message": "Answer generation started"}


def _run_generation(
    project_id: str,
    questionnaire_id: str,
    questions: list[dict],
    refs: list[ReferenceDocument],
    question_ids: list[int] | None,
    user_id: str,
):
    """Background task: generate answers for all (or selected) questions."""
    reference_docs = {doc.original_filename: doc.content for doc in refs}
    doc_name_to_id = {doc.original_filename: doc.id for doc in refs}

    print(f"[GENERATION] Starting for project={project_id}, {'partial' if question_ids else 'full'} run, {len(refs)} ref docs")

    db = SessionLocal()
    try:
        # Save snapshot for version history before overwriting
        existing = db.execute(
            select(Answer).where(Answer.questionnaire_id == questionnaire_id)
        )
        existing_answers = existing.scalars().all()

        if existing_answers and not question_ids:
            # New full run — save version history
            version_num = (existing_answers[0].version_number or 1)
            print(f"[GENERATION] Saving version history snapshot (v{version_num}) before overwrite")
            snapshot = [
                {
                    "question_number": a.question_number,
                    "question_text": a.question_text,
                    "generated_answer": a.generated_answer,
                    "confidence_score": a.confidence_score,
                    "not_found": a.not_found,
                }
                for a in existing_answers
            ]
            coverage = db.execute(
                select(CoverageSummary)
                .where(CoverageSummary.questionnaire_id == questionnaire_id)
                .order_by(CoverageSummary.generated_at.desc())
            )
            coverage_data = coverage.scalar_one_or_none()
            history = VersionHistory(
                questionnaire_id=questionnaire_id,
                version_number=version_num,
                answers_snapshot=snapshot,
                coverage_summary={
                    "total": coverage_data.total_questions if coverage_data else 0,
                    "answered": coverage_data.answered_with_citations if coverage_data else 0,
                    "not_found": coverage_data.not_found_count if coverage_data else 0,
                    "avg_confidence": coverage_data.average_confidence_score if coverage_data else 0,
                } if coverage_data else {},
                created_by=user_id,
            )
            db.add(history)

            # Delete current answers for full regeneration
            db.execute(
                delete(Answer).where(Answer.questionnaire_id == questionnaire_id)
            )
        elif question_ids:
            # Partial: capture existing question texts BEFORE deletion so we can re-ask them
            pre_regen_answers = db.execute(
                select(Answer).where(
                    Answer.questionnaire_id == questionnaire_id,
                    Answer.question_number.in_(question_ids)
                )
            ).scalars().all()
            partial_questions = [{"number": a.question_number, "text": a.question_text} for a in pre_regen_answers]

            # Now delete the targeted answers
            db.execute(
                delete(Answer).where(
                    Answer.questionnaire_id == questionnaire_id,
                    Answer.question_number.in_(question_ids)
                )
            )

        db.flush()

        # Compute current version number
        existing_count = db.execute(
            select(Answer).where(Answer.questionnaire_id == questionnaire_id)
        )
        base_version = len(existing_count.scalars().all()) + 1

        # Generate answers
        # - Full run: send raw questionnaire to LLM which identifies + answers every question
        # - Partial run: re-ask the already-known question texts
        if question_ids:
            print(f"[GENERATION] Partial regen for {len(partial_questions)} questions")
            question_candidates_map = generate_batch_answer_candidates(partial_questions, reference_docs)
        else:
            raw_text = questions[0]["text"] if questions else ""
            print(f"[GENERATION] Full run: sending raw questionnaire ({len(raw_text)} chars) to LLM")
            raw_result = generate_answers_from_raw(raw_text, reference_docs)
            question_candidates_map = {}
            for ans_data in raw_result.get("answers", []):
                q_num = ans_data.get("question_number")
                if q_num is None:
                    continue
                question_candidates_map[q_num] = [{
                    "candidate_id": 1,
                    "generation_strategy": "detailed",
                    "question_text": ans_data.get("question_text", f"Question {q_num}"),
                    "answer": ans_data.get("answer", "Not present in the document"),
                    "confidence_score": ans_data.get("confidence_score", 0.0),
                    "not_found": ans_data.get("not_found", True),
                    "raw_citations": ans_data.get("citations", []),
                }]

        # Process candidates and insert answers to DB
        answered_count = 0
        not_found_count = 0
        confidence_scores = []

        for q_num, candidates_raw in sorted(question_candidates_map.items()):
            processed_candidates = []

            if not candidates_raw:
                print(f"[GENERATION] Q{q_num} missing from batch response - using fallback")
                candidates_raw = [{
                    "candidate_id": 1,
                    "generation_strategy": "detailed",
                    "question_text": f"Question {q_num}",
                    "answer": "Not present in the document",
                    "confidence_score": 0.0,
                    "not_found": True,
                    "raw_citations": [],
                }]

            q_text = candidates_raw[0].get("question_text") or f"Question {q_num}"

            for cand in candidates_raw:
                cit, snippets, hall_risk, cit_verified = process_citations(
                    cand["raw_citations"], reference_docs, doc_name_to_id
                )
                confidence = calculate_confidence(cand["answer"], cit, cand["not_found"])
                processed_candidates.append({
                    "candidate_id": cand["candidate_id"],
                    "generation_strategy": cand["generation_strategy"],
                    "answer": cand["answer"],
                    "confidence_score": confidence,
                    "not_found": cand["not_found"],
                    "citations": cit,
                    "evidence_snippets": snippets,
                })

            print(f"[GENERATION] Q{q_num} processed: {q_text[:60]!r}")
            primary = processed_candidates[0]
            is_not_found = all(c["not_found"] for c in processed_candidates)

            if not is_not_found:
                answered_count += 1
            else:
                not_found_count += 1

            confidence_scores.append(primary["confidence_score"])

            answer = Answer(
                questionnaire_id=questionnaire_id,
                question_number=q_num,
                question_text=q_text,
                generated_answer=primary["answer"],
                answer_candidates=processed_candidates,
                selected_candidate_index=0,
                citations=primary["citations"],
                confidence_score=primary["confidence_score"],
                evidence_snippets=primary["evidence_snippets"],
                hallucination_risk=primary.get("hallucination_risk", 0.1),
                citations_verified=all(
                    c.get("validated", False) for c in primary["citations"]
                ),
                not_found=is_not_found,
                version_number=base_version,
            )
            db.add(answer)

        # Update questionnaire.questions with LLM-identified questions so
        # regenerate and version history reflect the real question texts
        identified_questions = sorted(
            [
                {"number": q_num, "text": (candidates[0].get("question_text") or f"Question {q_num}")}
                for q_num, candidates in question_candidates_map.items()
            ],
            key=lambda q: q["number"],
        )
        q_obj = db.get(Questionnaire, questionnaire_id)
        if q_obj and not question_ids:  # only overwrite on full runs
            q_obj.questions = identified_questions
            db.add(q_obj)

        db.flush()

        # Update coverage summary
        db.execute(
            delete(CoverageSummary).where(CoverageSummary.questionnaire_id == questionnaire_id)
        )
        avg_conf = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
        coverage = CoverageSummary(
            questionnaire_id=questionnaire_id,
            total_questions=len(question_candidates_map),
            answered_with_citations=answered_count,
            not_found_count=not_found_count,
            average_confidence_score=round(avg_conf, 3),
            version_number=base_version,
        )
        db.add(coverage)

        db.commit()
        print(f"[GENERATION] ✅ Done! answered={answered_count}, not_found={not_found_count}, avg_confidence={round(avg_conf, 3)}")
    except Exception as e:
        print(f"[GENERATION] ❌ FAILED with error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


# ─── List & Get Answers ───────────────────────────────────────────────────────

@router.get("/{project_id}/answers", response_model=list[AnswerResponse])
def list_answers(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_owned_project(db, project_id, current_user.id)
    q = _get_questionnaire(db, project_id)
    if not q:
        return []
    result = db.execute(
        select(Answer)
        .where(Answer.questionnaire_id == q.id)
        .order_by(Answer.question_number.asc())
    )
    return result.scalars().all()


@router.get("/{project_id}/coverage", response_model=CoverageSummaryResponse | None)
def get_coverage(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_owned_project(db, project_id, current_user.id)
    q = _get_questionnaire(db, project_id)
    if not q:
        return None
    result = db.execute(
        select(CoverageSummary)
        .where(CoverageSummary.questionnaire_id == q.id)
        .order_by(CoverageSummary.generated_at.desc())
    )
    return result.scalar_one_or_none()


# ─── Edit Answers ─────────────────────────────────────────────────────────────

@router.put("/{project_id}/answers/{answer_id}", response_model=AnswerResponse)
def edit_answer(
    project_id: str,
    answer_id: str,
    body: AnswerEditRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_owned_project(db, project_id, current_user.id)
    answer = _get_answer(db, answer_id, project_id)
    answer.edited_answer = body.edited_answer
    answer.user_edited = True
    db.commit()
    db.refresh(answer)
    return answer


@router.post("/{project_id}/answers/{answer_id}/select-candidate", response_model=AnswerResponse)
def select_candidate(
    project_id: str,
    answer_id: str,
    body: SelectCandidateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_owned_project(db, project_id, current_user.id)
    answer = _get_answer(db, answer_id, project_id)

    candidates = answer.answer_candidates or []
    if body.candidate_index < 0 or body.candidate_index >= len(candidates):
        raise HTTPException(status_code=400, detail="Invalid candidate index")

    chosen = candidates[body.candidate_index]
    answer.selected_candidate_index = body.candidate_index
    answer.generated_answer = chosen["answer"]
    answer.citations = chosen.get("citations", [])
    answer.confidence_score = chosen.get("confidence_score")
    answer.evidence_snippets = chosen.get("evidence_snippets", [])

    db.commit()
    db.refresh(answer)
    return answer


@router.post("/{project_id}/answers/{answer_id}/regenerate", response_model=AnswerResponse)
def regenerate_single_answer(
    project_id: str,
    answer_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Regenerate a single answer synchronously and return updated answer."""
    _get_owned_project(db, project_id, current_user.id)
    answer = _get_answer(db, answer_id, project_id)

    # Get reference docs
    refs = _get_references(db, project_id)
    if not refs:
        raise HTTPException(status_code=400, detail="No reference documents uploaded")

    reference_docs = {doc.original_filename: doc.content for doc in refs}
    doc_name_to_id = {doc.original_filename: doc.id for doc in refs}

    print(f"[REGEN] Regenerating answer for Q{answer.question_number}: {answer.question_text[:60]}...")

    # Call LLM synchronously
    try:
        llm_result = generate_single_answer(answer.question_text, reference_docs, "detailed")
    except Exception as e:
        # On rate limit or other errors, just return the existing answer unchanged
        print(f"[REGEN] ⚠️ LLM error (possibly rate limited): {e}")
        return answer

    # Extract answer data from LLM response
    # LLM returns {"answers": [...]} format, get first answer
    answers_list = llm_result.get("answers", [])
    if answers_list:
        ans_data = answers_list[0]
    else:
        # Fallback if no answers array (direct answer format)
        ans_data = llm_result

    raw_citations = ans_data.get("citations", [])
    answer_text = ans_data.get("answer", "Not present in the document")
    not_found = ans_data.get("not_found", False)

    # If we got an error response from LLM, keep existing answer
    if "Error generating answer" in answer_text:
        print(f"[REGEN] ⚠️ LLM returned error, keeping existing answer")
        return answer

    # Process citations
    citations, snippets, hall_risk, cit_verified = process_citations(
        raw_citations, reference_docs, doc_name_to_id
    )
    confidence = calculate_confidence(answer_text, citations, not_found)

    # Build candidate
    processed_candidate = {
        "candidate_id": 1,
        "generation_strategy": "detailed",
        "answer": answer_text,
        "confidence_score": confidence,
        "not_found": not_found,
        "citations": citations,
        "evidence_snippets": snippets,
    }

    # Update answer record
    answer.generated_answer = answer_text
    answer.answer_candidates = [processed_candidate]
    answer.selected_candidate_index = 0
    answer.citations = citations
    answer.confidence_score = confidence
    answer.evidence_snippets = snippets
    answer.hallucination_risk = hall_risk
    answer.citations_verified = cit_verified
    answer.not_found = not_found
    answer.user_edited = False
    answer.edited_answer = None

    db.commit()
    db.refresh(answer)

    print(f"[REGEN] ✅ Done! confidence={confidence}, not_found={not_found}")
    return answer


# ─── Version History ──────────────────────────────────────────────────────────

@router.get("/{project_id}/versions", response_model=list[VersionHistoryResponse])
def list_versions(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_owned_project(db, project_id, current_user.id)
    q = _get_questionnaire(db, project_id)
    if not q:
        return []
    result = db.execute(
        select(VersionHistory)
        .where(VersionHistory.questionnaire_id == q.id)
        .order_by(VersionHistory.version_number.desc())
    )
    return result.scalars().all()


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _get_owned_project(db: Session, project_id: str, user_id: str) -> Project:
    result = db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == user_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _get_questionnaire(db: Session, project_id: str):
    result = db.execute(
        select(Questionnaire).where(Questionnaire.project_id == project_id)
    )
    return result.scalar_one_or_none()


def _get_references(db: Session, project_id: str) -> list[ReferenceDocument]:
    result = db.execute(
        select(ReferenceDocument).where(ReferenceDocument.project_id == project_id)
    )
    return result.scalars().all()


def _get_answer(db: Session, answer_id: str, project_id: str) -> Answer:
    q = db.execute(
        select(Questionnaire).where(Questionnaire.project_id == project_id)
    )
    questionnaire = q.scalar_one_or_none()
    if not questionnaire:
        raise HTTPException(status_code=404, detail="No questionnaire found")

    result = db.execute(
        select(Answer).where(
            Answer.id == answer_id,
            Answer.questionnaire_id == questionnaire.id
        )
    )
    answer = result.scalar_one_or_none()
    if not answer:
        raise HTTPException(status_code=404, detail="Answer not found")
    return answer
