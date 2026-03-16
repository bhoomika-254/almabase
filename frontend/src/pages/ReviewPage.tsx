import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import api from '../services/api'
import type { Answer, CoverageSummary, Project } from '../types'
import AnswerCard from '../components/AnswerCard'

type GenerationStatus = 'idle' | 'generating' | 'done' | 'error'

export default function ReviewPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()

  const [project, setProject] = useState<Project | null>(null)
  const [answers, setAnswers] = useState<Answer[]>([])
  const [coverage, setCoverage] = useState<CoverageSummary | null>(null)
  const [genStatus, setGenStatus] = useState<GenerationStatus>('idle')
  const [loadingPage, setLoadingPage] = useState(true)
  const [showExport, setShowExport] = useState(false)
  const [regeneratingId, setRegeneratingId] = useState<string | null>(null)
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    if (!projectId) return
    loadPage()
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current)
    }
  }, [projectId])

  const loadPage = async () => {
    setLoadingPage(true)
    try {
      const projRes = await api.get<Project>(`/projects/${projectId}`)
      setProject(projRes.data)

      const [answersRes, coverageRes] = await Promise.allSettled([
        api.get<Answer[]>(`/projects/${projectId}/answers`),
        api.get<CoverageSummary>(`/projects/${projectId}/coverage`),
      ])

      if (answersRes.status === 'fulfilled') setAnswers(answersRes.value.data)
      if (coverageRes.status === 'fulfilled') setCoverage(coverageRes.value.data)

      if (answersRes.status === 'fulfilled' && answersRes.value.data.length > 0) {
        setGenStatus('done')
      }
    } catch {
      navigate('/')
    } finally {
      setLoadingPage(false)
    }
  }

  const handleGenerate = async (questionIds?: number[]) => {
    if (!projectId) return
    setGenStatus('generating')
    try {
      await api.post(`/projects/${projectId}/generate-answers`, {
        question_ids: questionIds ?? null,
      })
      pollingRef.current = setInterval(async () => {
        try {
          const [answersRes, coverageRes] = await Promise.all([
            api.get<Answer[]>(`/projects/${projectId}/answers`),
            api.get<CoverageSummary>(`/projects/${projectId}/coverage`),
          ])
          if (answersRes.data.length > 0) {
            setAnswers(answersRes.data)
            setCoverage(coverageRes.data)
            setGenStatus('done')
            if (pollingRef.current) clearInterval(pollingRef.current)
          }
        } catch {
          // keep polling
        }
      }, 3000)
    } catch {
      setGenStatus('error')
    }
  }

  const handleRegenerate = useCallback(async (answerId: string) => {
    if (!projectId) return
    setRegeneratingId(answerId)
    try {
      const res = await api.post<Answer>(`/projects/${projectId}/answers/${answerId}/regenerate`)
      // Update the specific answer in state
      setAnswers((prev) => prev.map((a) => (a.id === answerId ? res.data : a)))
      // Refresh coverage summary
      const coverageRes = await api.get<CoverageSummary>(`/projects/${projectId}/coverage`)
      setCoverage(coverageRes.data)
    } catch (err: unknown) {
      // Silently skip on rate limit (429) or other errors - don't show alert
      console.error('Regeneration failed:', err)
    } finally {
      setRegeneratingId(null)
    }
  }, [projectId])

  const handleEdit = useCallback(async (answerId: string, text: string) => {
    const res = await api.put<Answer>(`/projects/${projectId}/answers/${answerId}`, {
      edited_answer: text,
    })
    setAnswers((prev) => prev.map((a) => (a.id === answerId ? res.data : a)))
  }, [projectId])

  const handleExport = async (format: string) => {
    try {
      const res = await api.post(
        `/projects/${projectId}/export`,
        { format },
        { responseType: 'blob' }
      )
      const url = window.URL.createObjectURL(new Blob([res.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `questionnaire_answers.${format}`)
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
    } catch {
      alert('Export failed. Please try again.')
    }
    setShowExport(false)
  }

  if (loadingPage) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <svg className="animate-spin h-8 w-8 text-primary" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-border px-6 py-4 sticky top-0 z-10">
        <div className="max-w-4xl mx-auto flex items-center gap-4">
          <button onClick={() => navigate(`/projects/${projectId}/upload`)}
            className="text-text-tertiary hover:text-text-primary transition-colors">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <div>
            <h1 className="font-bold text-text-primary">{project?.name}</h1>
            <p className="text-xs text-text-tertiary">Review &amp; Export</p>
          </div>
          <div className="ml-auto flex items-center gap-2">
            <button
              onClick={() => navigate(`/projects/${projectId}/history`)}
              className="btn-secondary text-sm"
            >
              History
            </button>
            {/* Export */}
            <div className="relative">
              <button className="btn-secondary text-sm" onClick={() => setShowExport((v) => !v)}>
                Export ▾
              </button>
              {showExport && (
                <div className="absolute right-0 mt-1 w-44 bg-white border border-border rounded-lg shadow-md z-20">
                  {['pdf', 'docx', 'html', 'json', 'csv'].map((fmt) => (
                    <button
                      key={fmt}
                      onClick={() => handleExport(fmt)}
                      className="block w-full text-left px-4 py-2.5 text-sm text-text-primary hover:bg-gray-50 first:rounded-t-lg last:rounded-b-lg"
                    >
                      Export as .{fmt.toUpperCase()}
                    </button>
                  ))}
                </div>
              )}
            </div>
            {genStatus !== 'generating' && (
              <button onClick={() => handleGenerate()} className="btn-primary text-sm">
                {answers.length > 0 ? 'Regenerate All' : 'Generate Answers'}
              </button>
            )}
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-8">
        {/* Coverage banner */}
        {coverage && (
          <div className="card mb-6 bg-gradient-to-r from-primary-light to-white border-primary">
            <div className="flex items-center justify-between flex-wrap gap-4">
              <h2 className="text-lg font-bold text-primary">Coverage Summary</h2>
              <div className="flex items-center gap-6 text-sm">
                <div className="text-center">
                  <p className="text-2xl font-bold text-text-primary">{coverage.total_questions}</p>
                  <p className="text-text-secondary text-xs">Total</p>
                </div>
                <div className="text-center">
                  <p className="text-2xl font-bold text-success">{coverage.answered_with_citations}</p>
                  <p className="text-text-secondary text-xs">Answered</p>
                </div>
                <div className="text-center">
                  <p className="text-2xl font-bold text-warning">{coverage.not_found_count}</p>
                  <p className="text-text-secondary text-xs">Not Found</p>
                </div>
                <div className="text-center">
                  <p className="text-2xl font-bold text-primary">
                    {coverage.average_confidence_score
                      ? `${Math.round(coverage.average_confidence_score * 100)}%`
                      : 'N/A'}
                  </p>
                  <p className="text-text-secondary text-xs">Avg Confidence</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Status states */}
        {genStatus === 'generating' && (
          <div className="card text-center py-12 mb-6">
            <svg className="animate-spin h-10 w-10 text-primary mx-auto mb-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            <h3 className="text-lg font-semibold text-text-primary mb-2">Generating answers...</h3>
            <p className="text-text-secondary text-sm">
              AI is reading reference documents and generating answers for each question.
            </p>
          </div>
        )}

        {genStatus === 'error' && (
          <div className="card border-error bg-red-50 text-center py-8 mb-6">
            <p className="text-error font-semibold">Generation failed.</p>
            <p className="text-text-secondary text-sm mt-1">Check your GROQ_API_KEY and try again.</p>
            <button onClick={() => handleGenerate()} className="btn-primary mt-4">Retry</button>
          </div>
        )}

        {genStatus === 'idle' && answers.length === 0 && (
          <div className="card text-center py-16">
            <div className="w-16 h-16 rounded-full bg-primary-light flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                  d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-text-primary mb-2">No answers yet</h3>
            <p className="text-text-secondary text-sm mb-6">
              Click "Generate Answers" to have AI answer all questions using your reference documents
            </p>
            <button onClick={() => handleGenerate()} className="btn-primary">Generate Answers</button>
          </div>
        )}

        {/* Answer cards */}
        {answers.length > 0 && (
          <div className="space-y-4">
            {answers.map((answer) => (
              <AnswerCard
                key={answer.id}
                answer={answer}
                onEdit={handleEdit}
                onRegenerate={handleRegenerate}
                regenerating={regeneratingId === answer.id}
              />
            ))}
          </div>
        )}
      </main>
    </div>
  )
}

