import { useEffect, useRef, useState } from 'react'

export default function ComposerExport({ apiBase }: { apiBase: string }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [download, setDownload] = useState('')
  const active = useRef<AbortController | null>(null)
  const url = useRef('')
  useEffect(
    () => () => {
      active.current?.abort()
      if (url.current) URL.revokeObjectURL(url.current)
    },
    [],
  )
  async function start() {
    if (active.current) return
    const controller = new AbortController()
    active.current = controller
    setBusy(true)
    setError('')
    if (url.current) URL.revokeObjectURL(url.current)
    url.current = ''
    setDownload('')
    try {
      const response = await fetch(`${apiBase}/composer/sample-export`, {
        method: 'POST',
        signal: AbortSignal.any([controller.signal, AbortSignal.timeout(120000)]),
      })
      if (!response.ok) {
        const body = await response.json().catch(() => null)
        throw new Error(body?.detail?.message || 'Export তৈরি করা যায়নি। আবার চেষ্টা করুন।')
      }
      const blob = await response.blob()
      if (!controller.signal.aborted) {
        url.current = URL.createObjectURL(blob)
        setDownload(url.current)
      }
    } catch (failure) {
      if (!controller.signal.aborted)
        setError(
          failure instanceof Error &&
            failure.name !== 'TypeError' &&
            failure.name !== 'TimeoutError'
            ? failure.message
            : 'সার্ভারের সঙ্গে যোগাযোগ করা যায়নি বা সময় শেষ হয়েছে। আবার চেষ্টা করুন।',
        )
    } finally {
      if (!controller.signal.aborted) setBusy(false)
      active.current = null
    }
  }
  return (
    <section aria-label="Composer sample export">
      <h2>Sample video export</h2>
      <p>
        দুই সেকেন্ডের স্থির sample, synthetic audio, subtitle ও thumbnail পরীক্ষা করুন। এটি আপনার
        prompt থেকে তৈরি video নয়।
      </p>
      <button type="button" disabled={busy} onClick={() => void start()}>
        {busy
          ? 'Export তৈরি হচ্ছে…'
          : error
            ? 'আবার export চেষ্টা করুন'
            : 'Sample export তৈরি করুন'}
      </button>
      {busy && <p role="status">Sample তৈরি হচ্ছে…</p>}
      {error && <p role="alert">{error}</p>}
      {download && (
        <a href={download} download="composer-sample.zip">
          ZIP download করুন
        </a>
      )}
    </section>
  )
}
