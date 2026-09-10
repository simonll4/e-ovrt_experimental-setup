import { fireEvent, screen, waitFor } from '@testing-library/react'
import { Route, Routes } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import RunDetailPage from '../../pages/RunDetailPage'
import { corrida, evaluacion, instalarHttp, json, montar } from './soporte'

describe('Contrato: detalle, traza y evaluación', () => {
  it('lee detalle y traza, permite inspeccionar cuadros y evaluar contra BENCH', async () => {
    const path = `/api/runs/${corrida.run_id}`
    const http = instalarHttp((p) => p.method === 'POST' && p.url.pathname === `${path}/evaluate`
      ? json(evaluacion) : undefined)
    await montar(<Routes><Route path="/runs/:id" element={<RunDetailPage />} /></Routes>,
      `/runs/${corrida.run_id}`)
    await screen.findByRole('listbox', { name: /Cuadros de la traza/i })
    expect(http.a('GET', path).length).toBeGreaterThan(0)
    expect(http.a('GET', `${path}/trace`).length).toBeGreaterThan(0)
    expect(http.a('GET', `${path}/trace`)[0].url.searchParams.get('page')).toBe('1')
    expect(Number(http.a('GET', `${path}/trace`)[0].url.searchParams.get('page_size'))).toBeGreaterThan(0)
    expect(screen.getByRole('img', { name: /Actividad de .*cuadros|Detecciones por cuadro a lo largo/i })).toBeTruthy()
    fireEvent.click(screen.getByRole('option', { name: /frame_1/ }))
    expect(screen.getByRole('img', { name: `Cuadro 1 de la corrida ${corrida.run_id}` })).toBeTruthy()
    expect(screen.getByText('person')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: /Cuadro anterior/i }))
    expect(screen.getByRole('img', { name: `Cuadro 0 de la corrida ${corrida.run_id}` })).toBeTruthy()
    fireEvent.click(screen.getByRole('tab', { name: /^Evaluación$/i }))
    fireEvent.click(await screen.findByRole('button', { name: /Evaluar contra BENCH/i }))
    await waitFor(() => expect(http.a('POST', `${path}/evaluate`)).toHaveLength(1))
    expect(http.a('POST', `${path}/evaluate`)[0].body).toBeNull()
    expect(await screen.findByRole('cell', { name: 'person' })).toBeTruthy()
    expect(screen.getByRole('cell', { name: /0[,.]72/ })).toBeTruthy()
    expect(screen.getByText(/mAP@0\.5.*0[,.]47/)).toBeTruthy()
  })
})
