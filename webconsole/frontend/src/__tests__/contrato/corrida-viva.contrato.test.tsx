import { act, fireEvent, screen } from '@testing-library/react'
import { Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import Shell from '../../components/Shell'
import RunDetailPage from '../../pages/RunDetailPage'
import { corrida, instalarHttp, json, montar } from './soporte'

describe('Contrato: corrida viva', () => {
  it('permite alcanzar la corrida activa desde una ruta distinta del listado', async () => {
    instalarHttp((p) => p.url.pathname === '/api/runs'
      ? json([{ ...corrida, status: 'running', live: true }]) : undefined)
    await montar(<Shell><h1>Ruta ajena al listado</h1></Shell>, '/prompts')
    const aviso = await screen.findByRole('link', { name: new RegExp(corrida.run_id) })
    expect(aviso.getAttribute('href')).toBe(`/runs/${corrida.run_id}`)
  })

  it('consulta mientras corre, permite detener y cesa el polling del detalle al terminar', async () => {
    vi.useFakeTimers()
    let status = 'running'
    const path = `/api/runs/${corrida.run_id}`
    const http = instalarHttp((p) => {
      if (p.method === 'GET' && p.url.pathname === path) {
        return json({ ...corrida, status, live: status === 'running' })
      }
      if (p.method === 'POST' && p.url.pathname === `${path}/stop`) {
        return json({ run_id: corrida.run_id, stopping: true })
      }
    })
    await montar(<Routes><Route path="/runs/:id" element={<RunDetailPage />} /></Routes>,
      `/runs/${corrida.run_id}`)
    await act(async () => { await vi.advanceTimersByTimeAsync(0) })
    const iniciales = http.a('GET', path).length
    await act(async () => { await vi.advanceTimersByTimeAsync(12_000) })
    expect(http.a('GET', path).length).toBeGreaterThan(iniciales)
    fireEvent.click(screen.getByRole('button', { name: /Detener/i }))
    await act(async () => { await vi.advanceTimersByTimeAsync(0) })
    expect(http.a('POST', `${path}/stop`)).toHaveLength(1)
    expect(http.a('POST', `${path}/stop`)[0].body).toBeNull()
    status = 'succeeded'
    await act(async () => { await vi.advanceTimersByTimeAsync(12_000) })
    expect(screen.queryByRole('button', { name: /Detener/i })).toBeNull()
    const terminadas = http.a('GET', path).length
    await act(async () => { await vi.advanceTimersByTimeAsync(20_000) })
    expect(http.a('GET', path)).toHaveLength(terminadas)
  })
})
