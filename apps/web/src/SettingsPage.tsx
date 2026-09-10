import { useEffect, useState } from 'react'
import './LibraryPages.css'

export default function SettingsPage({ apiBase }: { apiBase: string }) {
  const [databasePath, setDatabasePath] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [retry, setRetry] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    const load = async () => {
      setLoading(true)
      setError('')
      try {
        const response = await fetch(`${apiBase}/settings`, {
          signal: AbortSignal.any([controller.signal, AbortSignal.timeout(10000)]),
        })
        if (!response.ok) throw new Error(`Unable to load settings (HTTP ${response.status}).`)
        const data: unknown = await response.json()
        if (typeof data !== 'object' || data === null || !('database_path' in data)
          || typeof data.database_path !== 'string' || !data.database_path.trim()) {
          throw new Error('Database path is missing from the settings response.')
        }
        if (!controller.signal.aborted) setDatabasePath(data.database_path)
      } catch (failure) {
        if (!controller.signal.aborted) {
          setError(failure instanceof Error ? failure.message : 'Unable to load settings.')
        }
      } finally {
        if (!controller.signal.aborted) setLoading(false)
      }
    }
    void load()
    return () => controller.abort()
  }, [apiBase, retry])

  return (
    <main className="app-shell"><section className="panel workspace library-page settings-page">
      <a href="#/">Back to projects</a>
      <header className="library-intro">
        <div>
          <p className="eyebrow">Behind the scenes / Studio configuration</p>
          <h1>Settings</h1>
          <p className="library-lede">A place for <em>everything.</em></p>
          <p className="library-description">View the current database location. Settings are read-only.</p>
        </div>
        <div className="library-illustration settings-illustration" aria-hidden="true">
          <svg viewBox="0 0 210 150" fill="none">
            <path d="M44 29h122v101H44zM44 59h122M44 97h122" stroke="currentColor" />
            <path d="M54 20h122v101M64 11h122v101" stroke="currentColor" opacity=".3" />
            <path d="M88 39h34v10H88zM88 73h34v10H88zM88 107h34v10H88z" fill="currentColor" opacity=".13" />
            <path d="M99 44h12M99 78h12M99 112h12M49 131v7m112-7v7" stroke="currentColor" />
          </svg>
          <span>The studio archive</span>
        </div>
      </header>
      <section className="settings-record" aria-labelledby="storage-title">
        <div className="library-section-heading">
          <div><p className="eyebrow">01 / Storage</p><h2 id="storage-title">The studio records</h2></div>
          <span className="read-only-label">Read-only</span>
        </div>
      {loading ? <p role="status">Loading settings…</p> : error ? (
        <div>
          <p role="alert">{error}</p>
          <button type="button" onClick={() => setRetry(value => value + 1)}>Retry</button>
        </div>
      ) : (
        <dl className="project-details">
          <div><dt>Database path</dt><dd className="database-path">{databasePath}</dd></div>
        </dl>
      )}
      </section>
    </section></main>
  )
}
