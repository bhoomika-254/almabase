import type { CitationItem } from '../types'

interface Props {
  citations: CitationItem[]
}

export default function CitationDisplay({ citations }: Props) {
  if (!citations || citations.length === 0) return null

  return (
    <div className="mt-4 border-t border-border pt-4">
      <h4 className="section-label mb-3">Citations</h4>
      <div className="space-y-3">
        {citations.map((citation, idx) => (
          <div
            key={idx}
            className="bg-gray-50 rounded-lg border border-border p-3"
          >
            <div className="flex items-start gap-2">
              <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-primary text-white text-xs font-bold flex-shrink-0 mt-0.5">
                {idx + 1}
              </span>
              <div className="flex-1 min-w-0">
                <p className="text-xs font-semibold text-primary mb-1 truncate">
                  {citation.doc_name}
                </p>
                <blockquote className="text-sm text-text-primary italic border-l-2 border-primary pl-2 my-1">
                  &ldquo;{citation.excerpt}&rdquo;
                </blockquote>
                {citation.full_context && citation.full_context !== citation.excerpt && (
                  <p className="text-xs text-text-secondary mt-1 line-clamp-2">
                    Context: {citation.full_context}
                  </p>
                )}
                <span
                  className={`text-xs font-medium ${
                    citation.confidence >= 0.9
                      ? 'text-success'
                      : citation.confidence >= 0.7
                      ? 'text-warning'
                      : 'text-error'
                  }`}
                >
                  {Math.round(citation.confidence * 100)}% confidence
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
