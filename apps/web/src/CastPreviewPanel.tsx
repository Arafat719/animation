import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { readCastChoices, readCastPreview, readCastProfile, originLabel } from './castPreview'
import type { CastChoice, CastPreview } from './castPreview'
import './CastPreviewPanel.css'

export default function CastPreviewPanel({
  apiBase,
  projectId,
}: {
  apiBase: string
  projectId: number
}) {
  const [choices, setChoices] = useState<CastChoice[]>([])
  const [selected, setSelected] = useState<number[]>([])
  const [loading, setLoading] = useState(true)
  const [listError, setListError] = useState('')
  const [reload, setReload] = useState(0)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [preview, setPreview] = useState<CastPreview | null>(null)
  const active = useRef<AbortController | null>(null)

  useEffect(() => () => active.current?.abort(), [])
  useEffect(() => {
    const controller = new AbortController()
    async function load() {
      try {
        const response = await fetch(`${apiBase}/characters`, {
          signal: AbortSignal.any([controller.signal, AbortSignal.timeout(10000)]),
        })
        if (!response.ok) throw new Error('Character list unavailable')
        const data = readCastChoices(await response.json())
        const loaded: CastChoice[] = []
        for (let start = 0; start < data.length; start += 8) {
          if (controller.signal.aborted) return
          const batch = await Promise.all(
            data.slice(start, start + 8).map(async (choice) => {
              const profile = await fetch(`${apiBase}/v2/characters/${choice.id}/profile`, {
                signal: AbortSignal.any([controller.signal, AbortSignal.timeout(10000)]),
              })
              if (!profile.ok) throw new Error('Profile unavailable')
              return { ...choice, origin: readCastProfile(await profile.json(), choice.id) }
            }),
          )
          loaded.push(...batch)
        }
        if (!controller.signal.aborted) setChoices(loaded)
      } catch {
        if (!controller.signal.aborted) setListError('Unable to load characters. Retry the list.')
      } finally {
        if (!controller.signal.aborted) setLoading(false)
      }
    }
    void load()
    return () => controller.abort()
  }, [apiBase, reload])

  function invalidate() {
    active.current?.abort()
    active.current = null
    setBusy(false)
    setPreview(null)
    setError('')
  }
  function toggle(id: number) {
    invalidate()
    setSelected((current) =>
      current.includes(id) ? current.filter((value) => value !== id) : [...current, id],
    )
  }
  function reloadChoices() {
    invalidate()
    setSelected([])
    setChoices([])
    setListError('')
    setLoading(true)
    setReload((current) => current + 1)
  }
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (active.current || loading || listError || selected.length < 1 || selected.length > 100)
      return
    const controller = new AbortController()
    active.current = controller
    const ids = [...selected]
    setBusy(true)
    setPreview(null)
    setError('')
    try {
      const response = await fetch(`${apiBase}/projects/${projectId}/mock-plan`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ character_ids: ids }),
        signal: AbortSignal.any([controller.signal, AbortSignal.timeout(10000)]),
      })
      if (!response.ok) {
        const messages: Record<number, string> = {
          404: 'The project or a selected character was not found. Reload the character list or reopen the project.',
          409: 'A selected character has no saved visual profile. Save its profile in Characters, then try again.',
          422: 'Preview requires a 1–4000 character project prompt, 30–60 seconds, and traits that fit the shot prompt limits.',
        }
        throw new Error(
          messages[response.status] ??
            'Unable to create the mock preview. Check the saved profiles and try again.',
        )
      }
      const result = readCastPreview(await response.json(), ids)
      if (!controller.signal.aborted && active.current === controller) setPreview(result)
    } catch (failure) {
      if (!controller.signal.aborted && active.current === controller) {
        setError(
          failure instanceof Error && failure.name === 'Error'
            ? failure.message
            : 'Preview request failed or timed out. Try again when ready.',
        )
      }
    } finally {
      if (active.current === controller) {
        active.current = null
        setBusy(false)
      }
    }
  }

  return (
    <section className="cast-preview" aria-labelledby="cast-preview-title">
      <h2 id="cast-preview-title">Character mock preview</h2>
      <p>Choose characters with saved visual profiles to preview their traits in shot prompts.</p>
      <p>
        This is a temporary, read-only mock preview. Selection and results reset on reload. No plan
        is saved, approved or rendered here.
      </p>
      <a href="#/characters">Manage character profiles</a>
      {loading ? (
        <p role="status">Loading preview characters…</p>
      ) : listError ? (
        <div>
          <p role="alert">{listError}</p>
          <button type="button" onClick={reloadChoices}>
            Retry character list
          </button>
        </div>
      ) : (
        <>
          <button type="button" onClick={reloadChoices}>
            Reload preview characters
          </button>
          {choices.length === 0 ? (
            <p>No saved characters yet. Create a character and save its visual profile first.</p>
          ) : (
            <form onSubmit={submit}>
              <fieldset>
                <legend>Preview cast · choose 1–100 characters</legend>
                {choices.map((character) => (
                  <label key={character.id} className="cast-choice">
                    <input
                      aria-label={`${character.name} · ID ${character.id}`}
                      type="checkbox"
                      checked={selected.includes(character.id)}
                      disabled={
                        !character.origin ||
                        (!selected.includes(character.id) && selected.length >= 100)
                      }
                      onChange={() => toggle(character.id)}
                    />
                    <span>
                      {character.name} · ID {character.id}
                    </span>
                    <small>
                      {character.origin ? originLabel(character.origin) : 'No saved visual profile'}
                    </small>
                  </label>
                ))}
              </fieldset>
              <p>
                {selected.length} selected
                {selected.length ? ` · Order: ${selected.join(', ')}` : ' · Select a cast to begin'}
              </p>
              <button type="submit" disabled={busy || selected.length === 0}>
                {busy ? 'Creating preview…' : 'Create character preview'}
              </button>
            </form>
          )}
        </>
      )}
      {busy && <p role="status">Creating read-only mock preview…</p>}
      {error && <p role="alert">{error}</p>}
      {preview && (
        <div className="cast-preview-result">
          <p role="status">Mock preview · Review required · Read-only</p>
          <p>
            {preview.shots.length} shots · {preview.estimated_total_duration_seconds} seconds total
          </p>
          <h3>Profile names used</h3>
          <ul>
            {preview.characters.map((character, index) => (
              <li key={character.id}>
                <span>
                  {character.name} · {character.id}
                </span>
                <p>{originLabel(preview.profile_origins[index])}</p>
              </li>
            ))}
          </ul>
          <ol className="cast-preview-shots">
            {preview.shots.map((shot) => (
              <li key={shot.id}>
                <h3>
                  Preview shot {shot.order} · {shot.duration_seconds} seconds
                </h3>
                <p>Pending · Seed {shot.seed}</p>
                <p>Visible cast: {shot.visible_character_ids.join(', ') || 'None'}</p>
                <dl>
                  <dt>Image prompt</dt>
                  <dd>{shot.image_prompt}</dd>
                  <dt>Motion prompt</dt>
                  <dd>{shot.motion_prompt}</dd>
                  <dt>Traits to avoid</dt>
                  <dd>{shot.negative_prompt || 'None specified'}</dd>
                </dl>
              </li>
            ))}
          </ol>
        </div>
      )}
    </section>
  )
}
