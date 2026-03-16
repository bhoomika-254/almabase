import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import api from '../services/api'
import type { SearchResult } from '../types'

export default function SearchReferencesPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()

  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResult[]>([])
  const [loading, setLoading] = useState(false)
  const [searched, setSearched] = useState(false)

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!query.trim() || !projectId) return
    setLoading(true)
    setSearched(true)
    try {
      const res = await api.get<SearchResult[]>(
        `/projects/${projectId}/references/search`,
        { params: { q: query.trim(), limit: 20 } }
      )
      setResults(res.data)
    } catch {
      setResults([])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-border px-6 py-4">
        <div className="max-w-3xl mx-auto flex items-center gap-4">
          <button onClick={() => navigate(-1)} className="text-text-tertiary hover:text-text-primary transition-colors">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <div>
            <h1 className="font-bold text-text-primary">Search Reference Documents</h1>
            <p className="text-xs text-text-tertiary">Find specific information across all uploaded docs</p>
          </div>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-6 py-8">
        <form onSubmit={handleSearch} className="flex gap-3 mb-8">
          <input
            type="text"
            className="input-field flex-1"
            placeholder="e.g. FERPA, encryption, data retention, uptime SLA..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            autoFocus
          />
          <button type="submit" disabled={loading || !query.trim()} className="btn-primary px-6">
            {loading ? (
              <svg className="animate-spin h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            ) : 'Search'}
          </button>
        </form>

        {searched && !loading && results.length === 0 && (
          <div className="text-center py-12">
            <svg className="w-12 h-12 text-text-tertiary mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <p className="text-text-secondary">No matches found for &ldquo;{query}&rdquo;</p>
            <p className="text-text-tertiary text-sm mt-1">Try different keywords</p>
          </div>
        )}

        {results.length > 0 && (
          <div className="space-y-3">
            <p className="text-sm text-text-secondary mb-4">
              {results.length} result{results.length > 1 ? 's' : ''} for &ldquo;{query}&rdquo;
            </p>
            {results.map((result, idx) => (
              <div key={idx} className="card hover:border-primary transition-colors">
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-md bg-primary-light flex items-center justify-center flex-shrink-0 mt-0.5">
                    <svg className="w-4 h-4 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                        d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-primary mb-1">{result.doc_name}</p>
                    <p className="text-sm text-text-secondary leading-relaxed">
                      {highlightTerms(result.snippet, query.split(/\s+/).filter(Boolean))}
                    </p>
                    <p className="text-xs text-text-tertiary mt-2">Section {result.chunk_position + 1}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {!searched && (
          <div className="text-center py-16 text-text-tertiary">
            <svg className="w-12 h-12 mx-auto mb-3 opacity-40" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <p className="text-sm">Search across all your uploaded reference documents</p>
          </div>
        )}
      </main>
    </div>
  )
}

function highlightTerms(text: string, terms: string[]): React.ReactNode {
  if (!terms.length) return text
  const pattern = new RegExp(
    `(${terms.map(t => t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')})`,
    'gi'
  )
  const parts = text.split(pattern)
  return parts.map((part, i) =>
    pattern.test(part)
      ? <mark key={i} className="bg-yellow-100 text-text-primary rounded px-0.5">{part}</mark>
      : part
  )
}

