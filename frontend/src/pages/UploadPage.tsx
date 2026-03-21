import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import api from '../services/api'
import type { Project, ReferenceDocument, Questionnaire } from '../types'
import UploadArea from '../components/UploadArea'

function FileIcon({ type }: { type: string }) {
  const color = type === 'pdf' || type === 'pdf_ocr' ? 'text-red-500' : 'text-primary'
  return (
    <svg className={`w-4 h-4 flex-shrink-0 ${color}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
        d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
    </svg>
  )
}

export default function UploadPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()

  const [project, setProject] = useState<Project | null>(null)
  const [refs, setRefs] = useState<ReferenceDocument[]>([])
  const [questionnaire, setQuestionnaire] = useState<Questionnaire | null>(null)
  const [loadingPage, setLoadingPage] = useState(true)
  const [uploadingRefs, setUploadingRefs] = useState(false)
  const [uploadingQ, setUploadingQ] = useState(false)
  const [refError, setRefError] = useState('')
  const [qError, setQError] = useState('')
  const [deletingId, setDeletingId] = useState<string | null>(null)

  useEffect(() => {
    if (!projectId) return
    loadAll()
  }, [projectId])

  const loadAll = async () => {
    setLoadingPage(true)
    try {
      const [projRes, refsRes] = await Promise.all([
        api.get<Project>(`/projects/${projectId}`),
        api.get<ReferenceDocument[]>(`/projects/${projectId}/references`),
      ])
      setProject(projRes.data)
      setRefs(refsRes.data)

      try {
        const qRes = await api.get<Questionnaire>(`/projects/${projectId}/questionnaire`)
        setQuestionnaire(qRes.data)
      } catch {
        setQuestionnaire(null)
      }
    } catch {
      navigate('/')
    } finally {
      setLoadingPage(false)
    }
  }

  const handleRefUpload = useCallback(async (files: File[]) => {
    setRefError('')
    setUploadingRefs(true)
    const newDocs: ReferenceDocument[] = []
    for (const file of files) {
      const form = new FormData()
      form.append('file', file)
      try {
        const res = await api.post<ReferenceDocument>(
          `/projects/${projectId}/references`,
          form,
          { headers: { 'Content-Type': 'multipart/form-data' } }
        )
        newDocs.push(res.data)
      } catch (err: unknown) {
        const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || `Failed: ${file.name}`
        setRefError(msg)
        break
      }
    }
    if (newDocs.length) setRefs((prev) => [...prev, ...newDocs])
    setUploadingRefs(false)
  }, [projectId])

  const handleQUpload = useCallback(async (files: File[]) => {
    if (!files[0]) return
    setQError('')
    setUploadingQ(true)
    const form = new FormData()
    form.append('file', files[0])
    try {
      const res = await api.post<Questionnaire>(
        `/projects/${projectId}/questionnaire`,
        form,
        { headers: { 'Content-Type': 'multipart/form-data' } }
      )
      setQuestionnaire(res.data)
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Upload failed'
      setQError(msg)
    } finally {
      setUploadingQ(false)
    }
  }, [projectId])

  const handleDeleteRef = async (docId: string) => {
    setDeletingId(docId)
    try {
      await api.delete(`/projects/${projectId}/references/${docId}`)
      setRefs((prev) => prev.filter((r) => r.id !== docId))
    } catch {
      // ignore
    } finally {
      setDeletingId(null)
    }
  }

  const canGenerate = refs.length > 0 && questionnaire !== null

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
      <header className="bg-white border-b border-border px-6 py-4">
        <div className="max-w-4xl mx-auto flex items-center gap-4">
          <button onClick={() => navigate('/')} className="text-text-tertiary hover:text-text-primary transition-colors">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <div>
            <h1 className="font-bold text-text-primary">{project?.name}</h1>
            <p className="text-xs text-text-tertiary">Upload &amp; Configure</p>
          </div>
          <div className="ml-auto flex items-center gap-3">
            <button
              onClick={() => navigate(`/projects/${projectId}/search`)}
              className="btn-secondary text-sm"
            >
              Search Docs
            </button>
            <button
              disabled={!canGenerate}
              onClick={() => navigate(`/projects/${projectId}/review`)}
              className={`btn-primary text-sm ${!canGenerate ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
              Generate Answers
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-8 space-y-8">
        {/* Step 1: Reference docs */}
        <section>
          <div className="flex items-center justify-between mb-3">
            <div>
              <h2 className="text-lg font-semibold text-text-primary">
                Step 1: Reference Documents
              </h2>
              <p className="text-sm text-text-secondary">
                Upload the source docs the AI will use to answer questions (PDF, MD, TXT)
              </p>
            </div>
            <span className="badge-success">{refs.length} uploaded</span>
          </div>

          <UploadArea
            accept=".pdf,.md,.txt"
            multiple
            onFiles={handleRefUpload}
            label="Upload reference documents"
            hint="PDF, Markdown, or TXT — up to 20 MB each"
            loading={uploadingRefs}
          />

          <p className="text-[10px] text-text-tertiary mt-2">
            Note: Currently this website doesn't scan for scanned PDFs because I don't have money.
          </p>

          {refError && <p className="text-sm text-error mt-2">{refError}</p>}

          {refs.length > 0 && (
            <ul className="mt-4 space-y-2">
              {refs.map((doc) => (
                <li key={doc.id} className="flex items-center gap-3 bg-white border border-border rounded-lg px-4 py-3">
                  <FileIcon type={doc.file_type} />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-text-primary truncate">{doc.original_filename}</p>
                    <p className="text-xs text-text-tertiary">
                      {doc.file_type.toUpperCase()}
                      {doc.file_size && ` · ${(doc.file_size / 1024).toFixed(0)} KB`}
                      {doc.file_type === 'pdf_ocr' && ' · OCR processed'}
                    </p>
                  </div>
                  <button
                    onClick={() => handleDeleteRef(doc.id)}
                    disabled={deletingId === doc.id}
                    className="text-text-tertiary hover:text-error transition-colors flex-shrink-0"
                    title="Remove"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>

        {/* Step 2: Questionnaire */}
        <section>
          <div className="flex items-center justify-between mb-3">
            <div>
              <h2 className="text-lg font-semibold text-text-primary">
                Step 2: Questionnaire
              </h2>
              <p className="text-sm text-text-secondary">
                Upload a numbered questionnaire (CSV, PDF, TXT, or MD)
              </p>
            </div>
            {questionnaire && <span className="badge-success">Uploaded</span>}
          </div>

          {!questionnaire ? (
            <>
              <UploadArea
                accept=".csv,.pdf,.txt,.md"
                onFiles={handleQUpload}
                label="Upload questionnaire"
                hint="CSV, PDF, TXT, or MD — questions will be identified automatically"
                loading={uploadingQ}
              />
              <p className="text-[10px] text-text-tertiary mt-2">
                Note: Currently this website doesn't scan for scanned PDFs because I don't have money.
              </p>
              {qError && <p className="text-sm text-error mt-2">{qError}</p>}
            </>
          ) : (
            <div className="card">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <svg className="w-5 h-5 text-success" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  <p className="font-medium text-text-primary">{questionnaire.original_filename}</p>
                  <span className="text-xs text-text-tertiary">({questionnaire.questions.length} question{questionnaire.questions.length !== 1 ? 's' : ''})</span>
                </div>
                <button
                  onClick={() => setQuestionnaire(null)}
                  className="text-xs text-text-tertiary hover:text-primary"
                >
                  Replace
                </button>
              </div>
              <div className="bg-gray-50 rounded-lg p-3 max-h-64 overflow-y-auto">
                {questionnaire.questions.length === 1 ? (
                  // Single raw questionnaire text
                  <pre className="text-sm text-text-secondary whitespace-pre-wrap font-sans leading-relaxed">
                    {questionnaire.questions[0]?.text}
                  </pre>
                ) : (
                  // Multiple numbered questions (after LLM extraction)
                  <div className="space-y-3">
                    {questionnaire.questions.map((q) => (
                      <div key={q.number} className="text-sm">
                        <p className="font-medium text-text-primary">Q{q.number}</p>
                        <p className="text-text-secondary mt-1">{q.text}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </section>

        {/* Step 3: Generate */}
        {canGenerate && (
          <section className="card bg-primary-light border-primary">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-semibold text-primary mb-1">Ready to generate answers!</h3>
                <p className="text-sm text-text-secondary">
                  {refs.length} reference doc{refs.length > 1 ? 's' : ''} · Questionnaire ready
                </p>
              </div>
              <button
                onClick={() => navigate(`/projects/${projectId}/review`)}
                className="btn-primary"
              >
                Generate Answers
              </button>
            </div>
          </section>
        )}
      </main>
    </div>
  )
}

