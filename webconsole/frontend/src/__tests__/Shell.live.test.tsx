import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { simularVentana } from '../test-utils'
import { Route, Routes } from 'react-router-dom'
import { expect, it } from 'vitest'
import Shell from '../components/Shell'
import ComposePage from '../pages/ComposePage'
import { corrida, instalarHttp, json, montar } from './contrato/soporte'

it('seguir la corrida viva cierra el cajón de navegación móvil', async () => {
  localStorage.setItem('eovrt-sidebar-collapsed', '1')
  const restaurar = simularVentana('compacta')
  try {
    instalarHttp((p) => p.url.pathname === '/api/runs'
      ? json([{ ...corrida, status: 'running', live: true }]) : undefined)
    await montar(<Shell>Conjuntos de prompts</Shell>, '/prompts')
    fireEvent.click(screen.getByRole('button', { name: 'Abrir navegación' }))
    const cajon = screen.getByRole('dialog', { name: 'Navegación principal' })
    expect(cajon.hasAttribute('open')).toBe(true)
    // El cajón no hereda el colapso de escritorio: muestra los rótulos.
    const sidebar = within(cajon).getByRole('complementary', { name: 'Navegación principal' })
    expect(sidebar.className).not.toContain('eo-sidebar--collapsed')
    expect(localStorage.getItem('eovrt-sidebar-collapsed')).toBe('1')
    fireEvent.click(await within(cajon).findByRole('link', { name: 'Corrida en curso: ' + corrida.run_id }))
    expect(cajon.hasAttribute('open')).toBe(false)
    // La preferencia de escritorio queda intacta.
    expect(localStorage.getItem('eovrt-sidebar-collapsed')).toBe('1')
  } finally {
    restaurar()
  }
})

it('lanzar desde el formulario invalida la lista vacía y muestra la corrida global', async () => {
  let running = false
  const http = instalarHttp((p) => {
    if (p.url.pathname !== '/api/runs') return undefined
    if (p.method === 'POST') {
      running = true
      return json({ run_id: corrida.run_id }, 201)
    }
    return json(running ? [{ ...corrida, status: 'running', live: true }] : [])
  })
  await montar(<Shell><Routes>
    <Route path="/compose" element={<ComposePage />} />
    <Route path="/runs/:id" element={<h1>Detalle lanzado</h1>} />
  </Routes></Shell>, '/compose')
  await waitFor(() => expect(http.a('GET', '/api/runs').length).toBeGreaterThan(0))
  expect(screen.queryByRole('link', { name: /^Corrida en curso:/ })).toBeNull()
  for (const [field, value] of [
    [/Conjunto del catálogo/i, 'contrato_dataset'],
    [/Conjunto de prompts/i, 'contrato_prompts'],
  ] as const) {
    fireEvent.click(await screen.findByRole('button', { name: field }))
    fireEvent.click(await screen.findByRole('option', { name: value }))
  }
  const launch = screen.getByRole('button', { name: /^Lanzar corrida$/ })
  await waitFor(() => expect(launch).toHaveProperty('disabled', false))
  const readsBefore = http.a('GET', '/api/runs').length
  fireEvent.click(launch)
  await screen.findByRole('heading', { name: 'Detalle lanzado' })
  await screen.findByRole('link', { name: 'Corrida en curso: ' + corrida.run_id })
  expect(http.a('GET', '/api/runs').length).toBeGreaterThan(readsBefore)
  expect(http.a('POST', '/api/runs')).toHaveLength(1)
})
