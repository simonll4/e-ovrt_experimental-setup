import { screen } from '@testing-library/react'
import { expect, it } from 'vitest'
import CamerasPage from '../pages/CamerasPage'
import { instalarHttp, json, montar } from './contrato/soporte'

it('muestra el fallo del sondeo de preview sin rechazar una promesa sin manejar', async () => {
  instalarHttp((p) => {
    if (p.url.pathname === '/api/preview') return json({ detail: 'Servicio inaccesible' }, 502)
    if (p.url.pathname === '/api/preview/stop') return json({ status: 'idle' })
    if (p.url.pathname === '/api/recordings/current') return json({ detail: 'Sin grabación' }, 404)
    return undefined
  })
  await montar(<CamerasPage />, '/cameras')
  expect(await screen.findByText(/No se pudo consultar la previsualización/)).toBeTruthy()
  expect(screen.getByRole('heading', { name: 'Cámaras' })).toBeTruthy()
})
