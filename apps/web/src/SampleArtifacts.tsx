import { useEffect, useRef, useState } from 'react'
import './SampleArtifacts.css'

type Kind = 'image' | 'audio' | 'video'

const media = {
  image: { label: 'Image', type: 'image/png', extension: 'png' },
  audio: { label: 'Audio', type: 'audio/wav', extension: 'wav' },
  video: { label: 'Video', type: 'video/mp4', extension: 'mp4' },
}

async function readMedia(url: string, kind: Kind, signal: AbortSignal): Promise<Blob> {
  const response = await fetch(url, {
    signal: AbortSignal.any([signal, AbortSignal.timeout(10000)]),
    cache: 'no-store',
  })
  if (!response.ok) {
    const message = response.status === 410 ? 'সংরক্ষিত ফাইলটি আর পাওয়া যাচ্ছে না।'
      : response.status === 404 ? 'এই job-এর media এখনও পাওয়া যায়নি।'
        : response.status === 409 ? 'সংরক্ষিত ফাইলটি বদলে গেছে বা বৈধ নয়।'
          : 'Media এখন পড়া যাচ্ছে না।'
    throw new Error(`${message} (HTTP ${response.status})`)
  }
  const blob = await response.blob()
  if (blob.type !== media[kind].type || blob.size === 0) {
    throw new Error('সঠিক media ফাইল পাওয়া যায়নি। আবার চেষ্টা করুন।')
  }
  return blob
}

function failureMessage(error: unknown): string {
  if (error instanceof Error && (error.name === 'TimeoutError' || error.name === 'AbortError')) {
    return 'Media পড়তে বেশি সময় লাগছে। আবার চেষ্টা করুন।'
  }
  return error instanceof Error && error.name !== 'TypeError'
    ? error.message : 'Media লোড করা যায়নি। সংযোগ দেখে আবার চেষ্টা করুন।'
}

function ArtifactCard({ apiBase, jobId, kind }: { apiBase: string; jobId: number; kind: Kind }) {
  const [preview, setPreview] = useState({ url: '', loading: true, error: '' })
  const [retry, setRetry] = useState(0)
  const [downloading, setDownloading] = useState(false)
  const [downloadError, setDownloadError] = useState('')
  const [downloadStarted, setDownloadStarted] = useState(false)
  const downloadRequest = useRef<AbortController | null>(null)
  const downloadUrls = useRef(new Map<string, ReturnType<typeof setTimeout>>())
  const endpoint = `${apiBase}/jobs/${jobId}/artifacts/${kind}`
  const { label, extension } = media[kind]

  useEffect(() => {
    const controller = new AbortController()
    let objectUrl = ''
    void readMedia(endpoint, kind, controller.signal).then(blob => {
      if (controller.signal.aborted) return
      objectUrl = URL.createObjectURL(blob)
      setPreview({ url: objectUrl, loading: true, error: '' })
    }).catch(error => {
      if (!controller.signal.aborted) {
        setPreview({ url: '', loading: false, error: failureMessage(error) })
      }
    })
    return () => {
      controller.abort()
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [endpoint, kind, retry])

  useEffect(() => {
    const urls = downloadUrls.current
    return () => {
      downloadRequest.current?.abort()
      for (const [url, timer] of urls) {
        clearTimeout(timer)
        URL.revokeObjectURL(url)
      }
      urls.clear()
    }
  }, [])

  const finishPreview = (url: string, failed = false) => {
    setPreview(current => current.url === url ? {
      ...current,
      loading: false,
      error: failed ? 'এই browser-এ preview খোলা যায়নি। Retry করুন বা ফাইলটি download করুন।' : '',
    } : current)
  }

  const download = async () => {
    if (downloadRequest.current) return
    const controller = new AbortController()
    downloadRequest.current = controller
    setDownloading(true)
    setDownloadError('')
    setDownloadStarted(false)
    try {
      const blob = await readMedia(`${endpoint}?download=true`, kind, controller.signal)
      if (controller.signal.aborted) return
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `job-${jobId}-${kind}.${extension}`
      document.body.append(link)
      link.click()
      link.remove()
      // Allow the browser to consume the URL before releasing the download copy.
      const timer = setTimeout(() => {
        URL.revokeObjectURL(url)
        downloadUrls.current.delete(url)
      }, 1000)
      downloadUrls.current.set(url, timer)
      setDownloadStarted(true)
    } catch (error) {
      if (!controller.signal.aborted) setDownloadError(failureMessage(error))
    } finally {
      if (!controller.signal.aborted) setDownloading(false)
      downloadRequest.current = null
    }
  }

  return (
    <section className="artifact-card" data-artifact-kind={kind} aria-label={`Job ${jobId} ${kind}`}>
      <h3>{label}</h3>
      {kind === 'audio' && <p className="artifact-caption">Silent sample · no speech</p>}
      <div className={`artifact-preview artifact-preview-${kind}`} aria-busy={preview.loading}>
        {preview.loading && <p role="status">Loading {kind}…</p>}
        {preview.url && !preview.error && (kind === 'image' ? (
          <img key={preview.url} src={preview.url} alt={`Fixed sample image for job ${jobId}`}
            onLoad={() => finishPreview(preview.url)} onError={() => finishPreview(preview.url, true)} />
        ) : kind === 'video' ? (
          <video key={preview.url} src={preview.url} controls playsInline preload="auto"
            aria-label={`Sample video for job ${jobId}`}
            onLoadedData={() => finishPreview(preview.url)} onError={() => finishPreview(preview.url, true)} />
        ) : (
          <audio key={preview.url} src={preview.url} controls preload="auto"
            aria-label={`Silent sample audio for job ${jobId}`}
            onLoadedData={() => finishPreview(preview.url)} onError={() => finishPreview(preview.url, true)} />
        ))}
        {preview.error && <p role="alert">{preview.error}</p>}
      </div>
      <div className="artifact-actions">
        {preview.error && <button type="button" onClick={() => {
          setPreview({ url: '', loading: true, error: '' })
          setRetry(value => value + 1)
        }}
          aria-label={`Retry ${kind} preview for job ${jobId}`}>Retry preview</button>}
        <button type="button" onClick={() => void download()} disabled={downloading}
          aria-label={`Download ${kind} for job ${jobId}`}>
          {downloading ? 'Downloading…' : downloadError ? 'Retry download' : `Download ${label.toLowerCase()}`}
        </button>
      </div>
      {downloadError && <p className="artifact-download-error" role="alert">{downloadError}</p>}
      {downloadStarted && <p role="status">Download started.</p>}
    </section>
  )
}

export default function SampleArtifacts({ apiBase, jobId }: { apiBase: string; jobId: number }) {
  return (
    <div className="sample-artifacts">
      {(['image', 'video', 'audio'] as const).map(kind => (
        <ArtifactCard key={`${apiBase}/${jobId}/${kind}`} apiBase={apiBase} jobId={jobId} kind={kind} />
      ))}
    </div>
  )
}
