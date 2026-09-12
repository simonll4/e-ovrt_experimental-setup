import type { ComponentType } from 'react'
import {
  IconNavRuns, IconNavExperiments, IconNavCompare, IconNavPrompts,
  IconNavCatalog, IconNavEvidence, IconNavPlatform, IconNavCameras, IconNavClips,
  IconNavDocs,
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
export type NavGroup = { title: string; items: NavItem[] }

export const NAV_GROUPS: NavGroup[] = [
  {
    title: 'Trabajo',
    items: [
      // Primero del grupo a propósito: es lo que se lee ANTES que todo lo
      // demás. Sin esto, quien abre la consola por primera vez —el tribunal
      // incluido— se encuentra con nombres que hay que memorizar en vez de
      // entender.
      { to: '/documentacion', label: 'Documentación', icon: IconNavDocs },
      { to: '/evidencia', label: 'Evidencia', icon: IconNavEvidence },
      { to: '/', label: 'Corridas', icon: IconNavRuns, countKey: 'runs' },
      { to: '/experiments', label: 'Experimentos', icon: IconNavExperiments, countKey: 'experiments' },
      { to: '/compare', label: 'Comparar', icon: IconNavCompare },
    ],
  },
  {
    title: 'Definiciones',
    items: [
      { to: '/prompts', label: 'Conjuntos de prompts', short: 'Conjuntos', icon: IconNavPrompts, countKey: 'promptSets' },
      { to: '/catalog', label: 'Catálogos', icon: IconNavCatalog },
    ],
  },
  {
    title: 'Sistema',
    items: [
      { to: '/platform', label: 'Plataforma', icon: IconNavPlatform },
      { to: '/cameras', label: 'Cámaras', icon: IconNavCameras },
      { to: '/clips', label: 'Clips', icon: IconNavClips },
    ],
  },
]

// Rutas que no viven en la nav pero necesitan crumb propio.
const STANDALONE: Record<string, string> = {
  '/compose': 'Nueva corrida',
  '/experiments/new': 'Nuevo experimento',
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
  if (pathname === '/evidencia/paso') {
    const n = new URLSearchParams(search).get('n')
    return [
      { to: '/evidencia', label: 'Evidencia' },
      { to: pathname + search, label: n ? `Paso ${n}` : 'Paso' },
    ]
  }
  if (pathname === '/evidencia/respaldo') {
    return [
      { to: '/evidencia', label: 'Evidencia' },
      { to: pathname, label: 'Respaldo instrumental' },
    ]
  }
  if (pathname === '/evidencia/resultado' || pathname === '/evidencia/run') {
    const params = new URLSearchParams(search)
    const id = params.get('id')
    const pasoN = params.get('paso')
    const crumbs = [{ to: '/evidencia', label: 'Evidencia' }]
    // Sólo aparece cuando se llegó desde un paso (el query trae `paso`): no se
    // inventa el paso de origen cuando la navegación no lo trajo.
    if (pasoN) crumbs.push({ to: `/evidencia/paso?n=${pasoN}`, label: `Paso ${pasoN}` })
    if (id) crumbs.push({ to: `/evidencia/resultado?${new URLSearchParams({ id })}`, label: id })
    if (pathname === '/evidencia/run') crumbs.push({ to: pathname + search, label: params.get('run_id') ?? 'Corrida' })
    return crumbs
  }
  if (STANDALONE[pathname]) return [{ to: pathname, label: STANDALONE[pathname] }]
  const runMatch = pathname.match(/^\/runs\/(.+)$/)
  if (runMatch) {
    return [
      { to: '/', label: 'Corridas' },
      { to: pathname, label: runMatch[1] },
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
