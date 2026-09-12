import { Route, Routes } from 'react-router-dom'
import Shell from './components/Shell'
import CamerasPage from './pages/CamerasPage'
import CatalogPage from './pages/CatalogPage'
import ClipsPage from './pages/ClipsPage'
import ComparePage from './pages/ComparePage'
import ComposePage from './pages/ComposePage'
import ExperimentDetailPage from './pages/ExperimentDetailPage'
import ExperimentsPage from './pages/ExperimentsPage'
import NotFoundPage from './pages/NotFoundPage'
import PlatformPage from './pages/PlatformPage'
import PromptSetsPage from './pages/PromptSetsPage'
import RunDetailPage from './pages/RunDetailPage'
import RunsPage from './pages/RunsPage'
import EvidencePage from './pages/EvidencePage'
import DocumentacionPage from './pages/DocumentacionPage'

export default function App() {
  return (
    <Shell>
      <Routes>
        <Route path="/" element={<RunsPage />} />
        <Route path="/documentacion" element={<DocumentacionPage />} />
        <Route path="/evidencia" element={<EvidencePage />} />
        <Route path="/evidencia/paso" element={<EvidencePage />} />
        <Route path="/evidencia/respaldo" element={<EvidencePage />} />
        <Route path="/evidencia/resultado" element={<EvidencePage />} />
        <Route path="/evidencia/run" element={<EvidencePage />} />
        <Route path="/compose" element={<ComposePage />} />
        <Route path="/catalog" element={<CatalogPage />} />
        <Route path="/compare" element={<ComparePage />} />
        <Route path="/runs/:id" element={<RunDetailPage />} />
        <Route path="/platform" element={<PlatformPage />} />
        <Route path="/experiments" element={<ExperimentsPage />} />
        {/* Declarada ANTES de /experiments/:id: si no, "new" matchea como :id y
            se ve el detalle buscando un experimento llamado "new" (ver test en
            App.test.tsx que fija este orden). */}
        <Route path="/experiments/new" element={<ExperimentsPage />} />
        <Route path="/experiments/:id" element={<ExperimentDetailPage />} />
        <Route path="/prompts" element={<PromptSetsPage />} />
        <Route path="/cameras" element={<CamerasPage />} />
        <Route path="/clips" element={<ClipsPage />} />
        {/* Última: cualquier ruta que no matcheó antes. Sin esto, una URL vieja
            dejaba el armazón dibujado y el contenido en blanco. */}
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </Shell>
  )
}
