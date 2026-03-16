import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import api from '../services/api'
import type { Project, VersionHistoryItem } from '../types'

export default function VersionHistoryPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()

  const [project, setProject] = useState<Project | null>(null)
  const [versions, setVersions] = useState<VersionHistoryItem[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!projectId) return
    loadVersions()
  }, [projectId])

  const loadVersions = async () => {
    try {
      const [projRes, versionsRes] = await Promise.all([
        api.get<Project>(`/projects/${projectId}`),
        api.get<VersionHistoryItem[]>(`/projects/${projectId}/versions`),
      ])
      setProject(projRes.data)
      setVersions(versionsRes.data)
    } catch {
      navigate('/')
    } finally {
      setLoading(false)
    }
  }

  const formatDate = (iso: string) =>
    new Date(iso).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })

  if (loading) {
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
      <header className="bg-white border-b border-border px-6 py-4">
        <div className="max-w-3xl mx-auto flex items-center gap-4">
          <button
            onClick={() => navigate(`/projects/${projectId}/review`)}
            className="text-text-tertiary hover:text-text-primary transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <div>
            <h1 className="font-bold text-text-primary">{project?.name}</h1>
            <p className="text-xs text-text-tertiary">Version History</p>
          </div>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-6 py-8">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-bold text-text-primary">Past Generation Runs</h2>
          <button
            onClick={() => navigate(`/projects/${projectId}/review`)}
            className="btn-primary text-sm"
          >
            View Current Answers
          </button>
        </div>

        {versions.length === 0 ? (
          <div className="card text-center py-16">
            <div className="w-16 h-16 rounded-full bg-primary-light flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                  d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-text-primary mb-2">No version history yet</h3>
            <p className="text-text-secondary text-sm">
              Version snapshots are saved each time you regenerate answers for this project.
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {versions.map((version) => {
              const cov = version.coverage_summary as unknown as Record<string, number | null> | null
              return (
                <div key={version.id} className="card hover:border-primary transition-colors">
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="inline-flex items-center justify-center w-7 h-7 rounded-full bg-primary text-white text-sm font-bold">
                          v{version.version_number}
                        </span>
                        <span className="text-sm font-semibold text-text-primary">
                          Version {version.version_number}
                        </span>
                      </div>
                      <p className="text-xs text-text-tertiary ml-9">{formatDate(version.created_at)}</p>
                    </div>

                    {cov && (
                      <div className="flex items-center gap-4 text-right">
                        <div>
                          <p className="text-lg font-bold text-text-primary">{cov.total ?? '—'}</p>
                          <p className="text-xs text-text-tertiary">Questions</p>
                        </div>
                        <div>
                          <p className="text-lg font-bold text-success">{cov.answered ?? '—'}</p>
                          <p className="text-xs text-text-tertiary">Answered</p>
                        </div>
                        <div>
                          <p className="text-lg font-bold text-warning">{cov.not_found ?? '—'}</p>
                          <p className="text-xs text-text-tertiary">Not Found</p>
                        </div>
                        {cov.avg_confidence != null && (
                          <div>
                            <p className="text-lg font-bold text-primary">
                              {Math.round((cov.avg_confidence as number) * 100)}%
                            </p>
                            <p className="text-xs text-text-tertiary">Avg Conf</p>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </main>
    </div>
  )
}

