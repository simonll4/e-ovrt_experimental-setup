import { useEffect, useState, type ReactNode } from 'react'
import { Link, NavLink } from 'react-router-dom'
import { NAV_GROUPS } from '../nav'
import { IconNavExperimentNew, IconPlus } from './ui/icons'
import Breadcrumbs from './Breadcrumbs'
import TargetBadge from './TargetBadge'
import { useSidebarCounts } from '../api/queries/sidebar'
import { useServiceHealth, type ServiceStatus } from '../api/queries/platform'

const COLLAPSE_KEY = 'eovrt-sidebar-collapsed'

export default function Shell({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false)
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem(COLLAPSE_KEY) === '1')
  const counts = useSidebarCounts()
  const health = useServiceHealth()
  const close = () => setOpen(false)

  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') close()
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open])

  useEffect(() => {
    localStorage.setItem(COLLAPSE_KEY, collapsed ? '1' : '0')
  }, [collapsed])

  const countFor = (key?: 'runs' | 'experiments' | 'promptSets') => {
    if (!key) return null
    const v = counts[key]
    return v === null || v === 0 ? null : v
  }

  const statusText = (s: ServiceStatus) =>
    s === 'ok' ? 'operativo' : s === 'down' ? 'sin respuesta' : 'verificando…'
  const mediaTip = `Motor de detección — ${statusText(health.media)}`
  const controlTip = `Motor de reglas — ${statusText(health.control)}`

  const sidebarClass = [
    'eo-sidebar',
    open ? 'eo-sidebar--open' : '',
    collapsed ? 'eo-sidebar--collapsed' : '',
  ]
    .filter(Boolean)
    .join(' ')

  return (
    <div className="eo-shell">
      {open && <div className="eo-sidebar__scrim" onClick={close} />}
      <aside className={sidebarClass} aria-label="Navegación principal">
        <div className="eo-sidebar__brand">
          <b>E-OVRT</b>
          <span className="eo-sidebar__brand-sub">consola</span>
          <button
            type="button"
            className="eo-sidebar__collapse"
            aria-label={collapsed ? 'Expandir barra lateral' : 'Colapsar barra lateral'}
            onClick={() => setCollapsed((c) => !c)}
          >
            <svg width="15" height="15" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4" aria-hidden="true">
              <rect x="1.8" y="2.8" width="12.4" height="10.4" rx="1.6" />
              <path d="M6.4 2.8v10.4" />
            </svg>
          </button>
        </div>
        {/* El icono va como hermano del rótulo, no dentro: con la barra
            colapsada el CSS esconde los <span> y deja el <svg>, que es lo único
            que queda para identificar el botón. Sin él eran dos rectángulos
            violetas mudos. */}
        <Link to="/compose" className="eo-sidebar__action" title="Nueva corrida" onClick={close}>
          <IconPlus />
          <span>Nueva corrida</span>
          <span className="eo-tip" aria-hidden="true" data-tip="Nueva corrida" />
        </Link>
        <Link to="/experiments/new" className="eo-sidebar__action" title="Nuevo experimento" onClick={close}>
          <IconNavExperimentNew />
          <span>Nuevo experimento</span>
          <span className="eo-tip" aria-hidden="true" data-tip="Nuevo experimento" />
        </Link>
        <nav className="eo-sidebar__nav">
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
                    title={item.label}
                    /* El nombre accesible es el completo aunque se muestre la
                       etiqueta corta: el contenido visible ganaría si no. */
                    aria-label={item.label}
                    onClick={close}
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
        {/* Sin píldora de corrida viva: el banner del listado de Corridas ya
            anuncia la corrida en curso, y el prototipo lo diseñó así a
            propósito para no decir lo mismo en dos lugares. */}
        <div className="eo-sidebar__services" role="group" aria-label="Estado de los servicios">
          <div className="eo-service" title={mediaTip}>
            <span
              className="eo-service__dot"
              style={{
                background:
                  health.media === 'ok' ? 'var(--ok)' : health.media === 'down' ? 'var(--er)' : 'var(--nt)',
              }}
            />
            <span className="eo-service__label">Motor de detección</span>
            <code>:8080</code>
            <span className="eo-tip" aria-hidden="true" data-tip={mediaTip} />
          </div>
          <div className="eo-service" title={controlTip}>
            <span
              className="eo-service__dot"
              style={{
                background:
                  health.control === 'ok' ? 'var(--ok)' : health.control === 'down' ? 'var(--er)' : 'var(--nt)',
              }}
            />
            <span className="eo-service__label">Motor de reglas</span>
            <code>:8081</code>
            <span className="eo-tip" aria-hidden="true" data-tip={controlTip} />
          </div>
        </div>
      </aside>
      <div className="eo-main">
        {/* La barra superior es exclusiva de pantallas chicas: ahí la lateral se
            esconde y esto es lo único que queda para navegar. En escritorio no
            aporta nada que la lateral no diga ya, y le robaba alto al contenido.
            El CSS la muestra recién a ≤760 px, el mismo corte en que la lateral
            pasa a cajón. */}
        <header className="eo-topbar">
          <button
            type="button"
            className="eo-topbar__menu"
            aria-label={open ? 'Cerrar navegación' : 'Abrir navegación'}
            aria-expanded={open}
            onClick={() => setOpen((o) => !o)}
          >
            ☰
          </button>
          <b className="eo-topbar__brand">E-OVRT</b>
        </header>
        <main className="eo-content">
          {/* Las migas viven en el contenido, no en una barra global: acompañan
              a la pantalla y se van con ella. La insignia de la instancia activa
              las acompaña porque perdió su lugar al esconderse la barra. */}
          <div className="eo-crumbsbar">
            <Breadcrumbs />
            <TargetBadge />
          </div>
          {children}
        </main>
      </div>
    </div>
  )
}
