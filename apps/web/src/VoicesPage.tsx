import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import './LibraryPages.css'

interface Voice {
  id: number
  name: string
  voice_type: string
  language: string | null
  style: string | null
  created_at: string
}

export default function VoicesPage({ apiBase }: { apiBase: string }) {
  const [voices, setVoices] = useState<Voice[]>([])
  const [name, setName] = useState('')
  const [language, setLanguage] = useState('')
  const [style, setStyle] = useState('')
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
        const response = await fetch(`${apiBase}/voices`, {
          signal: AbortSignal.any([controller.signal, AbortSignal.timeout(10000)]),
        })
        if (!response.ok) throw new Error(`Unable to load voices (HTTP ${response.status}).`)
        const data: Voice[] = await response.json()
        if (!controller.signal.aborted) setVoices(data)
      } catch (error) {
        if (!controller.signal.aborted) setListError(error instanceof Error ? error.message : 'Unable to load voices.')
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
      setSaveError('Voice name is required.')
      return
    }
    const controller = new AbortController()
    saveRequest.current = controller
    setSaving(true)
    try {
      const response = await fetch(`${apiBase}/voices`, {
        method: 'POST',
        signal: AbortSignal.any([controller.signal, AbortSignal.timeout(10000)]),
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: name.trim(), language: language.trim() || null, style: style.trim() || null }),
      })
      if (!response.ok) throw new Error(`Unable to save voice (HTTP ${response.status}).`)
      const voice: Voice = await response.json()
      if (!controller.signal.aborted) {
        setVoices(current => [...current, voice])
        setName('')
        setLanguage('')
        setStyle('')
        setMessage(`Voice saved: ${voice.name}`)
      }
    } catch (error) {
      if (!controller.signal.aborted) {
        const detail = error instanceof Error ? error.message : 'Unable to save voice.'
        setSaveError(`${detail} Check the list before retrying.`)
        setReload(value => value + 1)
      }
    } finally {
      if (!controller.signal.aborted) setSaving(false)
      saveRequest.current = null
    }
  }

  return (
    <main className="app-shell"><section className="panel workspace library-page voices-page">
      <a href="#/">Back to projects</a>
      <header className="library-intro">
        <div>
          <p className="eyebrow">The studio collection / 02</p>
          <h1>Voices</h1>
          <p className="library-lede">Give the story <em>its own voice.</em></p>
          <p className="library-description">Save built-in voice profiles for future speech generation. Audio generation is not available yet.</p>
        </div>
        <div className="library-illustration sound-illustration" aria-hidden="true">
          <svg viewBox="0 0 210 150" fill="none">
            <circle cx="105" cy="70" r="56" stroke="currentColor" opacity=".25" />
            <circle cx="105" cy="70" r="47" stroke="currentColor" opacity=".15" />
            <path d="M23 70h164M47 62v16m9-29v42m9-37v32m9-52v72m9-61v50m9-44v38m9-62v86m9-71v56m9-44v32m9-45v58m9-48v38m9-32v26m9-36v46m9-29v12" stroke="currentColor" />
            <path d="M100 132h10M105 127v10" stroke="currentColor" />
          </svg>
          <span>The sound of a story</span>
        </div>
      </header>
      <div className="library-layout">
      <section className="library-composer" aria-labelledby="voice-form-title">
        <p className="eyebrow">01 / Voice notes</p>
        <h2 id="voice-form-title">Find the right tone.</h2>
      <form className="project-form" onSubmit={submit}>
        <label><span>Voice name</span>
          <input name="name" value={name} maxLength={120} required disabled={saving}
            onChange={event => setName(event.target.value)} />
        </label>
        <label><span>Language (optional)</span>
          <input name="language" value={language} maxLength={80} disabled={saving}
            onChange={event => setLanguage(event.target.value)} />
        </label>
        <label><span>Style (optional)</span>
          <textarea name="style" value={style} maxLength={400} rows={3} disabled={saving}
            onChange={event => setStyle(event.target.value)} />
        </label>
        <button type="submit" disabled={saving || loading || Boolean(listError)}>{saving ? 'Saving…' : 'Save voice'}</button>
      </form>
      {message && <p role="status">{message}</p>}
      {saveError && <p role="alert">{saveError}</p>}
      </section>
      <section className="library-catalog" aria-labelledby="voices-catalog-title">
      <div className="library-section-heading">
        <div><p className="eyebrow">02 / The voice collection</p><h2 id="voices-catalog-title">Saved voices</h2></div>
        {!loading && !listError && <span className="library-count" aria-label={`${voices.length} saved voices`}>{String(voices.length).padStart(2, '0')}</span>}
      </div>
      {loading && <p role="status">Loading voices…</p>}
      {listError && <div><p role="alert">{listError}</p><button type="button" disabled={saving} onClick={() => setReload(value => value + 1)}>Retry</button></div>}
      {!loading && !listError && voices.length === 0 && <div className="library-empty">
        <svg className="library-empty-wave" viewBox="0 0 120 60" fill="none" aria-hidden="true"><path d="M10 30h100M24 24v12m9-22v32m9-27v22m9-34v48m9-39v30m9-27v24m9-33v42m9-28v14m9-12v10" stroke="currentColor" /></svg>
        <p>No voices yet.</p>
        <span>Collect the accents, rhythms, and tones of your world.</span>
      </div>}
      <ul className="voice-list">
        {voices.map(voice => (
          <li key={voice.id} data-voice-id={voice.id}>
            <div className="voice-profile-top">
              <span className="profile-index">Voice / {String(voice.id).padStart(2, '0')}</span>
              <svg viewBox="0 0 80 30" fill="none" aria-hidden="true"><path d="M4 15h72M12 10v10m7-16v22m7-17v12m7-19v26m7-19v12m7-17v22m7-15v8m7-13v18m7-12v6" stroke="currentColor" /></svg>
            </div>
            <h3>{voice.name}</h3>
            <div className="voice-profile-meta">
              <p>Type: {voice.voice_type === 'built_in' ? 'Built-in' : voice.voice_type}</p>
              <p>Language: {voice.language || 'Not specified'}</p>
            </div>
            <p className="master-prompt">{voice.style || 'No style saved.'}</p>
          </li>
        ))}
      </ul>
      </section>
      </div>
    </section></main>
  )
}
