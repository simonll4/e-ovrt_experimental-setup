import { cleanup, fireEvent, render, screen, waitFor, within } from '../test-utils'
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

const PENDING_DETAIL = {
  id: 'eind_v1', status: 'frozen_pending_review', derives_from: 'cr01_cr02_v2_short',
  classes: [{ id: 'person', phrasings: { default: ['una persona', 'alguien caminando'] } }],
  diff: {
    from: 'cr01_cr02_v2_short',
    classes_added: ['helmet', 'vest'],
    classes_removed: [],
    phrases_added: { helmet: ['un casco'], vest: ['un chaleco', 'chaleco reflectivo'] },
    phrases_removed: {},
  },
}

const FROZEN_DETAIL = {
  id: 'cr01_cr02_bench_v2', status: 'frozen', frozen_sha256: 'abc123',
  classes: [{ id: 'person', phrasings: { default: ['person'] } }],
}

/** La lista de la izquierda. El panel de detalle repite el identificador y el
 *  chip de estado del conjunto elegido, así que las consultas se acotan. */
const lista = () => screen.getByRole('button', { name: /eind_v1/ }).closest('section') as HTMLElement

describe('PromptSetsPage', () => {
  it('lista los sets con badge de estado', async () => {
    vi.mocked(api.listPromptSets).mockResolvedValue(SUMMARIES)
    vi.mocked(api.getPromptSetDetail).mockResolvedValue(PENDING_DETAIL as never)
    render(<PromptSetsPage />)
    await waitFor(() => expect(screen.getByText('eind_v1')).toBeTruthy())
    // El estado se muestra con nombre legible; el código crudo no llega a la pantalla.
    expect(within(lista()).getByText('Pendiente de revisión')).toBeTruthy()
    expect(screen.queryByText('frozen_pending_review')).toBeNull()
    expect(within(lista()).getByText('Congelado')).toBeTruthy()
    expect(screen.queryByText('frozen')).toBeNull()
  })

  // §8.2: es lo que explica por qué un conjunto se puede o no editar. Sin el
  // diagrama, "Congelado" es un adjetivo sin consecuencia visible.
  it('muestra el ciclo de vida con el paso actual marcado', async () => {
    vi.mocked(api.listPromptSets).mockResolvedValue(SUMMARIES)
    vi.mocked(api.getPromptSetDetail).mockResolvedValue(PENDING_DETAIL as never)
    render(<PromptSetsPage />)
    const paso = await screen.findByText('En exploración')
    // El primero ya se recorrió; el actual es "Pendiente de revisión".
    expect(paso.className).toContain('eo-flow__step--done')
    const actual = screen.getAllByText('Pendiente de revisión')
      .find((n) => n.className.includes('eo-flow__step'))
    expect(actual?.className).toContain('eo-flow__step--on')
    expect(actual?.getAttribute('aria-current')).toBe('step')
  })

  it('explica qué se puede hacer en el estado actual', async () => {
    vi.mocked(api.listPromptSets).mockResolvedValue(SUMMARIES)
    vi.mocked(api.getPromptSetDetail).mockResolvedValue(PENDING_DETAIL as never)
    render(<PromptSetsPage />)
    expect(await screen.findByText(/Ya no se puede editar/)).toBeTruthy()
  })

  // §8.3: las frases son lo que define al conjunto y antes solo se veían
  // entrando al editor.
  it('muestra las clases con sus frases entre comillas angulares', async () => {
    vi.mocked(api.listPromptSets).mockResolvedValue(SUMMARIES)
    vi.mocked(api.getPromptSetDetail).mockResolvedValue(PENDING_DETAIL as never)
    render(<PromptSetsPage />)
    expect(await screen.findByText(/«una persona» · «alguien caminando»/)).toBeTruthy()
  })

  // §8.4: `derives_from` decía de dónde venía, pero no qué había cambiado.
  it('la tarjeta de origen resume el diff contra el conjunto padre', async () => {
    vi.mocked(api.listPromptSets).mockResolvedValue(SUMMARIES)
    vi.mocked(api.getPromptSetDetail).mockResolvedValue(PENDING_DETAIL as never)
    render(<PromptSetsPage />)
    expect(await screen.findByText('Origen')).toBeTruthy()
    expect(screen.getByText('cr01_cr02_v2_short')).toBeTruthy()
    expect(screen.getByText('2 clases nuevas, 3 frases nuevas')).toBeTruthy()
  })

  it('un conjunto congelado no ofrece editar, sino ver', async () => {
    vi.mocked(api.listPromptSets).mockResolvedValue(SUMMARIES)
    vi.mocked(api.getPromptSetDetail).mockResolvedValue(FROZEN_DETAIL as never)
    render(<PromptSetsPage />)
    await waitFor(() => expect(screen.getByText('cr01_cr02_bench_v2')).toBeTruthy())
    fireEvent.click(screen.getByRole('button', { name: /cr01_cr02_bench_v2/ }))
    await waitFor(() =>
      expect(screen.getByRole('button', { name: 'Ver clases y frases' })).toBeTruthy(),
    )
    expect(screen.queryByRole('button', { name: 'Editar clases y frases' })).toBeNull()
    expect(screen.getByText(/Congelado y con huella verificable/)).toBeTruthy()
  })

  it('abre el editor en la columna derecha, sin perder la lista', async () => {
    vi.mocked(api.listPromptSets).mockResolvedValue(SUMMARIES)
    vi.mocked(api.getPromptSetDetail).mockResolvedValue(FROZEN_DETAIL as never)
    render(<PromptSetsPage />)
    await waitFor(() => expect(screen.getByText('cr01_cr02_bench_v2')).toBeTruthy())
    fireEvent.click(screen.getByRole('button', { name: /cr01_cr02_bench_v2/ }))
    fireEvent.click(await screen.findByRole('button', { name: 'Ver clases y frases' }))
    // La lista sigue ahí: se puede saltar a otro conjunto sin volver atrás.
    await waitFor(() => expect(screen.getByRole('button', { name: /eind_v1/ })).toBeTruthy())
  })
})
