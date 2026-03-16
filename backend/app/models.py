from sqlalchemy import (
    Column, String, Text, Float, Boolean, Integer,
    DateTime, ForeignKey, JSON, Enum as SAEnum
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db import Base
import uuid
import enum


def gen_uuid():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    projects = relationship("Project", back_populates="user", cascade="all, delete-orphan")


class Project(Base):
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="projects")
    reference_documents = relationship("ReferenceDocument", back_populates="project", cascade="all, delete-orphan")
    questionnaires = relationship("Questionnaire", back_populates="project", cascade="all, delete-orphan")


class FileType(str, enum.Enum):
    txt = "txt"
    md = "md"
    pdf = "pdf"
    pdf_ocr = "pdf_ocr"


class ReferenceDocument(Base):
    __tablename__ = "reference_documents"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    project_id = Column(UUID(as_uuid=False), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    file_type = Column(String(20), nullable=False)
    file_size = Column(Integer, nullable=True)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project", back_populates="reference_documents")
    index_chunks = relationship("ReferenceDocumentIndex", back_populates="reference_doc", cascade="all, delete-orphan")


class ReferenceDocumentIndex(Base):
    __tablename__ = "reference_document_index"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    reference_doc_id = Column(UUID(as_uuid=False), ForeignKey("reference_documents.id", ondelete="CASCADE"), nullable=False)
    content_chunk = Column(Text, nullable=False)
    chunk_position = Column(Integer, nullable=False)
    line_number = Column(Integer, nullable=True)
    indexed_at = Column(DateTime(timezone=True), server_default=func.now())

    reference_doc = relationship("ReferenceDocument", back_populates="index_chunks")


class Questionnaire(Base):
    __tablename__ = "questionnaires"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    project_id = Column(UUID(as_uuid=False), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    questions = Column(JSON, nullable=False)  # [{"number": 1, "text": "..."}]
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project", back_populates="questionnaires")
    answers = relationship("Answer", back_populates="questionnaire", cascade="all, delete-orphan")
    versions = relationship("VersionHistory", back_populates="questionnaire", cascade="all, delete-orphan")
    coverage_summaries = relationship("CoverageSummary", back_populates="questionnaire", cascade="all, delete-orphan")
    exports = relationship("ExportFormat", back_populates="questionnaire", cascade="all, delete-orphan")


class Answer(Base):
    __tablename__ = "answers"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    questionnaire_id = Column(UUID(as_uuid=False), ForeignKey("questionnaires.id", ondelete="CASCADE"), nullable=False)
    question_number = Column(Integer, nullable=False)
    question_text = Column(Text, nullable=False)
    generated_answer = Column(Text, nullable=True)
    answer_candidates = Column(JSON, nullable=True)   # [{candidate_id, answer, strategy, confidence, citations}]
    selected_candidate_index = Column(Integer, default=0)
    citations = Column(JSON, nullable=True)            # [{doc_id, doc_name, excerpt, full_context, paragraph_number, confidence}]
    confidence_score = Column(Float, nullable=True)
    evidence_snippets = Column(JSON, nullable=True)    # [{doc_name, snippet_text}]
    hallucination_risk = Column(Float, nullable=True)
    citations_verified = Column(Boolean, default=False)
    not_found = Column(Boolean, default=False)
    user_edited = Column(Boolean, default=False)
    edited_answer = Column(Text, nullable=True)
    version_number = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    questionnaire = relationship("Questionnaire", back_populates="answers")


class VersionHistory(Base):
    __tablename__ = "version_history"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    questionnaire_id = Column(UUID(as_uuid=False), ForeignKey("questionnaires.id", ondelete="CASCADE"), nullable=False)
    version_number = Column(Integer, nullable=False)
    answers_snapshot = Column(JSON, nullable=False)
    coverage_summary = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)

    questionnaire = relationship("Questionnaire", back_populates="versions")


class CoverageSummary(Base):
    __tablename__ = "coverage_summaries"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    questionnaire_id = Column(UUID(as_uuid=False), ForeignKey("questionnaires.id", ondelete="CASCADE"), nullable=False)
    total_questions = Column(Integer, nullable=False)
    answered_with_citations = Column(Integer, nullable=False)
    not_found_count = Column(Integer, nullable=False)
    average_confidence_score = Column(Float, nullable=True)
    version_number = Column(Integer, nullable=False)
    generated_at = Column(DateTime(timezone=True), server_default=func.now())

    questionnaire = relationship("Questionnaire", back_populates="coverage_summaries")


class ExportFormat(Base):
    __tablename__ = "export_formats"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    questionnaire_id = Column(UUID(as_uuid=False), ForeignKey("questionnaires.id", ondelete="CASCADE"), nullable=False)
    format = Column(String(10), nullable=False)  # pdf, docx, html, json, csv
    exported_at = Column(DateTime(timezone=True), server_default=func.now())
    exported_by = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)

    questionnaire = relationship("Questionnaire", back_populates="exports")
