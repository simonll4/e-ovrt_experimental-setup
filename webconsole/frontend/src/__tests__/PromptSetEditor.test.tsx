import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import PromptSetEditor from '../components/PromptSetEditor'
import * as api from '../api'

vi.mock('../api')

// @testing-library/react no engancha su cleanup automático entre tests en este
// repo (sin setupFiles); sin esto, el DOM de un test queda montado y contamina
// las queries del siguiente (mismo patrón en ComposePage.test.tsx / PromptSetsPage.test.tsx).
afterEach(() => cleanup())

const EXPLORATORY = {
  id: 'exp_set', status: 'exploratory', track: 'core',
  classes: [{ id: 'person', strategy: 'canonical_positive', phrasings: { default: ['person'] } }],
}

describe('PromptSetEditor', () => {
  it('exploratory: permite editar y guardar via updatePromptSet', async () => {
    vi.mocked(api.updatePromptSet).mockResolvedValue({ ...EXPLORATORY })
    const onChanged = vi.fn()
    render(<PromptSetEditor initial={EXPLORATORY} onChanged={onChanged} onClose={() => {}} />)
    fireEvent.click(screen.getByRole('button', { name: /guardar/i }))
    await waitFor(() => expect(api.updatePromptSet).toHaveBeenCalledWith('exp_set', expect.anything()))
    expect(onChanged).toHaveBeenCalled()
  })

  it('exploratory: strategy es un select con la taxonomía, sin campo status editable', () => {
    render(<PromptSetEditor initial={EXPLORATORY} onChanged={() => {}} onClose={() => {}} />)
    const select = screen.getByLabelText(/strategy/i)
    expect(select.tagName).toBe('SELECT')
    expect(screen.queryByLabelText(/^status$/i)).toBeNull()
  })

  it('freeze flow: pedir congelamiento y confirmar', async () => {
    vi.mocked(api.requestFreeze).mockResolvedValue({ ...EXPLORATORY, status: 'frozen_pending_review' })
    const onChanged = vi.fn()
    render(<PromptSetEditor initial={EXPLORATORY} onChanged={onChanged} onClose={() => {}} />)
    fireEvent.click(screen.getByRole('button', { name: /pedir congelamiento/i }))
    await waitFor(() => expect(api.requestFreeze).toHaveBeenCalledWith('exp_set'))

    vi.mocked(api.confirmFreeze).mockResolvedValue({ ...EXPLORATORY, status: 'frozen', frozen_sha256: 'x' })
    render(<PromptSetEditor
      initial={{ ...EXPLORATORY, status: 'frozen_pending_review' }}
      onChanged={onChanged} onClose={() => {}} />)
    fireEvent.click(screen.getByRole('button', { name: /confirmar freeze/i }))
    await waitFor(() => expect(api.confirmFreeze).toHaveBeenCalledWith('exp_set'))
  })

  it('frozen: sin guardar, con derivar', async () => {
    vi.mocked(api.derivePromptSet).mockResolvedValue({ ...EXPLORATORY, id: 'exp_set_v2' })
    render(<PromptSetEditor
      initial={{ ...EXPLORATORY, status: 'frozen', frozen_sha256: 'x' }}
      onChanged={() => {}} onClose={() => {}} />)
    expect(screen.queryByRole('button', { name: /guardar/i })).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: /derivar/i }))
    fireEvent.change(screen.getByLabelText(/nuevo id/i), { target: { value: 'exp_set_v2' } })
    fireEvent.change(screen.getByLabelText(/cambios/i), { target: { value: 'ajuste de fraseo' } })
    fireEvent.click(screen.getByRole('button', { name: /crear derivado/i }))
    await waitFor(() =>
      expect(api.derivePromptSet).toHaveBeenCalledWith('exp_set', 'exp_set_v2', 'ajuste de fraseo'))
  })

  it('error con detail array Pydantic se formatea sin [object Object]', async () => {
    const pydanticErrors = [
      { msg: 'phrasings vacío', loc: ['classes', 0] },
      { msg: 'strategy inválida', loc: ['classes', 0, 'strategy'] },
    ]
    vi.mocked(api.updatePromptSet).mockRejectedValueOnce({
      payload: { detail: pydanticErrors },
    })
    const onChanged = vi.fn()
    render(<PromptSetEditor initial={EXPLORATORY} onChanged={onChanged} onClose={() => {}} />)
    fireEvent.click(screen.getByRole('button', { name: /guardar/i }))
    await waitFor(() => {
      const alert = screen.getByRole('alert')
      expect(alert.textContent).toContain('phrasings vacío')
      expect(alert.textContent).not.toContain('[object Object]')
    })
  })
})
