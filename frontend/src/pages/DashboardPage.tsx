import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../services/api'
import type { Project } from '../types'
import { useAuth } from '../context/AuthContext'

export default function DashboardPage() {
  const navigate = useNavigate()
  const { user, logout } = useAuth()

  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [newName, setNewName] = useState('')
  const [newDesc, setNewDesc] = useState('')
  const [creating, setCreating] = useState(false)
  const [createError, setCreateError] = useState('')
  const [openMenuId, setOpenMenuId] = useState<string | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<Project | null>(null)
  const [deleting, setDeleting] = useState(false)
  const [showSamplePreview, setShowSamplePreview] = useState(false)
  const [loadingSample, setLoadingSample] = useState(false)

  useEffect(() => {
    fetchProjects()
  }, [])

  const fetchProjects = async () => {
    try {
      const res = await api.get<Project[]>('/projects')
      setProjects(res.data)
    } catch {
      // handled by 401 interceptor
    } finally {
      setLoading(false)
    }
  }

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newName.trim()) return
    setCreating(true)
    setCreateError('')
    try {
      const res = await api.post<Project>('/projects', {
        name: newName.trim(),
        description: newDesc.trim() || undefined,
      })
      setProjects((prev) => [res.data, ...prev])
      setShowCreate(false)
      setNewName('')
      setNewDesc('')
      navigate(`/projects/${res.data.id}/upload`)
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Could not create project.'
      setCreateError(msg)
    } finally {
      setCreating(false)
    }
  }

  const formatDate = (iso: string) =>
    new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })

  const handleDelete = async () => {
    if (!deleteTarget) return
    setDeleting(true)
    try {
      await api.delete(`/projects/${deleteTarget.id}`)
      setProjects((prev) => prev.filter((p) => p.id !== deleteTarget.id))
      setDeleteTarget(null)
    } catch {
      // silently ignore; user can retry
    } finally {
      setDeleting(false)
    }
  }

  const handleLoadSample = async () => {
    setLoadingSample(true)
    setShowSamplePreview(false)
    try {
      const res = await api.post<Project>('/projects/sample')
      setProjects((prev) => [res.data, ...prev])
      navigate(`/projects/${res.data.id}/review`)
    } catch {
      // silently ignore
    } finally {
      setLoadingSample(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Top nav */}
      <header className="bg-white border-b border-border px-6 py-4">
        <div className="max-w-5xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
              <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <span className="font-bold text-text-primary">QuestionnaireAI</span>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-sm text-text-secondary">{user?.full_name || user?.email}</span>
            <button onClick={logout} className="text-sm text-text-tertiary hover:text-text-primary transition-colors">
              Sign out
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-10">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold text-text-primary">My Projects</h1>
            <p className="text-text-secondary text-sm mt-1">
              Upload questionnaires and reference docs to auto-generate grounded answers
            </p>
          </div>
          <button onClick={() => setShowCreate(true)} className="btn-primary">
            + New Project
          </button>
        </div>

        {/* Sample data notice */}
        <div className="mb-6 bg-primary-light border border-primary rounded-lg px-4 py-3 flex items-center justify-between gap-4">
          <p className="text-xs text-text-secondary">
            Don't have data? No worries, test it out on the sample data that I generated
          </p>
          <button
            onClick={() => setShowSamplePreview(true)}
            disabled={loadingSample}
            className="btn-primary text-xs py-1.5 px-3 whitespace-nowrap"
          >
            {loadingSample ? 'Loading...' : 'Use Sample Data'}
          </button>
        </div>

        {loading && (
          <div className="flex justify-center py-20">
            <svg className="animate-spin h-8 w-8 text-primary" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
          </div>
        )}

        {!loading && projects.length === 0 && (
          <div className="card text-center py-16">
            <div className="w-16 h-16 rounded-full bg-primary-light flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                  d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-text-primary mb-2">No projects yet</h3>
            <p className="text-text-secondary text-sm mb-6 max-w-xs mx-auto">
              Create a project to start uploading reference documents and questionnaires
            </p>
            <button onClick={() => setShowCreate(true)} className="btn-primary">
              Create your first project
            </button>
          </div>
        )}

        {!loading && projects.length > 0 && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {/* Invisible overlay to close menu when clicking outside */}
            {openMenuId && (
              <div className="fixed inset-0 z-10" onClick={() => setOpenMenuId(null)} />
            )}
            {projects.map((project) => (
              <div
                key={project.id}
                className="card hover:shadow-md cursor-pointer transition-all duration-200 hover:border-primary group"
                onClick={() => navigate(`/projects/${project.id}/upload`)}
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="w-10 h-10 rounded-lg bg-primary-light flex items-center justify-center flex-shrink-0">
                    <svg className="w-5 h-5 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                        d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                  </div>
                  {/* Three-dot menu */}
                  <div className="relative z-20" onClick={(e) => e.stopPropagation()}>
                    <button
                      className="p-1 rounded hover:bg-gray-100 text-text-tertiary hover:text-text-primary transition-colors"
                      onClick={() => setOpenMenuId(openMenuId === project.id ? null : project.id)}
                    >
                      <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                        <circle cx="12" cy="5" r="1.5" />
                        <circle cx="12" cy="12" r="1.5" />
                        <circle cx="12" cy="19" r="1.5" />
                      </svg>
                    </button>
                    {openMenuId === project.id && (
                      <div className="absolute right-0 top-7 w-32 bg-white border border-border rounded-lg shadow-lg z-20 py-1">
                        <button
                          className="w-full text-left px-3 py-2 text-sm text-error hover:bg-red-50 transition-colors"
                          onClick={() => { setDeleteTarget(project); setOpenMenuId(null) }}
                        >
                          Delete
                        </button>
                      </div>
                    )}
                  </div>
                </div>
                <h3 className="font-semibold text-text-primary mb-1 truncate">{project.name}</h3>
                {project.description && (
                  <p className="text-text-secondary text-sm mb-3 line-clamp-2">{project.description}</p>
                )}
                <p className="text-xs text-text-tertiary mt-2">Created {formatDate(project.created_at)}</p>
              </div>
            ))}
          </div>
        )}
      </main>

      {/* Create project modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50 px-4">
          <div className="card w-full max-w-md shadow-lg">
            <h2 className="text-xl font-bold text-text-primary mb-1">New Project</h2>
            <p className="text-text-secondary text-sm mb-5">
              Give your questionnaire answering project a name
            </p>
            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="section-label block mb-1">Project Name</label>
                <input
                  type="text"
                  className="input-field w-full"
                  placeholder="e.g. FERPA Compliance Review 2025"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  required
                  autoFocus
                />
              </div>
              <div>
                <label className="section-label block mb-1">Description (optional)</label>
                <input
                  type="text"
                  className="input-field w-full"
                  placeholder="Brief description of this project"
                  value={newDesc}
                  onChange={(e) => setNewDesc(e.target.value)}
                />
              </div>
              {createError && <p className="text-sm text-error">{createError}</p>}
              <div className="flex gap-3 pt-1">
                <button type="submit" disabled={creating} className="btn-primary flex-1">
                  {creating ? 'Creating...' : 'Create Project'}
                </button>
                <button
                  type="button"
                  onClick={() => { setShowCreate(false); setCreateError('') }}
                  className="btn-secondary flex-1"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete confirmation modal */}
      {deleteTarget && (
        <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50 px-4">
          <div className="card w-full max-w-sm shadow-lg">
            <h2 className="text-lg font-bold text-text-primary mb-2">Delete Project</h2>
            <p className="text-text-secondary text-sm mb-5">
              Are you sure you want to delete <span className="font-semibold text-text-primary">"{deleteTarget.name}"</span>?
              This will permanently remove the project and all its documents and answers.
            </p>
            <div className="flex gap-3">
              <button
                onClick={handleDelete}
                disabled={deleting}
                className="flex-1 px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-60"
              >
                {deleting ? 'Deleting...' : 'Delete'}
              </button>
              <button
                onClick={() => setDeleteTarget(null)}
                disabled={deleting}
                className="btn-secondary flex-1"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Sample data preview modal */}
      {showSamplePreview && (
        <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50 px-4">
          <div className="card w-full max-w-2xl shadow-lg max-h-[80vh] overflow-y-auto">
            <h2 className="text-xl font-bold text-text-primary mb-1">Sample Data Preview</h2>
            <p className="text-text-secondary text-sm mb-5">
              This will create a project with pre-loaded FERPA compliance questionnaire and reference documents
            </p>

            <div className="space-y-4 mb-6">
              <div>
                <h3 className="text-sm font-semibold text-text-primary mb-2">Reference Documents (7 files)</h3>
                <ul className="text-xs text-text-secondary space-y-1 bg-gray-50 rounded-lg p-3">
                  <li>• Company Overview</li>
                  <li>• Security & Privacy Policy</li>
                  <li>• FERPA Compliance Policy</li>
                  <li>• Infrastructure & Operations</li>
                  <li>• Data Retention & Privacy Policy</li>
                  <li>• Accessibility Standards & Compliance</li>
                  <li>• Third-Party Integrations</li>
                </ul>
              </div>

              <div>
                <h3 className="text-sm font-semibold text-text-primary mb-2">Sample Questionnaire</h3>
                <p className="text-xs text-text-secondary bg-gray-50 rounded-lg p-3">
                  12 FERPA compliance questions covering security, data retention, encryption standards, uptime SLA, GDPR compliance, authentication, data residency, accessibility, and certifications.
                </p>
              </div>
            </div>

            <div className="flex gap-3">
              <button
                onClick={handleLoadSample}
                disabled={loadingSample}
                className="btn-primary flex-1"
              >
                {loadingSample ? 'Loading...' : 'Load Sample & Generate Answers'}
              </button>
              <button
                onClick={() => setShowSamplePreview(false)}
                disabled={loadingSample}
                className="btn-secondary flex-1"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

