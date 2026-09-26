import { useEffect, useRef, useState } from 'react'
import './ShotList.css'

type Preview = {
  shots: { id: string; order: number; duration_seconds: number; image_prompt: string }[]
  estimated_total_duration_seconds: number
}

function readPreview(value: unknown): Preview | null {
  if (value === null) return null
  const plan = value as Preview
  if (
    !plan ||
    !Array.isArray(plan.shots) ||
    plan.shots.length < 6 ||
    plan.shots.length > 10 ||
    !Number.isFinite(plan.estimated_total_duration_seconds) ||
    plan.shots.some(
      (shot, i) =>
        !shot ||
        typeof shot.id !== 'string' ||
        shot.order !== i + 1 ||
        !Number.isFinite(shot.duration_seconds) ||
        shot.duration_seconds < 3 ||
        shot.duration_seconds > 6 ||
        typeof shot.image_prompt !== 'string' ||
        !shot.image_prompt.trim(),
    ) ||
    new Set(plan.shots.map((shot) => shot.id)).size !== plan.shots.length ||
    plan.estimated_total_duration_seconds < 30 ||
    plan.estimated_total_duration_seconds > 60 ||
    Math.abs(
      plan.shots.reduce((sum, shot) => sum + shot.duration_seconds, 0) -
        plan.estimated_total_duration_seconds,
    ) > 0.000001
  ) {
    throw new Error('Invalid shot preview received.')
  }
  return plan
}

export default function ShotList({ apiBase, projectId }: { apiBase: string; projectId: number }) {
  const [plan, setPlan] = useState<Preview | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [retry, setRetry] = useState(0)
  const [revision, setRevision] = useState(0)
  const [approved, setApproved] = useState(false)
  const [dirty, setDirty] = useState(false)
  const [busy, setBusy] = useState(false)
  const [actionError, setActionError] = useState('')
  const [completed, setCompleted] = useState(false)
  const active = useRef<AbortController | null>(null)
  useEffect(() => () => active.current?.abort(), [])

  async function change(action: 'save' | 'approve' | 'mock-render') {
    if (active.current || !plan) return
    const controller = new AbortController()
    active.current = controller
    setBusy(true)
    setActionError('')
    try {
      const response = await fetch(
        `${apiBase}/projects/${projectId}/plan${action === 'save' ? '' : '/' + action}`,
        {
          method: action === 'save' ? 'PUT' : 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(action === 'save' ? { revision, plan } : { revision }),
          signal: AbortSignal.any([controller.signal, AbortSignal.timeout(10000)]),
        },
      )
      const data = await response.json()
      if (!response.ok)
        throw new Error(
          typeof data.detail === 'string'
            ? data.detail
            : 'Plan action failed. Check the prompts and retry.',
        )
      const next = readPreview(data.plan)
      if (!controller.signal.aborted) {
        setPlan(next)
        setRevision(data.revision)
        setApproved(data.approved)
        setDirty(false)
        setCompleted(Boolean(data.result))
      }
    } catch (failure) {
      if (!controller.signal.aborted)
        setActionError(failure instanceof Error ? failure.message : 'Plan action failed.')
    } finally {
      if (!controller.signal.aborted) setBusy(false)
      active.current = null
    }
  }
  useEffect(() => {
    const controller = new AbortController()
    setLoading(true)
    setPlan(null)
    setError('')
    async function load() {
      try {
        const response = await fetch(`${apiBase}/projects/${projectId}/plan`, {
          signal: AbortSignal.any([controller.signal, AbortSignal.timeout(10000)]),
        })
        if (!response.ok)
          throw new Error(
            response.status === 422
              ? 'Mock preview needs a prompt of up to 4000 characters and a duration of 30–60 seconds.'
              : `Unable to load shots (HTTP ${response.status}).`,
          )
        const data = await response.json()
        const preview = readPreview(data.plan)
        if (!controller.signal.aborted) {
          setPlan(preview)
          setRevision(data.revision)
          setApproved(data.approved)
          setDirty(false)
          setCompleted(Boolean(data.result))
          setActionError('')
        }
      } catch (failure) {
        if (!controller.signal.aborted)
          setError(failure instanceof Error ? failure.message : 'Unable to load shots.')
      } finally {
        if (!controller.signal.aborted) setLoading(false)
      }
    }
    void load()
    return () => controller.abort()
  }, [apiBase, projectId, retry])
  return (
    <section className="shot-preview" aria-labelledby="shot-preview-title">
      <h2 id="shot-preview-title">Shot list</h2>
      <p>Mock plan · Edit prompts, save and approve before a mock render. No video is generated.</p>
      {loading ? (
        <p role="status">Loading shots…</p>
      ) : error ? (
        <div>
          <p role="alert">{error}</p>
          <button type="button" onClick={() => setRetry((value) => value + 1)}>
            Retry shots
          </button>
        </div>
      ) : !plan ? (
        <p>No shots yet. Save a project with a prompt to see its mock plan.</p>
      ) : (
        <>
          <p>
            {plan.shots.length} shots · {plan.estimated_total_duration_seconds} seconds total
          </p>
          <p role="status">
            {busy
              ? 'Saving or processing…'
              : dirty
                ? 'Unsaved changes · approval required after saving'
                : completed
                  ? 'Mock render completed · no media generated'
                  : approved
                    ? 'Approved'
                    : 'Draft · approval required'}
          </p>
          {actionError && <p role="alert">{actionError}</p>}
          <div className="plan-actions">
            <button
              type="button"
              disabled={busy || (!dirty && revision > 0)}
              onClick={() => void change('save')}
            >
              Save plan
            </button>
            <button
              type="button"
              disabled={busy || dirty || revision === 0 || approved}
              onClick={() => void change('approve')}
            >
              Approve plan
            </button>
            <button
              type="button"
              disabled={busy || dirty || !approved || completed}
              onClick={() => void change('mock-render')}
            >
              Mock render
            </button>
            <button type="button" disabled={busy} onClick={() => setRetry((value) => value + 1)}>
              Reload saved plan
            </button>
          </div>
          <ol className="shot-list">
            {plan.shots.map((shot) => (
              <li key={shot.id}>
                <h3>
                  Shot {shot.order}{' '}
                  <span>· {Number(shot.duration_seconds.toFixed(3))} seconds</span>
                </h3>
                <label>
                  Shot {shot.order} prompt
                  <textarea
                    className="shot-prompt"
                    value={shot.image_prompt}
                    maxLength={4000}
                    disabled={busy}
                    onChange={(event) => {
                      setPlan({
                        ...plan,
                        shots: plan.shots.map((item) =>
                          item.id === shot.id
                            ? { ...item, image_prompt: event.target.value }
                            : item,
                        ),
                      })
                      setDirty(true)
                      setCompleted(false)
                      setActionError('')
                    }}
                  />
                </label>
              </li>
            ))}
          </ol>
        </>
      )}
    </section>
  )
}
