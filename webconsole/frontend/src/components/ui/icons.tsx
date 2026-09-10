export function IconPlay() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">
      <path d="M4 3l9 5-9 5z" fill="currentColor" />
    </svg>
  )
}

export function IconStop() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">
      <rect x="4" y="4" width="8" height="8" rx="1" fill="currentColor" />
    </svg>
  )
}

export function IconWarn() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
      <path d="M8 2.6L14.4 13.9h-12.8z" />
      <path d="M8 6.6v3.1M8 11.6v.1" />
    </svg>
  )
}

export function IconCheck() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
      <path d="M3.5 8.5l3 3 6-7" />
    </svg>
  )
}

export function IconDownload() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true">
      <path d="M8 2.5v8M4.5 7.5L8 11l3.5-3.5M3 13.5h10" />
    </svg>
  )
}

export function IconClose() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
      <path d="M4 4l8 8M12 4l-8 8" />
    </svg>
  )
}

export function IconInfo() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
      <circle cx="8" cy="8" r="6" />
      <path d="M8 7.4v3.6M8 5.2v.1" />
    </svg>
  )
}

export function IconChevron() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true">
      <path d="M4 6.5L8 10.5l4-4" />
    </svg>
  )
}

export function IconSearch() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true">
      <circle cx="7" cy="7" r="4.6" />
      <path d="M10.4 10.4L14 14" />
    </svg>
  )
}

export function IconCircle() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true">
      <circle cx="8" cy="8" r="5.6" />
    </svg>
  )
}

/** Signo de más de las acciones primarias de la barra lateral. Es el mismo trazo
 *  que el botón "Nueva corrida" del prototipo. */
export function IconPlus() {
  return (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
      <path d="M8 3v10M3 8h10" />
    </svg>
  )
}

export function IconNavRuns() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4" aria-hidden="true">
      <path d="M2.5 4h11M2.5 8h6M2.5 12h6" />
      <path d="M11.2 9.6l3 1.9-3 1.9z" />
    </svg>
  )
}

export function IconNavExperiments() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4" aria-hidden="true">
      <path d="M6.3 2v4.2L2.9 12a1.4 1.4 0 0 0 1.2 2.1h7.8A1.4 1.4 0 0 0 13.1 12L9.7 6.2V2" />
      <path d="M5.4 2h5.2M4.7 10h6.6" />
    </svg>
  )
}

/** Matraz con un más: la acción "Nuevo experimento" de la barra lateral.
 *
 *  No alcanza con reusar el más a secas: con la barra colapsada las dos acciones
 *  primarias quedan como dos cuadrados violetas de 38 px, y dos signos de más
 *  idénticos no se distinguen. Tampoco sirve el matraz solo, porque sería igual
 *  al ítem "Experimentos" que está tres filas más abajo.
 *
 *  El matraz va escalado dentro de un grupo para dejarle lugar al más; el trazo
 *  se compensa (1.4 / 0.82) para que se vea del mismo grosor que el resto. */
export function IconNavExperimentNew() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4" aria-hidden="true">
      <g transform="translate(-1.1 1.4) scale(0.82)" strokeWidth="1.71">
        <path d="M6.3 2v4.2L2.9 12a1.4 1.4 0 0 0 1.2 2.1h7.8A1.4 1.4 0 0 0 13.1 12L9.7 6.2V2" />
        <path d="M5.4 2h5.2M4.7 10h6.6" />
      </g>
      <path d="M12.7 1.5v4M10.7 3.5h4" strokeWidth="1.6" />
    </svg>
  )
}

export function IconNavCompare() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4" aria-hidden="true">
      <path d="M2.5 13.5h11" />
      <rect x="3.4" y="7" width="2.6" height="4.4" />
      <rect x="7.2" y="3.6" width="2.6" height="7.8" />
      <rect x="11" y="8.8" width="2.6" height="2.6" />
    </svg>
  )
}

export function IconNavPrompts() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4" aria-hidden="true">
      <path d="M2.4 3.6a1.2 1.2 0 0 1 1.2-1.2h8.8a1.2 1.2 0 0 1 1.2 1.2v6a1.2 1.2 0 0 1-1.2 1.2H6.6L3.4 13.4v-2.6a1.2 1.2 0 0 1-1-1.2z" />
      <path d="M5.2 5.6h5.6M5.2 7.8h3.4" />
    </svg>
  )
}

export function IconNavCatalog() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4" aria-hidden="true">
      <path d="M8 3.4L2.4 6 8 8.6 13.6 6z" />
      <path d="M2.4 9.2L8 11.8l5.6-2.6" />
      <path d="M2.4 12.2L8 14.8l5.6-2.6" />
    </svg>
  )
}

export function IconNavEvidence() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4" aria-hidden="true">
      <path d="M9.5 2.2H4a1 1 0 0 0-1 1v9.6a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1V5.7zM9.5 2.2v3.5H13" />
      <path d="M5 10l1.8 1.8L10.5 8" />
    </svg>
  )
}

export function IconNavPlatform() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4" aria-hidden="true">
      <rect x="2.2" y="2.6" width="11.6" height="4.4" rx="1.2" />
      <rect x="2.2" y="9" width="11.6" height="4.4" rx="1.2" />
      <path d="M4.8 4.8v.01M4.8 11.2v.01" />
    </svg>
  )
}

export function IconNavCameras() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4" aria-hidden="true">
      <rect x="1.8" y="4.4" width="12.4" height="8.2" rx="1.4" />
      <circle cx="8" cy="8.5" r="2.4" />
      <path d="M5.6 4.4l.9-1.6h3l.9 1.6" />
    </svg>
  )
}

export function IconNavClips() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4" aria-hidden="true">
      <rect x="1.8" y="3.2" width="12.4" height="9.6" rx="1.4" />
      <path d="M5.2 3.2v9.6M10.8 3.2v9.6M1.8 8h12.4" />
    </svg>
  )
}
