import type { ReactNode } from 'react'
import { Link, NavLink } from 'react-router-dom'
import { NAV_GROUPS } from '../nav'
import Breadcrumbs from './Breadcrumbs'
import LiveRunPill from './LiveRunPill'
import TargetBadge from './TargetBadge'

export default function Shell({ children }: { children: ReactNode }) {
  return (
    <div className="eo-shell">
      <aside className="eo-sidebar">
        <div className="eo-sidebar__brand">
          <h1>E-OVRT</h1>
        </div>
        <Link to="/compose" className="eo-sidebar__action">+ Nueva corrida</Link>
        <Link to="/experiments/new" className="eo-sidebar__action">+ Nuevo experimento</Link>
        <nav className="eo-sidebar__nav">
          {NAV_GROUPS.map((group) => (
            <div key={group.title} className="eo-sidebar__group">
              <span className="eo-sidebar__group-title">{group.title}</span>
              {group.items.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.to === '/'}
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
          <Breadcrumbs />
          <div className="eo-topbar__right"><TargetBadge /></div>
        </header>
        <main className="eo-content">{children}</main>
      </div>
    </div>
  )
}
