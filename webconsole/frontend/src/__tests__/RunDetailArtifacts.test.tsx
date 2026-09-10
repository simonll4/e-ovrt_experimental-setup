import { fireEvent, screen } from '@testing-library/react'
import { Route, Routes } from 'react-router-dom'
import { expect, it } from 'vitest'
import RunDetailPage from '../pages/RunDetailPage'
import { corrida, evaluacion, instalarHttp, json, montar } from './contrato/soporte'

it('expone el inventario limitado del servicio anterior con descargas verificadas', async () => {
  instalarHttp((p) => p.url.pathname.endsWith('/artifacts') ? json({
    run_id: corrida.run_id, complete: false, notice: 'Inventario estándar, no completo',
    items: [{ path: 'summary.json', name: 'summary.json', size_bytes: 123, n_files: null,
      description: 'Métricas de la corrida' }],
  }) : undefined)
  await montar(<Routes><Route path="/runs/:id" element={<RunDetailPage />} /></Routes>,
    '/runs/'+corrida.run_id)
  fireEvent.click(await screen.findByRole('tab', { name: /Archivos/ }))
  expect(await screen.findByText('Inventario estándar, no completo')).toBeTruthy()
  expect(screen.getByRole('link', { name: 'Descargar summary.json' }).getAttribute('href'))
    .toBe('/api/runs/'+corrida.run_id+'/artifacts/summary.json')
})

it('muestra la falla del inventario, sin presentarla como ausencia de archivos', async () => {
  instalarHttp((p) => p.url.pathname.endsWith('/artifacts') ? json({ detail: 'Caído' }, 503) : undefined)
  await montar(<Routes><Route path="/runs/:id" element={<RunDetailPage />} /></Routes>,
    '/runs/'+corrida.run_id)
  fireEvent.click(await screen.findByRole('tab', { name: /Archivos/ }))
  expect(await screen.findByText('No se pudo consultar el inventario de archivos.')).toBeTruthy()
})

it('actualiza los archivos después de evaluar sin recargar el detalle', async () => {
  let evaluated = false
  instalarHttp((p) => {
    if (p.url.pathname.endsWith('/evaluate')) {
      if (p.method === 'POST') evaluated = true
      return evaluated ? json(evaluacion) : json({ detail: 'Sin evaluación' }, 404)
    }
    if (p.url.pathname === '/api/runs/'+corrida.run_id) return json({ ...corrida, evaluated })
    if (p.url.pathname.endsWith('/artifacts')) return json({ run_id: corrida.run_id,
      items: (evaluated ? ['summary.json', 'eval_perception.json'] : ['summary.json'])
        .map((name) => ({ name, path: name, size_bytes: 123, n_files: null, description: name })),
    })
    return undefined
  })
  await montar(<Routes><Route path="/runs/:id" element={<RunDetailPage />} /></Routes>,
    '/runs/'+corrida.run_id)
  fireEvent.click(await screen.findByRole('tab', { name: /Archivos/ }))
  await screen.findByRole('link', { name: 'Descargar summary.json' })
  expect(screen.queryByRole('link', { name: 'Descargar eval_perception.json' })).toBeNull()
  fireEvent.click(screen.getByRole('tab', { name: 'Evaluación' }))
  fireEvent.click(await screen.findByRole('button', { name: 'Evaluar contra BENCH' }))
  await screen.findByText(/mAP@0.5:/)
  fireEvent.click(screen.getByRole('tab', { name: /Archivos/ }))
  expect(await screen.findByRole('link', { name: 'Descargar eval_perception.json' })).toBeTruthy()
})
