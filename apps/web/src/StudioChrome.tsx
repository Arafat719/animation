import { useRef } from 'react'
import type { CSSProperties, PointerEvent } from 'react'

const navigation = [
  { href: '#/', label: 'Projects', path: 'M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z' },
  { href: '#/characters', label: 'Characters', path: 'M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M16 3a4 4 0 0 1 0 8M22 21v-2a4 4 0 0 0-3-3.87M13 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0Z' },
  { href: '#/voices', label: 'Voices', path: 'M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3ZM5 10v2a7 7 0 0 0 14 0v-2M12 19v3M8 22h8' },
  { href: '#/settings', label: 'Settings', path: 'M4 7h9M17 7h3M4 17h3M11 17h9M17 7a2 2 0 1 1-4 0 2 2 0 0 1 4 0ZM11 17a2 2 0 1 1-4 0 2 2 0 0 1 4 0Z' },
]

export function StudioHeader({ route, motionPaused, onToggleMotion }: {
  route: string
  motionPaused: boolean
  onToggleMotion: () => void
}) {
  const section = route.startsWith('#/projects/') || !route || route === '#' ? '#/' : route
  const activeIndex = navigation.findIndex(item => item.href === section)
  return (
    <header className="studio-header">
      <a className="skip-link" href="#main-content" onClick={event => {
        event.preventDefault()
        const main = document.querySelector<HTMLElement>('main')
        if (main) { main.tabIndex = -1; main.focus() }
      }}>Skip to content</a>
      <div className="header-inner">
        <a className="studio-brand" href="#/" aria-label="Animation Studio home">
          <span className="brand-mark" aria-hidden="true"><svg viewBox="0 0 32 32" fill="none"><path d="M8 23 16 7l8 16M11 18h10" /><path d="M23 5v6M20 8h6" /></svg></span>
          <span>Animation<span className="brand-subtitle">STUDIO</span></span>
        </a>
        <nav aria-label="Studio pages" style={{ '--active-tab': Math.max(activeIndex, 0) } as CSSProperties}>
          {activeIndex >= 0 && <span className="nav-liquid" aria-hidden="true" />}
          {navigation.map(({ href, label, path }) => (
            <a key={href} href={href} aria-current={section === href ? 'page' : undefined}>
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d={path} /></svg>{label}
            </a>
          ))}
        </nav>
        <button type="button" className="motion-toggle" onClick={onToggleMotion} aria-pressed={motionPaused}
          aria-label="Pause decorative motion" title={motionPaused ? 'Resume decorative motion' : 'Pause decorative motion'}>
          <svg viewBox="0 0 20 20" aria-hidden="true">{motionPaused ? <path d="m7 4 9 6-9 6Z" /> : <><path d="M7 5v10M13 5v10" /><circle cx="10" cy="10" r="9" /></>}</svg>
          <span>Motion {motionPaused ? 'off' : 'on'}</span>
        </button>
      </div>
    </header>
  )
}

export function StudioScene() {
  const scene = useRef<HTMLElement>(null)
  const moveLight = (event: PointerEvent<HTMLElement>) => {
    if (event.pointerType !== 'mouse' || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
    const bounds = event.currentTarget.getBoundingClientRect()
    scene.current?.style.setProperty('--pointer-x', `${((event.clientX - bounds.left) / bounds.width - .5) * 14}px`)
    scene.current?.style.setProperty('--pointer-y', `${((event.clientY - bounds.top) / bounds.height - .5) * 14}px`)
  }
  return (
    <figure className="studio-scene" ref={scene} onPointerMove={moveLight} onPointerLeave={() => {
      scene.current?.style.setProperty('--pointer-x', '0px')
      scene.current?.style.setProperty('--pointer-y', '0px')
    }}>
      <div className="liquid-sculpture" aria-hidden="true">
        <div className="liquid-halo" /><div className="liquid-orb" /><div className="liquid-pearl pearl-one" /><div className="liquid-pearl pearl-two" />
        <span className="orb-spark spark-one">✦</span><span className="orb-spark spark-two">✧</span>
      </div>
      <div className="scene-float">
        <div className="scene-window">
          <div className="scene-window-bar"><span className="window-dots" aria-hidden="true"><i /><i /><i /></span><span>A glimpse of possibility</span><svg viewBox="0 0 20 20" fill="none" aria-hidden="true"><path d="M12 3h5v5M17 3l-6 6M8 17H3v-5M3 17l6-6" /></svg></div>
          <div className="scene-mat"><img src="/art/the-last-tram.png" width="1536" height="1024" fetchPriority="high"
            alt="A green tram crossing a stone bridge above a sunlit coastal town." />
            <span className="scene-art-label"><span className="art-label-dot" />Studio artwork</span>
          </div>
          <div className="scene-card-caption"><span><strong>The last tram</strong><small>A study in golden hour</small></span><span className="scene-frame-mark" aria-hidden="true">01<span>/ 01</span></span></div>
        </div>
        <div className="scene-thought"><span className="thought-icon" aria-hidden="true">✧</span><span>Made of little wonders.<small>One frame. Infinite possibilities.</small></span></div>
      </div>
      <figcaption className="scene-footer"><span className="scene-line" /> Imagination, in its element.</figcaption>
    </figure>
  )
}
