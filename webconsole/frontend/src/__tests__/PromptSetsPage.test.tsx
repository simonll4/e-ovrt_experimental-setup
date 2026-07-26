import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import PromptSetsPage from '../pages/PromptSetsPage'
import * as api from '../api'

vi.mock('../api')

// @testing-library/react no engancha su cleanup automático entre tests en este
// repo (sin setupFiles); sin esto, el DOM de un test queda montado y contamina
// las queries del siguiente (ver mismo patrón en ComposePage.test.tsx).
afterEach(() => cleanup())

const SUMMARIES = [
  { id: 'eind_v1', description: 'núcleo', status: 'frozen_pending_review',
    track: 'core', derives_from: 'cr01_cr02_v2_short', n_classes: 3, n_phrases: 9 },
  { id: 'cr01_cr02_bench_v2', description: 'BENCH', status: 'frozen',
    track: 'core', derives_from: null, n_classes: 4, n_phrases: 4 },
]

const FROZEN_DETAIL = {
  id: 'cr01_cr02_bench_v2', status: 'frozen', frozen_sha256: 'abc123',
  classes: [{ id: 'person', phrasings: { default: ['person'] } }],
}

describe('PromptSetsPage', () => {
  it('lista los sets con badge de estado, traducido por el glosario', async () => {
    vi.mocked(api.listPromptSets).mockResolvedValue(SUMMARIES)
    render(<PromptSetsPage />)
    await waitFor(() => expect(screen.getByText('eind_v1')).toBeTruthy())
    expect(screen.getByText('congelado, pendiente de revisión')).toBeTruthy()
    expect(screen.getByText('congelado')).toBeTruthy()
  })

  it('el botón "Nuevo set" es el primitivo Button', async () => {
    vi.mocked(api.listPromptSets).mockResolvedValue([])
    render(<PromptSetsPage />)
    await waitFor(() => expect(screen.getByRole('button', { name: 'Nuevo conjunto' }).className).toContain('eo-btn'))
  })

  it('un set frozen se muestra read-only con acción Derivar', async () => {
    vi.mocked(api.listPromptSets).mockResolvedValue(SUMMARIES)
    vi.mocked(api.getPromptSetDetail).mockResolvedValue(FROZEN_DETAIL)
    render(<PromptSetsPage />)
    await waitFor(() => screen.getByText('cr01_cr02_bench_v2'))
    fireEvent.click(screen.getByText('cr01_cr02_bench_v2'))
    await waitFor(() => expect(screen.getByText(/inmutable/i)).toBeTruthy())
    expect(screen.queryByRole('button', { name: /guardar/i })).toBeNull()
    expect(screen.getByRole('button', { name: /derivar/i })).toBeTruthy()
  })
})
