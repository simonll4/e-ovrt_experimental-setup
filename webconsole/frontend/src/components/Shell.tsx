import { useEffect, useRef, useState, type ReactNode } from 'react'
import { Link, NavLink, useLocation } from 'react-router-dom'
import { NAV_GROUPS } from '../nav'
import { Dialog, IconClose, IconMenu, enfocarCuandoAparezca } from './ui'
import { IconNavExperimentNew, IconPlus } from './ui/icons'
import Breadcrumbs from './Breadcrumbs'
import { GlosarioProvider } from './Glosario'
import TargetBadge from './TargetBadge'
import LiveRunPill from './LiveRunPill'
import { useSidebarCounts, type SidebarCounts } from '../api/queries/sidebar'
import { useServiceHealth, type ServiceHealth, type ServiceStatus } from '../api/queries/platform'

const COLLAPSE_KEY = 'eovrt-sidebar-collapsed'
/** Desde acá la barra lateral es persistente; debajo pasa a cajón. */
export const DESKTOP_QUERY = '(min-width: 1024px)'

/** `matchMedia` como estado. Sin `matchMedia` (jsdom) se asume escritorio:
 *  es el modo en que todos los destinos están en el DOM sin abrir nada. */
function useMediaQuery(query: string): boolean {
  const leer = () =>
    typeof window !== 'undefined' && typeof window.matchMedia === 'function'
      ? window.matchMedia(query).matches
      : true
  const [coincide, setCoincide] = useState(leer)
  useEffect(() => {
    if (typeof window.matchMedia !== 'function') return
    const mql = window.matchMedia(query)
    const cambio = () => setCoincide(mql.matches)
    cambio()
    if (typeof mql.addEventListener === 'function') {
      mql.addEventListener('change', cambio)
      return () => mql.removeEventListener('change', cambio)
    }
    mql.addListener(cambio)
    return () => mql.removeListener(cambio)
  }, [query])
  return coincide
}

const statusText = (s: ServiceStatus) =>
  s === 'ok' ? 'operativo' : s === 'down' ? 'sin respuesta' : 'verificando…'

const enfocarEncabezado = () => enfocarCuandoAparezca('#contenido h1')

function Servicio({ nombre, puerto, estado }: { nombre: string; puerto: string; estado: ServiceStatus }) {
  const tip = `${nombre} — ${statusText(estado)}`
  return (
    <div className="eo-service" title={tip}>
      <span
        className={`eo-service__dot eo-service__dot--${estado}`}
        aria-hidden="true"
        style={{
          background: estado === 'ok' ? 'var(--ok)' : estado === 'down' ? 'var(--er)' : 'var(--nt)',
        }}
      />
      <span className="eo-service__label">{nombre}</span>
      <code>{puerto}</code>
      <span className={estado === 'down' ? 'eo-service__state eo-service__state--down' : 'eo-service__state'}>
        <span className="eo-sr">{nombre}: </span>
        {statusText(estado)}
      </span>
      <span className="eo-tip" aria-hidden="true" data-tip={tip} />
    </div>
  )
}

/** El contenido de la navegación: el mismo en la barra persistente y en el
 *  cajón, con el mismo orden, destinos, conteos y acciones. */
function Navegacion({
  archive,
  counts,
  health,
  onNavigate,
}: {
  archive: boolean
  counts: SidebarCounts
  health: ServiceHealth
  onNavigate: () => void
}) {
  const countFor = (key?: 'runs' | 'experiments' | 'promptSets') => {
    if (!key) return null
    const v = counts[key]
    return v === null || v === 0 ? null : v
  }

  return (
    <>
      {/* El icono va como hermano del rótulo, no dentro: con la barra
          colapsada el CSS esconde los <span> y deja el <svg>, que es lo único
          que queda para identificar el botón. */}
      <div className="eo-sidebar__actions">
        <Link to="/compose" className="eo-sidebar__action" aria-label="Nueva corrida" onClick={onNavigate}>
          <IconPlus />
          <span>Nueva corrida</span>
          <span className="eo-tip" aria-hidden="true" data-tip="Nueva corrida" />
        </Link>
        <Link to="/experiments/new" className="eo-sidebar__action" aria-label="Nuevo experimento" onClick={onNavigate}>
          <IconNavExperimentNew />
          <span>Nuevo experimento</span>
          <span className="eo-tip" aria-hidden="true" data-tip="Nuevo experimento" />
        </Link>
      </div>
      <nav className="eo-sidebar__nav" aria-label="Secciones">
        {NAV_GROUPS.map((group) => (
          <div key={group.title} className="eo-sidebar__group">
            <span className="eo-sidebar__group-title">{group.title}</span>
            {group.items.map((item) => {
              const Icon = item.icon
              const count = countFor(item.countKey)
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.to === '/'}
                  /* El nombre accesible es el completo aunque se muestre la
                     etiqueta corta: el contenido visible ganaría si no. */
                  aria-label={item.label}
                  onClick={onNavigate}
                  className={({ isActive }) =>
                    isActive ? 'eo-sidebar__link eo-sidebar__link--active' : 'eo-sidebar__link'
                  }
                >
                  {Icon && <Icon />}
                  <span className="eo-sidebar__link-label">{item.short ?? item.label}</span>
                  {count !== null && <span className="eo-sidebar__count">{count}</span>}
                  <span className="eo-tip" aria-hidden="true" data-tip={item.label} />
                </NavLink>
              )
            })}
          </div>
        ))}
      </nav>
      {!archive && <LiveRunPill onNavigate={onNavigate} />}
      {archive ? (
        <div className="eo-sidebar__services">Archivo local · servicios no consultados</div>
      ) : (
        <div className="eo-sidebar__services" role="group" aria-label="Estado de los servicios">
          <Servicio nombre="Motor de detección" puerto=":8080" estado={health.media} />
          <Servicio nombre="Motor de reglas" puerto=":8081" estado={health.control} />
          <Servicio nombre="Distribución de alertas" puerto=":8082" estado={health.distribution} />
        </div>
      )}
    </>
  )
}

export default function Shell({ children }: { children: ReactNode }) {
  const { pathname } = useLocation()
  const archive = pathname === '/evidencia' || pathname.startsWith('/evidencia/')
  const desktop = useMediaQuery(DESKTOP_QUERY)
  const [open, setOpen] = useState(false)
  // Al cerrar por navegación el foco va al encabezado del destino, no de
  // vuelta al botón de menú.
  const [restaurarFoco, setRestaurarFoco] = useState(true)
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem(COLLAPSE_KEY) === '1')
  const counts = useSidebarCounts(!archive)
  const health = useServiceHealth(!archive)
  const menuRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    localStorage.setItem(COLLAPSE_KEY, collapsed ? '1' : '0')
  }, [collapsed])

  // Al pasar a escritorio no puede quedar un cajón abierto con el fondo inerte.
  useEffect(() => {
    if (desktop) setOpen(false)
  }, [desktop])

  const abrirCajon = () => {
    setRestaurarFoco(true)
    setOpen(true)
  }
  const cerrarCajon = () => {
    setRestaurarFoco(true)
    setOpen(false)
  }
  const alNavegar = () => {
    if (!open) return
    setRestaurarFoco(false)
    setOpen(false)
    enfocarEncabezado()
  }

  return (
    <div className={desktop ? 'eo-shell eo-shell--desktop' : 'eo-shell eo-shell--compact'}>
      {/* Primera parada de Tab: evita recorrer toda la navegación en cada
          pantalla. Es un botón y no un enlace a #contenido porque el hash es
          del router. */}
      <button type="button" className="eo-skip" onClick={enfocarEncabezado}>
        Saltar al contenido
      </button>
      {desktop ? (
        <aside
          className={collapsed ? 'eo-sidebar eo-sidebar--collapsed' : 'eo-sidebar'}
          aria-label="Navegación principal"
        >
          <div className="eo-sidebar__brand">
            <b>E-OVRT</b>
            <span className="eo-sidebar__brand-sub">consola</span>
            <button
              type="button"
              className="eo-sidebar__collapse"
              aria-label={collapsed ? 'Expandir barra lateral' : 'Colapsar barra lateral'}
              aria-pressed={collapsed}
              onClick={() => setCollapsed((c) => !c)}
            >
              <svg width="15" height="15" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4" aria-hidden="true">
                <rect x="1.8" y="2.8" width="12.4" height="10.4" rx="1.6" />
                <path d="M6.4 2.8v10.4" />
              </svg>
            </button>
          </div>
          <Navegacion archive={archive} counts={counts} health={health} onNavigate={() => undefined} />
        </aside>
      ) : null}
      <div className="eo-main">
        {/* La barra superior es exclusiva del modo compacto: ahí la lateral es
            un cajón y esto es lo único que queda para navegar. */}
        {!desktop ? (
          <header className="eo-topbar">
            <button
              ref={menuRef}
              type="button"
              className="eo-topbar__menu"
              aria-label="Abrir navegación"
              aria-haspopup="dialog"
              aria-expanded={open}
              onClick={abrirCajon}
            >
              <IconMenu />
            </button>
            <b className="eo-topbar__brand">E-OVRT</b>
          </header>
        ) : null}
        <main className="eo-content" id="contenido">
          {/* Las migas viven en el contenido: acompañan a la pantalla. El
              estado de la instancia va en su propio contenedor, a la derecha. */}
          <div className="eo-crumbsbar">
            <div className="eo-crumbsbar__trail">
              <Breadcrumbs />
            </div>
            {!archive && (
              <div className="eo-crumbsbar__status">
                <TargetBadge />
              </div>
            )}
          </div>
          {/* El vocabulario compartido de la consola. No pide nada hasta que
              una pantalla monta su primer término marcado. */}
          <GlosarioProvider>{children}</GlosarioProvider>
        </main>
      </div>
      {!desktop ? (
        <Dialog
          open={open}
          onClose={cerrarCajon}
          label="Navegación principal"
          className="eo-drawer"
          restoreFocus={restaurarFoco}
        >
          {open && (
            <aside className="eo-sidebar eo-sidebar--drawer" aria-label="Navegación principal">
              <div className="eo-sidebar__brand">
                <b>E-OVRT</b>
                <span className="eo-sidebar__brand-sub">consola</span>
                <button
                  type="button"
                  className="eo-btn eo-btn--ghost eo-btn--icon eo-drawer__close"
                  aria-label="Cerrar navegación"
                  onClick={cerrarCajon}
                >
                  <IconClose />
                </button>
              </div>
              <Navegacion archive={archive} counts={counts} health={health} onNavigate={alNavegar} />
            </aside>
          )}
        </Dialog>
      ) : null}
    </div>
  )
}
