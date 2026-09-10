import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { cleanup, fireEvent, render, screen, waitFor, within } from '../test-utils'
import RunsPage from '../pages/RunsPage'
import type { RunRow } from '../types'

const evidence: RunRow = {
  run_id: 'measured', status: 'succeeded', evidence: {
    is_evidence: true, result_ids: ['clip_bench/a', 'realtime/b'], collections: ['dbe_video'],
  },
}
const archived: RunRow = { run_id: 'noise', status: 'failed', evidence: {
  is_evidence: false, result_ids: [], collections: [],
} }
let urls: URL[] = []
let available = true
beforeEach(() => {
  localStorage.clear()
  urls = []
  available = true
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
    const url = new URL(String(input), 'http://localhost')
    urls.push(url)
    if (url.pathname !== '/api/runs') throw new Error(`Petición inesperada: ${url}`)
    let rows = [evidence, archived]
    if (url.searchParams.get('vista') === 'evidencia') rows = available ? [evidence] : []
    if (url.searchParams.get('vista') === 'archivadas') rows = [archived]
    if (url.searchParams.get('estado') === 'running') rows = []
    return new Response(JSON.stringify(rows), { headers: {
      'Content-Type': 'application/json', 'X-Total-Count': String(rows.length),
      'X-Archived-Count': '1', 'X-Evidence-Available': String(available),
    } })
  }))
})
afterEach(() => { cleanup(); vi.unstubAllGlobals(); localStorage.clear() })
const page = () => render(<MemoryRouter><RunsPage /></MemoryRouter>)

it('pide evidencia y alterna los tres estados sin filtrar en el cliente', async () => {
  page()
  await screen.findByText('1 corridas archivadas')
  const table = within(screen.getByRole('table'))
  expect(table.getByText('measured')).toBeTruthy()
  expect(table.queryByText('noise')).toBeNull()
  expect(urls.some(u => u.searchParams.get('vista') === 'evidencia')).toBe(true)
  const control = within(screen.getByRole('group', { name: 'Vista de evidencia' }))
  fireEvent.click(control.getByRole('button', { name: 'Archivadas' }))
  await waitFor(() => expect(table.getByText('noise')).toBeTruthy())
  expect(table.queryByText('measured')).toBeNull()
  fireEvent.click(control.getByRole('button', { name: 'Todas' }))
  await waitFor(() => expect(table.getByText('measured')).toBeTruthy())
  expect(table.getByText('noise')).toBeTruthy()
  expect(urls.some(u => u.searchParams.get('vista') === 'archivadas')).toBe(true)
  expect(urls.some(u => u.searchParams.get('vista') === 'todas')).toBe(true)
})

it('persiste la elección al remontar y muestra un solo distintivo con ambos resultados en title', async () => {
  const mounted = page()
  await screen.findByText('clip_bench/a')
  const badge = screen.getByText('clip_bench/a')
  expect(badge.parentElement?.title).toBe('clip_bench/a\nrealtime/b')
  expect(screen.queryByText('realtime/b')).toBeNull()
  fireEvent.click(within(screen.getByRole('group', { name: 'Vista de evidencia' }))
    .getByRole('button', { name: 'Todas' }))
  await screen.findByText('noise')
  mounted.unmount()
  page()
  await screen.findByText('noise')
  expect(within(screen.getByRole('group', { name: 'Vista de evidencia' }))
    .getByRole('button', { name: 'Todas' }).getAttribute('aria-pressed')).toBe('true')
})

it('explica la ausencia del registro y permite volver al historial', async () => {
  available = false
  page()
  await screen.findByText(/Registro de evidencia no disponible/)
  expect(screen.getByText('No hay corridas en esta vista')).toBeTruthy()
  fireEvent.click(within(screen.getByRole('group', { name: 'Vista de evidencia' }))
    .getByRole('button', { name: 'Todas' }))
  await screen.findByText('noise')
})
