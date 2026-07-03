import { Link, Route, Routes } from 'react-router-dom'
import TargetBadge from './components/TargetBadge'
import CatalogPage from './pages/CatalogPage'
import ComposePage from './pages/ComposePage'
import RunDetailPage from './pages/RunDetailPage'
import RunsPage from './pages/RunsPage'

export default function App() {
  return (
    <div style={{ fontFamily: 'system-ui, sans-serif', margin: '0 auto', maxWidth: 1100, padding: 16 }}>
      <header style={{ display: 'flex', gap: 16, alignItems: 'center', marginBottom: 16 }}>
        <h1 style={{ fontSize: 20, margin: 0 }}>E-OVRT Console</h1>
        <nav style={{ display: 'flex', gap: 12 }}>
          <Link to="/">Runs</Link>
          <Link to="/compose">Nueva corrida</Link>
          <Link to="/catalog">Catálogos</Link>
        </nav>
        <div style={{ marginLeft: 'auto' }}><TargetBadge /></div>
      </header>
      <Routes>
        <Route path="/" element={<RunsPage />} />
        <Route path="/compose" element={<ComposePage />} />
        <Route path="/catalog" element={<CatalogPage />} />
        <Route path="/runs/:id" element={<RunDetailPage />} />
      </Routes>
    </div>
  )
}
