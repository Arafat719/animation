import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { profileFields, profileLists, profileFromForm, readSavedProfile } from './characterProfile'
import type { ProfileForm, SavedProfile } from './characterProfile'
import './CharacterProfilePanel.css'

interface Props {
  apiBase: string
  character: { id: number; name: string; description: string | null }
}
type View = 'loading' | 'empty' | 'saved' | 'error'

const readError =
  'Unable to verify the saved profile. Retry loading before saving. Your entries are preserved.'
async function fetchProfile(url: string, characterId: number, signal: AbortSignal) {
  const response = await fetch(url, {
    signal: AbortSignal.any([signal, AbortSignal.timeout(10000)]),
  })
  if (!response.ok) throw new Error('Profile read failed')
  const data: unknown = await response.json()
  return data === null ? null : readSavedProfile(data, characterId)
}

// Parent keys this panel by API base + character ID, so a selection change retires all requests.
export default function CharacterProfilePanel({ apiBase, character }: Props) {
  const [view, setView] = useState<View>('loading')
  const [saved, setSaved] = useState<SavedProfile | null>(null)
  const [form, setForm] = useState<ProfileForm>({
    name: character.name,
    description: character.description ?? '',
    face: '',
    hair: '',
    eyes: '',
    outfit: '',
    colors: '',
    accessories: '',
    negative_traits: '',
  })
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [saving, setSaving] = useState(false)
  const active = useRef<AbortController | null>(null)
  const url = `${apiBase}/characters/${character.id}/profile`

  async function load(controller: AbortController, recovering = false) {
    try {
      const snapshot = await fetchProfile(url, character.id, controller.signal)
      if (controller.signal.aborted) return
      setSaved(snapshot)
      setView(snapshot ? 'saved' : 'empty')
      if (recovering) {
        setNotice(snapshot ? 'The saved profile has been retrieved.' : '')
        if (!snapshot)
          setError(
            'No saved profile was found. Your entries are preserved; review them before saving again.',
          )
      }
    } catch {
      if (!controller.signal.aborted) {
        setView('error')
        setError(readError)
      }
    }
  }

  useEffect(() => {
    const controller = new AbortController()
    active.current = controller
    void fetchProfile(url, character.id, controller.signal)
      .then((snapshot) => {
        if (controller.signal.aborted) return
        setSaved(snapshot)
        setView(snapshot ? 'saved' : 'empty')
      })
      .catch(() => {
        if (controller.signal.aborted) return
        setView('error')
        setError(readError)
      })
      .finally(() => {
        if (active.current === controller) active.current = null
      })
    return () => {
      controller.abort()
      active.current?.abort()
    }
  }, [url, character.id])

  async function retry() {
    if (active.current) return
    setView('loading')
    setError('')
    const controller = new AbortController()
    active.current = controller
    try {
      await load(controller)
    } finally {
      if (active.current === controller) active.current = null
    }
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (active.current || view !== 'empty') return
    setError('')
    setNotice('')
    let payload
    try {
      payload = profileFromForm(form)
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'Check the profile fields.')
      return
    }
    const controller = new AbortController()
    active.current = controller
    setSaving(true)
    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: AbortSignal.any([controller.signal, AbortSignal.timeout(10000)]),
      })
      if (controller.signal.aborted) return
      if (response.status === 422) {
        setError('The profile was rejected. Check the required fields and item limits.')
        return
      }
      if (!response.ok) throw new Error('Save needs verification')
      const snapshot = readSavedProfile(await response.json(), character.id)
      if (!controller.signal.aborted) {
        setSaved(snapshot)
        setView('saved')
        setNotice('Profile saved. These traits are now read-only.')
      }
    } catch {
      if (!controller.signal.aborted) {
        setView('loading')
        setError('')
        await load(controller, true)
      }
    } finally {
      if (!controller.signal.aborted) setSaving(false)
      if (active.current === controller) active.current = null
    }
  }

  return (
    <section
      className="character-traits-panel"
      aria-label={`Profile for ${character.name}`}
      aria-busy={view === 'loading' || saving}
    >
      <h2>Visual profile · {character.name}</h2>
      <p>Describe the character’s appearance yourself. These traits are not extracted by AI.</p>
      {view === 'loading' && <p role="status">Loading profile…</p>}
      {notice && <p role="status">{notice}</p>}
      {error && <p role="alert">{error}</p>}
      {view === 'error' && (
        <button type="button" onClick={() => void retry()}>
          Retry profile load
        </button>
      )}
      {view === 'empty' && (
        <>
          <p>No visual profile saved yet.</p>
          <form className="project-form" onSubmit={submit}>
            {profileFields.map(([field, label, limit]) => (
              <label key={field}>
                <span>
                  {label} (required, up to {limit} characters)
                </span>
                <textarea
                  name={`profile-${field}`}
                  value={form[field]}
                  required
                  rows={field === 'description' ? 4 : 2}
                  disabled={saving}
                  onChange={(event) =>
                    setForm((current) => ({ ...current, [field]: event.target.value }))
                  }
                />
              </label>
            ))}
            {profileLists.map(([field, label, min, max]) => (
              <label key={field}>
                <span>
                  {label} ({min ? 'required' : 'optional'}; {min}–{max} items)
                </span>
                <small>
                  One item per line, up to 500 characters each. Blank lines are ignored.
                </small>
                <textarea
                  name={`profile-${field}`}
                  value={form[field]}
                  required={min > 0}
                  rows={3}
                  disabled={saving}
                  onChange={(event) =>
                    setForm((current) => ({ ...current, [field]: event.target.value }))
                  }
                />
              </label>
            ))}
            <p>Saving locks this profile. You cannot edit or replace its traits afterward.</p>
            <button type="submit" disabled={saving}>
              {saving ? 'Saving profile…' : 'Save immutable profile'}
            </button>
          </form>
        </>
      )}
      {view === 'saved' && saved && (
        <>
          <p className="read-only-label">Saved profile · Read-only</p>
          <h3>{saved.profile.name}</h3>
          <p className="profile-description">{saved.profile.description}</p>
          <dl>
            {(['face', 'hair', 'eyes', 'outfit'] as const).map((field) => (
              <div key={field}>
                <dt>{field}</dt>
                <dd>{saved.profile.visual_traits[field]}</dd>
              </div>
            ))}
            {profileLists.map(([field, label]) => {
              const values =
                field === 'negative_traits'
                  ? saved.profile.negative_traits
                  : saved.profile.visual_traits[field]
              return (
                <div key={field}>
                  <dt>{label}</dt>
                  <dd>
                    {values.length ? (
                      <ul>
                        {values.map((value, index) => (
                          <li key={index}>{value}</li>
                        ))}
                      </ul>
                    ) : (
                      'None specified'
                    )}
                  </dd>
                </div>
              )
            })}
          </dl>
        </>
      )}
    </section>
  )
}
