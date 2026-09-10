import { useEffect, useState } from 'react'
import type { Project } from './App'
import JobsPanel from './JobsPanel'
import './LibraryPages.css'

export default function ProjectWorkspace({ apiBase, projectId }: { apiBase: string; projectId: number }) {
  const [project, setProject] = useState<Project | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [retry, setRetry] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    const load = async () => {
      setLoading(true)
      setError('')
      try {
        const response = await fetch(`${apiBase}/projects/${projectId}`, {
          signal: AbortSignal.any([controller.signal, AbortSignal.timeout(10000)]),
        })
        if (!response.ok) {
          throw new Error(response.status === 404 ? 'Project not found.' : `Unable to load project (HTTP ${response.status}).`)
        }
        const data: Project = await response.json()
        if (!controller.signal.aborted) setProject(data)
      } catch (failure) {
        if (!controller.signal.aborted) {
          setError(failure instanceof Error ? failure.message : 'Unable to load project.')
        }
      } finally {
        if (!controller.signal.aborted) setLoading(false)
      }
    }
    void load()
    return () => controller.abort()
  }, [apiBase, projectId, retry])

  return (
    <main className="app-shell">
      <section className="panel workspace library-page project-workspace-page">
        <a href="#/">Back to projects</a>
        <p className="eyebrow">Project workspace</p>
        {loading ? <p role="status">Loading project…</p> : error ? (
          <div>
            <h1>Project unavailable</h1>
            <p role="alert">{error}</p>
            <button type="button" onClick={() => setRetry(value => value + 1)}>Retry</button>
          </div>
        ) : project && (
          <>
            <header className="project-workspace-intro">
              <h1>{project.title}</h1>
              <span className="project-folio">Production no. {String(project.id).padStart(3, '0')}</span>
            </header>
            <dl className="project-details">
              <div><dt>Project ID</dt><dd>{project.id}</dd></div>
              <div><dt>Status</dt><dd>{project.status}</dd></div>
              <div><dt>Target duration</dt><dd>{project.target_duration_seconds === null ? 'Not set' : `${project.target_duration_seconds} seconds`}</dd></div>
            </dl>
            <section className="project-brief" aria-labelledby="master-prompt-title">
              <div className="project-brief-heading"><p className="eyebrow">01 / The creative brief</p><h2 id="master-prompt-title">Master prompt</h2></div>
              <p className="master-prompt">{project.master_prompt?.trim() ? project.master_prompt : 'No prompt saved yet.'}</p>
            </section>
            <JobsPanel apiBase={apiBase} projects={[project]} projectId={project.id} />
          </>
        )}
      </section>
    </main>
  )
}
