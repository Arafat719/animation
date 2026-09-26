import { useEffect, useState } from 'react'
import type { ChangeEvent, FormEvent } from 'react'
import JobsPanel from './JobsPanel'
import ProjectWorkspace from './ProjectWorkspace'
import CharactersPage from './CharactersPage'
import VoicesPage from './VoicesPage'
import SettingsPage from './SettingsPage'
import { StudioHeader, StudioScene } from './StudioChrome'
import './App.css'

const API_BASE = 'http://127.0.0.1:8000'

type ConnectionStatus = 'checking' | 'connected' | 'error'

export interface Project {
  id: number
  title: string
  master_prompt: string | null
  target_duration_seconds: number | null
  status: string | null
}

interface ProjectForm {
  title: string
  master_prompt: string
  target_duration_seconds: number
}

function apiErrorMessage(data: unknown, fallback: string): string {
  if (typeof data === 'object' && data !== null && 'detail' in data) {
    return typeof data.detail === 'string' && data.detail ? data.detail : fallback
  }
  return fallback
}

function errorMessage(error: unknown, fallback: string): string {
  return error instanceof Error && error.message ? error.message : fallback
}

const emptyForm: ProjectForm = {
  title: '',
  master_prompt: '',
  target_duration_seconds: 30,
}

function Home() {
  const [status, setStatus] = useState<ConnectionStatus>('checking')
  const [message, setMessage] = useState('Checking backend connection...')
  const [form, setForm] = useState(emptyForm)
  const [projects, setProjects] = useState<Project[]>([])
  const [isSubmitting, setIsSubmitting] = useState(false)

  const loadProjects = async () => {
    try {
      const response = await fetch(`${API_BASE}/projects`)
      if (!response.ok) {
        throw new Error(apiErrorMessage(await response.json(), 'Unable to load projects.'))
      }

      const data: Project[] = await response.json()
      setProjects(data)
      return data
    } catch (error) {
      setMessage(errorMessage(error, 'Unable to load projects.'))
      setStatus('error')
      return []
    }
  }

  useEffect(() => {
    let isMounted = true

    const checkHealth = async () => {
      try {
        const response = await fetch(`${API_BASE}/health`)
        const data: { status: string } = await response.json()

        if (!isMounted) {
          return
        }

        if (response.ok && data.status === 'ok') {
          setStatus('connected')
          setMessage('Backend connected: API is healthy.')
          await loadProjects()
        } else {
          setStatus('error')
          setMessage('Backend responded, but health check failed.')
        }
      } catch {
        if (!isMounted) {
          return
        }

        setStatus('error')
        setMessage('Backend unavailable. Start the FastAPI server on port 8000.')
      }
    }

    checkHealth()

    return () => {
      isMounted = false
    }
  }, [])

  const handleChange = (event: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = event.target
    if (name !== 'title' && name !== 'master_prompt' && name !== 'target_duration_seconds') {
      return
    }
    setForm((current) => ({
      ...current,
      [name]: name === 'target_duration_seconds' ? Number(value) : value,
    }))
  }

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setIsSubmitting(true)

    try {
      const response = await fetch(`${API_BASE}/projects`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(form),
      })

      if (!response.ok) {
        throw new Error(apiErrorMessage(await response.json(), 'Project could not be created.'))
      }

      const data: Project = await response.json()
      setForm(emptyForm)
      setMessage(`Project created: ${data.title}`)
      setStatus('connected')
      await loadProjects()
    } catch (error) {
      setStatus('error')
      setMessage(errorMessage(error, 'Project creation failed.'))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <main className="app-shell" id="main-content" tabIndex={-1}>
      <section className="panel home-panel">
        <div className="studio-kicker">
          <span>A little space for big ideas.</span>
          <span>
            YOUR PERSONAL ANIMATION ATELIER <span aria-hidden="true">✧</span>
          </span>
        </div>
        <div className="studio-hero">
          <div className="hero-copy">
            <p className="hero-badge">
              <span aria-hidden="true">✧</span> A canvas for your imagination
            </p>
            <h1>
              Let your
              <br />
              imagination <em>flow.</em>
            </h1>
            <p className="hero-note">
              A quiet place to dream up extraordinary worlds.
              <br className="desktop-break" /> Bring your characters, voices, and stories together.
              <br className="desktop-break" /> Make something that feels like you.
            </p>
            <button
              type="button"
              className="hero-action"
              onClick={() => {
                document.querySelector<HTMLElement>('.composer-card')?.scrollIntoView({
                  behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches
                    ? 'instant'
                    : 'smooth',
                  block: 'start',
                })
                document
                  .querySelector<HTMLInputElement>('input[name=title]')
                  ?.focus({ preventScroll: true })
              }}
            >
              Begin a new story <span aria-hidden="true">↗</span>
            </button>
            <div className="hero-postscript">
              <span className="postscript-line" aria-hidden="true" /> A small beginning. An entire
              world.
            </div>
          </div>
          <StudioScene />
        </div>
        <div className="workspace-divider">
          <div>
            <span className="eyebrow">YOUR CREATIVE SPACE</span>
            <h2>Good things start here.</h2>
          </div>
          <span>
            One idea at a time. <span aria-hidden="true">↓</span>
          </span>
        </div>

        <div className="home-workspace">
          <div className="composer-card">
            <div className="composer-heading">
              <div>
                <p className="eyebrow">01 / A fresh canvas</p>
                <h2>Your next story.</h2>
              </div>
              <span className="chapter-mark" aria-hidden="true">
                ＋
              </span>
            </div>
            <div className={`status-card ${status}`} role="status">
              <span className="dot" aria-hidden="true" />
              <div>
                <strong>
                  {status === 'connected' && 'API connected'}
                  {status === 'error' && 'API unavailable'}
                  {status === 'checking' && 'Checking API'}
                </strong>
                <p>{message}</p>
              </div>
            </div>

            <form className="project-form" onSubmit={handleSubmit}>
              <label>
                <span>Project title</span>
                <input
                  name="title"
                  value={form.title}
                  onChange={handleChange}
                  placeholder="Give your story a name"
                  required
                />
              </label>

              <label>
                <span>
                  The scene you imagine <small>Master prompt</small>
                </span>
                <textarea
                  name="master_prompt"
                  value={form.master_prompt}
                  onChange={handleChange}
                  placeholder="A quiet rooftop. The city glows below. Two old friends meet again…"
                  rows={4}
                />
              </label>

              <label>
                <span>
                  Target duration <small>Seconds</small>
                </span>
                <input
                  type="number"
                  name="target_duration_seconds"
                  min="1"
                  max="600"
                  value={form.target_duration_seconds}
                  onChange={handleChange}
                />
              </label>

              <button type="submit" disabled={isSubmitting}>
                {isSubmitting ? 'Saving...' : 'Create project'}
                <span aria-hidden="true">↗</span>
              </button>
            </form>
          </div>

          <div className="projects-list">
            <div className="collection-heading">
              <div>
                <p className="eyebrow">02 / The collection</p>
                <h2>Stories in the making.</h2>
              </div>
              <span className="collection-count" aria-label={`${projects.length} saved projects`}>
                {String(projects.length).padStart(2, '0')}
              </span>
            </div>
            {projects.length === 0 ? (
              <div className="empty-collection">
                <div className="empty-story-art" aria-hidden="true">
                  <span className="story-sheet back" />
                  <span className="story-sheet front">
                    <span>SCENE 01</span>
                    <svg viewBox="0 0 100 65" fill="none">
                      <circle cx="70" cy="19" r="10" />
                      <path d="m5 55 28-29 17 16 12-12 33 25M5 61h90M14 9h24M14 14h16" />
                    </svg>
                    <i>A story yet to be told.</i>
                  </span>
                </div>
                <p className="empty-state">No projects yet.</p>
                <p>
                  Every collection begins with a first story.
                  <br />
                  Yours is waiting to be written.
                </p>
              </div>
            ) : (
              <ul>
                {projects.map((project, index) => (
                  <li key={project.id}>
                    <span className="project-index" aria-hidden="true">
                      {String(index + 1).padStart(2, '0')}
                    </span>
                    <div className="project-record">
                      <strong>{project.title}</strong>
                      <small>
                        {project.target_duration_seconds || 0}s <span aria-hidden="true">·</span>{' '}
                        {project.status ?? 'Unknown'}
                      </small>
                    </div>
                    <a
                      href={`#/projects/${project.id}`}
                      aria-label={`Open workspace: ${project.title}`}
                    >
                      <span className="workspace-link-label">Open workspace</span>{' '}
                      <span aria-hidden="true">↗</span>
                    </a>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
        <JobsPanel apiBase={API_BASE} projects={projects} />
      </section>
    </main>
  )
}

export default function App() {
  const [route, setRoute] = useState(window.location.hash)
  const [motionPaused, setMotionPaused] = useState(false)
  useEffect(() => {
    const navigate = () => setRoute(window.location.hash)
    window.addEventListener('hashchange', navigate)
    return () => window.removeEventListener('hashchange', navigate)
  }, [])
  return (
    <div className="studio-app" data-motion={motionPaused ? 'paused' : 'running'}>
      <div className="ambient-light" aria-hidden="true">
        <span />
        <span />
        <span />
      </div>
      <StudioHeader
        route={route}
        motionPaused={motionPaused}
        onToggleMotion={() => setMotionPaused((value) => !value)}
      />
      <StudioPage route={route} />
      <footer className="studio-footer">
        <span>
          <span aria-hidden="true">✧</span> Animation Studio
        </span>
        <span>Thoughtfully made. Endlessly imagined.</span>
        <span className="footer-signoff">A LITTLE WONDER GOES A LONG WAY.</span>
      </footer>
    </div>
  )
}

function StudioPage({ route }: { route: string }) {
  if (!route || route === '#' || route === '#/') return <Home />
  if (route === '#/characters') return <CharactersPage apiBase={API_BASE} />
  if (route === '#/voices') return <VoicesPage apiBase={API_BASE} />
  if (route === '#/settings') return <SettingsPage apiBase={API_BASE} />
  const match = /^#\/projects\/([1-9]\d*)$/.exec(route)
  if (match && Number.isSafeInteger(Number(match[1]))) {
    return <ProjectWorkspace key={match[1]} apiBase={API_BASE} projectId={Number(match[1])} />
  }
  return (
    <main className="app-shell" id="main-content" tabIndex={-1}>
      <section className="panel workspace">
        <a href="#/">Back to projects</a>
        <h1>Page not found</h1>
      </section>
    </main>
  )
}
