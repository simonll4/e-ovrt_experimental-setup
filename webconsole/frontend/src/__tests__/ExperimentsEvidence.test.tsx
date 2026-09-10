import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { cleanup, fireEvent, render, screen, waitFor, within } from '../test-utils'
import ExperimentsPage from '../pages/ExperimentsPage'
import type { ExperimentManifestSummary } from '../types'

const measured: ExperimentManifestSummary = {
  slug: 'talert_integrated_video', n_runs: 0, evidence: {
    is_evidence: true, result_ids: ['realtime/t_alert_notification'], collections: ['ebe_realtime'],
    n_executions: 4, executions: ['exp_rep3', 'exp_rep2', 'exp_rep1'],
  },
}
const recipe: ExperimentManifestSummary = { slug: 'recipe', n_runs: 0, evidence: {
  is_evidence: false, result_ids: [], collections: [], n_executions: 0, executions: [],
} }
let urls: URL[]
let available: boolean
beforeEach(() => {
  localStorage.clear()
  urls = []
  available = true
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
    const url = new URL(String(input), 'http://localhost')
    urls.push(url)
    if (url.pathname === '/api/experiments/current') return new Response('{}', { status: 404 })
    if (url.pathname === '/api/preflight') return new Response(JSON.stringify({
      ready: true, blockers: [], media: { healthy: true, ready: true }, control: { healthy: true, ready: true },
    }))
    if (url.pathname !== '/api/experiments/manifests') throw new Error(`Petición inesperada: ${url}`)
    const vista = url.searchParams.get('vista')
    const rows = vista === 'evidencia' ? (available ? [measured] : []) : vista === 'archivadas' ? [recipe] : [measured, recipe]
    return new Response(JSON.stringify(rows), { headers: {
      'X-Evidence-Available': String(available), 'X-Archived-Count': '1', 'X-Archived-Executions-Count': '406',
    } })
  }))
})
afterEach(() => { cleanup(); vi.unstubAllGlobals(); localStorage.clear() })
const page = () => render(<MemoryRouter><ExperimentsPage /></MemoryRouter>)

it('pide evidencia, conserva el conteo histórico y ofrece los tres enlaces de consolidaciones', async () => {
  page()
  await screen.findByText('talert_integrated_video')
  expect(screen.queryByText('recipe')).toBeNull()
  expect(screen.getByText('406 ejecuciones archivadas')).toBeTruthy()
  expect(screen.getByText('3 ejecuciones de evidencia')).toBeTruthy()
  for (const id of ['exp_rep1', 'exp_rep2', 'exp_rep3']) {
    expect(screen.getByRole('link', { name: id }).getAttribute('href')).toBe(`/experiments/${id}`)
  }
  expect(urls.some(url => url.searchParams.get('vista') === 'evidencia')).toBe(true)
  expect(screen.getAllByText('realtime/t_alert_notification')).toHaveLength(1)
})

it('alterna Archivadas y Todas, persiste y vuelve a evidencia sin cruzar cachés', async () => {
  const mounted = page()
  await screen.findByText('talert_integrated_video')
  let control = within(screen.getByRole('group', { name: 'Vista de evidencia' }))
  fireEvent.click(control.getByRole('button', { name: 'Archivadas' }))
  await screen.findByText('recipe')
  expect(screen.queryByText('talert_integrated_video')).toBeNull()
  mounted.unmount()
  page()
  await screen.findByText('recipe')
  control = within(screen.getByRole('group', { name: 'Vista de evidencia' }))
  expect(control.getByRole('button', { name: 'Archivadas' }).getAttribute('aria-pressed')).toBe('true')
  fireEvent.click(control.getByRole('button', { name: 'Todas' }))
  await screen.findByText('talert_integrated_video')
  expect(screen.getByText('recipe')).toBeTruthy()
  fireEvent.click(control.getByRole('button', { name: 'Evidencia' }))
  await waitFor(() => expect(screen.queryByText('recipe')).toBeNull())
  expect(screen.getByText('talert_integrated_video')).toBeTruthy()
})

it('permite cambiar de vista cuando el registro ausente deja el listado vacío', async () => {
  available = false
  page()
  await screen.findByText(/Registro de evidencia no disponible/)
  expect(screen.getByText('No hay manifiestos en esta vista')).toBeTruthy()
  fireEvent.click(within(screen.getByRole('group', { name: 'Vista de evidencia' })).getByRole('button', { name: 'Todas' }))
  await screen.findByText('recipe')
})
