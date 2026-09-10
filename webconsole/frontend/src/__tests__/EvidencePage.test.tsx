import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { cleanup, fireEvent, render, screen, within } from '../test-utils'
import App from '../App'
import { crumbsFor } from '../nav'
import type { ArchivedRun, EvidenceResult } from '../types'

const rid = 'clip_bench/campaign_one'
const info: EvidenceResult = {
  result_id: rid, index: 'clip_bench', etiqueta: 'campaign one', titulo: null,
  n_runs: 26, n_rows: 26, roles: { campaign_media: 26 },
  documents: ['docs/medicion.md'], source_refs: ['results/eval.json'],
}
const row: ArchivedRun = {
  result_id: rid, run_id: 'm1', plane: 'media-plane', status: 'copied',
  role: 'campaign_media', source_ref: 'results/eval.json', artifact_path: 'artifacts/media-plane/m1',
  tiene_detalle_vivo: true, reason: null,
}
let urls: URL[]
let unavailable: boolean
let archived: boolean
let title: string | null
beforeEach(() => {
  urls = []; unavailable = false; archived = false; title = null
  localStorage.clear()
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
    const url = new URL(String(input), 'http://localhost'); urls.push(url)
    const state = { available: !unavailable, message: unavailable ? 'Falta results/evidence-runs/. Restaurar desde docs/operacion/126.' : null }
    const result = { ...info, titulo: title }
    if (url.pathname === '/api/evidencia') return new Response(JSON.stringify({ ...state, collections: unavailable ? [] : [
      { id: 'clip_bench', n_results: 1, n_rows: 26, results: [result] },
    ] }))
    if (url.pathname === '/api/evidencia/resultado') {
      const page = Number(url.searchParams.get('page'))
      return new Response(JSON.stringify({ ...state, result, items: [{ ...row, run_id: page === 1 ? 'm1' : 'm26' }], total: 26, page, page_size: 25 }))
    }
    if (url.pathname === '/api/evidencia/run') return new Response(JSON.stringify({ ...state,
      run: { ...row, status: archived ? 'archived_only' : 'copied', tiene_detalle_vivo: !archived, reason: archived ? 'Original retirado; evaluación preservada.' : null },
      summary: archived ? null : { run_id: 'm1', units_processed: 17 },
      substitutes: archived ? [{ name: 'eval.json', data: { precision: .75 } }] : [],
      notice: archived ? 'Sin summary individual; artefacto sustituto.' : null, relations: [row],
    }))
    throw new Error(`Esta vista no debe consultar ${url}`)
  }))
})
afterEach(() => { cleanup(); vi.unstubAllGlobals(); localStorage.clear() })
const open = (url = '/evidencia') => render(<MemoryRouter initialEntries={[url]}><App /></MemoryRouter>)

it('navega los tres niveles por query y no consulta servicios desde el Shell', async () => {
  open()
  fireEvent.click(await screen.findByRole('link', { name: 'campaign one' }))
  await screen.findByText('docs/medicion.md')
  fireEvent.click(await screen.findByRole('link', { name: 'm1' }))
  await screen.findByRole('heading', { name: 'Summary congelado' })
  expect(screen.getByText('17')).toBeTruthy()
  expect(screen.getByRole('link', { name: 'Abrir detalle vivo' }).getAttribute('href')).toBe('/runs/m1')
  expect(urls.map(url => url.pathname)).toEqual(['/api/evidencia', '/api/evidencia/resultado', '/api/evidencia/run'])
  expect(urls[1].searchParams.get('id')).toBe(rid)
  expect(urls[2].searchParams.get('plane')).toBe('media-plane')
  expect(screen.queryByRole('group', { name: 'Estado de los servicios' })).toBeNull()
  expect(screen.getByText('Archivo local · servicios no consultados')).toBeTruthy()
})

it('pagina corridas preservando el result_id con barra y el rol', async () => {
  open(`/evidencia/resultado?${new URLSearchParams({ id: rid })}`)
  await screen.findByRole('link', { name: 'm1' })
  fireEvent.click(screen.getByRole('button', { name: 'Siguiente' }))
  await screen.findByRole('link', { name: 'm26' })
  expect(screen.queryByRole('link', { name: 'm1' })).toBeNull()
  expect(screen.getByText('Página 2 de 2')).toBeTruthy()
  expect((screen.getByRole('button', { name: 'Siguiente' }) as HTMLButtonElement).disabled).toBe(true)
  expect(urls.every(url => url.searchParams.get('id') === rid)).toBe(true)
  expect(within(screen.getByRole('table', { name: 'Corridas de evidencia' })).getByText('campaign_media')).toBeTruthy()
})

it('archived_only muestra motivo y sustituto, sin enlace vivo ni imágenes', async () => {
  archived = true
  open(`/evidencia/run?plane=media-plane&run_id=m1&id=${encodeURIComponent(rid)}`)
  await screen.findByText('Original retirado; evaluación preservada.')
  expect(screen.getByRole('heading', { name: 'eval.json' })).toBeTruthy()
  expect(screen.queryByRole('link', { name: 'Abrir detalle vivo' })).toBeNull()
  expect(screen.queryByRole('heading', { name: 'Summary congelado' })).toBeNull()
  expect(screen.queryByRole('img')).toBeNull()
})

it('muestra el estado vacío con la ubicación y el backup, sin servicios', async () => {
  unavailable = true
  open()
  await screen.findByText('Archivo de evidencia no disponible')
  expect(screen.getByText(/Restaurar desde docs\/operacion\/126/)).toBeTruthy()
  expect(urls.map(url => url.pathname)).toEqual(['/api/evidencia'])
})

it('usa el título del usuario cuando está y la etiqueta derivada cuando falta', async () => {
  title = 'Título de prueba aportado por el usuario'
  open()
  await screen.findByRole('link', { name: title })
  expect(screen.queryByRole('link', { name: 'campaign one' })).toBeNull()
})

it('las migas conservan id con barra en query y la raíz sigue siendo Corridas', () => {
  const search = `?${new URLSearchParams({ id: rid, plane: 'media-plane', run_id: 'm1' })}`
  const crumbs = crumbsFor('/evidencia/run', search)
  expect(crumbs.map(crumb => crumb.label)).toEqual(['Evidencia', rid, 'm1'])
  expect(new URL(crumbs[1].to, 'http://localhost').searchParams.get('id')).toBe(rid)
  expect(crumbsFor('/')).toEqual([{ to: '/', label: 'Corridas' }])
})
