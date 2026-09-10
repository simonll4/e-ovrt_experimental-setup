import { act, fireEvent, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import ComposePage from '../pages/ComposePage'
import { POLL } from '../api/queryClient'
import { corrida, instalarHttp, json, montar, preflight } from './contrato/soporte'

describe('ComposePage: bloqueos de preflight', () => {
  it.each([false, true])('informa los motivos con ready=%s sin bloquear DBE y los actualiza por polling', async (ready) => {
    vi.useFakeTimers()
    let blockers = ['Motor de reglas sin respuesta']
    let control = { ...preflight.control, healthy: false, ready: false }
    const http = instalarHttp((p) => {
      if (p.url.pathname === '/api/preflight') return json({ ...preflight, ready, blockers, control })
      if (p.method === 'POST' && p.url.pathname === '/api/runs') {
        return json({ run_id: corrida.run_id }, 201)
      }
    })

    await act(async () => { await montar(<ComposePage />, '/compose') })
    await act(async () => { await vi.advanceTimersByTimeAsync(20) })
    await act(async () => { await vi.advanceTimersByTimeAsync(20) })
    fireEvent.click(screen.getByRole('button', { name: 'Conjunto del catálogo' }))
    fireEvent.click(screen.getByRole('option', { name: 'contrato_dataset' }))
    fireEvent.click(screen.getByRole('button', { name: 'Conjunto de prompts' }))
    fireEvent.click(screen.getByRole('option', { name: 'contrato_prompts' }))
    const lanzar = screen.getByRole('button', { name: /Lanzar corrida/i })
    expect(lanzar).toHaveProperty('disabled', false)
    expect(screen.getByText(/Motor de reglas sin respuesta/)).toBeTruthy()
    await act(async () => { fireEvent.click(lanzar) })
    expect(http.a('POST', '/api/runs')).toHaveLength(1)

    blockers = []
    ready = true
    control = { ...preflight.control, healthy: true, ready: true }
    await act(async () => { await vi.advanceTimersByTimeAsync(POLL.salud + 1) })
    expect(lanzar).toHaveProperty('disabled', false)
    expect(screen.queryByText(/Motor de reglas sin respuesta/)).toBeNull()
    expect(screen.getByText(/Motor de reglas operativo/)).toBeTruthy()

    blockers = ['Motor de reglas no listo']
    ready = false
    control = { ...preflight.control, healthy: true, ready: false }
    await act(async () => { await vi.advanceTimersByTimeAsync(POLL.salud + 1) })
    expect(lanzar).toHaveProperty('disabled', false)
    expect(screen.getByText(/Motor de reglas no listo/)).toBeTruthy()
    await act(async () => { fireEvent.click(lanzar) })
    expect(http.a('POST', '/api/runs')).toHaveLength(2)
  })
})
