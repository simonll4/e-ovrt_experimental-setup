import type { ReactNode } from 'react'
import { Link, Route, Routes } from 'react-router-dom'
import Shell from './components/Shell'
import { Banner } from './components/ui'
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
import DemoPage from './pages/DemoPage'
import DemoResultPage from './pages/DemoResultPage'
import TribunalPage from './pages/TribunalPage'
import ResultadosPage from './pages/ResultadosPage'
import PruebaPage from './pages/PruebaPage'
import { RUNS_PATH } from './nav'

/** La validación inicial (generación 1): el recorrido de evidencia de siempre,
 *  con un encabezado fijo que dice qué es (doc 135 §3.6). */
function ValidacionInicial({ children }: { children: ReactNode }) {
  return (
    <>
      <div className="eo-gen1-aviso">
        <Banner tone="warn">
          Estas cifras son de la validación inicial, en otra máquina y con la referencia anterior a la
          revisión dirigida. Los resultados finales están en <Link to="/resultados">Resultados</Link>.
        </Banner>
      </div>
      {children}
    </>
  )
}

const gen1 = <ValidacionInicial><EvidencePage /></ValidacionInicial>

export default function App() {
  return (
    <Shell>
      <Routes>
        {/* La entrada es «Para el tribunal» (doc 135); la lista de corridas se
            mudó a /corridas. Ninguna ruta anterior se borró. */}
        <Route path="/" element={<TribunalPage />} />
        <Route path={RUNS_PATH} element={<RunsPage />} />
        <Route path="/resultados" element={<ResultadosPage />} />
        <Route path="/resultados/:id" element={<PruebaPage />} />
        <Route path="/documentacion" element={<DocumentacionPage />} />
        <Route path="/evidencia" element={gen1} />
        <Route path="/evidencia/generacion-1" element={gen1} />
        <Route path="/evidencia/paso" element={gen1} />
        <Route path="/evidencia/respaldo" element={gen1} />
        <Route path="/evidencia/resultado" element={gen1} />
        <Route path="/evidencia/run" element={gen1} />
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
        {/* Demo en vivo de la defensa: pantalla completa, sin armazón (Shell la
            reconoce por el pathname) y fuera de la navegación. */}
        <Route path="/demo" element={<DemoPage />} />
        <Route path="/demo/resultado/:sessionId" element={<DemoResultPage />} />
        {/* Última: cualquier ruta que no matcheó antes. Sin esto, una URL vieja
            dejaba el armazón dibujado y el contenido en blanco. */}
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </Shell>
  )
}
