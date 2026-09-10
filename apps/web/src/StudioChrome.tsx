export function StudioHeader({ route }: { route: string }) {
  const section = route.startsWith('#/projects/') || !route || route === '#' ? '#/' : route
  return (
    <header className="studio-header">
      <a className="skip-link" href="#main-content" onClick={event => {
        event.preventDefault()
        document.querySelector<HTMLElement>('main')?.focus()
      }}>Skip to content</a>
      <div className="header-inner">
        <a className="studio-brand" href="#/" aria-label="Animation Studio home">
          <svg viewBox="0 0 40 40" aria-hidden="true">
            <rect x="2" y="2" width="36" height="36" rx="2" />
            <path d="m10 29 10-19 10 19M14 23h12M20 10v21M8 32h24" />
            <path d="M7 7h4M29 7h4" />
          </svg>
          <span>Animation<span className="brand-subtitle">S T U D I O</span></span>
        </a>
        <nav aria-label="Studio pages">
          {[
            ['#/', 'Projects'], ['#/characters', 'Characters'],
            ['#/voices', 'Voices'], ['#/settings', 'Settings'],
          ].map(([href, label], index) => (
            <a key={href} href={href} aria-current={section === href ? 'page' : undefined}>
              <span className="nav-number" aria-hidden="true">0{index + 1}</span>{label}
            </a>
          ))}
        </nav>
        <span className="studio-edition"><span aria-hidden="true">✳</span> An independent imagination</span>
      </div>
    </header>
  )
}

export function StudioScene() {
  return (
    <figure className="studio-scene">
      <div className="scene-mat">
        <img src="/art/the-last-tram.png" width="1536" height="1024" fetchPriority="high"
          alt="A green tram crosses a stone bridge above a sunlit coastal town, with a traveler waiting at the stop." />
        <div className="scene-art-label"><span className="art-label-dot" />Studio artwork</div>
      </div>
      <figcaption className="scene-footer">
        <span><span className="scene-number">FIG. 001</span> The last tram</span>
        <span>A study in golden hour <span aria-hidden="true">↗</span></span>
      </figcaption>
      <div className="scene-stamp" aria-hidden="true"><span>MADE OF</span><strong>little<br /><i>wonders.</i></strong><span>FRAME BY FRAME</span></div>
    </figure>
  )
}
