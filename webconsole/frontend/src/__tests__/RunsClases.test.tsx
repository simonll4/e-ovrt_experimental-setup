import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { cleanup, fireEvent, render, screen } from '../test-utils'
import App from '../App'

/** Los dos grupos comparten las MISMAS 34 corridas (una corrida que es
 *  evidencia de dos resultados está en los dos grupos). Sumar `n_runs` da 68;
 *  las corridas distintas son 34. Es la trampa de C-1 en miniatura. */
type Grupo = {
  result_id: string | null; titulo: string | null; etiqueta: string | null
  clase: string; n_runs: number; last_run_at: string
  // La cifra del PASO que cita al resultado (no la del resultado). Opcionales
  // porque la mayoría de estos casos no la ejercita; el que sí, la manda entera.
  paso?: number | null; cifra?: string | null; cifra_label?: string | null
  cifra_origen?: 'leida' | 'citada' | null; fuente?: string | null
}
const GRUPOS: Grupo[] = [
  { result_id: 'clip_bench/t1', titulo: 'Línea de base del Nivel B', etiqueta: 't1',
    clase: 'resultado', n_runs: 34, last_run_at: '2026-08-03T22:33:23Z' },
  { result_id: 'clip_bench/g1', titulo: null, etiqueta: 'g1',
    clase: 'resultado', n_runs: 34, last_run_at: '2026-08-04T10:00:00Z' },
  { result_id: 'realtime/claqueta_reloj_externo', titulo: 'La claqueta con reloj externo',
    etiqueta: 'claqueta reloj externo',
    clase: 'instrumento', n_runs: 4, last_run_at: '2026-08-05T10:00:00Z' },
]
/** Lo que devuelve el endpoint en cada test: por defecto los tres de arriba. */
let grupos: Grupo[]

/** `sin_cabeceras` reproduce una respuesta que no las manda (proxy que las
 *  filtra, fixture vieja); las otras dos degradan UNO de los dos archivos de
 *  los que depende toda clasificación de esta pantalla. */
type Variante = 'completo' | 'sin_cabeceras' | 'registro_ausente' | 'sin_taxonomia'
  | 'taxonomia_parcial'
/** `X-Clasificacion-Roles` = "roles sin clase / roles del registro". El caso
 *  completo es 0 de 21, que es el del repo hoy. */
const ROLES: Record<Variante, string> = {
  completo: '0/21', sin_cabeceras: '0/21', registro_ausente: '0/0',
  sin_taxonomia: '21/21', taxonomia_parcial: '20/21',
}
let variante: Variante
let urls: URL[]

beforeEach(() => {
  urls = []
  variante = 'completo'
  grupos = GRUPOS
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
    const url = new URL(String(input), 'http://localhost'); urls.push(url)
    if (url.pathname === '/api/runs/grupos') {
      const headers: Record<string, string> = {}
      if (variante !== 'sin_cabeceras') {
        headers['X-Evidence-Available'] = variante === 'registro_ausente' ? 'false' : 'true'
        headers['X-Clasificacion-Available'] = variante === 'sin_taxonomia' ? 'false' : 'true'
        headers['X-Clasificacion-Roles'] = ROLES[variante]
        headers['X-Class-Counts'] =
          'resultado=34,instrumento=4,ensayo=0,plataforma=0,sin_clasificar=0'
      }
      const clase = url.searchParams.get('clase')
      const filas = clase ? grupos.filter((g) => g.clase === clase) : grupos
      return new Response(JSON.stringify(filas), { headers })
    }
    if (url.pathname === '/api/runs') {
      return new Response(JSON.stringify([]), { headers: { 'X-Total-Count': '38' } })
    }
    return new Response('{}')
  }))
})
// El resto del archivo de tests sí llama `afterEach(cleanup)`: sin esto el DOM
// de un `it()` se acumula sobre el del siguiente (misma función `App`, mismo
// documento) y "Línea de base del Nivel B" deja de ser un match único.
afterEach(() => { cleanup(); vi.unstubAllGlobals() })

const montar = () => render(<MemoryRouter initialEntries={['/']}><App /></MemoryRouter>)

it('arranca agrupada por resultado: pide los grupos, no las 472 filas', async () => {
  montar()
  expect(await screen.findByText('Línea de base del Nivel B')).toBeTruthy()
  expect(urls.some((u) => u.pathname === '/api/runs/grupos')).toBe(true)
})

it('el chip de clase filtra del lado del servidor', async () => {
  montar()
  fireEvent.click(await screen.findByRole('button', { name: /Instrumento/ }))
  await screen.findByText('La claqueta con reloj externo')
  expect(urls.some((u) => u.searchParams.get('clase') === 'instrumento')).toBe(true)
})

it('expandir un grupo pide sólo las corridas de ese resultado', async () => {
  montar()
  fireEvent.click(await screen.findByText('Línea de base del Nivel B'))
  await vi.waitFor(() => expect(
    urls.some((u) => u.searchParams.get('result_id') === 'clip_bench/t1')).toBe(true))
})

it('el chip cuenta corridas distintas (la cabecera), no la suma de citaciones', async () => {
  // C-1: sumando `n_runs` el chip decía 68 —más que el total de la pantalla—
  // porque las mismas 34 corridas están citadas por dos resultados.
  montar()
  const chip = await screen.findByRole('button', { name: /^Resultado 34$/ })
  expect(chip).toBeTruthy()
  expect(screen.queryByRole('button', { name: /Resultado 68/ })).toBeNull()
})

it('sin la cabecera de conteos no dibuja chips: no los inventa', async () => {
  variante = 'sin_cabeceras'
  montar()
  await screen.findByText('Línea de base del Nivel B')
  expect(screen.queryByRole('group', { name: 'Filtrar por clase' })).toBeNull()
})

it('declara el registro ausente en vez de afirmar una clasificación', async () => {
  // C-3: sin el archivo la pantalla decía "472 corridas · agrupadas en 1
  // resultados de respaldo" con chip "Fuera del registro 472", sin una sola
  // advertencia — una frase perfecta construida entera sobre un archivo ausente.
  variante = 'registro_ausente'
  montar()
  const banner = (await screen.findByText(/Registro de evidencia no disponible/)).closest('.eo-banner')
  // El CUERPO, no sólo el titular: desde R-31 este flag también dispara con
  // los cuatro CSV presentes y cero filas, así que el banner no puede afirmar
  // que el archivo no está, ni mandar a restaurar del backup a secas.
  expect(banner?.textContent).toMatch(/no se encontró, o está presente y no trae una sola fila/)
  expect(banner?.textContent).toMatch(/Si falta, restauralo.*si está, regeneralo/)
  expect(banner?.textContent).not.toMatch(/no se encontró\. Restauralo/)
})

it('declara la taxonomía ausente aunque el registro sí esté', async () => {
  variante = 'sin_taxonomia'
  montar()
  const banner = (await screen.findByText(/Taxonomía de clases no disponible/)).closest('.eo-banner')
  // Mismo motivo: el flag ya no significa `is_file()`, así que el cuerpo no
  // puede decir «falta el archivo» — los dos modos de falla que el backend
  // fabrica en sus tests son con el archivo PRESENTE.
  expect(banner?.textContent).toMatch(/no está, o está y no declara ningún rol/)
  expect(banner?.textContent).not.toMatch(/pero falta results\/evidence-vista/)
})

it('declara la clasificación PARCIAL, que ningún booleano distingue', async () => {
  // Con 20 de 21 roles sin clase la cabecera dice `true` y no había banner:
  // las corridas de esos roles se mostraban «Fuera del registro» sin que nada
  // dijera que es por falta de declaración.
  variante = 'taxonomia_parcial'
  montar()
  const banner = (await screen.findByText(/Clasificación incompleta/)).closest('.eo-banner')
  expect(banner?.textContent).toMatch(/20 de 21 roles sin clasificar/)
  // El titular es un conteo medido; la explicación NO es universal: una corrida
  // con dos roles toma la MÁS FUERTE, así que un rol sin clasificar puede quedar
  // tapado por otro que sí lo está (49 corridas con más de un rol hoy).
  expect(banner?.textContent).toMatch(/Puede haber corridas que se muestren/)
  expect(banner?.textContent).not.toMatch(/Las corridas de esos roles se muestran/)
})

it('con la clasificación completa no dice nada de los roles', async () => {
  montar()
  await screen.findByText('Línea de base del Nivel B')
  expect(screen.queryByText(/Clasificación incompleta/)).toBeNull()
})

it('no advierte nada cuando los dos archivos están', async () => {
  montar()
  await screen.findByText('Línea de base del Nivel B')
  expect(screen.queryByText(/no disponible/)).toBeNull()
})

it('un grupo sin título usa la etiqueta del backend, no una derivada acá', async () => {
  montar()
  expect(await screen.findByText('g1')).toBeTruthy()
})

it('sin título NI etiqueta muestra el result_id, no lo declara fuera del registro', async () => {
  // R-30: la cadena `titulo ?? etiqueta ?? 'Fuera del registro de evidencia'`
  // convertía la AUSENCIA de dos campos editoriales en la afirmación negativa
  // más fuerte de la pantalla — para un grupo que sí está en el registro y que
  // imprime su `result_id` dos líneas más abajo, contradiciéndola. El
  // disparador real es un despliegue desincronizado o un payload cacheado.
  grupos = [{ ...GRUPOS[0], titulo: null, etiqueta: null }]
  montar()
  expect(await screen.findAllByText('clip_bench/t1')).toHaveLength(2)
  expect(screen.queryByText('Fuera del registro de evidencia')).toBeNull()
})

it('sólo declara fuera del registro al grupo que no cita ningún resultado', async () => {
  grupos = [{ ...GRUPOS[0], result_id: null, titulo: null, etiqueta: null }]
  montar()
  expect(await screen.findByText('Fuera del registro de evidencia')).toBeTruthy()
  expect(screen.getByText('sin resultado citado')).toBeTruthy()
})

it('la cifra de una fila se declara DEL PASO, no del resultado de esa fila', async () => {
  // El modo de falla que este test existe para atajar: `paso_de` le cuelga a
  // TODOS los resultados de un paso la misma cifra y el mismo rótulo. En la
  // fila de NA1 eso imprimía «precision de E-DIR (veto < 0,5) 0,146» — un
  // número que es de D1, correcto en sí y con el dueño equivocado. Es el mismo
  // modo de falla que la tarjeta de H1, y el anti-fraude NO lo ataja: busca la
  // cifra cruzada entre los 17 metrics.json, no en el del resultado que la
  // muestra. La única defensa es que la pantalla diga de quién es.
  grupos = [{
    ...GRUPOS[0],
    result_id: 'bench_nivel_a/na1',
    titulo: 'Estado por persona sobre video (NA1)',
    etiqueta: 'na1',
    paso: 2,
    cifra: '0,146',
    cifra_label: 'precision de E-DIR (veto < 0,5)',
    cifra_origen: 'leida',
    fuente: null,
  }]
  montar()
  await screen.findByText('Estado por persona sobre video (NA1)')
  // El rótulo lleva el paso pegado: la celda se entiende sola, aunque se la
  // lea fuera de la tabla.
  expect(screen.getByText('Paso 2 — precision de E-DIR (veto < 0,5)')).toBeTruthy()
  // Y el rótulo pelado, el que atribuía el número a NA1, ya no existe.
  expect(screen.queryByText('precision de E-DIR (veto < 0,5)')).toBeNull()
  // La columna también lo dice, para quien lee de arriba hacia abajo.
  expect(screen.getByRole('columnheader', { name: 'Cifra del paso' })).toBeTruthy()
})

it('un grupo sin paso no inventa un rótulo de paso', async () => {
  grupos = [GRUPOS[2]]
  montar()
  await screen.findByText('La claqueta con reloj externo')
  expect(screen.getByText('sin cifra reportada')).toBeTruthy()
  expect(screen.queryByText(/^Paso /)).toBeNull()
})
