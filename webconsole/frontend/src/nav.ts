export type NavItem = { to: string; label: string }
export type NavGroup = { title: string; items: NavItem[] }

export const NAV_GROUPS: NavGroup[] = [
  {
    title: 'Trabajo',
    items: [
      { to: '/', label: 'Corridas' },
      { to: '/experiments', label: 'Experimentos' },
      { to: '/compare', label: 'Comparar' },
    ],
  },
  {
    title: 'Definiciones',
    items: [
      { to: '/prompts', label: 'Prompt sets' },
      { to: '/catalog', label: 'Catálogos' },
    ],
  },
  {
    title: 'Sistema',
    items: [
      { to: '/platform', label: 'Plataforma' },
      { to: '/cameras', label: 'Cámaras' },
      { to: '/clips', label: 'Clips' },
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
    if (item) return [item]
  }
  return []
}
