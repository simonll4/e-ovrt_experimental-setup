import { Link, Route, Routes } from 'react-router-dom'
import TargetBadge from './components/TargetBadge'
import CatalogPage from './pages/CatalogPage'
import ComparePage from './pages/ComparePage'
import ComposePage from './pages/ComposePage'
import ExperimentDetailPage from './pages/ExperimentDetailPage'
import ExperimentsPage from './pages/ExperimentsPage'
import PlatformPage from './pages/PlatformPage'
import PromptSetsPage from './pages/PromptSetsPage'
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
          <Link to="/compare">Comparar</Link>
          <Link to="/platform">Plataforma</Link>
          <Link to="/experiments">Experimentos</Link>
          <Link to="/prompts">Prompts</Link>
        </nav>
        <div style={{ marginLeft: 'auto' }}><TargetBadge /></div>
      </header>
      <Routes>
        <Route path="/" element={<RunsPage />} />
        <Route path="/compose" element={<ComposePage />} />
        <Route path="/catalog" element={<CatalogPage />} />
        <Route path="/compare" element={<ComparePage />} />
        <Route path="/runs/:id" element={<RunDetailPage />} />
        <Route path="/platform" element={<PlatformPage />} />
        <Route path="/experiments" element={<ExperimentsPage />} />
        <Route path="/experiments/:id" element={<ExperimentDetailPage />} />
        <Route path="/prompts" element={<PromptSetsPage />} />
      </Routes>
    </div>
  )
}
