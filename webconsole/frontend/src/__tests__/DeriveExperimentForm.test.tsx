import { describe, expect, it, vi, beforeEach } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { DeriveExperimentForm } from '../components/DeriveExperimentForm'

const derive = vi.fn()
// Defaults del manifiesto fuente (GET .../derive-defaults). Con valores NO vacíos
// a propósito: precargarlos no debe convertirlos en overrides explícitos.
const DEFAULTS = {
  warmup_frames: 20,
  fps: null,
  camera_id: 'oak_d_lab',
  prompt_set_id: 'cr01_cr02_v2_short',
  stride: 2,
  max_units: null,
  pattern_set_file: '/p/v2.yaml',
  pattern_active_ids: ['CR-01', 'CR-02'],
}
const deriveDefaults = vi.fn()
vi.mock('../api', () => ({
  deriveExperimentManifest: (...args: unknown[]) => derive(...args),
  getDeriveDefaults: (...args: unknown[]) => deriveDefaults(...args),
  listCameras: async () => [
    { id: 'oak_d_lab', name: 'OAK-D', plugin: 'oak_d', config: {} },
    { id: 'otra', name: 'Otra', plugin: 'rtsp', config: {} },
  ],
  getPromptSets: async () => [
    { id: 'cr01_cr02_v2_short', description: null, language: null, frozen: false, classes: [] },
    { id: 'otro_set', description: null, language: null, frozen: false, classes: [] },
  ],
}))

beforeEach(() => {
  derive.mockReset()
  deriveDefaults.mockReset()
  deriveDefaults.mockResolvedValue(DEFAULTS)
  cleanup()
})

/** Espera a que la precarga haya aterrizado en los inputs. */
async function esperarPrecarga() {
  await waitFor(() =>
    expect((screen.getByLabelText('warmup_frames') as HTMLInputElement).value).toBe('20'),
  )
}

describe('DeriveExperimentForm', () => {
  it('precarga los valores del manifiesto fuente', async () => {
    render(<DeriveExperimentForm source="base" onDone={() => {}} onCancel={() => {}} />)
    await esperarPrecarga()
    expect(deriveDefaults).toHaveBeenCalledWith('base')
    expect((screen.getByLabelText('fps') as HTMLInputElement).value).toBe('')
    expect((screen.getByLabelText('cámara') as HTMLSelectElement).value).toBe('oak_d_lab')
    expect((screen.getByLabelText('prompt set') as HTMLSelectElement).value).toBe(
      'cr01_cr02_v2_short',
    )
    expect((screen.getByLabelText('stride') as HTMLInputElement).value).toBe('2')
    expect((screen.getByLabelText('max_units') as HTMLInputElement).value).toBe('')
    // el <label> incluye el hint, por eso el prefijo en vez de igualdad exacta
    expect((screen.getByLabelText(/^pattern setruta absoluta/) as HTMLInputElement).value).toBe(
      '/p/v2.yaml',
    )
    expect((screen.getByLabelText(/^pattern set clases/) as HTMLInputElement).value).toBe(
      'CR-01, CR-02',
    )
  })

  it('con los valores precargados sin tocar, overrides sale vacío', async () => {
    // El error fácil de la precarga: mandar TODO como override explícito. Un
    // campo que el usuario no tocó conserva el valor del fuente por ausencia.
    derive.mockResolvedValue({ slug: 'nuevo' })
    render(<DeriveExperimentForm source="base" onDone={() => {}} onCancel={() => {}} />)
    await esperarPrecarga()

    fireEvent.change(screen.getByLabelText('nombre nuevo'), { target: { value: 'nuevo' } })
    fireEvent.click(screen.getByText('Derivar'))

    await waitFor(() => expect(derive).toHaveBeenCalled())
    expect(derive.mock.calls[0][1].overrides).toEqual({})
  })

  it('sólo manda el campo que el usuario cambió respecto del fuente', async () => {
    derive.mockResolvedValue({ slug: 'nuevo' })
    render(<DeriveExperimentForm source="base" onDone={() => {}} onCancel={() => {}} />)
    await esperarPrecarga()

    fireEvent.change(screen.getByLabelText('nombre nuevo'), { target: { value: 'nuevo' } })
    fireEvent.change(screen.getByLabelText('warmup_frames'), { target: { value: '30' } })
    fireEvent.click(screen.getByText('Derivar'))

    await waitFor(() => expect(derive).toHaveBeenCalled())
    expect(derive.mock.calls[0][1].overrides).toEqual({ warmup_frames: 30 })
  })

  it('si la precarga falla, el formulario sigue usable y arranca vacío', async () => {
    deriveDefaults.mockRejectedValue(new Error('boom'))
    derive.mockResolvedValue({ slug: 'nuevo' })
    render(<DeriveExperimentForm source="base" onDone={() => {}} onCancel={() => {}} />)

    fireEvent.change(screen.getByLabelText('nombre nuevo'), { target: { value: 'nuevo' } })
    fireEvent.click(screen.getByText('Derivar'))

    await waitFor(() => expect(derive).toHaveBeenCalled())
    expect(derive.mock.calls[0][1].overrides).toEqual({})
  })

  it('manda el body esperado y avisa el slug nuevo', async () => {
    derive.mockResolvedValue({ slug: 'nuevo' })
    const onDone = vi.fn()
    render(<DeriveExperimentForm source="base" onDone={onDone} onCancel={() => {}} />)

    fireEvent.change(screen.getByLabelText('nombre nuevo'), { target: { value: 'nuevo' } })
    fireEvent.change(screen.getByLabelText('warmup_frames'), { target: { value: '30' } })
    fireEvent.click(screen.getByText('Derivar'))

    await waitFor(() => expect(onDone).toHaveBeenCalledWith('nuevo'))
    expect(derive).toHaveBeenCalledWith('base', expect.objectContaining({
      new_slug: 'nuevo',
      overrides: expect.objectContaining({ warmup_frames: 30 }),
    }))
  })

  it('muestra el detail real del backend (409), no el "API 409" genérico de ApiError', async () => {
    // Forma real de un ApiError: `.message` es el string genérico `API ${status}`
    // (ver api.ts:9-15); el mensaje útil viaja en `.payload.detail`.
    derive.mockRejectedValue(
      Object.assign(new Error('API 409'), { status: 409, payload: { detail: 'Ya existe: nuevo' } }),
    )
    render(<DeriveExperimentForm source="base" onDone={() => {}} onCancel={() => {}} />)

    fireEvent.change(screen.getByLabelText('nombre nuevo'), { target: { value: 'nuevo' } })
    fireEvent.click(screen.getByText('Derivar'))

    await waitFor(() => expect(screen.getByText('Ya existe: nuevo')).toBeTruthy())
    expect(screen.queryByText('API 409')).toBeNull()
  })

  it('no deja derivar sin nombre', () => {
    render(<DeriveExperimentForm source="base" onDone={() => {}} onCancel={() => {}} />)
    expect(screen.getByText('Derivar')).toHaveProperty('disabled', true)
  })

  it('no manda claves vacías en overrides (solo lo que el usuario tocó)', async () => {
    derive.mockResolvedValue({ slug: 'nuevo' })
    render(<DeriveExperimentForm source="base" onDone={() => {}} onCancel={() => {}} />)

    fireEvent.change(screen.getByLabelText('nombre nuevo'), { target: { value: 'nuevo' } })
    fireEvent.click(screen.getByText('Derivar'))

    await waitFor(() => expect(derive).toHaveBeenCalled())
    const body = derive.mock.calls[0][1]
    expect(body.overrides).toEqual({})
    expect(body.changes).toBeUndefined()
  })

  it('un valor no numérico en warmup_frames no se manda (evita el borrado silencioso vía null) y muestra un error', async () => {
    const onDone = vi.fn()
    render(<DeriveExperimentForm source="base" onDone={onDone} onCancel={() => {}} />)

    fireEvent.change(screen.getByLabelText('nombre nuevo'), { target: { value: 'nuevo' } })
    fireEvent.change(screen.getByLabelText('warmup_frames'), { target: { value: '3o' } })
    fireEvent.click(screen.getByText('Derivar'))

    await waitFor(() => expect(screen.getByText(/no es un número válido/)).toBeTruthy())
    expect(derive).not.toHaveBeenCalled()
    expect(onDone).not.toHaveBeenCalled()
  })

  it('parsea pattern_active_ids separado por comas, con trim y sin vacíos', async () => {
    derive.mockResolvedValue({ slug: 'nuevo' })
    render(<DeriveExperimentForm source="base" onDone={() => {}} onCancel={() => {}} />)

    fireEvent.change(screen.getByLabelText('nombre nuevo'), { target: { value: 'nuevo' } })
    fireEvent.change(screen.getByLabelText(/^pattern set clases/), {
      target: { value: 'CR-01,  CR-02 ' },
    })
    fireEvent.click(screen.getByText('Derivar'))

    await waitFor(() => expect(derive).toHaveBeenCalled())
    const body = derive.mock.calls[0][1]
    expect(body.overrides.pattern_active_ids).toEqual(['CR-01', 'CR-02'])
  })

  it('mode "derive" (default): título "Derivar de <source>" y botón "Derivar"', async () => {
    render(<DeriveExperimentForm source="base" onDone={() => {}} onCancel={() => {}} />)
    expect(screen.getByText('Derivar de base')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Derivar' })).toBeTruthy()
  })

  it('mode "create": título "Nuevo experimento" y botón "Crear", sin repetir la fuente', async () => {
    render(
      <DeriveExperimentForm source="base" mode="create" onDone={() => {}} onCancel={() => {}} />,
    )
    expect(screen.getByText('Nuevo experimento')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Crear' })).toBeTruthy()
    expect(screen.queryByText(/^Derivar de/)).toBeNull()
    expect(screen.queryByRole('button', { name: 'Derivar' })).toBeNull()
  })

  it('no manda pattern_active_ids si el campo queda vacío', async () => {
    derive.mockResolvedValue({ slug: 'nuevo' })
    render(<DeriveExperimentForm source="base" onDone={() => {}} onCancel={() => {}} />)

    fireEvent.change(screen.getByLabelText('nombre nuevo'), { target: { value: 'nuevo' } })
    fireEvent.click(screen.getByText('Derivar'))

    await waitFor(() => expect(derive).toHaveBeenCalled())
    const body = derive.mock.calls[0][1]
    expect(body.overrides.pattern_active_ids).toBeUndefined()
  })
})
