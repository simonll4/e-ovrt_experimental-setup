import { useEffect, useState, type ReactNode } from 'react'
import { Link, NavLink } from 'react-router-dom'
import { NAV_GROUPS } from '../nav'
import Breadcrumbs from './Breadcrumbs'
import LiveRunPill from './LiveRunPill'
import TargetBadge from './TargetBadge'

export default function Shell({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false)
  const close = () => setOpen(false)

  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') close()
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open])

  return (
    <div className="eo-shell">
      {open && <div className="eo-sidebar__scrim" onClick={close} />}
      <aside className={open ? 'eo-sidebar eo-sidebar--open' : 'eo-sidebar'}>
        <div className="eo-sidebar__brand">
          <h1>E-OVRT</h1>
        </div>
        <Link to="/compose" className="eo-sidebar__action" onClick={close}>+ Nueva corrida</Link>
        <Link to="/experiments/new" className="eo-sidebar__action" onClick={close}>+ Nuevo experimento</Link>
        <nav className="eo-sidebar__nav">
          {NAV_GROUPS.map((group) => (
            <div key={group.title} className="eo-sidebar__group">
              <span className="eo-sidebar__group-title">{group.title}</span>
              {group.items.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.to === '/'}
                  onClick={close}
                  className={({ isActive }) =>
                    isActive ? 'eo-sidebar__link eo-sidebar__link--active' : 'eo-sidebar__link'
                  }
                >
                  {item.label}
                </NavLink>
              ))}
            </div>
          ))}
        </nav>
        <LiveRunPill />
      </aside>
      <div className="eo-main">
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
          <Breadcrumbs />
          <div className="eo-topbar__right"><TargetBadge /></div>
        </header>
        <main className="eo-content">{children}</main>
      </div>
    </div>
  )
}
