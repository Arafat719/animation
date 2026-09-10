import { useEffect, useRef, useState } from 'react'
import SampleArtifacts from './SampleArtifacts'

interface RenderJob {
  id: number
  project_id: number
  current_step: string | null
  current_shot: number | null
  state: string
  progress: number
}

interface SavedOutcome {
  result: { image: Artifact; audio: Artifact; video: Artifact } | null
  error: { code: string; message: string } | null
}

interface Artifact {
  kind: string
  duration_seconds: number | null
}

const isActive = (job: RenderJob) => job.state === 'queued' || job.state === 'running'

interface JobsPanelProps {
  apiBase: string
  projects: { id: number; title: string }[]
  projectId?: number
}

async function requestJobData<T>(url: string, signal: AbortSignal, method = 'GET'): Promise<T> {
  const response = await fetch(url, {
    method,
    signal: AbortSignal.any([signal, AbortSignal.timeout(10000)]),
    ...(method === 'POST' ? {
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    } : {}),
  })
  if (!response.ok) {
    throw new Error(`Job request failed (HTTP ${response.status}).`)
  }
  return response.json()
}

export default function JobsPanel({ apiBase, projects, projectId }: JobsPanelProps) {
  const [jobs, setJobs] = useState<RenderJob[]>([])
  const [outcomes, setOutcomes] = useState<Record<number, SavedOutcome | null>>({})
  const [resultErrors, setResultErrors] = useState<Record<number, string>>({})
  const [loading, setLoading] = useState(true)
  const [pollError, setPollError] = useState('')
  const [createError, setCreateError] = useState('')
  const [startingId, setStartingId] = useState<number | null>(null)
  const [cancellingId, setCancellingId] = useState<number | null>(null)
  const [cancelError, setCancelError] = useState('')
  const [refresh, setRefresh] = useState(0)
  const createRequest = useRef<AbortController | null>(null)
  const cancelRequest = useRef<AbortController | null>(null)
  const pollRequest = useRef<AbortController | null>(null)

  useEffect(() => () => {
    createRequest.current?.abort()
    cancelRequest.current?.abort()
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    pollRequest.current = controller
    let timer: ReturnType<typeof setTimeout> | undefined

    const poll = async () => {
      try {
        let latest = await requestJobData<RenderJob[]>(`${apiBase}/jobs`, controller.signal)
        if (projectId !== undefined) latest = latest.filter(job => job.project_id === projectId)
        if (!controller.signal.aborted) {
          setJobs(latest)
          setPollError('')
          // Result failures must not hide progress or prevent cancellation.
          await Promise.all(latest.filter(job => !isActive(job)).map(async job => {
            try {
              const outcome = await requestJobData<SavedOutcome | null>(
                `${apiBase}/jobs/${job.id}/result`, controller.signal,
              )
              if (!controller.signal.aborted) {
                setOutcomes(current => ({ ...current, [job.id]: outcome }))
                setResultErrors(current => ({ ...current, [job.id]: '' }))
              }
            } catch (error) {
              if (!controller.signal.aborted) setResultErrors(current => ({
                ...current, [job.id]: error instanceof Error ? error.message : 'Unable to load result.',
              }))
            }
          }))
        }
      } catch (error) {
        if (!controller.signal.aborted) {
          setPollError(error instanceof Error ? error.message : 'Unable to refresh jobs.')
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false)
          // Schedule after completion: requests never overlap within this panel.
          timer = setTimeout(() => void poll(), 2000)
        }
      }
    }

    void poll()
    return () => {
      controller.abort()
      clearTimeout(timer)
    }
  }, [apiBase, refresh, projectId])

  const startJob = async (projectId: number) => {
    if (createRequest.current || cancelRequest.current) return
    const controller = new AbortController()
    createRequest.current = controller
    pollRequest.current?.abort()
    setStartingId(projectId)
    setCreateError('')
    try {
      const job = await requestJobData<RenderJob>(
        `${apiBase}/projects/${projectId}/fixture-jobs`, controller.signal, 'POST',
      )
      if (!controller.signal.aborted) {
        setJobs(current => [...current.filter(item => item.id !== job.id), job])
      }
    } catch (error) {
      if (!controller.signal.aborted) {
        const detail = error instanceof Error ? error.message : 'Unable to start job.'
        setCreateError(`${detail} Check the job list before trying again.`)
      }
    } finally {
      if (!controller.signal.aborted) {
        setStartingId(null)
        setLoading(true)
        // Re-read after success or an ambiguous network failure; never retry POST automatically.
        setRefresh(value => value + 1)
      }
      createRequest.current = null
    }
  }

  const cancelJob = async (jobId: number) => {
    if (cancelRequest.current || createRequest.current) return
    const controller = new AbortController()
    cancelRequest.current = controller
    // Prevent an older poll response from replacing the cancellation result.
    pollRequest.current?.abort()
    setCancellingId(jobId)
    setCancelError('')
    try {
      const job = await requestJobData<RenderJob>(
        `${apiBase}/jobs/${jobId}/cancel`, controller.signal, 'POST',
      )
      if (!controller.signal.aborted) {
        setJobs(current => current.map(item => item.id === job.id ? job : item))
      }
    } catch (error) {
      if (!controller.signal.aborted) {
        const detail = error instanceof Error ? error.message : 'Unable to cancel job.'
        setCancelError(`Job #${jobId}: ${detail} Check its latest status before retrying.`)
      }
    } finally {
      if (!controller.signal.aborted) {
        setCancellingId(null)
        setLoading(true)
        setRefresh(value => value + 1)
      }
      cancelRequest.current = null
    }
  }

  return (
    <section className="jobs-panel" aria-labelledby="jobs-heading">
      <div className="render-heading"><div><p className="eyebrow">03 / The screening room</p><h2 id="jobs-heading">Sample generation</h2></div><span className="sample-label"><span aria-hidden="true">◌</span> SAMPLE MODE</span></div>
      <p className="jobs-note">Run a sample with fixed image, audio and video. It does not create animation from your prompt or match the target duration. Work continues when you leave this page.</p>
      {projects.length === 0 ? <p>Create a project with a prompt to generate a sample.</p> : (
        <ul className="job-actions">
          {projects.map(project => {
            const running = jobs.some(job => job.project_id === project.id && isActive(job))
            return (
              <li key={project.id}>
                <span>{project.title}</span>
                <button type="button" onClick={() => void startJob(project.id)}
                  disabled={loading || Boolean(pollError) || startingId !== null || cancellingId !== null || running}>
                  {startingId === project.id ? 'Starting…' : running ? 'Sample in progress' : 'Generate sample'}
                </button>
              </li>
            )
          })}
        </ul>
      )}
      {loading && <p role="status">Loading jobs…</p>}
      {createError && <p role="alert">{createError}</p>}
      {cancelError && <p role="alert">{cancelError}</p>}
      {pollError && <p role="alert">{pollError} Displaying last known progress; reconnecting…</p>}
      {!loading && !pollError && jobs.length === 0 && <p>No jobs yet.</p>}
      <ul className="jobs-list">
        {jobs.map(job => (
          <li key={job.id} data-job-id={job.id}>
            <strong>{projects.find(project => project.id === job.project_id)?.title ?? `Project #${job.project_id}`} — Job #{job.id}</strong>
            <span>{job.state} · {job.current_step || 'queued'} · {job.progress}%</span>
            <progress max={100} value={job.progress} aria-label={`Job ${job.id} progress`} />
            {isActive(job) && (
              <button type="button" aria-label={`Cancel job ${job.id}`}
                onClick={() => void cancelJob(job.id)}
                disabled={cancellingId !== null || startingId !== null || loading}>
                {cancellingId === job.id ? 'Cancelling…' : 'Cancel job'}
              </button>
            )}
            {job.state === 'cancelled' && <small>Cancelled. Progress has stopped.</small>}
            {resultErrors[job.id] && <small role="alert">Result unavailable: {resultErrors[job.id]} Retrying…</small>}
            {outcomes[job.id]?.error && <small role="alert">{outcomes[job.id]?.error?.code}: {outcomes[job.id]?.error?.message}</small>}
            {outcomes[job.id]?.result && <div className="sample-result" aria-label={`Job ${job.id} result`}>
              <small>Sample ready. Preview the fixed sample or download each file below.</small>
              <small>Video duration: {outcomes[job.id]?.result?.video.duration_seconds}s</small>
              <SampleArtifacts apiBase={apiBase} jobId={job.id} />
            </div>}
            {!isActive(job) && outcomes[job.id] === null && <small>No saved result available for this job.</small>}
          </li>
        ))}
      </ul>
    </section>
  )
}
