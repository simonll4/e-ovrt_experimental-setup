import type { ComponentType } from 'react'
import {
  IconNavArchivo, IconNavCameras, IconNavClips, IconNavDemo, IconNavDocs, IconNavEvidence, IconNavInicio,
  IconNavPlatform,
} from './components/ui/icons'
import { nombreLlano } from './vocabulario'

export type NavItem = {
  to: string
  label: string
  /** Etiqueta corta para la barra lateral cuando el nombre completo no entra en
   *  sus 214 px y se corta con puntos suspensivos. El nombre completo sigue
   *  siendo `label`: va en el `title`, en el tooltip de colapsado y en las migas. */
  short?: string
  icon?: ComponentType
  /** Pantallas que no son su dirección pero cuentan como estar en el destino (la página de una
   *  pregunta está «en» Inicio; el resultado de una toma, «en» Tomas en vivo). */
  tambien?: (pathname: string) => boolean
  /** Solo la dirección exacta: «Demo con cámara» no se enciende en las tomas guardadas. */
  exacta?: boolean
}
export type NavGroup = {
  title: string
  items: NavItem[]
}

/** La lista de corridas. Sale de la navegación (plan de la consola, §3) pero sigue respondiendo. */
export const RUNS_PATH = '/corridas'

/** La página de una pregunta: `/preguntas/<id>`. Las siete no se listan en la barra (§3). */
export const PREGUNTA_PATH = '/preguntas'

/** «Correr un clip» (§7.2): un clip del rodaje por la cadena completa. */
export const CORRER_CLIP_PATH = '/correr-clip'

/** La navegación del plan de la consola de evidencia (§3): Evidencia, Demostrar y, al pie, Archivo. */
export const NAV_GROUPS: NavGroup[] = [
  {
    title: 'Evidencia',
    items: [
      { to: '/', label: 'Inicio', icon: IconNavInicio, tambien: (p) => p.startsWith(`${PREGUNTA_PATH}/`) },
      { to: '/resultados', label: 'Pruebas', icon: IconNavEvidence },
      { to: '/demo/sesiones', label: 'Tomas en vivo', icon: IconNavDemo, tambien: (p) => p.startsWith('/demo/resultado/') },
      { to: '/documentacion', label: 'Cómo leer', icon: IconNavDocs },
    ],
  },
  {
    title: 'Demostrar',
    items: [
      { to: '/platform', label: 'Plataforma', icon: IconNavPlatform },
      { to: CORRER_CLIP_PATH, label: 'Correr un clip', icon: IconNavClips },
      { to: '/demo', label: 'Demo con cámara', icon: IconNavCameras, exacta: true },
    ],
  },
]

/** La etapa de desarrollo: el recorrido de evidencia de antes, de solo lectura. Va al pie (§5). */
export const GEN1 = { to: '/archivo', label: 'Archivo' }
/** Las URLs anteriores del Archivo: siguen respondiendo para no romper enlaces guardados, pero la interfaz ya no
 *  las usa (la barra de direcciones no dice «generación», §4). */
export const ARCHIVO_ANTES = ['/evidencia', '/evidencia/generacion-1'] as const
export const NAV_ARCHIVO: NavItem = {
  to: GEN1.to, label: GEN1.label, icon: IconNavArchivo, tambien: (p) => p === '/evidencia' || p.startsWith('/evidencia/'),
}

/** ¿La pantalla actual es este destino? */
export function destinoActivo(item: NavItem, pathname: string): boolean {
  if (item.tambien?.(pathname)) return true
  if (item.to === '/' || item.exacta) return pathname === item.to
  return pathname === item.to || pathname.startsWith(`${item.to}/`)
}

/** Las pantallas de laboratorio: fuera de la navegación (§3), con su miga, hasta limpiarlas después
 *  de la defensa. */
const LABORATORIO: Record<string, string> = {
  [RUNS_PATH]: 'Corridas',
  '/experiments': 'Experimentos',
  '/compare': 'Comparar',
  '/prompts': 'Conjuntos de prompts',
  '/catalog': 'Catálogos',
  '/cameras': 'Cámaras',
  '/clips': 'Clips',
}

// Rutas que no viven en la nav pero necesitan crumb propio.
const STANDALONE: Record<string, string> = {
  ...LABORATORIO,
  '/compose': 'Nueva corrida',
  '/experiments/new': 'Nuevo experimento',
}

export function crumbsFor(pathname: string, search = ''): NavItem[] {
  // Declarada, no resuelta por el barrido de `NAV_GROUPS` del final: a
  // `/documentacion` se llega desde CUALQUIER pantalla —cada término marcado
  // enlaza a su entrada—, así que su miga no puede depender de la barra lateral.
  if (pathname === '/documentacion') {
    return [{ to: '/documentacion', label: 'Cómo leer' }]
  }
  if (pathname.startsWith(`${PREGUNTA_PATH}/`)) {
    // El título de la pregunta lo pone Breadcrumbs cuando la vista ya cargó; acá queda su id.
    return [{ to: '/', label: 'Inicio' }, { to: pathname, label: pathname.slice(PREGUNTA_PATH.length + 1) }]
  }
  // El Archivo vive en su URL y en las dos anteriores.
  if (pathname === GEN1.to || (ARCHIVO_ANTES as readonly string[]).includes(pathname)) return [GEN1]
  if (pathname === '/evidencia/paso') {
    const n = new URLSearchParams(search).get('n')
    return [GEN1, { to: pathname + search, label: n ? `Paso ${n}` : 'Paso' }]
  }
  if (pathname === '/evidencia/respaldo') {
    return [GEN1, { to: pathname, label: 'Respaldo instrumental' }]
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
    // pierde la cadena Archivo > Paso N > resultado.
    if (id) crumbs.push({ to: `/evidencia/resultado?${new URLSearchParams(pasoN ? { id, paso: pasoN } : { id })}`, label: id })
    if (pathname === '/evidencia/run') crumbs.push({ to: pathname + search, label: params.get('run_id') ?? 'Corrida' })
    return crumbs
  }
  if (STANDALONE[pathname]) return [{ to: pathname, label: STANDALONE[pathname] }]
  const demoMatch = pathname.match(/^\/demo\/resultado\/(.+)$/)
  if (demoMatch) {
    return [
      { to: '/demo/sesiones', label: 'Tomas en vivo' },
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
      { to: '/resultados', label: 'Pruebas' },
      { to: pathname, label: nombreLlano(resultadoMatch[1]) ?? resultadoMatch[1] },
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
