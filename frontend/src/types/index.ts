// ─── Auth ──────────────────────────────────────────────────────────────────

export interface User {
  user_id: string
  email: string
  full_name?: string
}

export interface TokenResponse extends User {
  access_token: string
  token_type: string
}

// ─── Projects ──────────────────────────────────────────────────────────────

export interface Project {
  id: string
  name: string
  description?: string
  created_at: string
  updated_at: string
}

// ─── Reference Documents ───────────────────────────────────────────────────

export interface ReferenceDocument {
  id: string
  filename: string
  original_filename: string
  file_type: string
  file_size?: number
  uploaded_at: string
}

export interface SearchResult {
  doc_id: string
  doc_name: string
  snippet: string
  chunk_position: number
}

// ─── Questionnaire ─────────────────────────────────────────────────────────

export interface QuestionItem {
  number: number
  text: string
}

export interface Questionnaire {
  id: string
  filename: string
  original_filename: string
  questions: QuestionItem[]
  uploaded_at: string
}

// ─── Citations ─────────────────────────────────────────────────────────────

export interface CitationItem {
  doc_id: string
  doc_name: string
  excerpt: string
  full_context: string
  paragraph_number?: number
  confidence: number
}

export interface EvidenceSnippet {
  doc_name: string
  snippet_text: string
}

export interface AnswerCandidate {
  candidate_id: number
  answer: string
  generation_strategy: 'detailed' | 'concise' | 'executive'
  confidence_score: number
  citations: CitationItem[]
}

// ─── Answers ───────────────────────────────────────────────────────────────

export interface Answer {
  id: string
  question_number: number
  question_text: string
  generated_answer?: string
  answer_candidates?: AnswerCandidate[]
  selected_candidate_index: number
  citations?: CitationItem[]
  confidence_score?: number
  evidence_snippets?: EvidenceSnippet[]
  hallucination_risk?: number
  citations_verified: boolean
  not_found: boolean
  user_edited: boolean
  edited_answer?: string
  version_number: number
  created_at: string
  updated_at: string
}

// ─── Coverage Summary ──────────────────────────────────────────────────────

export interface CoverageSummary {
  id: string
  total_questions: number
  answered_with_citations: number
  not_found_count: number
  average_confidence_score?: number
  version_number: number
  generated_at: string
}

// ─── Version History ───────────────────────────────────────────────────────

export interface VersionHistoryItem {
  id: string
  version_number: number
  coverage_summary?: CoverageSummary
  created_at: string
}
