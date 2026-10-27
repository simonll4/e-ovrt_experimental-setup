import type { ComponentType } from 'react'
import {
  IconNavRuns, IconNavExperiments, IconNavCompare, IconNavPrompts,
  IconNavCatalog, IconNavEvidence, IconNavPlatform, IconNavCameras, IconNavClips,
  IconNavDocs, IconNavTribunal, IconNavDemo,
} from './components/ui/icons'

export type NavItem = {
  to: string
  label: string
  /** Etiqueta corta para la barra lateral cuando el nombre completo no entra en
   *  sus 214 px y se corta con puntos suspensivos. El nombre completo sigue
   *  siendo `label`: va en el `title`, en el tooltip de colapsado y en las migas. */
  short?: string
  icon?: ComponentType
  countKey?: 'runs' | 'experiments' | 'promptSets'
}
export type NavGroup = {
  title: string
  items: NavItem[]
  /** Plegable y plegado por defecto (se recuerda por navegador). Se abre solo
   *  cuando la pantalla actual es uno de sus destinos. */
  colapsable?: boolean
}

/** La lista de corridas: hasta la generación 2 era la entrada (`/`); ahora la
 *  entrada es «Para el tribunal» y la lista vive acá (doc 135 §3.1). */
export const RUNS_PATH = '/corridas'

export const NAV_GROUPS: NavGroup[] = [
  {
    // Lo que ve primero quien abre la consola —el tribunal incluido—: la
    // evidencia final y la respuesta a cada observación (doc 135).
    title: 'Evidencia',
    items: [
      { to: '/', label: 'Para el tribunal', icon: IconNavTribunal },
      { to: '/resultados', label: 'Resultados', icon: IconNavEvidence },
      { to: '/demo', label: 'Demo en vivo', icon: IconNavDemo },
      { to: '/documentacion', label: 'Documentación', icon: IconNavDocs },
      { to: '/platform', label: 'Plataforma', icon: IconNavPlatform },
    ],
  },
  {
    // Lo operativo sigue existiendo, pero fuera del camino del jurado.
    title: 'Laboratorio',
    colapsable: true,
    items: [
      { to: RUNS_PATH, label: 'Corridas', icon: IconNavRuns, countKey: 'runs' },
      { to: '/experiments', label: 'Experimentos', icon: IconNavExperiments, countKey: 'experiments' },
      { to: '/compare', label: 'Comparar', icon: IconNavCompare },
      { to: '/prompts', label: 'Conjuntos de prompts', short: 'Conjuntos', icon: IconNavPrompts, countKey: 'promptSets' },
      { to: '/catalog', label: 'Catálogos', icon: IconNavCatalog },
      { to: '/cameras', label: 'Cámaras', icon: IconNavCameras },
      { to: '/clips', label: 'Clips', icon: IconNavClips },
    ],
  },
]

/** ¿La pantalla actual es uno de los destinos del grupo (o una de sus hojas)? */
export function grupoContiene(group: NavGroup, pathname: string): boolean {
  if (pathname.startsWith('/runs/') || pathname === '/compose') {
    return group.items.some((i) => i.to === RUNS_PATH)
  }
  return group.items.some((i) => i.to !== '/' && (pathname === i.to || pathname.startsWith(`${i.to}/`)))
}

/** La validación inicial: el recorrido de evidencia de la generación 1. */
export const GEN1 = { to: '/evidencia/generacion-1', label: 'Validación inicial (generación 1)' }

// Rutas que no viven en la nav pero necesitan crumb propio.
const STANDALONE: Record<string, string> = {
  '/compose': 'Nueva corrida',
  '/experiments/new': 'Nuevo experimento',
  // La demo en vivo va a pantalla completa (sin armazón ni migas visibles), pero
  // su destino se declara igual: no vive en NAV_GROUPS (spec 2026-10-23 §6.5).
  '/demo': 'Demo en vivo',
}

export function crumbsFor(pathname: string, search = ''): NavItem[] {
  // Declarada, no resuelta por el barrido de `NAV_GROUPS` del final: a
  // `/documentacion` se llega desde CUALQUIER pantalla —cada término marcado
  // enlaza a su entrada— así que su miga no puede depender de que el ítem siga
  // estando en la barra lateral. Es el único destino con esa propiedad.
  if (pathname === '/documentacion') {
    return [{ to: '/documentacion', label: 'Documentación' }]
  }
  // El nivel intermedio del recorrido: sin esto, `crumbsFor` caía al `[]` del
  // final y las migas quedaban vacías justo en el paso del argumento, que es
  // el corazón de la pantalla de evidencia.
  // La validación inicial (generación 1) vive en dos URLs: la histórica y la nueva.
  if (pathname === '/evidencia' || pathname === GEN1.to) return [GEN1]
  if (pathname === '/evidencia/paso') {
    const n = new URLSearchParams(search).get('n')
    return [
      GEN1,
      { to: pathname + search, label: n ? `Paso ${n}` : 'Paso' },
    ]
  }
  if (pathname === '/evidencia/respaldo') {
    return [
      GEN1,
      { to: pathname, label: 'Respaldo instrumental' },
    ]
  }
  if (pathname === '/evidencia/resultado' || pathname === '/evidencia/run') {
    const params = new URLSearchParams(search)
    const id = params.get('id')
    const pasoN = params.get('paso')
    const crumbs = [GEN1]
    // Sólo aparece cuando se llegó desde un paso (el query trae `paso`): no se
    // inventa el paso de origen cuando la navegación no lo trajo.
    if (pasoN) crumbs.push({ to: `/evidencia/paso?n=${pasoN}`, label: `Paso ${pasoN}` })
    // El resultado conserva el paso de origen: volver a él desde la corrida no
    // pierde la cadena Evidencia > Paso N > resultado.
    if (id) crumbs.push({ to: `/evidencia/resultado?${new URLSearchParams(pasoN ? { id, paso: pasoN } : { id })}`, label: id })
    if (pathname === '/evidencia/run') crumbs.push({ to: pathname + search, label: params.get('run_id') ?? 'Corrida' })
    return crumbs
  }
  if (STANDALONE[pathname]) return [{ to: pathname, label: STANDALONE[pathname] }]
  const demoMatch = pathname.match(/^\/demo\/resultado\/(.+)$/)
  if (demoMatch) {
    return [
      { to: '/demo', label: STANDALONE['/demo'] },
      { to: pathname, label: demoMatch[1] },
    ]
  }
  const runMatch = pathname.match(/^\/runs\/(.+)$/)
  if (runMatch) {
    return [
      { to: RUNS_PATH, label: 'Corridas' },
      { to: pathname, label: runMatch[1] },
    ]
  }
  const resultadoMatch = pathname.match(/^\/resultados\/(.+)$/)
  if (resultadoMatch) {
    return [
      { to: '/resultados', label: 'Resultados' },
      { to: pathname, label: resultadoMatch[1] },
    ]
  }
  const expMatch = pathname.match(/^\/experiments\/(.+)$/)
  if (expMatch) {
    return [
      { to: '/experiments', label: 'Experimentos' },
      { to: pathname, label: expMatch[1] },
    ]
  }
  for (const group of NAV_GROUPS) {
    const item = group.items.find((i) => i.to === pathname)
    if (item) return [{ to: item.to, label: item.label }]
  }
  return []
}
