import { afterEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { cleanup, fireEvent, render, screen, waitFor, within } from '../test-utils'
import App from '../App'
import RunsPage from '../pages/RunsPage'
import ComparePage, { MAX_CORRIDAS } from '../pages/ComparePage'
import RunDetailPage from '../pages/RunDetailPage'
import DocumentacionPage from '../pages/DocumentacionPage'
import ActivityTimeline from '../components/charts/ActivityTimeline'
import PreviewWithBoxes from '../components/PreviewWithBoxes'
import type { TraceFrame } from '../types'

const json = (body: unknown, headers: Record<string, string> = {}, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json', ...headers } })

afterEach(() => { cleanup(); vi.unstubAllGlobals() })

function http(responder: (url: URL) => Response | undefined) {
  const urls: URL[] = []
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
    const url = new URL(String(input), 'http://localhost')
    urls.push(url)
    return responder(url) ?? json({ detail: 'sin fixture' }, {}, 404)
  }))
  return urls
}

describe('Corridas agrupadas: expansión y subtabla accesibles', () => {
  const grupo = {
    result_id: 'clip_bench/t1', titulo: 'Línea de base', etiqueta: 't1', clase: 'resultado',
    n_runs: 1, last_run_at: '2026-09-09T09:00:00Z', paso: 3, cifra: '0,789', cifra_label: 'F1',
    cifra_origen: 'citada', fuente: 'results/clip_bench/index.md',
  }
  const corrida = {
    run_id: 'run_20260909_090000_a', name: 'Inspección', status: 'succeeded', source_type: 'video_file',
    total_detections: 4, created_at: '2026-09-09T09:00:00Z',
  }

  it('el grupo se abre con un botón con aria-expanded; la subtabla tiene sus propios encabezados y enlaces', async () => {
    const urls = http((url) => {
      if (url.pathname === '/api/runs/grupos') return json([grupo], { 'X-Class-Counts': 'resultado=1' })
      if (url.pathname === '/api/runs') return json(url.searchParams.get('result_id') ? [corrida] : [], { 'X-Total-Count': '1' })
      if (url.pathname === '/api/target') return json({ healthy: true, ready: true, model: null })
      return undefined
    })
    render(<MemoryRouter><RunsPage /></MemoryRouter>)
    const toggle = await screen.findByRole('button', { name: 'Mostrar las corridas de Línea de base' })
    expect(toggle.getAttribute('aria-expanded')).toBe('false')
    fireEvent.click(toggle)
    const abierto = screen.getByRole('button', { name: 'Ocultar las corridas de Línea de base' })
    expect(abierto.getAttribute('aria-expanded')).toBe('true')
    const sub = document.getElementById(abierto.getAttribute('aria-controls')!)!
    const tabla = await within(sub).findByRole('table', { name: 'Corridas de Línea de base' })
    expect(within(tabla).getAllByRole('columnheader').map((h) => h.textContent))
      .toEqual(['Corrida', 'Estado', 'Fuente', 'Detecciones', 'Cuándo'])
    expect(within(tabla).getByRole('link', { name: 'Inspección' }).getAttribute('href'))
      .toBe('/runs/run_20260909_090000_a')
    // El mismo pedido al servidor que antes: las corridas de ESE resultado.
    const pedido = urls.find((u) => u.searchParams.get('result_id') === 'clip_bench/t1')!
    expect(pedido.searchParams.get('vista')).toBe('todas')
    expect(pedido.searchParams.get('page_size')).toBe('8')
  })

  it('la cifra citada dice que es citada y su fuente se abre con un botón', async () => {
    http((url) => {
      if (url.pathname === '/api/runs/grupos') return json([grupo], { 'X-Class-Counts': 'resultado=1' })
      if (url.pathname === '/api/runs') return json([], { 'X-Total-Count': '0' })
      return undefined
    })
    render(<MemoryRouter><RunsPage /></MemoryRouter>)
    expect(await screen.findByText('citada')).toBeTruthy()
    const boton = screen.getByRole('button', { name: 'Fuente de la cifra 0,789' })
    expect(boton.getAttribute('aria-expanded')).toBe('false')
    fireEvent.click(boton)
    expect(screen.getByRole('status').textContent).toBe('results/clip_bench/index.md')
  })
})

describe('Comparar: el límite del servidor', () => {
  it(`deja elegir hasta ${MAX_CORRIDAS} y explica por qué no una más; desmarcar habilita de nuevo`, async () => {
    const corridas = Array.from({ length: MAX_CORRIDAS + 1 }, (_, i) => ({
      run_id: `run_${i}`, name: `Corrida ${i}`, status: 'succeeded', evaluated: true, bench_split: 'b',
    }))
    http((url) => {
      if (url.pathname === '/api/runs') return json(corridas, { 'X-Total-Count': String(corridas.length) })
      if (url.pathname === '/api/compare') return json({ runs: [], classes: [], ap_by_class: {}, skipped: [] })
      return undefined
    })
    render(<MemoryRouter><ComparePage /></MemoryRouter>)
    for (let i = 0; i < MAX_CORRIDAS; i++) {
      fireEvent.click(await screen.findByRole('checkbox', { name: `Corrida ${i}` }))
    }
    const novena = screen.getByRole('checkbox', { name: `Corrida ${MAX_CORRIDAS}` }) as HTMLInputElement
    expect(novena.disabled).toBe(true)
    expect(screen.getByText(/el máximo que compara el servidor/)).toBeTruthy()
    // La casilla bloqueada dice por qué, además de su modelo y conjunto.
    const descripcion = novena.getAttribute('aria-describedby')!.split(' ')
      .map((id) => document.getElementById(id)?.textContent ?? '').join(' ')
    expect(descripcion).toMatch(/b · .*el máximo que compara el servidor/)
    fireEvent.click(screen.getByRole('checkbox', { name: 'Corrida 0' }))
    expect(novena.disabled).toBe(false)
  })

  it('con una sola elegida pide otra, sin presentar un resultado vacío', async () => {
    http((url) => (url.pathname === '/api/runs'
      ? json([{ run_id: 'a', name: 'A', status: 'succeeded', evaluated: true }, { run_id: 'b', name: 'B', status: 'succeeded', evaluated: true }], { 'X-Total-Count': '2' })
      : undefined))
    render(<MemoryRouter><ComparePage /></MemoryRouter>)
    fireEvent.click(await screen.findByRole('checkbox', { name: 'A' }))
    expect(screen.getByText('Elegí otra corrida para comparar')).toBeTruthy()
  })

  it('sin corridas evaluadas da una sola explicación y lleva a Corridas', async () => {
    http((url) => (url.pathname === '/api/runs' ? json([{ run_id: 'a', status: 'succeeded', evaluated: false }], { 'X-Total-Count': '1' }) : undefined))
    render(<MemoryRouter><ComparePage /></MemoryRouter>)
    expect(await screen.findByText('Todavía no hay corridas evaluadas')).toBeTruthy()
    expect(screen.getByRole('link', { name: 'Ir a Corridas' }).getAttribute('href')).toBe('/corridas')
    expect(screen.queryByText('Elegí al menos dos corridas')).toBeNull()
  })
})

describe('Evidencia: la navegación conserva su contexto', () => {
  const rid = 'clip_bench/con/barras'
  const resultado = {
    result_id: rid, index: 'clip_bench', etiqueta: 'e', titulo: 'Título', reclamo: null,
    n_runs: 26, n_rows: 26, roles: { campaign_media: 26, rol_que_no_conocemos: 1 }, documents: [], source_refs: [], metricas: null,
  }
  const fila = (run_id: string) => ({
    result_id: rid, run_id, plane: 'media-plane', status: 'copied', role: 'rol_que_no_conocemos',
    source_ref: 's', artifact_path: 'a', tiene_detalle_vivo: true, reason: null,
  })

  it('paginar cambia sólo la página: id con barras y paso quedan; los enlaces a corridas llevan el paso', async () => {
    const urls = http((url) => {
      if (url.pathname === '/api/evidencia/resultado') {
        const page = Number(url.searchParams.get('page'))
        return json({ available: true, message: null, result: resultado, items: [fila(page === 1 ? 'm1' : 'm26')], total: 26, page, page_size: 25 })
      }
      return undefined
    })
    render(<MemoryRouter initialEntries={[`/evidencia/resultado?${new URLSearchParams({ id: rid, paso: '3' })}`]}><App /></MemoryRouter>)
    const m1 = await screen.findByRole('link', { name: 'm1' })
    expect(new URL(m1.getAttribute('href')!, 'http://x').searchParams.get('paso')).toBe('3')
    fireEvent.click(screen.getByRole('button', { name: 'Siguiente' }))
    const m26 = await screen.findByRole('link', { name: 'm26' })
    const destino = new URL(m26.getAttribute('href')!, 'http://x').searchParams
    expect(destino.get('id')).toBe(rid)
    expect(destino.get('paso')).toBe('3')
    // La miga del paso sigue: la página no se llevó el `paso`.
    expect(screen.getByRole('navigation', { name: 'Ruta de navegación' }).textContent).toContain('Paso 3')
    const pedidos = urls.filter((u) => u.pathname === '/api/evidencia/resultado')
    const pedido = pedidos[pedidos.length - 1]
    expect(pedido.searchParams.get('id')).toBe(rid)
    expect(pedido.searchParams.get('page')).toBe('2')
    // Un rol desconocido conserva su literal.
    expect(screen.getAllByText('rol_que_no_conocemos').length).toBeGreaterThan(0)
  })
})

const cuadros = (n: number): TraceFrame[] =>
  Array.from({ length: n }, (_, i) => ({
    frame_index: i, unit_id: `frame_${i}`, timestamp_ms: i * 100, detections: [],
    control: 'received', progress: [], alert: [],
  })) as TraceFrame[]

describe('Línea de tiempo: control temporal y correspondencia con la lista', () => {
  it('el control deslizante elige el mismo cuadro que el click, con el teclado', () => {
    const onSelect = vi.fn()
    render(<ActivityTimeline frames={cuadros(10)} selected={2} onSelect={onSelect} />)
    const control = screen.getByRole('slider', { name: 'Cuadro elegido en la línea de tiempo' }) as HTMLInputElement
    expect(control.value).toBe('2')
    expect(control.getAttribute('aria-valuetext')).toMatch(/cuadro 2/)
    fireEvent.change(control, { target: { value: '7' } })
    expect(onSelect).toHaveBeenCalledWith(7, 7)
  })

  it('los tres gráficos y el control comparten la misma columna', () => {
    const { container } = render(<ActivityTimeline frames={cuadros(10)} selected={3} />)
    const plots = container.querySelectorAll('.eo-timeline__plot')
    expect(plots).toHaveLength(3)
    // Un cursor por gráfico, todos en la misma posición: el overlay no ocupa
    // una celda de la grilla.
    const cursores = [...container.querySelectorAll<HTMLElement>('.eo-timeline__cursor')]
    expect(cursores.map((c) => c.style.left)).toEqual(['30%', '30%', '30%'])
    expect(container.querySelector('.eo-timeline__lanes > .eo-timeline__cursor')).toBeNull()
  })

  it('elegir un cuadro en la lista (o con sus flechas) mueve el cursor de la línea de tiempo', async () => {
    const frames = cuadros(4).map((f) => ({ ...f, active_patterns: [] }))
    http((url) => {
      if (url.pathname === '/api/runs/r1') return json({ run_id: 'r1', status: 'succeeded', live: false })
      if (url.pathname === '/api/runs/r1/trace/index') return json({
        media_run_id: 'r1', control_run_id: null, topology: null, control_error: null,
        totals: { frames: 4, detections: 0, dropped_by_reason: {}, alerts: 0, received: 4, not_received: 0 },
        total: 4, unit_id: frames.map((f) => f.unit_id), frame_index: frames.map((f) => f.frame_index),
        timestamp_ms: frames.map((f) => f.timestamp_ms), detections: [0, 0, 0, 0],
        control_state: ['received', 'received', 'received', 'received'], alert: [0, 0, 0, 0],
      })
      if (url.pathname === '/api/runs/r1/trace') return json({
        media_run_id: 'r1', control_run_id: null, topology: null, control_error: null,
        totals: { frames: 4, detections: 0, dropped_by_reason: {}, alerts: 0, received: 4, not_received: 0 },
        page: 1, page_size: 200, total: 4, frames,
      })
      if (url.pathname === '/api/runs/r1/artifacts') return json({ run_id: 'r1', items: [] })
      if (url.pathname === '/api/runs/r1/comparison') return json({ run_id: 'r1', previous_run_id: null, matched_on: [], deltas: {} })
      return undefined
    })
    const { container } = render(
      <MemoryRouter initialEntries={['/runs/r1']}><Routes><Route path="/runs/:id" element={<RunDetailPage />} /></Routes></MemoryRouter>,
    )
    const lista = await screen.findByRole('listbox', { name: 'Cuadros de la traza' })
    await waitFor(() => expect(container.querySelector('.eo-timeline__cursor')).toBeTruthy())
    fireEvent.click(within(lista).getByRole('option', { name: /frame_2/ }))
    await waitFor(() => expect((container.querySelector('.eo-timeline__cursor') as HTMLElement).style.left).toBe('50%'))
    // La lista es un listbox de una sola parada: las flechas avanzan.
    expect(lista.tabIndex).toBe(0)
    fireEvent.keyDown(lista, { key: 'ArrowDown' })
    await waitFor(() => expect((container.querySelector('.eo-timeline__cursor') as HTMLElement).style.left).toBe('75%'))
    expect(document.getElementById(lista.getAttribute('aria-activedescendant')!)?.textContent).toContain('frame_3')
    // Y la línea de tiempo lleva la lista al cuadro.
    fireEvent.change(screen.getByRole('slider'), { target: { value: '1' } })
    await waitFor(() => expect(within(lista).getByRole('option', { selected: true }).textContent).toContain('frame_1'))
  })

  it('sin conjunto de evaluación, la pestaña Evaluación lo explica en vez de quedar en blanco', async () => {
    http((url) => {
      if (url.pathname === '/api/runs/r2') return json({ run_id: 'r2', status: 'succeeded', live: false, bench_split: null })
      if (url.pathname.startsWith('/api/runs/r2/')) return json({ detail: 'x' }, {}, 404)
      return undefined
    })
    render(<MemoryRouter initialEntries={['/runs/r2']}><Routes><Route path="/runs/:id" element={<RunDetailPage />} /></Routes></MemoryRouter>)
    fireEvent.click(await screen.findByRole('tab', { name: 'Evaluación' }))
    expect(screen.getByText('Esta corrida no tiene un conjunto de evaluación asociado')).toBeTruthy()
  })
})

describe('Ampliación de la vista previa', () => {
  it('abre la misma imagen con sus cajas en un diálogo, y Escape la cierra devolviendo el foco', () => {
    render(
      <PreviewWithBoxes
        src="/p.jpg" alt="Cuadro 3" zoomable
        detections={[{ label: 'person', confidence: 0.9, bbox_norm_xyxy: [0.1, 0.1, 0.5, 0.5] }]}
      />,
    )
    const ampliar = screen.getByRole('button', { name: 'Ampliar' })
    ampliar.focus()
    fireEvent.click(ampliar)
    const dialogo = screen.getByRole('dialog', { name: 'Ampliación: Cuadro 3' })
    expect(dialogo.querySelector('img')?.getAttribute('src')).toBe('/p.jpg')
    expect(dialogo.querySelectorAll('.eo-preview__box')).toHaveLength(1)
    fireEvent.keyDown(dialogo, { key: 'Escape' })
    expect(screen.queryByRole('dialog')).toBeNull()
    expect(document.activeElement).toBe(ampliar)
  })
})

describe('Documentación: enlace directo a un término', () => {
  it('abre la familia del término pedido', async () => {
    http((url) => (url.pathname === '/api/documentacion' ? json({
      available: true, message: null, titulo: 'Doc', bajada: null, metodo: [], aportes: [], colisiones: [],
      vocabulario: [
        { id: 'f1', titulo: 'Familia uno', nota: null, terminos: [{ id: 'T1', termino: 'T1', definicion: 'Def T1.', mono: false, nivel: null, result_ids: [] }] },
        { id: 'f2', titulo: 'Familia dos', nota: null, terminos: [{ id: 'T2', termino: 'T2', definicion: 'Def T2.', mono: false, nivel: null, result_ids: [] }] },
      ],
      terminos: {},
    }) : undefined))
    const { container } = render(<MemoryRouter initialEntries={['/documentacion#T2']}><DocumentacionPage /></MemoryRouter>)
    await screen.findByText('Def T2.')
    await waitFor(() => expect((container.querySelector('#familia-f2') as HTMLDetailsElement).open).toBe(true))
    expect((container.querySelector('#familia-f1') as HTMLDetailsElement).open).toBe(false)
    expect(screen.getByRole('navigation', { name: 'Índice de la documentación' })).toBeTruthy()
  })
})
