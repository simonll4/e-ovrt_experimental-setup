import { fireEvent, screen, waitFor } from '@testing-library/react'
import { Route, Routes } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import ComposePage from '../../pages/ComposePage'
import RunDetailPage from '../../pages/RunDetailPage'
import { corrida, instalarHttp, json, montar, preflight, target } from './soporte'

async function abrirComposicion() {
  await montar(<Routes>
    <Route path="/compose" element={<ComposePage />} />
    <Route path="/runs/:id" element={<RunDetailPage />} />
  </Routes>, '/compose')
}

async function completar() {
  await elegir(/Dataset del catálogo|Conjunto del catálogo/i, 'contrato_dataset')
  await elegir(/Conjunto de prompts/i, 'contrato_prompts')
}

// La selección es la capacidad; un desplegable nativo y un selector con botón
// son presentaciones válidas. En ambos caminos se exige la opción accesible.
async function elegir(nombre: RegExp, valor: string) {
  await waitFor(() => expect(
    screen.queryByRole('combobox', { name: nombre })
      ?? screen.queryByRole('button', { name: nombre }),
  ).toBeTruthy())
  const select = screen.queryByRole('combobox', { name: nombre })
  if (select) {
    await screen.findByRole('option', { name: valor })
    fireEvent.change(select, { target: { value: valor } })
  } else {
    fireEvent.click(screen.getByRole('button', { name: nombre }))
    fireEvent.click(await screen.findByRole('option', { name: valor }))
  }
}

describe('Contrato: nueva corrida', () => {
  it('consulta preflight, compone fuente y prompts, lanza y abre el detalle real', async () => {
    const http = instalarHttp((p) => p.method === 'POST' && p.url.pathname === '/api/runs'
      ? json({ run_id: corrida.run_id }, 201) : undefined)
    await abrirComposicion()
    await completar()
    // La fuente puede elegirse con desplegable o con un botón de selección.
    const fuente = screen.queryByRole('combobox', { name: /Tipo de fuente/i })
    if (fuente) fireEvent.change(fuente, { target: { value: 'image_folder' } })
    else fireEvent.click(screen.getByRole('button', { name: /Carpeta de imágenes/i }))
    const helmet = screen.queryByRole('checkbox', { name: 'helmet' })
      ?? screen.getByRole('button', { name: 'helmet' })
    fireEvent.click(helmet)
    const lanzar = screen.getByRole('button', { name: /^Lanzar( corrida)?$/i })
    await waitFor(() => expect(lanzar).toHaveProperty('disabled', false))
    expect(http.a('GET', '/api/preflight').length).toBeGreaterThan(0)
    expect(http.a('GET', '/api/target').length).toBeGreaterThan(0)
    fireEvent.click(lanzar)
    await screen.findByRole('heading', { name: corrida.run_id })
    expect(http.a('POST', '/api/runs')).toHaveLength(1)
    expect(http.a('POST', '/api/runs')[0].body).toMatchObject({
      ingest: { plugin: 'image_folder', config: { dataset: 'contrato_dataset' } },
      prompts: { set_id: 'contrato_prompts', active_ids: ['person'] },
      run: { name: null, save_annotated_video: false },
      manifest_model_ref: null, confirm_target_model: false,
    })
    expect(http.a('GET', `/api/runs/${corrida.run_id}`).length).toBeGreaterThan(0)
  })

  it('impide lanzar con el formulario completo si el target aún no está listo', async () => {
    const http = instalarHttp((p) => p.url.pathname === '/api/target'
      ? json({ ...target, ready: false }) : undefined)
    await abrirComposicion()
    await completar()
    const lanzar = screen.getByRole('button', { name: /^Lanzar( corrida)?$/i })
    await waitFor(() => expect(lanzar).toHaveProperty('disabled', true))
    expect(screen.getByText(/no terminó de cargar el modelo/i)).toBeTruthy()
    fireEvent.click(lanzar)
    expect(http.a('POST', '/api/runs')).toHaveLength(0)
  })

  it('muestra los bloqueos del preflight y permite lanzar sólo medios con target listo', async () => {
    // D-8: el preflight agregado informa; la corrida DBE sólo necesita el target.
    const http = instalarHttp((p) => {
      if (p.url.pathname === '/api/preflight') {
        return json({
          ...preflight, ready: false, blockers: ['Motor de reglas sin respuesta'],
          control: { ...preflight.control, healthy: false, ready: false },
        })
      }
      if (p.method === 'POST' && p.url.pathname === '/api/runs') {
        return json({ run_id: corrida.run_id }, 201)
      }
    })
    await abrirComposicion()
    await completar()
    expect(http.a('GET', '/api/preflight').length).toBeGreaterThan(0)
    const lanzar = screen.getByRole('button', { name: /^Lanzar( corrida)?$/i })
    expect(lanzar).toHaveProperty('disabled', false)
    expect(screen.getByText(/Motor de reglas sin respuesta/)).toBeTruthy()
    fireEvent.click(lanzar)
    await waitFor(() => expect(http.a('POST', '/api/runs')).toHaveLength(1))
    await screen.findByRole('heading', { name: corrida.run_id })
  })
})
