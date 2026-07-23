import { Route, Routes } from 'react-router-dom'
import Shell from './components/Shell'
import CamerasPage from './pages/CamerasPage'
import CatalogPage from './pages/CatalogPage'
import ClipsPage from './pages/ClipsPage'
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
    <Shell>
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
        <Route path="/cameras" element={<CamerasPage />} />
        <Route path="/clips" element={<ClipsPage />} />
      </Routes>
    </Shell>
  )
}
