import type { ComponentType } from 'react'
import {
  IconNavRuns, IconNavExperiments, IconNavCompare, IconNavPrompts,
  IconNavCatalog, IconNavPlatform, IconNavCameras, IconNavClips,
} from './components/ui/icons'

export type NavItem = {
  to: string
  label: string
  icon?: ComponentType
  countKey?: 'runs' | 'experiments' | 'promptSets'
}
export type NavGroup = { title: string; items: NavItem[] }

export const NAV_GROUPS: NavGroup[] = [
  {
    title: 'Trabajo',
    items: [
      { to: '/', label: 'Corridas', icon: IconNavRuns, countKey: 'runs' },
      { to: '/experiments', label: 'Experimentos', icon: IconNavExperiments, countKey: 'experiments' },
      { to: '/compare', label: 'Comparar', icon: IconNavCompare },
    ],
  },
  {
    title: 'Definiciones',
    items: [
      { to: '/prompts', label: 'Conjuntos de prompts', icon: IconNavPrompts, countKey: 'promptSets' },
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

export function crumbsFor(pathname: string): NavItem[] {
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
