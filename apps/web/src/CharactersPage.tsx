import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import './LibraryPages.css'

interface Character {
  id: number
  name: string
  description: string | null
  created_at: string
}

export default function CharactersPage({ apiBase }: { apiBase: string }) {
  const [characters, setCharacters] = useState<Character[]>([])
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [listError, setListError] = useState('')
  const [saveError, setSaveError] = useState('')
  const [message, setMessage] = useState('')
  const [reload, setReload] = useState(0)
  const saveRequest = useRef<AbortController | null>(null)

  useEffect(() => () => saveRequest.current?.abort(), [])

  useEffect(() => {
    const controller = new AbortController()
    const load = async () => {
      setLoading(true)
      setListError('')
      try {
        const response = await fetch(`${apiBase}/characters`, {
          signal: AbortSignal.any([controller.signal, AbortSignal.timeout(10000)]),
        })
        if (!response.ok) throw new Error(`Unable to load characters (HTTP ${response.status}).`)
        const data: Character[] = await response.json()
        if (!controller.signal.aborted) setCharacters(data)
      } catch (error) {
        if (!controller.signal.aborted) setListError(error instanceof Error ? error.message : 'Unable to load characters.')
      } finally {
        if (!controller.signal.aborted) setLoading(false)
      }
    }
    void load()
    return () => controller.abort()
  }, [apiBase, reload])

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (saveRequest.current || loading || listError) return
    setSaveError('')
    setMessage('')
    if (!name.trim()) {
      setSaveError('Character name is required.')
      return
    }
    const controller = new AbortController()
    saveRequest.current = controller
    setSaving(true)
    try {
      const response = await fetch(`${apiBase}/characters`, {
        method: 'POST',
        signal: AbortSignal.any([controller.signal, AbortSignal.timeout(10000)]),
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: name.trim(), description: description.trim() || null }),
      })
      if (!response.ok) throw new Error(`Unable to save character (HTTP ${response.status}).`)
      const character: Character = await response.json()
      if (!controller.signal.aborted) {
        setCharacters(current => [...current, character])
        setName('')
        setDescription('')
        setMessage(`Character saved: ${character.name}`)
      }
    } catch (error) {
      if (!controller.signal.aborted) {
        const detail = error instanceof Error ? error.message : 'Unable to save character.'
        setSaveError(`${detail} Check the list before retrying.`)
        setReload(value => value + 1)
      }
    } finally {
      if (!controller.signal.aborted) setSaving(false)
      saveRequest.current = null
    }
  }

  return (
    <main className="app-shell"><section className="panel workspace library-page characters-page">
      <a href="#/">Back to projects</a>
      <header className="library-intro">
        <div>
          <p className="eyebrow">The studio collection / 01</p>
          <h1>Characters</h1>
          <p className="library-lede">Every story begins with <em>someone.</em></p>
          <p className="library-description">Save a name and description for each character.</p>
        </div>
        <div className="library-illustration cast-illustration" aria-hidden="true">
          <svg viewBox="0 0 210 150" fill="none">
            <path d="M32 128V35L58 16h120v112H32Z" stroke="currentColor" />
            <path d="M43 138V46M43 138h145V27" stroke="currentColor" opacity=".35" />
            <path d="M58 16v19H32M50 108h24m66 0h20M50 115h15m75 0h20" stroke="currentColor" />
            <path d="M81 104c0-15 10-29 25-29s25 14 25 29" fill="currentColor" opacity=".16" />
            <ellipse cx="106" cy="57" rx="15" ry="19" fill="currentColor" opacity=".25" />
            <path d="M76 104h60M91 34h29M106 30v8" stroke="currentColor" />
          </svg>
          <span>Notes on a character</span>
        </div>
      </header>
      <div className="library-layout">
      <section className="library-composer" aria-labelledby="character-form-title">
        <p className="eyebrow">01 / Character notes</p>
        <h2 id="character-form-title">Meet your next character.</h2>
      <form className="project-form" onSubmit={submit}>
        <label><span>Character name</span>
          <input name="name" value={name} maxLength={120} required disabled={saving}
            onChange={event => setName(event.target.value)} />
        </label>
        <label><span>Description (optional)</span>
          <textarea name="description" value={description} maxLength={4000} rows={4} disabled={saving}
            onChange={event => setDescription(event.target.value)} />
        </label>
        <button type="submit" disabled={saving || loading || Boolean(listError)}>{saving ? 'Saving…' : 'Save character'}</button>
      </form>
      {message && <p role="status">{message}</p>}
      {saveError && <p role="alert">{saveError}</p>}
      </section>
      <section className="library-catalog" aria-labelledby="characters-catalog-title">
      <div className="library-section-heading">
        <div><p className="eyebrow">02 / The cast</p><h2 id="characters-catalog-title">Saved characters</h2></div>
        {!loading && !listError && <span className="library-count" aria-label={`${characters.length} saved characters`}>{String(characters.length).padStart(2, '0')}</span>}
      </div>
      {loading && <p role="status">Loading characters…</p>}
      {listError && <div><p role="alert">{listError}</p><button type="button" disabled={saving} onClick={() => setReload(value => value + 1)}>Retry</button></div>}
      {!loading && !listError && characters.length === 0 && <div className="library-empty">
        <span className="library-empty-mark" aria-hidden="true">Aa</span>
        <p>No characters yet.</p>
        <span>A name, a few details, the beginning of a story.</span>
      </div>}
      <ul className="character-list">
        {characters.map(character => (
          <li key={character.id} data-character-id={character.id}>
            <div className="character-profile-top">
              <span className="character-monogram" aria-hidden="true">{Array.from(character.name.trim())[0]?.toLocaleUpperCase()}</span>
              <span className="profile-index">Character / {String(character.id).padStart(2, '0')}</span>
            </div>
            <h3>{character.name}</h3>
            <p className="master-prompt">{character.description || 'No description saved.'}</p>
          </li>
        ))}
      </ul>
      </section>
      </div>
    </section></main>
  )
}
