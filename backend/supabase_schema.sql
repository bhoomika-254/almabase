-- QuestionnaireAI - Supabase PostgreSQL Schema
-- Run this in your Supabase SQL editor

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ─── Users ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email       VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name   VARCHAR(255),
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ─── Projects ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS projects (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name        VARCHAR(255) NOT NULL,
    description TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ─── Reference Documents ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS reference_documents (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id        UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    filename          VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    content           TEXT NOT NULL,
    file_type         VARCHAR(20) NOT NULL,
    file_size         INTEGER,
    uploaded_at       TIMESTAMPTZ DEFAULT NOW()
);

-- ─── Reference Document Index (for search) ───────────────────────────────────
CREATE TABLE IF NOT EXISTS reference_document_index (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    reference_doc_id UUID NOT NULL REFERENCES reference_documents(id) ON DELETE CASCADE,
    content_chunk    TEXT NOT NULL,
    chunk_position   INTEGER NOT NULL,
    line_number      INTEGER,
    indexed_at       TIMESTAMPTZ DEFAULT NOW()
);

-- ─── Questionnaires ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS questionnaires (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id        UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    filename          VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    questions         JSONB NOT NULL DEFAULT '[]',
    uploaded_at       TIMESTAMPTZ DEFAULT NOW()
);

-- ─── Answers ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS answers (
    id                       UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    questionnaire_id         UUID NOT NULL REFERENCES questionnaires(id) ON DELETE CASCADE,
    question_number          INTEGER NOT NULL,
    question_text            TEXT NOT NULL,
    generated_answer         TEXT,
    answer_candidates        JSONB,
    selected_candidate_index INTEGER DEFAULT 0,
    citations                JSONB,
    confidence_score         FLOAT,
    evidence_snippets        JSONB,
    hallucination_risk       FLOAT,
    citations_verified       BOOLEAN DEFAULT FALSE,
    not_found                BOOLEAN DEFAULT FALSE,
    user_edited              BOOLEAN DEFAULT FALSE,
    edited_answer            TEXT,
    version_number           INTEGER DEFAULT 1,
    created_at               TIMESTAMPTZ DEFAULT NOW(),
    updated_at               TIMESTAMPTZ DEFAULT NOW()
);

-- ─── Version History ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS version_history (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    questionnaire_id UUID NOT NULL REFERENCES questionnaires(id) ON DELETE CASCADE,
    version_number   INTEGER NOT NULL,
    answers_snapshot JSONB NOT NULL DEFAULT '[]',
    coverage_summary JSONB,
    created_at       TIMESTAMPTZ DEFAULT NOW(),
    created_by       UUID NOT NULL REFERENCES users(id)
);

-- ─── Coverage Summaries ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS coverage_summaries (
    id                       UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    questionnaire_id         UUID NOT NULL REFERENCES questionnaires(id) ON DELETE CASCADE,
    total_questions          INTEGER NOT NULL,
    answered_with_citations  INTEGER NOT NULL,
    not_found_count          INTEGER NOT NULL,
    average_confidence_score FLOAT,
    version_number           INTEGER NOT NULL,
    generated_at             TIMESTAMPTZ DEFAULT NOW()
);

-- ─── Export Formats ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS export_formats (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    questionnaire_id UUID NOT NULL REFERENCES questionnaires(id) ON DELETE CASCADE,
    format           VARCHAR(10) NOT NULL,
    exported_at      TIMESTAMPTZ DEFAULT NOW(),
    exported_by      UUID NOT NULL REFERENCES users(id)
);

-- ─── Indexes for Performance ─────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_projects_user_id ON projects(user_id);
CREATE INDEX IF NOT EXISTS idx_ref_docs_project_id ON reference_documents(project_id);
CREATE INDEX IF NOT EXISTS idx_ref_index_doc_id ON reference_document_index(reference_doc_id);
CREATE INDEX IF NOT EXISTS idx_questionnaires_project_id ON questionnaires(project_id);
CREATE INDEX IF NOT EXISTS idx_answers_questionnaire_id ON answers(questionnaire_id);
CREATE INDEX IF NOT EXISTS idx_answers_version ON answers(questionnaire_id, version_number);
CREATE INDEX IF NOT EXISTS idx_version_history_questionnaire ON version_history(questionnaire_id);
CREATE INDEX IF NOT EXISTS idx_coverage_questionnaire ON coverage_summaries(questionnaire_id);

-- Full-text search index on reference document chunks
CREATE INDEX IF NOT EXISTS idx_ref_index_chunk_text ON reference_document_index
    USING gin(to_tsvector('english', content_chunk));
