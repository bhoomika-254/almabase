from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Any
from datetime import datetime


# ─── Auth ──────────────────────────────────────────────────────────────────

class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    full_name: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    full_name: Optional[str] = None


# ─── Projects ──────────────────────────────────────────────────────────────

class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ─── Reference Documents ───────────────────────────────────────────────────

class ReferenceDocumentResponse(BaseModel):
    id: str
    filename: str
    original_filename: str
    file_type: str
    file_size: Optional[int]
    uploaded_at: datetime

    model_config = {"from_attributes": True}


class SearchResult(BaseModel):
    doc_id: str
    doc_name: str
    snippet: str
    chunk_position: int


# ─── Questionnaire ─────────────────────────────────────────────────────────

class QuestionItem(BaseModel):
    number: int
    text: str


class QuestionnaireResponse(BaseModel):
    id: str
    filename: str
    original_filename: str
    questions: List[QuestionItem]
    uploaded_at: datetime

    model_config = {"from_attributes": True}


# ─── Citations ─────────────────────────────────────────────────────────────

class CitationItem(BaseModel):
    doc_id: str
    doc_name: str
    excerpt: str
    full_context: str
    paragraph_number: Optional[int] = None
    confidence: float


class EvidenceSnippet(BaseModel):
    doc_name: str
    snippet_text: str


class AnswerCandidate(BaseModel):
    candidate_id: int
    answer: str
    generation_strategy: str
    confidence_score: float
    citations: List[CitationItem]


# ─── Answers ───────────────────────────────────────────────────────────────

class AnswerResponse(BaseModel):
    id: str
    question_number: int
    question_text: str
    generated_answer: Optional[str]
    answer_candidates: Optional[List[AnswerCandidate]]
    selected_candidate_index: int
    citations: Optional[List[CitationItem]]
    confidence_score: Optional[float]
    evidence_snippets: Optional[List[EvidenceSnippet]]
    hallucination_risk: Optional[float]
    citations_verified: bool
    not_found: bool
    user_edited: bool
    edited_answer: Optional[str]
    version_number: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AnswerEditRequest(BaseModel):
    edited_answer: str


class SelectCandidateRequest(BaseModel):
    candidate_index: int


class GenerateAnswersRequest(BaseModel):
    question_ids: Optional[List[int]] = None  # None = generate all; list = partial regeneration


# ─── Coverage Summary ──────────────────────────────────────────────────────

class CoverageSummaryResponse(BaseModel):
    id: str
    total_questions: int
    answered_with_citations: int
    not_found_count: int
    average_confidence_score: Optional[float]
    version_number: int
    generated_at: datetime

    model_config = {"from_attributes": True}


# ─── Version History ───────────────────────────────────────────────────────

class VersionHistoryResponse(BaseModel):
    id: str
    version_number: int
    coverage_summary: Optional[Any]
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Export ────────────────────────────────────────────────────────────────

class ExportRequest(BaseModel):
    format: str = Field(pattern="^(pdf|docx|html|json|csv)$")
