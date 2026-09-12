/** Fábrica de claves de caché.
 *
 *  Todas las claves viven acá y no sueltas en cada hook, por una razón concreta:
 *  invalidar. Al borrar una corrida hay que refrescar el listado y los contadores
 *  de la barra lateral, pero no los catálogos ni los clips. Con las claves
 *  desperdigadas eso termina siendo un `invalidateQueries()` sin argumentos, que
 *  refetchea la aplicación entera.
 *
 *  Convención: cada recurso expone `all` (prefijo para invalidar todo lo suyo) y
 *  claves más específicas que lo tienen como prefijo. TanStack Query hace
 *  matching por prefijo, así que `invalidateQueries({ queryKey: qk.runs.all })`
 *  alcanza al listado y a todos los detalles.
 */

export const qk = {
  /** Estado del motor de detección (modelo cargado, listo). */
  target: ['target'] as const,
  /** Estado agregado de los dos motores + bloqueos para lanzar. */
  preflight: ['preflight'] as const,

  runs: {
    all: ['runs'] as const,
    /** El listado se cachea por filtros: con el filtrado del lado del servidor,
     *  cada combinación es una respuesta distinta. */
    list: (filtros?: Record<string, unknown>) =>
      filtros ? (['runs', 'list', filtros] as const) : (['runs', 'list'] as const),
    /** Los grupos por resultado (Task 7), por clase filtrada (o sin filtrar). */
    groups: (clase?: string) => ['runs', 'groups', clase ?? null] as const,
    detail: (id: string) => ['runs', 'detail', id] as const,
    trace: (id: string, pagina?: number) =>
      pagina == null ? (['runs', 'trace', id] as const) : (['runs', 'trace', id, pagina] as const),
    /** Índice de actividad de la corrida completa, para la línea de tiempo. */
    traceIndex: (id: string) => ['runs', 'traceIndex', id] as const,
    evaluation: (id: string) => ['runs', 'evaluation', id] as const,
    artifacts: (id: string) => ['runs', 'artifacts', id] as const,
  },

  compare: (ids: string[]) => ['compare', [...ids].sort()] as const,

  /** La documentación y su vocabulario. Una sola clave para las dos consumidoras
   *  —la pantalla y los términos marcados del resto de la consola— para que
   *  entre todas haya una única petición. */
  documentacion: ['documentacion'] as const,

  catalog: {
    all: ['catalog'] as const,
    promptSets: ['catalog', 'promptSets'] as const,
    experiments: ['catalog', 'experiments'] as const,
    ingestPlugins: ['catalog', 'ingestPlugins'] as const,
    datasets: ['catalog', 'datasets'] as const,
    conditions: ['catalog', 'conditions'] as const,
  },

  experiments: {
    all: ['experiments'] as const,
    manifests: ['experiments', 'manifests'] as const,
    deriveDefaults: (slug: string) => ['experiments', 'deriveDefaults', slug] as const,
    current: ['experiments', 'current'] as const,
    detail: (id: string) => ['experiments', 'detail', id] as const,
    alerts: (id: string) => ['experiments', 'alerts', id] as const,
    report: (id: string) => ['experiments', 'report', id] as const,
  },

  promptSets: {
    all: ['promptSets'] as const,
    list: ['promptSets', 'list'] as const,
    detail: (id: string) => ['promptSets', 'detail', id] as const,
  },

  cameras: {
    all: ['cameras'] as const,
    list: ['cameras', 'list'] as const,
  },

  clips: {
    all: ['clips'] as const,
    masters: ['clips', 'masters'] as const,
    list: ['clips', 'list'] as const,
  },

  platform: {
    all: ['platform'] as const,
    instances: ['platform', 'instances'] as const,
  },

  /** Estado vivo del motor de reglas (patrones activos). */
  controlCurrent: ['control', 'current'] as const,
  preview: ['preview'] as const,
  recording: ['recording'] as const,
  /** Contadores de la barra lateral: derivados, no un endpoint propio. */
  sidebarCounts: ['sidebarCounts'] as const,
} as const
