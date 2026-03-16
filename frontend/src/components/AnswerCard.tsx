import { useState } from 'react'
import type { Answer } from '../types'
import CitationDisplay from './CitationDisplay'

interface Props {
  answer: Answer
  onEdit: (answerId: string, text: string) => Promise<void>
  onRegenerate?: (answerId: string) => Promise<void>
  regenerating?: boolean
}

export default function AnswerCard({
  answer,
  onEdit,
  onRegenerate,
  regenerating = false,
}: Props) {
  const [editing, setEditing] = useState(false)
  const [editText, setEditText] = useState('')
  const [saving, setSaving] = useState(false)
  const [showCitations, setShowCitations] = useState(false)

  const displayAnswer =
    answer.user_edited && answer.edited_answer
      ? answer.edited_answer
      : answer.generated_answer || 'Not present in the document'

  const confidence = answer.confidence_score ?? 0
  const confidenceColor =
    confidence >= 0.8 ? 'text-success' : confidence >= 0.5 ? 'text-warning' : 'text-error'
  const confidenceBg =
    confidence >= 0.8 ? 'bg-success' : confidence >= 0.5 ? 'bg-warning' : 'bg-error'

  const handleStartEdit = () => {
    setEditText(displayAnswer)
    setEditing(true)
  }

  const handleSave = async () => {
    setSaving(true)
    await onEdit(answer.id, editText)
    setSaving(false)
    setEditing(false)
  }

  const citationsToShow = answer.citations ?? []

  return (
    <div className={`card ${answer.not_found ? 'border-l-4 border-l-warning' : ''}`}>
      {/* Question */}
      <div className="flex items-start gap-3 mb-3">
        <span className="inline-flex items-center justify-center w-7 h-7 rounded-full bg-primary-light text-primary text-sm font-bold flex-shrink-0">
          {answer.question_number}
        </span>
        <p className="text-sm font-semibold text-text-primary flex-1">{answer.question_text}</p>
      </div>

      {/* Status badges row */}
      <div className="flex items-center gap-2 mb-3 flex-wrap">
        {answer.not_found ? (
          <span className="badge-warning">Not found in references</span>
        ) : (
          <>
            <span className={`text-xs font-semibold ${confidenceColor}`}>
              {Math.round(confidence * 100)}% confidence
            </span>
            <div className="flex-1 max-w-24 h-1.5 bg-gray-200 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full ${confidenceBg}`}
                style={{ width: `${confidence * 100}%` }}
              />
            </div>
          </>
        )}
        {answer.user_edited && <span className="badge-success">Edited</span>}
        {answer.citations_verified && (
          <span className="text-xs text-success font-medium">Citations verified</span>
        )}
      </div>

      {/* Answer text */}
      {editing ? (
        <div className="mb-3">
          <textarea
            className="input-field w-full min-h-[100px] resize-y text-sm"
            value={editText}
            onChange={(e) => setEditText(e.target.value)}
            autoFocus
          />
          <div className="flex gap-2 mt-2">
            <button onClick={handleSave} disabled={saving} className="btn-primary text-sm py-1.5">
              {saving ? 'Saving...' : 'Save'}
            </button>
            <button onClick={() => setEditing(false)} className="btn-secondary text-sm py-1.5">
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <p className={`text-sm leading-relaxed mb-3 ${
          answer.not_found ? 'text-text-tertiary italic' : 'text-text-primary'
        }`}>
          {displayAnswer}
        </p>
      )}

      {/* Evidence snippets */}
      {answer.evidence_snippets && answer.evidence_snippets.length > 0 && !answer.not_found && (
        <div className="mb-3">
          <p className="text-xs font-semibold text-text-secondary mb-1">Sources:</p>
          <div className="flex flex-wrap gap-1">
            {answer.evidence_snippets.map((s, i) => (
              <span key={i} className="text-xs bg-primary-light text-primary rounded px-2 py-0.5">
                {s.doc_name}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Citations toggle */}
      {citationsToShow.length > 0 && (
        <button
          onClick={() => setShowCitations((v) => !v)}
          className="text-xs text-primary hover:underline mb-2"
        >
          {showCitations ? 'Hide' : 'Show'} {citationsToShow.length} citation
          {citationsToShow.length > 1 ? 's' : ''}
        </button>
      )}

      {showCitations && (
        <CitationDisplay citations={citationsToShow} />
      )}

      {/* Actions */}
      {!editing && (
        <div className="flex gap-2 mt-3 pt-3 border-t border-border">
          <button onClick={handleStartEdit} disabled={regenerating} className="btn-secondary text-xs py-1.5 px-3">
            Edit
          </button>
          {onRegenerate && (
            <button
              onClick={() => onRegenerate(answer.id)}
              disabled={regenerating}
              className="btn-secondary text-xs py-1.5 px-3 flex items-center gap-1.5"
            >
              {regenerating ? (
                <>
                  <svg className="animate-spin h-3 w-3" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Regenerating...
                </>
              ) : (
                'Regenerate'
              )}
            </button>
          )}
        </div>
      )}
    </div>
  )
}
