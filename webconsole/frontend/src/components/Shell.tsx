import { useEffect, useRef, useState, type ReactNode } from 'react'
import { Link, NavLink, useLocation } from 'react-router-dom'
import { NAV_GROUPS, grupoContiene, type NavGroup } from '../nav'
import { Dialog, IconClose, IconMenu, enfocarCuandoAparezca } from './ui'
import { IconChevron, IconNavExperimentNew, IconPlus } from './ui/icons'
import Breadcrumbs from './Breadcrumbs'
import { GlosarioProvider } from './Glosario'
import TargetBadge from './TargetBadge'
import LiveRunPill from './LiveRunPill'
import { useSidebarCounts, type SidebarCounts } from '../api/queries/sidebar'
import { useServiceHealth, type ServiceHealth, type ServiceStatus } from '../api/queries/platform'

const COLLAPSE_KEY = 'eovrt-sidebar-collapsed'
/** Grupos plegables abiertos a mano (por título). Preferencia de este navegador. */
const GRUPOS_ABIERTOS_KEY = 'eovrt-nav-grupos-abiertos'

function leerGruposAbiertos(): string[] {
  try {
    const crudo = localStorage.getItem(GRUPOS_ABIERTOS_KEY)
    const lista: unknown = crudo ? JSON.parse(crudo) : []
    return Array.isArray(lista) ? lista.filter((t): t is string => typeof t === 'string') : []
  } catch {
    return []
  }
}

function guardarGruposAbiertos(titulos: string[]) {
  try {
    localStorage.setItem(GRUPOS_ABIERTOS_KEY, JSON.stringify(titulos))
  } catch {
    /* sin almacenamiento (modo privado): la preferencia dura la sesión */
  }
}
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
  const { pathname } = useLocation()
  const countFor = (key?: 'runs' | 'experiments' | 'promptSets') => {
    if (!key) return null
    const v = counts[key]
    return v === null || v === 0 ? null : v
  }
  // «Laboratorio» va plegado por defecto (doc 135 §3.1): lo operativo no está en
  // el camino del jurado. Se abre solo si la pantalla actual es uno de sus
  // destinos, para que el destino activo nunca quede escondido.
  const [abiertos, setAbiertos] = useState<string[]>(leerGruposAbiertos)
  const estaAbierto = (group: NavGroup) =>
    !group.colapsable || abiertos.includes(group.title) || grupoContiene(group, pathname)
  const alternar = (group: NavGroup) => {
    const siguiente = estaAbierto(group)
      ? abiertos.filter((t) => t !== group.title)
      : [...abiertos, group.title]
    setAbiertos(siguiente)
    guardarGruposAbiertos(siguiente)
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
        {NAV_GROUPS.map((group) => {
          const abierto = estaAbierto(group)
          const idItems = `eo-nav-grupo-${group.title.toLowerCase()}`
          return (
          <div key={group.title} className="eo-sidebar__group">
            {group.colapsable ? (
              <button
                type="button"
                className="eo-sidebar__group-toggle"
                aria-expanded={abierto}
                aria-controls={idItems}
                onClick={() => alternar(group)}
              >
                <span className="eo-sidebar__group-title">{group.title}</span>
                <IconChevron />
                <span className="eo-tip" aria-hidden="true" data-tip={group.title} />
              </button>
            ) : (
              <span className="eo-sidebar__group-title">{group.title}</span>
            )}
            <div id={idItems} className="eo-sidebar__group-items" hidden={!abierto}>
            {abierto && group.items.map((item) => {
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
          </div>
          )
        })}
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
  // La demo en vivo de la defensa va a pantalla completa, sin el armazón y sin
  // ninguna consulta global (spec 2026-10-23 §6.5), decidido por pathname igual
  // que el modo archivo.
  const demo = pathname === '/demo' || pathname.startsWith('/demo/')
  const desktop = useMediaQuery(DESKTOP_QUERY)
  const [open, setOpen] = useState(false)
  // Al cerrar por navegación el foco va al encabezado del destino, no de
  // vuelta al botón de menú.
  const [restaurarFoco, setRestaurarFoco] = useState(true)
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem(COLLAPSE_KEY) === '1')
  const counts = useSidebarCounts(!archive && !demo)
  const health = useServiceHealth(!archive && !demo)
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

  if (demo) return <GlosarioProvider>{children}</GlosarioProvider>

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
