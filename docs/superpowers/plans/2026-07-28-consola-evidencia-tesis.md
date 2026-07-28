# Consola como evidencia de tesis — plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reconstruir la composición de las 4 pantallas que se muestran como evidencia en la defensa (Corridas, Detalle de corrida, Comparar, Detalle de experimento) con fidelidad al prototipo, sobre la capa de tokens/primitivas rescatada, agregando un set propio de gráficos SVG.

**Architecture:** Tres capas. La capa 0 (tokens, iconos, glosario, primitivas `ui/`, armazón) se rescata sin cambios desde `feature/webconsole-rediseno-fundacion`. La capa 1 son primitivas de gráfico nuevas en `components/charts/`, cada una con su layout como función pura testeable. La capa 2 son las 4 pantallas, reescritas en composición —no revestidas—, con todo bloque dentro de una `.card`.

**Tech Stack:** React 18 + TypeScript + Vite + react-router-dom (HashRouter) + Vitest/Testing Library. SVG a mano, sin librería de charts. Sin dependencias nuevas.

**Spec:** `docs/superpowers/specs/2026-07-28-consola-evidencia-tesis-design.md`
**Referencia visual a nivel componente:** `docs/superpowers/specs/proto-ref-01..04-*.md`
**Prototipo navegable:** `/home/simonll4/projects/rediseno-consola-eovrt/prototipo.html`

## Global Constraints

- **No commitear nunca.** `projects/CLAUDE.md` lo prohíbe explícitamente y anula la instrucción de auto-commit de las skills de superpowers. Cada tarea termina con la suite y el lint verdes, y se le informa al usuario. El `git commit` lo corre el usuario.
- **No tocar el backend.** Ni `webconsole/backend/`, ni los planos. Todo hueco se resuelve en el cliente.
- **Todo bloque de contenido va dentro de una `.card`** (`--s1` + borde `--bd`) sobre el lienzo `--bg`. Sin contención, la inversión de superficies destruye la jerarquía — es el error que hundió el intento anterior.
- **Nunca color solo.** Todo estado lleva icono + texto. Toda leyenda de gráfico lleva forma o etiqueta directa, no solo un cuadradito de color.
- **No reordenar `SERIES_COLORS`.** El orden es el mecanismo de seguridad para daltonismo, validado. Reordenar exige volver a correr el validador.
- **Identificadores nunca se traducen y van en monoespaciada**: `run_20260725_143012`, `grounding_dino`, `cr01_cr02_v2_short`, `person`, `CR-01`, nombres de archivo. Los códigos de condición se acompañan con su nombre (`CR-01 — Presencia de persona sin casco`), nunca se reemplazan.
- **Glosario obligatorio en todo texto de interfaz**: corrida, cuadro, motor de detección, motor de reglas, traza, en curso / completada / fallida, conjunto de prompts, cuadros por segundo, latencia (mediana), memoria de GPU.
- **Cifras tabulares** (`font-variant-numeric: tabular-nums`) en toda columna numérica.
- **Ningún tope silencioso.** Si algo se trunca (páginas de traza, filas), la interfaz lo dice.
- **Un solo vocabulario de tono.** `BadgeTone` en `types.ts` es `'live' | 'ok' | 'warn' | 'alert' | 'error' | 'neutral'` — verificado. **No existe `'serious'`**: el tono naranja se llama `'alert'` y mapea al token `--sr`. Las primitivas de gráfico usan ese mismo set más `'accent'` (token `--ac`). Nada de inventar un séptimo nombre.
- **Firmas reales de las primitivas rescatadas** (verificadas contra la rama, no supuestas): `Card` recibe `title`/`meta`/`className`/`children` (`meta` y `className` se le agregan en la Task 1). `PageHeader`: `title: string`, `meta?`, `actions?`. `EmptyState`: `children`, `hint?`. `Badge`: `tone`, `pulse?`, `children`. `Button`: `variant?: 'primary'|'secondary'|'danger'|'ghost'` + props nativas. `SearchInput`: `value`, `onChange`, `placeholder`, **`ariaLabel` (obligatoria)**. `SegmentedControl<T>`: `value`, `options`, `onChange`. `RowNameCell`: `title`, `subtitle?` — **no linkea**, el enlace va dentro de `title`. `InlineDeleteConfirm`: `onConfirm`, `onCancel`. `SortableHeader`: `label`, `sortKey`, `sortState`, `onSort`, `numeric?`. `PreviewWithBoxes`: `src`, `alt`, `detections`, `width?` (+ `emptyMessage?` que se agrega en la Task 9).
- Comandos: `npm test` (vitest run), `npm run build` (tsc + vite build). Directorio: `webconsole/frontend/`.

---

## Estructura de archivos

```
webconsole/frontend/src/
  components/charts/               # NUEVO — capa 1
    layout.ts                      # funciones puras: escalas, rutas, ticks
    Sparkline.tsx                  # área+línea sin ejes, para tiles KPI
    Meter.tsx                      # barra segmentada horizontal
    timeline.ts                    # layout puro de la línea de tiempo
    ActivityTimeline.tsx           # área de detecciones + carriles + cursor
    GroupedBars.tsx                # MOVIDO desde components/, + leyenda/eje
  runseries.ts                     # NUEVO — derivación de series desde la traza
  useFullTrace.ts                  # NUEVO — pagina /trace completo
  components/
    RunKpiStrip.tsx                # NUEVO — tira de 6 tiles KPI
    RunTimeline.tsx                # NUEVO — tarjeta que compone ActivityTimeline
    FrameInspector.tsx             # NUEVO — panel derecho del maestro-detalle
    ConditionProgress.tsx          # NUEVO — progreso de condiciones con Meter
  pages/
    RunsPage.tsx                   # REESCRITA
    RunDetailPage.tsx              # REESCRITA
    ComparePage.tsx                # REESCRITA
    ExperimentDetailPage.tsx       # REESCRITA
  styles/ui.css                    # crece con las clases de cada pantalla
```

Distinción entre capas 1 y 2: la primitiva no sabe qué es una corrida (recibe series ya calculadas y dibuja); la tarjeta sí (compone leyenda, eje, estado vacío y selección).

---

### Task 1: Rama nueva y rescate de la capa base

Se traen de la rama vieja **solo** los archivos de la capa 0. Las páginas revestidas **no** se traen: se reescriben en las tareas 7–10.

**Files:**
- Create (rama): `feature/webconsole-consola-tesis` desde `feature/webconsole`
- Copy desde `feature/webconsole-rediseno-fundacion`: `src/styles/tokens.css`, `src/styles/base.css`, `src/styles/ui.css`, `src/labels.ts`, `src/nav.ts`, `src/useServiceHealth.ts`, `src/useSidebarCounts.ts`, `src/components/Shell.tsx`, `src/components/ui/*`, `src/runview.ts`, `src/traceview.ts`, `src/experimentview.ts`, `src/types.ts`
- Copy tests: `src/__tests__/labels.test.ts`, `src/__tests__/ui/*`, `src/__tests__/useServiceHealth.test.ts`, `src/__tests__/useSidebarCounts.test.ts`, `src/__tests__/Shell.test.tsx`, `src/__tests__/runview.test.ts`, `src/__tests__/traceview.test.ts`

**Interfaces:**
- Produces: todo lo exportado por `src/components/ui/index.ts` (`Badge`, `Banner`, `Button`, `Card`, `EmptyState`, `ErrorBanner`, `PageHeader`, `StatTile`, `Field`, `DetChip`, `Select` + `SelectOption`, `SearchInput`, `SegmentedControl` + `SegmentedOption`, `Table`/`MonoCell`/`NumCell`/`SortableHeader`/`RowNameCell` + `SortState`, `ConditionName`, `InlineDeleteConfirm`, los `Icon*`), más `conditionLabel(code: string): string`, `CONTROL_DROP_REASONS`, `APPLICABILITY_STATUS`, `APPLICABILITY_CAUSE`, `applicabilityLabel(code, dict)`, `applyPlaneGlossary(text)` de `labels.ts`, y `useServiceHealth()`/`useSidebarCounts()`.

- [ ] **Step 1: Crear la rama desde `feature/webconsole`**

```bash
cd /home/simonll4/projects/e-ovrt_experimental-setup
git checkout feature/webconsole
git checkout -b feature/webconsole-consola-tesis
```

- [ ] **Step 2: Traer los archivos de la capa 0**

```bash
cd /home/simonll4/projects/e-ovrt_experimental-setup
B=feature/webconsole-rediseno-fundacion
F=webconsole/frontend/src
git checkout $B -- \
  $F/styles/tokens.css $F/styles/base.css $F/styles/ui.css \
  $F/labels.ts $F/nav.ts $F/useServiceHealth.ts $F/useSidebarCounts.ts \
  $F/components/Shell.tsx $F/components/ui/ \
  $F/runview.ts $F/traceview.ts $F/experimentview.ts $F/types.ts \
  $F/__tests__/labels.test.ts $F/__tests__/ui/ \
  $F/__tests__/useServiceHealth.test.ts $F/__tests__/useSidebarCounts.test.ts \
  $F/__tests__/Shell.test.tsx $F/__tests__/runview.test.ts \
  $F/__tests__/traceview.test.ts
```

- [ ] **Step 3: Correr la suite y ver qué rompe**

```bash
cd webconsole/frontend && npm test 2>&1 | tail -40
```

Esperado: **fallan** los tests de las páginas que todavía tienen el marcado viejo (`RunsPage`, `RunDetailPage`, `ComparePage`, `ExperimentDetailPage`, y las que usaban labels en inglés). Eso es correcto y esperado — esas páginas se reescriben en las tareas 7–10.

Anotá en un archivo `/tmp/claude-1000/-home-simonll4-projects/700ff69c-0e0b-4099-8475-9aa7096b69ce/scratchpad/task1-fallos.txt` la lista exacta de tests que fallan. Es el inventario de deuda que las tareas 7–10 tienen que dejar en cero.

- [ ] **Step 4: Reparar las 130 referencias a tokens borrados — la causa mecánica del "todo flotando"**

Esto es lo que hundió el intento anterior, y es medible. La rama reescribió `tokens.css` a los nombres v2 (`--s1`, `--bd`, `--tx`…) pero **dejó 130 referencias a los nombres v1 en `ui.css` y `base.css`**. Cada una resuelve a nada:

- `.eo-card { background: var(--surface) }` → sin fondo → **las tarjetas son invisibles**. Ese es el "contenido flotando en negro" de la captura, y no es una cuestión de gusto.
- `.eo-card { border: 1px solid var(--border) }` → declaración inválida → sin borde.
- `base.css: font-family: var(--font)` → la tipografía de toda la aplicación cae al default del navegador.

Medirlo antes de tocar nada:

```bash
cd /home/simonll4/projects/e-ovrt_experimental-setup/webconsole/frontend
node -e '
const fs=require("fs"),W="src/styles";
const defined=new Set([...fs.readFileSync(W+"/tokens.css","utf8").matchAll(/^\s*(--[\w-]+)\s*:/gm)].map(m=>m[1]));
let n=0; const miss=new Map();
for(const f of ["ui.css","base.css"]) for(const m of fs.readFileSync(W+"/"+f,"utf8").matchAll(/var\((--[\w-]+)/g))
  if(!defined.has(m[1])){n++; miss.set(m[1],(miss.get(m[1])||0)+1)}
console.log("referencias rotas:",n);
[...miss].sort((a,b)=>b[1]-a[1]).forEach(([k,v])=>console.log(String(v).padStart(4),k));'
```

Expected antes del arreglo: **130**. Aplicar el reemplazo con este mapeo exacto (v1 → v2), en `src/styles/ui.css` y `src/styles/base.css`:

| v1 (borrado) | v2 | | v1 (borrado) | v2 |
|---|---|---|---|---|
| `--surface` | `--s1` | | `--accent` | `--ac` |
| `--surface-raised` | `--s2` | | `--accent-hover` | `--ac-hover` |
| `--surface-emergent` | `--s3` | | `--status-live` | `--live` |
| `--surface-sunken` | `--sunken` | | `--status-ok` | `--ok` |
| `--border` | `--bd` | | `--status-warn` | `--wn` |
| `--border-strong` | `--bds` | | `--status-alert` | `--sr` |
| `--text` | `--tx` | | `--status-error` | `--er` |
| `--text-secondary` | `--tx2` | | `--status-neutral` | `--nt` |
| `--text-muted` | `--tx3` | | `--radius` | `--r` |
| `--font` | `--fs` | | `--font-mono` | `--fm` |

Ojo con el orden: reemplazar `--surface-raised` **antes** que `--surface`, y `--text-secondary`/`--text-muted` **antes** que `--text`, o el prefijo más corto se come al más largo.

```bash
cd /home/simonll4/projects/e-ovrt_experimental-setup/webconsole/frontend/src/styles
sed -i \
  -e 's/--surface-raised/--s2/g'   -e 's/--surface-emergent/--s3/g' \
  -e 's/--surface-sunken/--sunken/g' -e 's/--surface\b/--s1/g' \
  -e 's/--border-strong/--bds/g'   -e 's/--border\b/--bd/g' \
  -e 's/--text-secondary/--tx2/g'  -e 's/--text-muted/--tx3/g' \
  -e 's/var(--text)/var(--tx)/g' \
  -e 's/--accent-hover/--ac-hover/g' -e 's/var(--accent)/var(--ac)/g' \
  -e 's/--status-live/--live/g'    -e 's/--status-ok/--ok/g' \
  -e 's/--status-warn/--wn/g'      -e 's/--status-alert/--sr/g' \
  -e 's/--status-error/--er/g'     -e 's/--status-neutral/--nt/g' \
  -e 's/var(--radius)/var(--r)/g'  -e 's/var(--font-mono)/var(--fm)/g' \
  -e 's/var(--font)/var(--fs)/g' \
  ui.css base.css
```

**Cuidado**: `--text-xs`…`--text-xl` y `--space-1`…`--space-6` **sí** existen en tokens v2 (se conservaron como legacy) y no se tocan. Por eso los patrones usan `\b` o `var(--text)` completo y no `--text`.

Volver a correr el medidor. Expected: **0 referencias rotas**. Si queda alguna, es un nombre fuera del mapeo: agregarlo, no ignorarlo.

- [ ] **Step 5: Sacar las mayúsculas forzadas de los títulos**

`text-transform: uppercase` en 4 reglas de `ui.css` (líneas ~75, ~161, ~253, ~356) es lo que produce `SUMMARY`, `EVALUACIÓN DEL CONTROL-PLANE` y `POR LABEL` en las capturas. El prototipo no grita: los títulos de tarjeta van en 12 px, peso 500, color `--tx2`, en capitalización normal. Borrar las 4 declaraciones de `text-transform: uppercase` y sus `letter-spacing: .05em` acompañantes.

- [ ] **Step 6: Alinear `.eo-card` al prototipo y darle `meta` + `className`**

`Card` hoy solo acepta `title` y `children`. Las tareas 8–11 necesitan la meta a la derecha del título (el `.card > h3 .r` del prototipo) y una clase propia. Reescribir `src/components/ui/Card.tsx`:

```tsx
import type { ReactNode } from 'react'

export default function Card({ title, meta, className, children }: {
  title?: ReactNode
  meta?: ReactNode
  className?: string
  children: ReactNode
}) {
  const cls = ['eo-card', className].filter(Boolean).join(' ')
  return (
    <section className={cls}>
      {title ? (
        <h3 className="eo-card__title">
          {title}
          {meta ? <span className="eo-card__meta">{meta}</span> : null}
        </h3>
      ) : null}
      {children}
    </section>
  )
}
```

Y en `ui.css`, la tarjeta con la forma del prototipo — el título es una banda con borde inferior, y el cuerpo ya no lleva padding propio (cada contenido decide el suyo, porque una tabla densa va a sangre y un párrafo no):

```css
.eo-card {
  background: var(--s1);
  border: 1px solid var(--bd);
  border-radius: var(--rc);
  padding: 0;
  margin-bottom: 12px;
}
.eo-card__title {
  margin: 0;
  padding: 9px 12px;
  font-size: 12px;
  font-weight: 500;
  color: var(--tx2);
  border-bottom: 1px solid var(--bd);
  display: flex;
  align-items: center;
  gap: 8px;
  text-transform: none;
  letter-spacing: 0;
}
.eo-card__meta { margin-left: auto; font-weight: 400; color: var(--tx3); font-size: 11px; }
```

Al sacarle el padding a `.eo-card`, los contenidos que antes lo heredaban necesitan el suyo. Recorrer las páginas fuera de alcance y envolver el contenido suelto en `<div className="eo-card__body">` (la clase se define en la Task 10). Es un barrido mecánico: el compilador no lo detecta, la captura sí.

- [ ] **Step 7: Reparar solo lo que NO es de las 4 pantallas**

Las páginas fuera de alcance (`CamerasPage`, `CatalogPage`, `ClipsPage`, `ComposePage`, `ExperimentsPage`, `PlatformPage`, `PromptSetsPage`) y sus componentes tienen que compilar y pasar sus tests con la capa 0 nueva. Si un test falla ahí, es porque una clase CSS o un export cambió de nombre: arreglá el consumidor, no el token.

Regla: si el arreglo pide más de cambiar un nombre de clase o un import, traé también ese archivo de la rama vieja con `git checkout $B -- <ruta>`.

- [ ] **Step 8: Corregir la legibilidad de la barra lateral**

En la captura de la rama vieja los ítems de navegación quedaron ilegibles y el label "Conjuntos de prompts" se truncaba. En `src/styles/ui.css`, la regla del ítem de navegación:

```css
.eo-sidebar__nav-item {
  color: var(--tx2);          /* era --tx3: demasiado bajo sobre --s1 */
  font-size: 12.5px;
  min-width: 0;
}
.eo-sidebar__nav-item > .eo-sidebar__nav-label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.eo-sidebar__nav-item[aria-current='page'] {
  background: var(--ac-bg);
  color: var(--ac-tx);
}
```

Y en `src/nav.ts`, acortar el label que no entra: `'Conjuntos de prompts'` → `'Conjuntos'`. El nombre completo queda como `title` del ítem en `Shell.tsx`.

- [ ] **Step 9: Verificar el build, la suite y los píxeles**

```bash
cd webconsole/frontend && npm run build 2>&1 | tail -20 && npm test 2>&1 | tail -20
```

Esperado: `npm run build` PASA (compila). `npm test` falla **solo** en los tests de las 4 pantallas del inventario del Step 3. Cualquier otro fallo es deuda de esta tarea.

Y una captura, porque el arreglo de los tokens es visual y ningún test lo cubre:

```bash
S=/tmp/claude-1000/-home-simonll4-projects/700ff69c-0e0b-4099-8475-9aa7096b69ce/scratchpad
node $S/cdp-shoot.js 5173 $S/task1 "corridas=/#/"
```

La tabla tiene que leerse como una **tarjeta con fondo `#1a1a19` y borde** sobre el lienzo `#121211`. Si sigue flotando sobre el negro, quedaron referencias rotas: volvé al Step 4.

- [ ] **Step 10: NO commitear. Reportar.**

Informá al usuario: rama creada, capa 0 rescatada, las 130 referencias rotas en 0, build verde, la captura, y la lista exacta de tests que quedan rojos con la razón (esperan el marcado viejo de las 4 pantallas a reescribir).

---

### Task 2: `charts/layout.ts` y `Sparkline`

**Files:**
- Create: `src/components/charts/layout.ts`
- Create: `src/components/charts/Sparkline.tsx`
- Test: `src/__tests__/charts/layout.test.ts`

**Interfaces:**
- Produces:
  - `export interface AreaPaths { line: string; area: string }`
  - `export function areaPaths(values: Array<number | null>, width: number, height: number, pad?: number): AreaPaths`
  - `export function niceTicks(max: number, count?: number): number[]`
  - `export default function Sparkline({ values, tone, width, height }: { values: Array<number | null>; tone?: 'live' | 'ok' | 'warn' | 'alert' | 'error' | 'accent'; width?: number; height?: number })`

- [ ] **Step 1: Escribir los tests que fallan**

Crear `src/__tests__/charts/layout.test.ts`:

```ts
import { describe, expect, it } from 'vitest'
import { areaPaths, niceTicks } from '../../components/charts/layout'

describe('areaPaths', () => {
  it('devuelve rutas vacías con menos de dos valores finitos', () => {
    expect(areaPaths([], 100, 20)).toEqual({ line: '', area: '' })
    expect(areaPaths([5], 100, 20)).toEqual({ line: '', area: '' })
    expect(areaPaths([null, null], 100, 20)).toEqual({ line: '', area: '' })
  })

  it('mapea el primer y el último punto a los bordes del ancho', () => {
    const { line } = areaPaths([0, 10], 100, 20, 0)
    expect(line.startsWith('M0,')).toBe(true)
    expect(line).toContain('L100,')
  })

  it('invierte el eje Y: el valor máximo queda arriba (y menor)', () => {
    const { line } = areaPaths([0, 10], 100, 20, 0)
    const ys = [...line.matchAll(/[ML](?:[\d.]+),([\d.]+)/g)].map((m) => Number(m[1]))
    expect(ys[0]).toBeGreaterThan(ys[1])
  })

  it('una serie constante se dibuja plana a media altura, no dividiendo por cero', () => {
    const { line } = areaPaths([4, 4, 4], 100, 20, 0)
    const ys = [...line.matchAll(/[ML](?:[\d.]+),([\d.]+)/g)].map((m) => Number(m[1]))
    expect(new Set(ys).size).toBe(1)
    expect(ys[0]).toBeCloseTo(10, 5)
    expect(ys.every(Number.isFinite)).toBe(true)
  })

  it('el área cierra contra la línea base y vuelve al origen', () => {
    const { area } = areaPaths([1, 2], 100, 20, 0)
    expect(area.endsWith('Z')).toBe(true)
    expect(area).toContain('L100,20')
    expect(area).toContain('L0,20')
  })

  it('saltea los nulos sin romper la ruta', () => {
    const { line } = areaPaths([1, null, 3], 90, 20, 0)
    const pts = [...line.matchAll(/[ML]([\d.]+),([\d.]+)/g)]
    expect(pts).toHaveLength(2)
    expect(Number(pts[1][1])).toBe(90)
  })
})

describe('niceTicks', () => {
  it('devuelve marcas redondas que cubren el máximo', () => {
    expect(niceTicks(1)).toEqual([0, 0.25, 0.5, 0.75, 1])
  })

  it('el último tick nunca queda por debajo del máximo', () => {
    for (const max of [0.37, 3, 7, 42, 137, 1468]) {
      const ticks = niceTicks(max)
      expect(ticks[ticks.length - 1]).toBeGreaterThanOrEqual(max)
      expect(ticks[0]).toBe(0)
    }
  })

  it('no devuelve NaN ni ticks duplicados con máximo cero', () => {
    const ticks = niceTicks(0)
    expect(ticks.every(Number.isFinite)).toBe(true)
    expect(new Set(ticks).size).toBe(ticks.length)
  })
})
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/charts/layout.test.ts`
Expected: FAIL — `Failed to resolve import "../../components/charts/layout"`

- [ ] **Step 3: Implementar `layout.ts`**

```ts
// Funciones puras de layout de gráficos. Sin React, sin DOM: acá vive la
// aritmética que puede estar sutilmente mal, y por eso se testea sola.

export interface AreaPaths {
  /** Ruta de la línea. '' si no hay al menos dos puntos finitos. */
  line: string
  /** Ruta del área cerrada contra la línea base. '' en el mismo caso. */
  area: string
}

const fmt = (n: number): string => (Number.isInteger(n) ? String(n) : n.toFixed(2))

/**
 * Mapea `values` a rutas SVG en una caja de `width` x `height`.
 * El dominio Y va de min a max de la serie; una serie constante se dibuja plana
 * a media altura en vez de dividir por cero. Los nulos se saltean: la línea une
 * los puntos válidos, no interrumpe la ruta.
 * `pad` reserva píxeles arriba y abajo para que el trazo no se corte.
 */
export function areaPaths(
  values: Array<number | null>,
  width: number,
  height: number,
  pad = 2,
): AreaPaths {
  const idx: number[] = []
  values.forEach((v, i) => {
    if (v != null && Number.isFinite(v)) idx.push(i)
  })
  if (idx.length < 2) return { line: '', area: '' }

  const nums = idx.map((i) => values[i] as number)
  const min = Math.min(...nums)
  const max = Math.max(...nums)
  const span = max - min
  const top = pad
  const bottom = height - pad
  const usable = bottom - top

  const xOf = (i: number) => (values.length === 1 ? 0 : (i / (values.length - 1)) * width)
  const yOf = (v: number) => (span === 0 ? top + usable / 2 : bottom - ((v - min) / span) * usable)

  const pts = idx.map((i) => `${fmt(xOf(i))},${fmt(yOf(values[i] as number))}`)
  const line = `M${pts[0]}` + pts.slice(1).map((p) => `L${p}`).join('')
  const firstX = fmt(xOf(idx[0]))
  const lastX = fmt(xOf(idx[idx.length - 1]))
  const area = `${line}L${lastX},${fmt(height)}L${firstX},${fmt(height)}Z`
  return { line, area }
}

/** Marcas de eje redondas desde 0 hasta cubrir `max`, en `count` intervalos. */
export function niceTicks(max: number, count = 4): number[] {
  if (!Number.isFinite(max) || max <= 0) {
    return Array.from({ length: count + 1 }, (_, i) => i / count)
  }
  const raw = max / count
  const mag = 10 ** Math.floor(Math.log10(raw))
  const norm = raw / mag
  const step = (norm <= 1 ? 1 : norm <= 2 ? 2 : norm <= 2.5 ? 2.5 : norm <= 5 ? 5 : 10) * mag
  const ticks: number[] = []
  for (let i = 0; i <= count; i++) ticks.push(Number((step * i).toFixed(10)))
  while (ticks[ticks.length - 1] < max) {
    ticks.push(Number((ticks[ticks.length - 1] + step).toFixed(10)))
  }
  return ticks
}
```

- [ ] **Step 4: Correr y verificar que pasa**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/charts/layout.test.ts`
Expected: PASS, 9 tests.

- [ ] **Step 5: Implementar `Sparkline.tsx`**

Reemplaza el `Sparkline.tsx` de 14 líneas que hay en `src/components/`. Sin ejes, sin leyenda (una sola serie: el número grande del tile es su etiqueta), sin hover (el tile ya muestra el valor).

```tsx
import { areaPaths } from './layout'

const TONE_VAR: Record<string, string> = {
  live: '--live',
  ok: '--ok',
  warn: '--wn',
  alert: '--sr',
  error: '--er',
  accent: '--ac',
}

export default function Sparkline({
  values,
  tone = 'live',
  width = 132,
  height = 26,
}: {
  values: Array<number | null>
  tone?: 'live' | 'ok' | 'warn' | 'alert' | 'error' | 'accent'
  width?: number
  height?: number
}) {
  const { line, area } = areaPaths(values, width, height)
  const color = `var(${TONE_VAR[tone] ?? '--live'})`
  if (!line) return <div className="eo-spark eo-spark--empty" style={{ width, height }} />
  const gid = `spark-${tone}`
  return (
    <svg className="eo-spark" width={width} height={height} aria-hidden="true" focusable="false">
      <defs>
        <linearGradient id={gid} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.28" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={area} fill={`url(#${gid})`} />
      <path d={line} fill="none" stroke={color} strokeWidth="2"
            strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}
```

Mover el archivo: borrar `src/components/Sparkline.tsx` y actualizar los imports que lo usaban a `./charts/Sparkline`.

- [ ] **Step 6: CSS del sparkline en `src/styles/ui.css`**

```css
.eo-spark { display: block; }
.eo-spark--empty { border-bottom: 1px dashed var(--bd); }
```

- [ ] **Step 7: Verificar suite y build**

```bash
cd webconsole/frontend && npm test 2>&1 | tail -20 && npm run build 2>&1 | tail -10
```
Expected: los tests de `layout` pasan; no aparecen fallos nuevos respecto del inventario de la Task 1.

- [ ] **Step 8: NO commitear. Reportar.**

---

### Task 3: `Meter` — barra segmentada

Se usa en dos lugares: los tiles de Detalle de experimento (criterios cumplidos, alertas por severidad) y el progreso de condiciones en Detalle de corrida.

**Files:**
- Create: `src/components/charts/Meter.tsx`
- Test: `src/__tests__/charts/Meter.test.tsx`

**Interfaces:**
- Produces:
  - `export interface MeterSegment { value: number; tone: 'live' | 'ok' | 'warn' | 'alert' | 'error' | 'neutral' | 'accent'; label: string }`
  - `export default function Meter({ segments, total, height }: { segments: MeterSegment[]; total?: number; height?: number })`

- [ ] **Step 1: Escribir el test que falla**

```tsx
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import Meter from '../../components/charts/Meter'

describe('Meter', () => {
  it('cada segmento lleva su etiqueta accesible — nunca solo color', () => {
    render(<Meter segments={[
      { value: 2, tone: 'ok', label: 'cumplen' },
      { value: 1, tone: 'error', label: 'no cumple' },
    ]} />)
    expect(screen.getByTitle('cumplen: 2')).toBeTruthy()
    expect(screen.getByTitle('no cumple: 1')).toBeTruthy()
  })

  it('reparte el ancho en proporción al valor', () => {
    const { container } = render(<Meter segments={[
      { value: 3, tone: 'ok', label: 'a' },
      { value: 1, tone: 'warn', label: 'b' },
    ]} />)
    const parts = container.querySelectorAll('.eo-meter__seg')
    expect((parts[0] as HTMLElement).style.width).toBe('75%')
    expect((parts[1] as HTMLElement).style.width).toBe('25%')
  })

  it('con `total` explícito el resto queda vacío, no estirado', () => {
    const { container } = render(
      <Meter total={4} segments={[{ value: 1, tone: 'ok', label: 'a' }]} />,
    )
    const parts = container.querySelectorAll('.eo-meter__seg')
    expect(parts).toHaveLength(1)
    expect((parts[0] as HTMLElement).style.width).toBe('25%')
  })

  it('no divide por cero cuando todos los valores son 0', () => {
    const { container } = render(
      <Meter segments={[{ value: 0, tone: 'ok', label: 'a' }]} />,
    )
    const parts = container.querySelectorAll('.eo-meter__seg')
    expect((parts[0] as HTMLElement).style.width).toBe('0%')
  })
})
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/charts/Meter.test.tsx`
Expected: FAIL — no existe el módulo.

- [ ] **Step 3: Implementar**

```tsx
export interface MeterSegment {
  value: number
  tone: 'live' | 'ok' | 'warn' | 'alert' | 'error' | 'neutral' | 'accent'
  label: string
}

const TONE_VAR: Record<MeterSegment['tone'], string> = {
  live: '--live', ok: '--ok', warn: '--wn', alert: '--sr',
  error: '--er', neutral: '--nt', accent: '--ac',
}

/**
 * Barra segmentada. `total` fija el denominador cuando la barra representa una
 * proporción contra un límite (2 de 3 criterios); sin `total`, los segmentos se
 * reparten el ancho completo.
 * Cada segmento lleva su etiqueta en `title`: el color nunca es el único portador.
 */
export default function Meter({
  segments,
  total,
  height = 4,
}: {
  segments: MeterSegment[]
  total?: number
  height?: number
}) {
  const sum = segments.reduce((acc, s) => acc + Math.max(0, s.value), 0)
  const denom = total ?? sum
  const pct = (v: number) => (denom > 0 ? (Math.max(0, v) / denom) * 100 : 0)
  return (
    <div className="eo-meter" style={{ height }} role="img"
         aria-label={segments.map((s) => `${s.label}: ${s.value}`).join(', ')}>
      {segments.map((s) => (
        <i
          key={s.label}
          className="eo-meter__seg"
          title={`${s.label}: ${s.value}`}
          style={{ width: `${pct(s.value)}%`, background: `var(${TONE_VAR[s.tone]})` }}
        />
      ))}
    </div>
  )
}
```

- [ ] **Step 4: Correr y verificar que pasa**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/charts/Meter.test.tsx`
Expected: PASS, 4 tests.

- [ ] **Step 5: CSS en `src/styles/ui.css`**

Los 2 px de separación entre segmentos son el `gap`: es el espaciador de superficie que exige la guía de marcas.

```css
.eo-meter {
  border-radius: 2px;
  background: var(--sunken);
  overflow: hidden;
  display: flex;
  gap: 2px;
  width: 100%;
}
.eo-meter__seg { display: block; height: 100%; border-radius: 2px; }
```

- [ ] **Step 6: Verificar suite y build. NO commitear. Reportar.**

```bash
cd webconsole/frontend && npm test 2>&1 | tail -20 && npm run build 2>&1 | tail -10
```

---

### Task 4: `charts/timeline.ts` y `ActivityTimeline`

La pieza que reemplaza el volcado vertical. Área de detecciones por cuadro + dos carriles de eventos (entrega al motor de reglas, alertas) + cursor + eje temporal.

**Files:**
- Create: `src/components/charts/timeline.ts`
- Create: `src/components/charts/ActivityTimeline.tsx`
- Test: `src/__tests__/charts/timeline.test.ts`

**Interfaces:**
- Consumes: `areaPaths` de `charts/layout` (Task 2); `TraceFrame` de `src/types`.
- Produces:
  - `export type LaneKind = 'dropped' | 'not_received' | 'alert'`
  - `export interface LaneMark { x: number; width: number; kind: LaneKind; frameIndex: number }`
  - `export interface TimelineLayout { line: string; area: string; marks: LaneMark[]; maxDetections: number }`
  - `export function timelineLayout(frames: TraceFrame[], width: number, plotHeight: number): TimelineLayout`
  - `export function frameAtX(x: number, width: number, count: number): number`
  - `export default function ActivityTimeline({ frames, width, plotHeight, selected, onSelect })`

- [ ] **Step 1: Escribir los tests que fallan**

```ts
import { describe, expect, it } from 'vitest'
import { frameAtX, timelineLayout } from '../../components/charts/timeline'
import type { TraceFrame } from '../../types'

const f = (over: Partial<TraceFrame> = {}): TraceFrame => ({
  frame_index: 0, unit_id: 'u', timestamp_ms: 0, detections: [],
  control: 'received', progress: [], alert: [], active_patterns: [], ...over,
})

describe('timelineLayout', () => {
  it('el área sigue la cantidad de detecciones por cuadro', () => {
    const frames = [
      f({ frame_index: 0, detections: [] }),
      f({ frame_index: 1, detections: [{}, {}] as never }),
    ]
    const out = timelineLayout(frames, 100, 40)
    expect(out.maxDetections).toBe(2)
    expect(out.line).not.toBe('')
  })

  it('marca un descarte por cada cuadro con control dropped:*', () => {
    const frames = [
      f({ frame_index: 0, control: 'received' }),
      f({ frame_index: 1, control: 'dropped:queue_full' }),
    ]
    const marks = timelineLayout(frames, 100, 40).marks
    expect(marks).toHaveLength(1)
    expect(marks[0].kind).toBe('dropped')
    expect(marks[0].frameIndex).toBe(1)
  })

  it('distingue no recibido de descartado — son carriles distintos', () => {
    const frames = [f({ frame_index: 0, control: 'not_received' })]
    expect(timelineLayout(frames, 100, 40).marks[0].kind).toBe('not_received')
  })

  it('marca alerta cuando el cuadro tiene alertas, además de su estado de entrega', () => {
    const frames = [
      f({ frame_index: 0, control: 'dropped:rate_gate', alert: [{ alert_id: 'a' }] as never }),
    ]
    const kinds = timelineLayout(frames, 100, 40).marks.map((m) => m.kind).sort()
    expect(kinds).toEqual(['alert', 'dropped'])
  })

  it('no produce marcas de ancho cero con muchos cuadros', () => {
    const frames = Array.from({ length: 5000 }, (_, i) =>
      f({ frame_index: i, control: 'dropped:queue_full' }))
    const marks = timelineLayout(frames, 800, 40).marks
    expect(marks.every((m) => m.width >= 1)).toBe(true)
  })

  it('con cero cuadros devuelve un layout vacío, no NaN', () => {
    const out = timelineLayout([], 100, 40)
    expect(out).toEqual({ line: '', area: '', marks: [], maxDetections: 0 })
  })
})

describe('frameAtX', () => {
  it('mapea el borde izquierdo al primer cuadro y el derecho al último', () => {
    expect(frameAtX(0, 100, 10)).toBe(0)
    expect(frameAtX(100, 100, 10)).toBe(9)
  })

  it('acota fuera de rango en vez de devolver un índice inválido', () => {
    expect(frameAtX(-50, 100, 10)).toBe(0)
    expect(frameAtX(999, 100, 10)).toBe(9)
  })

  it('devuelve -1 sin cuadros', () => {
    expect(frameAtX(10, 100, 0)).toBe(-1)
  })
})
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/charts/timeline.test.ts`
Expected: FAIL — no existe el módulo.

- [ ] **Step 3: Implementar `timeline.ts`**

```ts
import type { TraceFrame } from '../../types'
import { areaPaths } from './layout'

export type LaneKind = 'dropped' | 'not_received' | 'alert'

export interface LaneMark {
  x: number
  width: number
  kind: LaneKind
  frameIndex: number
}

export interface TimelineLayout {
  line: string
  area: string
  marks: LaneMark[]
  maxDetections: number
}

/**
 * Layout de la línea de tiempo de una corrida.
 * El área es la cantidad de detecciones por cuadro; las marcas son eventos
 * discretos que van en carriles separados (la separación espacial es la
 * codificación secundaria que hace que el significado no dependa del matiz).
 * Un cuadro puede producir dos marcas: su estado de entrega y su alerta.
 */
export function timelineLayout(
  frames: TraceFrame[],
  width: number,
  plotHeight: number,
): TimelineLayout {
  if (!frames.length) return { line: '', area: '', marks: [], maxDetections: 0 }

  const counts = frames.map((fr) => fr.detections?.length ?? 0)
  const maxDetections = counts.reduce((a, b) => Math.max(a, b), 0)
  const { line, area } = areaPaths(counts, width, plotHeight)

  // Ancho mínimo de 1 px: con miles de cuadros el slot es subpíxel y una marca
  // de ancho 0 es una marca invisible — un descarte que no se ve es un descarte
  // silenciado.
  const slot = width / frames.length
  const markWidth = Math.max(1, slot)

  const marks: LaneMark[] = []
  frames.forEach((fr, i) => {
    const x = i * slot
    const frameIndex = fr.frame_index ?? i
    if (fr.control === 'not_received') {
      marks.push({ x, width: markWidth, kind: 'not_received', frameIndex })
    } else if (fr.control.startsWith('dropped:')) {
      marks.push({ x, width: markWidth, kind: 'dropped', frameIndex })
    }
    if ((fr.alert?.length ?? 0) > 0) {
      marks.push({ x, width: markWidth, kind: 'alert', frameIndex })
    }
  })

  return { line, area, marks, maxDetections }
}

/** Índice del cuadro bajo la coordenada x. -1 si no hay cuadros. */
export function frameAtX(x: number, width: number, count: number): number {
  if (count <= 0) return -1
  const ratio = Math.min(1, Math.max(0, x / width))
  return Math.min(count - 1, Math.floor(ratio * count))
}
```

- [ ] **Step 4: Correr y verificar que pasa**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/charts/timeline.test.ts`
Expected: PASS, 9 tests.

- [ ] **Step 5: Implementar `ActivityTimeline.tsx`**

**Regla de leyenda (§4.1 del spec):** la leyenda lleva la forma del carril, no un cuadradito de color. `#f0625f` (fallida) y `#ee8a5c` (alerta) tienen ΔE 8,8 en visión normal — por debajo del piso de 15. Sin la forma y la etiqueta al margen, un jurado no los distingue.

```tsx
import { useRef, useState } from 'react'
import type { TraceFrame } from '../../types'
import { frameAtX, timelineLayout, type LaneKind } from './timeline'

const LANE_STYLE: Record<LaneKind, { row: number; color: string; label: string }> = {
  dropped: { row: 0, color: 'var(--wn)', label: 'Descartado' },
  not_received: { row: 0, color: 'var(--er)', label: 'No recibido' },
  alert: { row: 1, color: 'var(--sr)', label: 'Alerta' },
}

const LANE_H = 8
const LANE_GAP = 4

export default function ActivityTimeline({
  frames,
  width = 1200,
  plotHeight = 56,
  selected,
  onSelect,
}: {
  frames: TraceFrame[]
  width?: number
  plotHeight?: number
  selected?: number | null
  onSelect?: (frameIndex: number, position: number) => void
}) {
  const ref = useRef<SVGSVGElement>(null)
  const [hover, setHover] = useState<number | null>(null)
  const { line, area, marks, maxDetections } = timelineLayout(frames, width, plotHeight)
  const lanesTop = plotHeight + LANE_GAP
  const height = lanesTop + LANE_H * 2 + LANE_GAP

  const posOf = (i: number) => (frames.length ? (i / frames.length) * width : 0)

  const pick = (clientX: number): number => {
    const box = ref.current?.getBoundingClientRect()
    if (!box) return -1
    return frameAtX(clientX - box.left, box.width, frames.length)
  }

  const describe = (pos: number): string => {
    const fr = frames[pos]
    if (!fr) return ''
    const dets = fr.detections?.length ?? 0
    const alerts = fr.alert?.length ?? 0
    const parts = [`cuadro ${fr.frame_index ?? pos}`, `${dets} detecciones`]
    if (alerts) parts.push(`${alerts} alertas`)
    if (fr.control !== 'received') parts.push(fr.control)
    return parts.join(' · ')
  }

  if (!frames.length) {
    return <p className="eo-cap">Todavía no hay cuadros para dibujar la línea de tiempo.</p>
  }

  return (
    <div className="eo-timeline">
      <svg
        ref={ref}
        className="eo-timeline__svg"
        viewBox={`0 0 ${width} ${height}`}
        preserveAspectRatio="none"
        role="img"
        aria-label={`Actividad de ${frames.length} cuadros: detecciones, entrega al motor de reglas y alertas`}
        onMouseMove={(e) => setHover(pick(e.clientX))}
        onMouseLeave={() => setHover(null)}
        onClick={(e) => {
          const pos = pick(e.clientX)
          const fr = frames[pos]
          if (fr && onSelect) onSelect(fr.frame_index ?? pos, pos)
        }}
      >
        <rect x={0} y={0} width={width} height={plotHeight} fill="var(--sunken)" />
        {area && <path d={area} fill="var(--live)" fillOpacity="0.22" />}
        {line && <path d={line} fill="none" stroke="var(--live)" strokeWidth="2"
                       vectorEffect="non-scaling-stroke" />}
        {marks.map((m, i) => {
          const st = LANE_STYLE[m.kind]
          return (
            <rect
              key={`${m.kind}-${m.frameIndex}-${i}`}
              x={m.x}
              y={lanesTop + st.row * (LANE_H + LANE_GAP)}
              width={m.width}
              height={LANE_H}
              rx={2}
              fill={st.color}
            />
          )
        })}
        {selected != null && selected >= 0 && (
          <line x1={posOf(selected)} y1={0} x2={posOf(selected)} y2={height}
                stroke="var(--ac)" strokeWidth="2" vectorEffect="non-scaling-stroke" />
        )}
      </svg>

      <div className="eo-timeline__axis">
        <span className="eo-mono">0,0 s</span>
        <span className="eo-mono">{frames.length} cuadros</span>
      </div>

      {/* Leyenda por FORMA y etiqueta, no por cuadradito de color: entre
          `alerta` (--sr) y `fallida` (--er) hay ΔE 8,8 en visión normal. */}
      <ul className="eo-timeline__legend">
        <li><span className="eo-timeline__key eo-timeline__key--area" /> Detecciones · pico {maxDetections}</li>
        <li><span className="eo-timeline__key eo-timeline__key--dropped" /> Descartado</li>
        <li><span className="eo-timeline__key eo-timeline__key--notrecv" /> No recibido</li>
        <li><span className="eo-timeline__key eo-timeline__key--alert" /> Alerta</li>
      </ul>

      <p className="eo-timeline__hint" aria-live="polite">
        {hover != null && hover >= 0 ? describe(hover) : 'Tocá la línea de tiempo para ir a un cuadro'}
      </p>
    </div>
  )
}
```

- [ ] **Step 6: CSS en `src/styles/ui.css`**

Las claves de la leyenda tienen forma distinta a propósito: barra alta para el área, barra baja para los carriles, y el triángulo para alerta.

```css
.eo-timeline__svg {
  width: 100%; height: auto; display: block;
  border-radius: var(--r); cursor: crosshair;
}
.eo-timeline__axis {
  display: flex; justify-content: space-between;
  font-size: 10.5px; color: var(--tx4); padding: 4px 2px 0;
}
.eo-timeline__legend {
  list-style: none; margin: 6px 0 0; padding: 0;
  display: flex; flex-wrap: wrap; gap: 14px;
  font-size: 11px; color: var(--tx3);
}
.eo-timeline__legend li { display: inline-flex; align-items: center; gap: 6px; }
.eo-timeline__key { display: inline-block; flex: none; }
.eo-timeline__key--area    { width: 10px; height: 10px; border-radius: 2px;
                             background: var(--live); opacity: .55; }
.eo-timeline__key--dropped { width: 12px; height: 4px; border-radius: 2px; background: var(--wn); }
.eo-timeline__key--notrecv { width: 4px;  height: 10px; border-radius: 2px; background: var(--er); }
.eo-timeline__key--alert   { width: 0; height: 0; border-left: 5px solid transparent;
                             border-right: 5px solid transparent;
                             border-bottom: 9px solid var(--sr); }
.eo-timeline__hint { margin: 6px 0 0; font-size: 11px; color: var(--tx4); min-height: 1.4em; }
```

- [ ] **Step 7: Verificar suite y build. NO commitear. Reportar.**

```bash
cd webconsole/frontend && npm test 2>&1 | tail -20 && npm run build 2>&1 | tail -10
```

---

### Task 5: Mover y completar `GroupedBars`

La paleta y el layout ya están bien y **pasan las seis verificaciones** sobre `#1a1a19`. Lo que falta es el eje Y, las etiquetas directas de valor y una leyenda que no dependa solo del color. **No reordenar `SERIES_COLORS`.**

**Files:**
- Move: `src/components/GroupedBars.tsx` → `src/components/charts/GroupedBars.tsx`
- Modify: `src/traceview.ts` (import de `SERIES_COLORS`)
- Modify: `src/__tests__/GroupedBars.test.tsx` → `src/__tests__/charts/GroupedBars.test.tsx`
- Test: agrega casos al mismo archivo

**Interfaces:**
- Consumes: `niceTicks` de `charts/layout` (Task 2).
- Produces: `SERIES_COLORS`, `groupedBarsLayout(groups, series, width, plotHeight): BarRect[]`, `BarRect`, y `default function GroupedBars({ groups, series, labels, width?, height? })` — misma firma que hoy.

- [ ] **Step 1: Mover el archivo y su test, ajustando imports**

```bash
cd /home/simonll4/projects/e-ovrt_experimental-setup/webconsole/frontend
mkdir -p src/__tests__/charts
git mv src/components/GroupedBars.tsx src/components/charts/GroupedBars.tsx
git mv src/__tests__/GroupedBars.test.tsx src/__tests__/charts/GroupedBars.test.tsx
```

En `src/traceview.ts` cambiar `from './components/GroupedBars'` a `from './components/charts/GroupedBars'`. En `src/__tests__/charts/GroupedBars.test.tsx` cambiar `from '../components/GroupedBars'` a `from '../../components/charts/GroupedBars'`. Buscar cualquier otro consumidor:

```bash
grep -rn "components/GroupedBars" src/ || echo "sin consumidores restantes"
```

- [ ] **Step 2: Agregar los tests nuevos que fallan**

Añadir al final de `src/__tests__/charts/GroupedBars.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react'
import GroupedBars from '../../components/charts/GroupedBars'

describe('GroupedBars — render', () => {
  it('etiqueta cada barra con su valor: no hace falta leer contra el eje', () => {
    render(<GroupedBars groups={['person']} series={[[0.78], [0.71]]}
                        labels={['Barrido diurno', 'Perímetro con lluvia']} />)
    expect(screen.getByText('0,78')).toBeTruthy()
    expect(screen.getByText('0,71')).toBeTruthy()
  })

  it('dibuja el eje Y con marcas redondas de 0 a 1', () => {
    render(<GroupedBars groups={['person']} series={[[0.5]]} labels={['a']} />)
    expect(screen.getByText('1,00')).toBeTruthy()
    expect(screen.getByText('0,00')).toBeTruthy()
  })

  it('la leyenda nombra cada serie — la identidad nunca es solo color', () => {
    render(<GroupedBars groups={['person']} series={[[0.5], [0.6]]}
                        labels={['Barrido diurno', 'Perímetro con lluvia']} />)
    expect(screen.getByText('Barrido diurno')).toBeTruthy()
    expect(screen.getByText('Perímetro con lluvia')).toBeTruthy()
  })
})
```

- [ ] **Step 3: Correr y verificar que falla**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/charts/GroupedBars.test.tsx`
Expected: los 3 tests nuevos FALLAN (no hay etiquetas de valor ni eje); los 3 viejos de `groupedBarsLayout` PASAN.

- [ ] **Step 4: Reescribir el render (el layout queda intacto)**

Reemplazar **solo** el `export default function GroupedBars` de `src/components/charts/GroupedBars.tsx`. `SERIES_COLORS`, `BarRect` y `groupedBarsLayout` no se tocan.

```tsx
import { niceTicks } from './layout'

const fmtValue = (v: number) => v.toFixed(2).replace('.', ',')

export default function GroupedBars({
  groups,
  series,
  labels,
  width = 720,
  height = 300,
}: {
  groups: string[]
  series: Array<Array<number | null>>
  labels: string[]
  width?: number
  height?: number
}) {
  const axisW = 44
  const bottomH = 34
  const topPad = 18            // aire para la etiqueta de valor sobre la barra
  const plotWidth = width - axisW
  const plotHeight = height - bottomH - topPad
  const rects = groupedBarsLayout(groups, series, plotWidth, plotHeight)
  const ticks = niceTicks(1)   // AP@0.5 vive en [0,1]: dominio fijo, no auto

  return (
    <div className="eo-bars">
      <svg width="100%" viewBox={`0 0 ${width} ${height}`} role="img"
           aria-label={`Precisión por clase, ${labels.join(' contra ')}`}>
        <g transform={`translate(${axisW}, ${topPad})`}>
          {ticks.map((t) => {
            const y = plotHeight - t * plotHeight
            return (
              <g key={t}>
                <line x1={0} y1={y} x2={plotWidth} y2={y} stroke="var(--bd)" />
                <text x={-8} y={y + 4} textAnchor="end" className="eo-bars__tick">
                  {fmtValue(t)}
                </text>
              </g>
            )
          })}
          {rects.map((r) => (
            <g key={`${r.series}-${r.group}`}>
              <rect x={r.x} y={r.y} width={r.width} height={r.height} fill={r.color} rx={4}>
                <title>{`${labels[r.series]} — ${groups[r.group]}: ${fmtValue(r.value)}`}</title>
              </rect>
              <text x={r.x + r.width / 2} y={r.y - 5} textAnchor="middle" className="eo-bars__value">
                {fmtValue(r.value)}
              </text>
            </g>
          ))}
          {groups.map((group, gi) => (
            <text key={group} x={(gi + 0.5) * (plotWidth / groups.length)}
                  y={plotHeight + 20} textAnchor="middle" className="eo-bars__group">
              {group}
            </text>
          ))}
        </g>
      </svg>
      <ul className="eo-bars__legend">
        {labels.map((label, i) => (
          <li key={label}>
            <span className="eo-bars__key" style={{ background: SERIES_COLORS[i % SERIES_COLORS.length] }} />
            {label}
          </li>
        ))}
      </ul>
    </div>
  )
}
```

- [ ] **Step 5: Correr y verificar que pasa**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/charts/GroupedBars.test.tsx`
Expected: PASS, 6 tests.

- [ ] **Step 6: CSS en `src/styles/ui.css`**

El texto va con tokens de texto, nunca con el color de la serie.

```css
.eo-bars__tick  { font-size: 10.5px; fill: var(--tx4); font-family: var(--fm); }
.eo-bars__value { font-size: 11px; fill: var(--tx2); font-family: var(--fm); }
.eo-bars__group { font-size: 12px; fill: var(--tx2); font-family: var(--fm); }
.eo-bars__legend {
  list-style: none; margin: 4px 0 0; padding: 0;
  display: flex; flex-wrap: wrap; gap: 16px;
  font-size: 11.5px; color: var(--tx2);
}
.eo-bars__legend li { display: inline-flex; align-items: center; gap: 6px; }
.eo-bars__key { width: 10px; height: 10px; border-radius: 2px; flex: none; }
```

- [ ] **Step 7: Verificar suite y build. NO commitear. Reportar.**

---

### Task 6: `runseries.ts` y `useFullTrace`

De acá salen las series de los sparklines y el índice completo que la línea de tiempo necesita. Es lógica pura + un hook: se testea la lógica, no el hook.

**Files:**
- Create: `src/runseries.ts`
- Create: `src/useFullTrace.ts`
- Test: `src/__tests__/runseries.test.ts`

**Interfaces:**
- Consumes: `TraceFrame`, `TraceTotals`, `TracePage` de `src/types`; `getTrace(id, page, pageSize, controlRunId?)` de `src/api`.
- Produces:
  - `export interface RunSeries { detectionsPerFrame: number[]; instantFps: Array<number | null>; elapsedSeconds: number[]; totalSeconds: number }`
  - `export function buildRunSeries(frames: TraceFrame[]): RunSeries`
  - `export function windowMean(values: Array<number | null>, seconds: number[], fromSec: number, toSec: number): number | null`
  - `export function recentDelta(values: Array<number | null>, seconds: number[], windowSec?: number): number | null`
  - `export interface FullTrace { frames: TraceFrame[]; totals: TraceTotals | null; controlRunId: string | null; controlError: string | null; loading: boolean; error: string | null; truncated: boolean }`
  - `export function useFullTrace(runId: string, enabled: boolean): FullTrace`

- [ ] **Step 1: Escribir los tests que fallan**

```ts
import { describe, expect, it } from 'vitest'
import { buildRunSeries, recentDelta, windowMean } from '../runseries'
import type { TraceFrame } from '../types'

const f = (i: number, ts: number | null, dets: number): TraceFrame => ({
  frame_index: i, unit_id: `frame_${i}`, timestamp_ms: ts,
  detections: Array.from({ length: dets }, () => ({})) as never,
  control: 'received', progress: [], alert: [], active_patterns: [],
})

describe('buildRunSeries', () => {
  it('cuenta detecciones por cuadro', () => {
    const s = buildRunSeries([f(0, 0, 2), f(1, 500, 0), f(2, 1000, 3)])
    expect(s.detectionsPerFrame).toEqual([2, 0, 3])
  })

  it('el tiempo transcurrido arranca en 0 y es relativo al primer cuadro', () => {
    const s = buildRunSeries([f(0, 1000, 0), f(1, 1500, 0), f(2, 3000, 0)])
    expect(s.elapsedSeconds).toEqual([0, 0.5, 2])
    expect(s.totalSeconds).toBe(2)
  })

  it('el fps instantáneo es el inverso del delta entre cuadros; el primero es null', () => {
    const s = buildRunSeries([f(0, 0, 0), f(1, 500, 0), f(2, 750, 0)])
    expect(s.instantFps[0]).toBeNull()
    expect(s.instantFps[1]).toBeCloseTo(2, 6)
    expect(s.instantFps[2]).toBeCloseTo(4, 6)
  })

  it('un delta de cero da null, no Infinity', () => {
    const s = buildRunSeries([f(0, 1000, 0), f(1, 1000, 0)])
    expect(s.instantFps[1]).toBeNull()
  })

  it('tolera timestamps ausentes sin propagar NaN', () => {
    const s = buildRunSeries([f(0, null, 1), f(1, null, 2)])
    expect(s.detectionsPerFrame).toEqual([1, 2])
    expect(s.elapsedSeconds.every(Number.isFinite)).toBe(true)
    expect(s.totalSeconds).toBe(0)
  })

  it('con cero cuadros devuelve series vacías', () => {
    expect(buildRunSeries([])).toEqual({
      detectionsPerFrame: [], instantFps: [], elapsedSeconds: [], totalSeconds: 0,
    })
  })
})

describe('windowMean', () => {
  it('promedia solo los valores dentro de la ventana', () => {
    expect(windowMean([1, 2, 3, 4], [0, 1, 2, 3], 2, 3)).toBe(3.5)
  })

  it('devuelve null si la ventana no tiene ningún valor', () => {
    expect(windowMean([1, 2], [0, 1], 10, 20)).toBeNull()
  })

  it('ignora los nulos en vez de contarlos como cero', () => {
    expect(windowMean([null, 4], [0, 1], 0, 1)).toBe(4)
  })
})

describe('recentDelta', () => {
  it('compara la última ventana contra la anterior', () => {
    // 0-30 s valen 1; 30-60 s valen 3 → delta +2
    const seconds = Array.from({ length: 61 }, (_, i) => i)
    const values = seconds.map((s) => (s < 30 ? 1 : 3))
    expect(recentDelta(values, seconds, 30)).toBeCloseTo(2, 6)
  })

  it('devuelve null si no hay dos ventanas completas — no se inventa un delta', () => {
    expect(recentDelta([1, 2], [0, 1], 30)).toBeNull()
  })
})
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/runseries.test.ts`
Expected: FAIL — no existe `../runseries`.

- [ ] **Step 3: Implementar `runseries.ts`**

```ts
import type { TraceFrame } from './types'

export interface RunSeries {
  detectionsPerFrame: number[]
  /** Inverso del delta entre cuadros consecutivos. null en el primero y cuando
   *  el delta es 0 o los timestamps faltan: un fps infinito es peor que un hueco. */
  instantFps: Array<number | null>
  /** Segundos desde el primer cuadro. 0 cuando no hay timestamps. */
  elapsedSeconds: number[]
  totalSeconds: number
}

/**
 * Deriva las series de una corrida desde la traza. El backend no expone series
 * temporales; todo esto sale de `timestamp_ms` y `detections` por cuadro, que sí
 * vienen en `/api/runs/{id}/trace`.
 */
export function buildRunSeries(frames: TraceFrame[]): RunSeries {
  if (!frames.length) {
    return { detectionsPerFrame: [], instantFps: [], elapsedSeconds: [], totalSeconds: 0 }
  }

  const detectionsPerFrame = frames.map((fr) => fr.detections?.length ?? 0)

  const base = frames.find((fr) => fr.timestamp_ms != null)?.timestamp_ms ?? null
  const elapsedSeconds = frames.map((fr) =>
    base != null && fr.timestamp_ms != null ? (fr.timestamp_ms - base) / 1000 : 0,
  )

  const instantFps: Array<number | null> = frames.map((fr, i) => {
    if (i === 0) return null
    const prev = frames[i - 1].timestamp_ms
    const cur = fr.timestamp_ms
    if (prev == null || cur == null) return null
    const deltaMs = cur - prev
    if (!Number.isFinite(deltaMs) || deltaMs <= 0) return null
    return 1000 / deltaMs
  })

  const totalSeconds = elapsedSeconds.length
    ? Math.max(...elapsedSeconds.filter(Number.isFinite))
    : 0

  return { detectionsPerFrame, instantFps, elapsedSeconds, totalSeconds: totalSeconds || 0 }
}

/** Promedio de los valores cuyo segundo cae en [fromSec, toSec]. null si no hay ninguno. */
export function windowMean(
  values: Array<number | null>,
  seconds: number[],
  fromSec: number,
  toSec: number,
): number | null {
  let sum = 0
  let n = 0
  for (let i = 0; i < values.length; i++) {
    const s = seconds[i]
    const v = values[i]
    if (s == null || s < fromSec || s > toSec) continue
    if (v == null || !Number.isFinite(v)) continue
    sum += v
    n++
  }
  return n ? sum / n : null
}

/**
 * Diferencia entre la última ventana y la anterior. Devuelve null si no hay dos
 * ventanas completas: en una corrida terminada o recién arrancada el delta no
 * existe, y mostrar un "+0,0" inventado sería peor que no mostrar nada.
 */
export function recentDelta(
  values: Array<number | null>,
  seconds: number[],
  windowSec = 30,
): number | null {
  const finite = seconds.filter(Number.isFinite)
  if (!finite.length) return null
  const end = Math.max(...finite)
  if (end < windowSec * 2) return null
  const recent = windowMean(values, seconds, end - windowSec, end)
  const prior = windowMean(values, seconds, end - windowSec * 2, end - windowSec)
  if (recent == null || prior == null) return null
  return recent - prior
}
```

- [ ] **Step 4: Correr y verificar que pasa**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/runseries.test.ts`
Expected: PASS, 11 tests.

- [ ] **Step 5: Implementar `useFullTrace.ts`**

El tope de páginas es explícito y **se informa** (`truncated`): un tope silencioso se lee como "esto es todo" cuando no lo es.

```ts
import { useEffect, useState } from 'react'
import { getTrace } from './api'
import type { TraceFrame, TraceTotals } from './types'

const PAGE_SIZE = 500
/** Tope duro: 40 páginas = 20 000 cuadros. La corrida más larga del banco es de
 *  minutos; esto es un cinturón contra una traza patológica, no un límite de diseño. */
const MAX_PAGES = 40

export interface FullTrace {
  frames: TraceFrame[]
  totals: TraceTotals | null
  controlRunId: string | null
  controlError: string | null
  loading: boolean
  error: string | null
  /** true si se llegó al tope de páginas y la traza quedó incompleta. */
  truncated: boolean
}

const EMPTY: FullTrace = {
  frames: [], totals: null, controlRunId: null, controlError: null,
  loading: false, error: null, truncated: false,
}

/**
 * Trae la traza completa paginando `/api/runs/{id}/trace`. La línea de tiempo
 * necesita el índice de actividad de toda la corrida, y el backend solo pagina
 * (decisión del spec: no se toca el backend).
 */
export function useFullTrace(runId: string, enabled: boolean): FullTrace {
  const [state, setState] = useState<FullTrace>(EMPTY)

  useEffect(() => {
    if (!enabled || !runId) {
      setState(EMPTY)
      return
    }
    let alive = true
    setState({ ...EMPTY, loading: true })

    const load = async () => {
      try {
        const first = await getTrace(runId, 1, PAGE_SIZE)
        if (!alive) return
        const frames = [...first.frames]
        const pages = Math.ceil(first.total / PAGE_SIZE)
        const limit = Math.min(pages, MAX_PAGES)
        for (let p = 2; p <= limit; p++) {
          const page = await getTrace(runId, p, PAGE_SIZE, first.control_run_id ?? undefined)
          if (!alive) return
          frames.push(...page.frames)
        }
        setState({
          frames,
          totals: first.totals,
          controlRunId: first.control_run_id,
          controlError: first.control_error,
          loading: false,
          error: null,
          truncated: pages > MAX_PAGES,
        })
      } catch (e) {
        if (alive) setState({ ...EMPTY, error: `No se pudo leer la traza: ${String(e)}` })
      }
    }

    void load()
    return () => {
      alive = false
    }
  }, [runId, enabled])

  return state
}
```

- [ ] **Step 6: Verificar suite y build. NO commitear. Reportar.**

```bash
cd webconsole/frontend && npm test 2>&1 | tail -20 && npm run build 2>&1 | tail -10
```

---

### Task 7: Pantalla Corridas

Referencia: `proto-ref-02-corridas.md` y la captura `scratchpad/proto/01-corridas.png`.

**Files:**
- Rewrite: `src/pages/RunsPage.tsx`
- Modify: `src/styles/ui.css`
- Modify: `src/__tests__/RunsPage.test.tsx`

**Interfaces:**
- Consumes: primitivas de la Task 1; `listRuns()`, `deleteRun(id)`, `getTrace(id, 1, 1)` de `src/api`; `isRunning`, `runStatusTone`, `runStatusLabel` de `src/runview`.
- Produces: nada que consuman otras tareas.

**Composición** (de arriba abajo, todo dentro de `.card` salvo el encabezado):

1. `PageHeader` — título "Corridas", subtítulo `"{N} en total · {M} en curso"`, acción primaria "Nueva corrida".
2. Banner `tone="live"` si hay corrida en curso: nombre + `"está procesando ahora — {D} detecciones, {A} alertas confirmadas"` + acción "Ver en vivo".
3. Barra de herramientas: `SearchInput` (placeholder `"Buscar por nombre o identificador"`) + `SegmentedControl` (Todas / En curso / Completadas / Detenidas / Fallidas) + contador `"{visibles} de {total}"` a la derecha.
4. `Table` densa. Columnas: Corrida (`RowNameCell`: nombre arriba, `run_id` monoespaciado abajo), Estado (`Badge` icono+texto), Modelo (mono), Fuente, Conjunto de prompts (mono), Cuadros/s (`NumCell`), Detecciones (`NumCell`), Duración (`NumCell`), antigüedad.
5. Paginación: 25 filas por página, con `"Página X de Y"` y botones anterior/siguiente. **Obligatoria**: hay 136 corridas reales.
6. Borrado con `InlineDeleteConfirm` en la fila, no un botón permanente por fila.

**Glosario obligatorio en encabezados**: Corrida, Estado, Modelo, Fuente, Conjunto de prompts, Cuadros/s, Detecciones, Duración. Estados: `running`→"En curso", `succeeded`→"Completada", `stopped`→"Detenida", `failed`→"Fallida".

- [ ] **Step 1: Escribir los tests que fallan**

Reescribir `src/__tests__/RunsPage.test.tsx` conservando el mock de `../api` que ya usa. Tests nuevos:

```tsx
it('pagina el listado en vez de volcar todas las filas', async () => {
  // 30 corridas mockeadas
  render(<MemoryRouter><RunsPage /></MemoryRouter>)
  await screen.findByText('Corridas')
  expect(screen.getAllByRole('row')).toHaveLength(26)   // 25 filas + encabezado
  expect(screen.getByText('Página 1 de 2')).toBeTruthy()
})

it('el segmentado filtra por estado con el vocabulario del glosario', async () => {
  render(<MemoryRouter><RunsPage /></MemoryRouter>)
  await screen.findByText('Corridas')
  fireEvent.click(screen.getByRole('button', { name: 'Completadas' }))
  expect(screen.queryByText('En curso')).toBeNull()
})

it('el buscador filtra por nombre y por identificador', async () => {
  render(<MemoryRouter><RunsPage /></MemoryRouter>)
  await screen.findByText('Corridas')
  fireEvent.change(screen.getByPlaceholderText('Buscar por nombre o identificador'),
                   { target: { value: 'telemetria' } })
  expect(screen.getByText(/de 30/)).toBeTruthy()
})

it('el borrado pide confirmación en línea, no muestra un botón permanente por fila', async () => {
  render(<MemoryRouter><RunsPage /></MemoryRouter>)
  await screen.findByText('Corridas')
  expect(screen.queryAllByRole('button', { name: 'Borrar' })).toHaveLength(0)
})

it('traduce los estados: nunca muestra el código crudo del backend', async () => {
  render(<MemoryRouter><RunsPage /></MemoryRouter>)
  await screen.findByText('Corridas')
  expect(screen.queryByText('stopped')).toBeNull()
  expect(screen.getAllByText('Detenida').length).toBeGreaterThan(0)
})
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/RunsPage.test.tsx`
Expected: FAIL en los 5 tests nuevos.

- [ ] **Step 3: Ampliar `runview.ts` con el glosario de estados**

`runStatusLabel` hoy devuelve `'vivo'`/`'OK'`/`'fallo'` y el código crudo para el resto. Reemplazar por:

```ts
export function runStatusLabel(run: { status: string; live?: boolean }): string {
  if (isRunning(run)) return 'En curso'
  if (run.status === 'succeeded') return 'Completada'
  if (run.status === 'stopped') return 'Detenida'
  if (run.status === 'failed') return 'Fallida'
  return run.status
}

export function sourceLabel(sourceType: string | null | undefined): string {
  if (!sourceType) return '—'
  const map: Record<string, string> = {
    image_folder: 'Carpeta de imágenes',
    video_file: 'Archivo de video',
    rtsp: 'Cámara RTSP',
    oak_d: 'Cámara OAK-D',
  }
  return map[sourceType] ?? sourceType
}
```

Actualizar `src/__tests__/runview.test.ts` a las etiquetas nuevas.

- [ ] **Step 4: Reescribir `RunsPage.tsx`**

Estructura (el detalle de props sale de las primitivas de la Task 1):

```tsx
export default function RunsPage() {
  const [rows, setRows] = useState<RunRow[] | null>(null)
  const [query, setQuery] = useState('')
  const [segment, setSegment] = useState<Segment>('all')
  const [page, setPage] = useState(1)
  const [sort, setSort] = useState<SortState>({ key: 'started_at', dir: 'desc' })
  const [confirmId, setConfirmId] = useState<string | null>(null)
  // … carga con polling solo si hay alguna corrida en curso (4 s)

  const filtered = useMemo(() => { /* segmento → query → orden */ }, [rows, query, segment, sort])
  const pages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE))
  const visible = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)

  return (
    <>
      <PageHeader
        title="Corridas"
        meta={`${rows?.length ?? 0} en total · ${running} en curso`}
        actions={<Button variant="primary" onClick={() => nav('/compose')}>Nueva corrida</Button>}
      />
      {liveRun && (
        <Banner tone="live" action={<Button onClick={() => nav(`/runs/${liveRun.run_id}`)}>Ver en vivo</Button>}>
          <b>{liveRun.name ?? liveRun.run_id}</b> está procesando ahora
          {liveDetections != null && ` — ${liveDetections} detecciones`}
          {liveAlerts != null && `, ${liveAlerts} alertas confirmadas`}
        </Banner>
      )}
      <div className="eo-toolbar">
        <SearchInput value={query} onChange={(v) => { setQuery(v); setPage(1); setConfirmId(null) }}
                     placeholder="Buscar por nombre o identificador"
                     ariaLabel="Buscar corridas por nombre o identificador" />
        <SegmentedControl value={segment} options={SEGMENTS}
                          onChange={(v) => { setSegment(v as Segment); setPage(1); setConfirmId(null) }} />
        <span className="eo-toolbar__count eo-mono">{filtered.length} de {rows?.length ?? 0}</span>
      </div>
      <Card>
        <Table>{/* thead con SortableHeader, tbody con las filas */}</Table>
      </Card>
      {pages > 1 && (
        <nav className="eo-pager" aria-label="Paginación de corridas">
          <Button disabled={page === 1} onClick={() => setPage((p) => p - 1)}>Anterior</Button>
          <span className="eo-mono">Página {page} de {pages}</span>
          <Button disabled={page === pages} onClick={() => setPage((p) => p + 1)}>Siguiente</Button>
        </nav>
      )}
    </>
  )
}
```

Cada fila:

```tsx
{/* RowNameCell no linkea (solo toma `title` y `subtitle`): el enlace va adentro. */}
<tr key={row.run_id} className={isRunning(row) ? 'eo-row--live' : undefined}>
  <RowNameCell
    title={<Link to={`/runs/${row.run_id}`}>{row.name ?? row.run_id}</Link>}
    subtitle={row.run_id}
  />
  <td><Badge tone={runStatusTone(row)}>{runStatusLabel(row)}</Badge></td>
  <MonoCell>{row.model ?? '—'}</MonoCell>
  <td>{sourceLabel(row.source_type)}</td>
  <MonoCell>{row.prompt_set_id ?? '—'}</MonoCell>
  <NumCell>{row.fps_effective?.toFixed(1).replace('.', ',') ?? '—'}</NumCell>
  <NumCell>{row.total_detections ?? '—'}</NumCell>
  <NumCell>{row.duration_seconds != null ? `${row.duration_seconds.toFixed(1).replace('.', ',')} s` : '—'}</NumCell>
  <td className="eo-cell--muted">{hace(row.started_at, row.run_id)}</td>
  <td className="eo-cell--actions">
    {confirmId === row.run_id
      ? <InlineDeleteConfirm onConfirm={() => handleDelete(row)} onCancel={() => setConfirmId(null)} />
      : <Button variant="ghost" aria-label={`Borrar ${row.run_id}`} onClick={() => setConfirmId(row.run_id)}>×</Button>}
  </td>
</tr>
```

Conservar del código actual: `parseRunIdDate`, `hace`, y el manejo de `deleteRun` con errores parciales por plano.

- [ ] **Step 5: CSS en `src/styles/ui.css`**

```css
.eo-toolbar { display: flex; align-items: center; gap: 10px; padding: 0 0 10px; flex-wrap: wrap; }
.eo-toolbar__count { margin-left: auto; font-size: 11px; color: var(--tx3); }
.eo-pager { display: flex; align-items: center; gap: 12px; justify-content: flex-end;
            padding: 10px 0 0; font-size: 11.5px; color: var(--tx3); }
.eo-row--live { box-shadow: inset 2px 0 0 var(--live); }
.eo-cell--muted { color: var(--tx4); font-size: 11px; }
.eo-cell--actions { text-align: right; width: 1%; white-space: nowrap; }
```

- [ ] **Step 6: Correr los tests y verificar que pasan**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/RunsPage.test.tsx`
Expected: PASS.

- [ ] **Step 7: Verificación visual contra el prototipo**

Los servicios y los servidores de desarrollo ya quedaron levantados en la sesión de diseño. Si no están:

```bash
cd /home/simonll4/projects/e-ovrt_media-plane && (EOVRT_MODEL_REF=mock nohup .venv/bin/python -m uvicorn --factory eovrt_media.service.app:create_app --port 8080 &)
cd /home/simonll4/projects/e-ovrt_control-plane && (nohup .venv/bin/eovrt-control serve --port 8081 &)
cd /home/simonll4/projects/e-ovrt_experimental-setup/webconsole/backend && (nohup .venv/bin/python -m uvicorn --factory eovrt_webconsole.app:create_app --port 8090 &)
cd /home/simonll4/projects/e-ovrt_experimental-setup/webconsole/frontend && (nohup npx vite --port 5173 --strictPort &)
```

Capturar (ojo: **HashRouter**, la ruta lleva `#/`):

```bash
S=/tmp/claude-1000/-home-simonll4-projects/700ff69c-0e0b-4099-8475-9aa7096b69ce/scratchpad
node $S/cdp-shoot.js 5173 $S/nuevo "01-corridas=/#/"
```

Comparar `$S/nuevo/01-corridas.png` contra `$S/proto/01-corridas.png`. Checklist:
alto de fila ≈32 px · encabezados en español · chips con icono+texto · `run_id` en monoespaciada bajo el nombre · buscador y segmentado presentes · paginador visible · sin botón "Borrar" repetido · la tabla se lee como una tarjeta sobre el lienzo, no flotando.

- [ ] **Step 8: Suite completa, build y lint. NO commitear. Reportar con la captura.**

```bash
cd webconsole/frontend && npm test 2>&1 | tail -20 && npm run build 2>&1 | tail -10
```

---

### Task 8: Detalle de corrida — encabezado, tira de KPI y línea de tiempo

Referencia: `proto-ref-02-corridas.md` y `scratchpad/proto/02-detalle-corrida.png`.

**Files:**
- Create: `src/components/RunKpiStrip.tsx`
- Create: `src/components/RunTimeline.tsx`
- Rewrite (parcial): `src/pages/RunDetailPage.tsx` — encabezado y las dos secciones nuevas; la traza queda para la Task 9
- Modify: `src/styles/ui.css`
- Test: `src/__tests__/RunKpiStrip.test.tsx`

**Interfaces:**
- Consumes: `Sparkline` (Task 2), `ActivityTimeline` (Task 4), `buildRunSeries`/`recentDelta`/`useFullTrace` (Task 6), `Meter` (Task 3).
- Produces:
  - `export default function RunKpiStrip({ summary, series, live }: { summary: Record<string, unknown> | undefined; series: RunSeries; live: boolean })`
  - `export default function RunTimeline({ frames, selected, onSelect, truncated }: { frames: TraceFrame[]; selected: number | null; onSelect: (frameIndex: number, position: number) => void; truncated: boolean })`

**Los 6 tiles** (rótulo · valor · unidad · sparkline · tono):

| Rótulo | Valor | Serie del sparkline | Tono |
|---|---|---|---|
| Cuadros por segundo | `summary.fps_effective` | `series.instantFps` | live |
| Latencia (mediana) | `summary.p50_latency_ms` ms | `series.instantFps` invertida — ver nota | live |
| Memoria de GPU | `summary.gpu_memory_peak_mb` MB | sin sparkline; `Meter` de uso | accent |
| Detecciones | `summary.total_detections` | `series.detectionsPerFrame` | accent |
| Descartes de entrega | `units_dropped / units_processed` % | acumulado de descartes | warn |
| Alertas confirmadas | `totals.alerts` | sin sparkline; "última hace X" | alert |

Nota sobre latencia: no hay serie de latencia por cuadro en la API. **No se inventa** — el tile de latencia muestra el número de `summary` sin sparkline, con `p95` como dato secundario. Un sparkline derivado del fps no es la latencia y no se dibuja.

**Delta de 30 s**: solo si `live === true`, vía `recentDelta`. En corrida terminada el delta se omite por completo, no se muestra "0".

- [ ] **Step 1: Escribir el test que falla**

```tsx
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import RunKpiStrip from '../components/RunKpiStrip'

const series = { detectionsPerFrame: [1, 2], instantFps: [null, 2], elapsedSeconds: [0, 0.5], totalSeconds: 0.5 }

describe('RunKpiStrip', () => {
  it('rotula con el glosario, nunca con la clave cruda del sumario', () => {
    render(<RunKpiStrip summary={{ fps_effective: 3.49, p50_latency_ms: 224 }} series={series} live={false} />)
    expect(screen.getByText('Cuadros por segundo')).toBeTruthy()
    expect(screen.getByText('Latencia (mediana)')).toBeTruthy()
    expect(screen.queryByText('fps_effective')).toBeNull()
    expect(screen.queryByText(/QUEUE_FULL/i)).toBeNull()
  })

  it('en corrida terminada no muestra variación: el delta no se inventa', () => {
    render(<RunKpiStrip summary={{ fps_effective: 3.49 }} series={series} live={false} />)
    expect(screen.queryByText(/Variación comparada/)).toBeNull()
  })

  it('en corrida en curso anuncia la ventana de comparación', () => {
    render(<RunKpiStrip summary={{ fps_effective: 3.49 }} series={series} live />)
    expect(screen.getByText(/Variación comparada con los últimos 30 s/)).toBeTruthy()
  })

  it('un valor ausente se muestra como sin dato, no como 0', () => {
    render(<RunKpiStrip summary={{}} series={series} live={false} />)
    expect(screen.getAllByText('—').length).toBeGreaterThan(0)
    expect(screen.queryByText('0')).toBeNull()
  })
})
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/RunKpiStrip.test.tsx`
Expected: FAIL — no existe el módulo.

- [ ] **Step 3: Implementar `RunKpiStrip.tsx`**

```tsx
import Sparkline from './charts/Sparkline'
import Meter from './charts/Meter'
import { recentDelta, type RunSeries } from '../runseries'

const nf = (v: number, d = 1) => v.toFixed(d).replace('.', ',')
const num = (s: Record<string, unknown> | undefined, k: string): number | null =>
  typeof s?.[k] === 'number' ? (s[k] as number) : null

function Kpi({ label, tone, value, unit, spark, foot, delta }: {
  label: string
  tone: 'live' | 'ok' | 'warn' | 'alert' | 'error' | 'accent'
  value: string
  unit?: string
  spark?: Array<number | null>
  foot?: React.ReactNode
  delta?: number | null
}) {
  return (
    <div className="eo-kpi">
      <span className="eo-kpi__label">
        <i className="eo-kpi__dot" style={{ background: `var(--${tone === 'accent' ? 'ac' : tone === 'alert' ? 'sr' : tone === 'warn' ? 'wn' : tone === 'error' ? 'er' : tone === 'ok' ? 'ok' : 'live'})` }} />
        {label}
      </span>
      <span className="eo-kpi__value">
        {value}{unit && <small>{unit}</small>}
        {delta != null && (
          <span className="eo-kpi__delta">{delta >= 0 ? '▲' : '▼'} {nf(Math.abs(delta), 1)}</span>
        )}
      </span>
      <span className="eo-kpi__foot">
        {spark && <Sparkline values={spark} tone={tone} />}
        {foot}
      </span>
    </div>
  )
}

export default function RunKpiStrip({ summary, series, live }: {
  summary: Record<string, unknown> | undefined
  series: RunSeries
  live: boolean
}) {
  const fps = num(summary, 'fps_effective')
  const p50 = num(summary, 'p50_latency_ms')
  const p95 = num(summary, 'p95_latency_ms')
  const gpu = num(summary, 'gpu_memory_peak_mb')
  const dets = num(summary, 'total_detections')
  const processed = num(summary, 'units_processed')
  const dropped = num(summary, 'units_dropped')
  const dropPct = dropped != null && processed ? (dropped / (processed + dropped)) * 100 : null

  const fpsDelta = live ? recentDelta(series.instantFps, series.elapsedSeconds) : null
  const detDelta = live ? recentDelta(series.detectionsPerFrame, series.elapsedSeconds) : null

  return (
    <section className="eo-kpis-wrap">
      {live && <p className="eo-kpis__note">Variación comparada con los últimos 30 s</p>}
      <div className="eo-kpis">
        <Kpi label="Cuadros por segundo" tone="live" value={fps != null ? nf(fps, 2) : '—'}
             spark={series.instantFps} delta={fpsDelta} />
        {/* Sin sparkline: la API no expone latencia por cuadro y no se inventa una. */}
        <Kpi label="Latencia (mediana)" tone="live" value={p50 != null ? nf(p50, 0) : '—'} unit=" ms"
             foot={p95 != null ? <span className="eo-kpi__sub">percentil 95: {nf(p95, 0)} ms</span> : undefined} />
        <Kpi label="Memoria de GPU" tone="accent" value={gpu != null ? nf(gpu, 0) : '—'} unit=" MB"
             foot={gpu != null ? <Meter segments={[{ value: gpu, tone: 'accent', label: 'en uso' }]} total={8192} /> : undefined} />
        <Kpi label="Detecciones" tone="accent" value={dets != null ? String(dets) : '—'}
             spark={series.detectionsPerFrame} delta={detDelta} />
        <Kpi label="Descartes de entrega" tone="warn" value={dropPct != null ? nf(dropPct, 1) : '—'} unit=" %"
             foot={dropped != null ? <span className="eo-kpi__sub">{dropped} cuadros descartados</span> : undefined} />
        <Kpi label="Alertas confirmadas" tone="alert" value={num(summary, 'alerts') != null ? String(num(summary, 'alerts')) : '—'} />
      </div>
    </section>
  )
}
```

- [ ] **Step 4: Correr y verificar que pasa**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/RunKpiStrip.test.tsx`
Expected: PASS, 4 tests.

- [ ] **Step 5: Implementar `RunTimeline.tsx`**

```tsx
import ActivityTimeline from './charts/ActivityTimeline'
import { Card } from './ui'
import type { TraceFrame } from '../types'

export default function RunTimeline({ frames, selected, onSelect, truncated }: {
  frames: TraceFrame[]
  selected: number | null
  onSelect: (frameIndex: number, position: number) => void
  truncated: boolean
}) {
  return (
    <Card title="Línea de tiempo" meta={`${frames.length} cuadros`}>
      <div className="eo-timeline__body">
        <ActivityTimeline frames={frames} selected={selected} onSelect={onSelect} />
        {truncated && (
          <p className="eo-cap">
            La traza se cortó en {frames.length} cuadros: la corrida tiene más de los que
            la consola trae de una vez. Lo que se ve acá es el comienzo, no la corrida entera.
          </p>
        )}
      </div>
    </Card>
  )
}
```

- [ ] **Step 6: Reescribir el encabezado y el cuerpo superior de `RunDetailPage.tsx`**

```tsx
const { frames, totals, controlError, loading, truncated, error: traceError } = useFullTrace(id, true)
const series = useMemo(() => buildRunSeries(frames), [frames])
const [selected, setSelected] = useState<number | null>(null)

return (
  <>
    <div className="eo-runhead">
      <h1>{run.name ?? run.run_id}</h1>
      <div className="eo-runhead__meta">
        <Badge tone={runStatusTone(run)}>{runStatusLabel(run)}</Badge>
        {topologyBadge(run.summary) && <Badge tone="neutral">{topologyLabel(run.summary)}</Badge>}
        <span className="eo-mono">{run.run_id}</span>
        <span className="eo-sep">·</span>
        <span>{sourceLabel(str(run.summary, 'source_type'))}</span>
        <span className="eo-sep">·</span>
        <span className="eo-mono">{nf(num(run.summary, 'duration_seconds') ?? 0, 1)} s</span>
      </div>
      <div className="eo-runhead__acts">{/* Detener / Evaluar / Borrar */}</div>
    </div>

    <RunKpiStrip summary={{ ...run.summary, alerts: totals?.alerts }} series={series} live={isLive(run)} />
    {loading
      ? <Card title="Línea de tiempo"><p className="eo-cap">Leyendo la traza…</p></Card>
      : <RunTimeline frames={frames} selected={selected} truncated={truncated}
                     onSelect={(_fi, pos) => setSelected(pos)} />}
    {traceError && <ErrorBanner>{traceError}</ErrorBanner>}
    {/* Las pestañas y el panel de traza llegan en la Task 9 */}
  </>
)
```

Agregar a `runview.ts`:

```ts
export function topologyLabel(summary: Record<string, unknown> | undefined): string | null {
  const badge = topologyBadge(summary)
  if (badge === 'two-node') return 'Dos equipos'
  if (badge === 'single-host') return 'Un solo equipo'
  return null
}
```

- [ ] **Step 7: CSS en `src/styles/ui.css`**

```css
.eo-runhead { display: flex; align-items: flex-start; gap: 12px;
              padding: 14px 0 12px; border-bottom: 1px solid var(--bd); flex-wrap: wrap; }
.eo-runhead h1 { margin: 0; font-size: 20px; font-weight: 500; letter-spacing: -.015em; }
.eo-runhead__meta { display: flex; align-items: center; gap: 8px; margin-top: 5px;
                    flex-wrap: wrap; font-size: 11.5px; color: var(--tx3); width: 100%; }
.eo-runhead__acts { margin-left: auto; display: flex; gap: 7px; align-items: center; }
.eo-sep { color: var(--tx4); }

.eo-kpis-wrap { padding: 14px 0 0; }
.eo-kpis__note { margin: 0 0 7px; font-size: 11px; color: var(--tx4); }
.eo-kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(146px, 1fr)); gap: 9px; }
.eo-kpi { background: var(--s1); border: 1px solid var(--bd); border-radius: var(--rc);
          padding: 11px 13px 12px; display: flex; flex-direction: column; }
.eo-kpi__label { font-size: 10.5px; color: var(--tx3); display: flex;
                 align-items: center; gap: 5px; line-height: 1.3; }
.eo-kpi__dot { width: 6px; height: 6px; border-radius: 2px; flex: none; display: block; }
.eo-kpi__value { font-size: 24px; font-weight: 500; letter-spacing: -.025em;
                 font-family: var(--fm); line-height: 1.1; margin-top: 2px;
                 display: flex; align-items: baseline; gap: 7px; flex-wrap: wrap; }
.eo-kpi__value small { font-size: 11px; color: var(--tx3); font-weight: 400; letter-spacing: 0; }
.eo-kpi__delta { font-size: 10.5px; font-family: var(--fm); color: var(--tx3); }
.eo-kpi__foot { margin-top: auto; padding-top: 11px; }
.eo-kpi__sub { font-size: 10.5px; color: var(--tx4); line-height: 1.5; }
.eo-timeline__body { padding: 10px 12px 12px; }
```

- [ ] **Step 8: Verificación visual**

```bash
S=/tmp/claude-1000/-home-simonll4-projects/700ff69c-0e0b-4099-8475-9aa7096b69ce/scratchpad
node $S/cdp-shoot.js 5173 $S/nuevo "02-detalle-corrida=/#/runs/run_20260728_004753_dbe_grounding_dino_5fd207"
```

Checklist contra `$S/proto/02-detalle-corrida.png`: seis tiles en una tira · sparklines dibujados · línea de tiempo con área y dos carriles · leyenda con formas distintas · sin volcado vertical de cuadros (todavía no está el panel de traza) · todo dentro de tarjetas.

- [ ] **Step 9: Suite, build. NO commitear. Reportar con la captura.**

---

### Task 9: Detalle de corrida — pestañas y panel de traza maestro-detalle

Esto es lo que reemplaza el scroll infinito de 1468 cuadros.

**Files:**
- Create: `src/components/FrameInspector.tsx`
- Create: `src/components/ConditionProgress.tsx`
- Rewrite: `src/components/TraceSection.tsx`
- Modify: `src/pages/RunDetailPage.tsx` (pestañas)
- Modify: `src/styles/ui.css`
- Modify: `src/__tests__/TraceSection.test.tsx`

**Interfaces:**
- Consumes: `Meter` (Task 3), `useFullTrace`/`buildRunSeries` (Task 6), `PreviewWithBoxes` (existente), `conditionLabel`/`CONTROL_DROP_REASONS` de `labels.ts`, `controlTone`/`frameHasActivity` de `traceview.ts`.
- Produces:
  - `export default function FrameInspector({ frame, runId, position, total, onStep }: { frame: TraceFrame | null; runId: string; position: number; total: number; onStep: (delta: number) => void })`
  - `export default function ConditionProgress({ frame }: { frame: TraceFrame | null })`
  - **`TraceSection` cambia de firma**: hoy trae la traza sola con `getTrace`; pasa a recibirla por props — `{ runId: string; frames: TraceFrame[]; totals: TraceTotals | null }`. Quien la trae es `useFullTrace` en `RunDetailPage`, para que la línea de tiempo y la lista compartan el mismo índice en vez de pedirlo dos veces.

**Composición del panel de Traza** — dos columnas, `grid-template-columns: 320px 1fr`:

- **Izquierda (maestro)**: casillas "Solo con actividad" / "Solo alertas", contador `"{visibles} de {total}"`, y la lista de cuadros. Cada ítem: índice, `unit_id` monoespaciado, cantidad de detecciones, punto de estado de entrega, chip "Alerta" si corresponde. La lista es **virtualizada por ventana**: se renderiza un tramo de 200 ítems alrededor del seleccionado, con botones "cargar más" arriba y abajo. Alto fijo con scroll propio (`max-height: 560px`), no crece con la corrida.
- **Derecha (detalle)**: banner de alerta si el cuadro tiene alertas (`conditionLabel` + cuadro y segundo del disparo) → visor `PreviewWithBoxes` → tarjeta "Detecciones" (clase monoespaciada + confianza) → tarjeta "Progreso de las condiciones" (`ConditionProgress`).

**Degradación del visor**: cuando no hay preview, `EmptyState` con el texto "Esta corrida se grabó sin vistas previas de cuadro. Las cajas no se pueden dibujar sin la imagen." — nunca un rectángulo negro.

- [ ] **Step 1: Escribir los tests que fallan**

Reescribir `src/__tests__/TraceSection.test.tsx` entero. `TraceSection` ya no pide la traza: la recibe por props (la trae `useFullTrace` en la página), así que el test no necesita mockear `../api` para los datos — solo para `artifactUrl`.

```tsx
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import TraceSection from '../components/TraceSection'
import type { TraceFrame, TraceTotals } from '../types'

vi.mock('../api', () => ({
  artifactUrl: (id: string, path: string) => `/api/runs/${id}/artifacts/${path}`,
}))

const frame = (i: number, over: Partial<TraceFrame> = {}): TraceFrame => ({
  frame_index: i,
  unit_id: `frame_${String(i).padStart(6, '0')}`,
  timestamp_ms: i * 250,
  detections: [],
  control: 'received',
  progress: [],
  alert: [],
  active_patterns: [],
  ...over,
})

const totals = (frames: number): TraceTotals => ({
  frames, detections: 0, dropped_by_reason: {}, alerts: 0, received: null, not_received: null,
})

const many = Array.from({ length: 1468 }, (_, i) => frame(i))

const few = [
  frame(0),
  ...Array.from({ length: 8 }, (_, i) => frame(i + 1)),
  frame(9, { detections: [{ label: 'person', confidence: 0.9 }] }),
]

const withAlert = [
  ...Array.from({ length: 19 }, (_, i) => frame(i)),
  frame(19, {
    detections: [{ label: 'person', confidence: 0.85 }],
    alert: [{ condition_id: 'CR-01', severity: 'high' }],
    progress: [{ condition_id: 'CR-01', progress: 1 }],
  }),
]

const droppedFrames = [
  frame(0, { control: 'dropped:queue_full' }),
  frame(1, { control: 'dropped:lo_que_sea' }),
]

describe('TraceSection', () => {
  it('no vuelca todos los cuadros: la lista se acota y dice el total', () => {
    render(<TraceSection runId="r" frames={many} totals={totals(1468)} />)
    expect(screen.getAllByRole('option').length).toBeLessThanOrEqual(200)
    expect(screen.getByText(/1468/)).toBeTruthy()
  })

  it('elegir un cuadro muestra su detalle a la derecha', () => {
    render(<TraceSection runId="r" frames={few} totals={totals(few.length)} />)
    fireEvent.click(screen.getByText('frame_000009'))
    expect(screen.getByText('person')).toBeTruthy()
  })

  it('el banner de alerta nombra la condición, no solo el código', () => {
    render(<TraceSection runId="r" frames={withAlert} totals={totals(withAlert.length)} />)
    fireEvent.click(screen.getByText('frame_000019'))
    expect(screen.getByText(/CR-01 — Presencia de persona sin casco/)).toBeTruthy()
  })

  it('traduce el motivo de descarte conocido y muestra crudo el desconocido', () => {
    render(<TraceSection runId="r" frames={droppedFrames} totals={totals(2)} />)
    fireEvent.click(screen.getByText('frame_000000'))
    expect(screen.getByText('cola llena')).toBeTruthy()
    fireEvent.click(screen.getByText('frame_000001'))
    expect(screen.getByText('lo_que_sea')).toBeTruthy()
  })

  it('sin preview explica por qué, en vez de dejar un rectángulo negro', () => {
    render(<TraceSection runId="r" frames={few} totals={totals(few.length)} />)
    fireEvent.click(screen.getByText('frame_000000'))
    fireEvent.error(screen.getByRole('img', { name: /Cuadro 0/ }))
    expect(screen.getByText(/sin vistas previas de cuadro/i)).toBeTruthy()
  })

  it('el filtro de solo alertas deja únicamente los cuadros con alerta', () => {
    render(<TraceSection runId="r" frames={withAlert} totals={totals(withAlert.length)} />)
    fireEvent.click(screen.getByLabelText('Solo alertas'))
    expect(screen.getAllByRole('option')).toHaveLength(1)
  })
})
```

**Ojo con el vocabulario de descartes**: `controlLabel` recorta el prefijo `dropped:` y devuelve el resto. Para que `dropped:queue_full` se lea "cola llena" hay que hacerlo pasar por `CONTROL_DROP_REASONS` de `labels.ts`, con caída al código crudo. Ajustar `controlLabel` en `traceview.ts`:

```ts
import { CONTROL_DROP_REASONS } from './labels'

export function controlLabel(control: string): string {
  if (control === 'received') return 'recibido'
  if (control === 'not_received') return 'no recibido'
  if (control.startsWith('dropped:')) {
    const code = control.slice('dropped:'.length)
    return CONTROL_DROP_REASONS[code] ?? code
  }
  return control
}

/** true cuando la etiqueta es un código crudo sin traducir: la interfaz lo
 *  muestra en monoespaciada para que se lea como dato y no como prosa. */
export function controlLabelIsRaw(control: string): boolean {
  if (control === 'received' || control === 'not_received') return false
  if (control.startsWith('dropped:')) {
    return !(control.slice('dropped:'.length) in CONTROL_DROP_REASONS)
  }
  return true
}
```

Actualizar `src/__tests__/traceview.test.ts` a este comportamiento.

- [ ] **Step 2: Correr y verificar que falla**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/TraceSection.test.tsx`
Expected: FAIL en los 5.

- [ ] **Step 3: Implementar `ConditionProgress.tsx`**

```tsx
import Meter from './charts/Meter'
import { conditionLabel } from '../labels'
import type { TraceFrame } from '../types'

export default function ConditionProgress({ frame }: { frame: TraceFrame | null }) {
  const rows = frame?.progress ?? []
  if (!rows.length) {
    return <p className="eo-cap">Ninguna condición en progreso en este cuadro.</p>
  }
  return (
    <ul className="eo-condprog">
      {rows.map((p) => {
        const pct = Math.round(Math.min(1, Math.max(0, p.progress ?? 0)) * 100)
        return (
          <li key={p.condition_id}>
            <span className="eo-condprog__name">{conditionLabel(p.condition_id)}</span>
            <Meter segments={[{ value: pct, tone: pct >= 100 ? 'alert' : 'warn', label: 'avance' }]}
                   total={100} />
            <span className="eo-condprog__pct eo-mono">{pct} %</span>
          </li>
        )
      })}
    </ul>
  )
}
```

`TraceProgress` es `{ condition_id: string; progress: number; elapsed_ms?: number | null; threshold_ms?: number | null; mode?: string | null }` — verificado. `progress` viene normalizado en [0,1].

- [ ] **Step 4: Implementar `FrameInspector.tsx`**

```tsx
import PreviewWithBoxes from './PreviewWithBoxes'
import ConditionProgress from './ConditionProgress'
import { Badge, Banner, Button, Card, EmptyState } from './ui'
import { conditionLabel } from '../labels'
import { controlLabel, controlTone } from '../traceview'
import type { TraceFrame } from '../types'

export default function FrameInspector({ frame, runId, position, total, onStep }: {
  frame: TraceFrame | null
  runId: string
  position: number
  total: number
  onStep: (delta: number) => void
}) {
  if (!frame) {
    return <EmptyState hint="Elegí un cuadro en la lista o en la línea de tiempo.">
      Ningún cuadro seleccionado
    </EmptyState>
  }
  const alerts = frame.alert ?? []
  const dets = frame.detections ?? []
  return (
    <div className="eo-inspector">
      {/* TraceAlert solo tiene `condition_id` y `severity` — no hay `alert_id`.
          La clave combina condición y severidad, que es lo único único por fila. */}
      {alerts.map((a) => (
        <Banner key={`${a.condition_id}-${a.severity}`} tone="warn">
          <b>Alerta confirmada — {conditionLabel(a.condition_id)}</b>
          <div>Se disparó en el cuadro {frame.frame_index}.</div>
        </Banner>
      ))}

      <Card
        title={`Cuadro ${frame.frame_index ?? position}`}
        meta={<>
          <span className="eo-mono">unidad {frame.unit_id}</span>
          <Badge tone={controlTone(frame.control)}>{controlLabel(frame.control)}</Badge>
          <Button aria-label="Cuadro anterior" disabled={position <= 0} onClick={() => onStep(-1)}>‹</Button>
          <Button aria-label="Cuadro siguiente" disabled={position >= total - 1} onClick={() => onStep(1)}>›</Button>
        </>}
      >
        {/* PreviewWithBoxes toma `src`/`alt`/`detections`/`width` — no `runId`/`unitId`.
            La ruta de la preview es la que ya usa TraceSection hoy. */}
        <PreviewWithBoxes
          src={artifactUrl(runId, `previews/${frame.unit_id}.preview.jpg`)}
          alt={`Cuadro ${frame.frame_index} de la corrida ${runId}`}
          detections={dets}
          width={520}
          emptyMessage="Esta corrida se grabó sin vistas previas de cuadro. Las cajas no se pueden dibujar sin la imagen."
        />
      </Card>

      <div className="eo-inspector__split">
        <Card title="Detecciones" meta={String(dets.length)}>
          {dets.length === 0
            ? <p className="eo-cap">Ninguna detección en este cuadro.</p>
            : <ul className="eo-detlist">
                {dets.map((d, i) => (
                  <li key={`${d.label}-${i}`}>
                    <span className="eo-detlist__label eo-mono">{d.label}</span>
                    <span className="eo-detlist__score eo-mono">{d.confidence.toFixed(2).replace('.', ',')}</span>
                  </li>
                ))}
              </ul>}
        </Card>
        <Card title="Progreso de las condiciones">
          <ConditionProgress frame={frame} />
        </Card>
      </div>
    </div>
  )
}
```

`PreviewWithBoxes` necesita la prop `emptyMessage` nueva. Hoy su rama de "sin imagen" (estado `hidden`, disparado por `onError` del `<img>`) muestra el literal `sin preview`, que es lo que produce los rectángulos negros de la captura. Agregarla con default y usarla:

```tsx
export default function PreviewWithBoxes({
  src, alt, detections, width = 240,
  emptyMessage = 'sin vista previa',
}: {
  src: string
  alt: string
  detections: TraceDetection[]
  width?: number
  emptyMessage?: string
}) {
  // …
  if (hidden) {
    return (
      <span className="eo-preview eo-preview--empty" style={{ width }}>
        {emptyMessage}
      </span>
    )
  }
```

Y en `ui.css`, que el vacío se lea como una explicación y no como un agujero:

```css
.eo-preview--empty {
  display: flex; align-items: center; justify-content: center;
  min-height: 120px; padding: 16px; text-align: center;
  background: var(--sunken); border: 1px dashed var(--bd); border-radius: var(--r);
  font-size: 11.5px; color: var(--tx4); line-height: 1.5;
}
```

`TraceSection` ya importa `artifactUrl` de `../api`; `FrameInspector` también lo necesita.

- [ ] **Step 5: Reescribir `TraceSection.tsx` como maestro-detalle**

```tsx
const WINDOW = 200

export default function TraceSection({ runId, frames, totals }: {
  runId: string
  frames: TraceFrame[]
  totals: TraceTotals | null
}) {
  const [onlyActivity, setOnlyActivity] = useState(false)
  const [onlyAlerts, setOnlyAlerts] = useState(false)
  const [pos, setPos] = useState(0)
  const [anchor, setAnchor] = useState(0)

  const visible = useMemo(() => frames.filter((f) =>
    (!onlyActivity || frameHasActivity(f)) && (!onlyAlerts || (f.alert?.length ?? 0) > 0),
  ), [frames, onlyActivity, onlyAlerts])

  const from = Math.max(0, Math.min(anchor, Math.max(0, visible.length - WINDOW)))
  const slice = visible.slice(from, from + WINDOW)

  return (
    <div className="eo-trace">
      <Card className="eo-trace__master">
        <div className="eo-trace__filters">
          <label><input type="checkbox" checked={onlyActivity}
                        onChange={(e) => setOnlyActivity(e.target.checked)} /> Solo con actividad</label>
          <label><input type="checkbox" checked={onlyAlerts}
                        onChange={(e) => setOnlyAlerts(e.target.checked)} /> Solo alertas</label>
          <span className="eo-mono">{visible.length} de {totals?.frames ?? frames.length}</span>
        </div>
        {from > 0 && <Button onClick={() => setAnchor(Math.max(0, from - WINDOW))}>Cuadros anteriores</Button>}
        <ul className="eo-trace__list" role="listbox" aria-label="Cuadros de la traza">
          {slice.map((f, i) => (
            <li key={f.unit_id ?? i} role="option" aria-selected={from + i === pos}
                className={from + i === pos ? 'is-selected' : undefined}
                onClick={() => setPos(from + i)}>
              <span className="eo-mono">{f.frame_index}</span>
              <span className="eo-mono">{f.unit_id}</span>
              <span>{f.detections?.length || '—'}</span>
              {(f.alert?.length ?? 0) > 0 && <Badge tone="alert">Alerta</Badge>}
            </li>
          ))}
        </ul>
        {from + WINDOW < visible.length && (
          <Button onClick={() => setAnchor(from + WINDOW)}>Cuadros siguientes</Button>
        )}
      </Card>
      <div className="eo-trace__detail">
        <FrameInspector frame={visible[pos] ?? null} runId={runId}
                        position={pos} total={visible.length}
                        onStep={(d) => setPos((p) => Math.min(visible.length - 1, Math.max(0, p + d)))} />
      </div>
    </div>
  )
}
```

- [ ] **Step 6: Pestañas en `RunDetailPage.tsx`**

```tsx
const [tab, setTab] = useState<'trace' | 'summary' | 'eval' | 'files'>('trace')

<nav className="eo-tabs" role="tablist">
  <button role="tab" aria-selected={tab === 'trace'} onClick={() => setTab('trace')}>
    Traza <span className="eo-tabs__count eo-mono">{frames.length}</span>
  </button>
  <button role="tab" aria-selected={tab === 'summary'} onClick={() => setTab('summary')}>Resumen</button>
  <button role="tab" aria-selected={tab === 'eval'} onClick={() => setTab('eval')}>Evaluación</button>
  <button role="tab" aria-selected={tab === 'files'} onClick={() => setTab('files')}>Archivos</button>
</nav>
{tab === 'trace' && <TraceSection runId={id} frames={frames} totals={totals} />}
{tab === 'summary' && <RunSummaryCard summary={run.summary} />}
{tab === 'eval' && <EvalSection runId={id} />}
{tab === 'files' && <RunFilesCard runId={id} />}
```

`RunSummaryCard` y `RunFilesCard` son extracciones del marcado que ya vive en `RunDetailPage.tsx` hoy (bloque de modelo/prompts/unidades/por clase, y la lista de artefactos): moverlos a componentes chicos dentro del mismo archivo, con los rótulos pasados por glosario (`POR LABEL` → "Por clase", `QUEUE_FULL` → "cola llena").

Conectar la línea de tiempo con la selección: `onSelect` de `RunTimeline` mueve `pos` en `TraceSection`. Subir `pos` a `RunDetailPage` y pasarlo como prop controlada a ambos.

- [ ] **Step 7: CSS en `src/styles/ui.css`**

```css
.eo-tabs { display: flex; gap: 4px; border-bottom: 1px solid var(--bd); margin: 16px 0 12px; }
.eo-tabs button { background: none; border: none; padding: 8px 12px; color: var(--tx3);
                  font-size: 13px; border-bottom: 2px solid transparent; margin-bottom: -1px; }
.eo-tabs button[aria-selected='true'] { color: var(--tx); border-bottom-color: var(--ac); }
.eo-tabs__count { font-size: 10.5px; color: var(--tx4); margin-left: 5px; }

.eo-trace { display: grid; grid-template-columns: 320px 1fr; gap: 12px; align-items: start; }
@media (max-width: 900px) { .eo-trace { grid-template-columns: 1fr; } }
.eo-trace__filters { display: flex; align-items: center; gap: 12px; padding: 9px 12px;
                     font-size: 11.5px; color: var(--tx2); border-bottom: 1px solid var(--bd); }
.eo-trace__filters .eo-mono { margin-left: auto; color: var(--tx4); font-size: 10.5px; }
.eo-trace__list { list-style: none; margin: 0; padding: 0; max-height: 560px; overflow-y: auto; }
.eo-trace__list li { display: flex; align-items: center; gap: 10px; height: var(--row);
                     padding: 0 12px; border-bottom: 1px solid var(--bd);
                     font-size: 11.5px; cursor: pointer; }
.eo-trace__list li:hover { background: var(--s2); }
.eo-trace__list li.is-selected { background: var(--ac-bg); color: var(--ac-tx);
                                 box-shadow: inset 2px 0 0 var(--ac); }
.eo-inspector { display: flex; flex-direction: column; gap: 12px; }
.eo-inspector__split { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
@media (max-width: 900px) { .eo-inspector__split { grid-template-columns: 1fr; } }
.eo-detlist { list-style: none; margin: 0; padding: 0; }
.eo-detlist li { display: flex; align-items: center; gap: 8px; height: var(--row);
                 padding: 0 12px; border-bottom: 1px solid var(--bd); font-size: 12px; }
.eo-detlist__score { margin-left: auto; color: var(--tx3); }
.eo-condprog { list-style: none; margin: 0; padding: 8px 12px 12px; }
.eo-condprog li { display: grid; grid-template-columns: 1fr 90px 48px;
                  align-items: center; gap: 10px; padding: 6px 0; font-size: 12px; }
.eo-condprog__pct { text-align: right; color: var(--tx3); font-size: 11px; }
```

- [ ] **Step 8: Correr los tests y verificar que pasan**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/TraceSection.test.tsx src/__tests__/RunDetailPage.test.tsx`
Expected: PASS.

- [ ] **Step 9: Verificación visual**

```bash
S=/tmp/claude-1000/-home-simonll4-projects/700ff69c-0e0b-4099-8475-9aa7096b69ce/scratchpad
node $S/cdp-shoot.js 5173 $S/nuevo "02-detalle-corrida=/#/runs/run_20260728_004753_dbe_grounding_dino_5fd207"
```

Checklist: **la página cabe en pantalla y no scrollea miles de píxeles** · lista de cuadros con scroll propio a la izquierda · detalle a la derecha · pestañas visibles · sin `SUMMARY`/`QUEUE_FULL`/`POR LABEL` en mayúsculas ni en inglés.

- [ ] **Step 10: Suite, build. NO commitear. Reportar con la captura.**

---

### Task 10: Pantalla Comparar

Referencia: `proto-ref-03-experimentos-comparar.md` y `scratchpad/proto/06-comparar.png`.

**Files:**
- Rewrite: `src/pages/ComparePage.tsx`
- Modify: `src/styles/ui.css`
- Modify: `src/__tests__/ComparePage.test.tsx`

**Interfaces:**
- Consumes: `GroupedBars` (Task 5), `listRuns()`, `getCompare(ids)`; `CompareResult`/`CompareRunEntry` de `types`.
- Produces: conserva `export function bestPerRow(values: Array<number | null>): number`.

**Composición**: dos columnas, `grid-template-columns: 340px 1fr`.

- **Izquierda**: `Card` "Corridas evaluadas" con meta `"{n} de {m} elegidas"`. Cada ítem: casilla + nombre (no `run_id` crudo) + segunda línea monoespaciada con modelo · conjunto de evaluación · antigüedad. Nota al pie: "Las corridas sin evaluación no aparecen acá: se evalúan desde el detalle de cada una."
- **Derecha**: `Card` "Métricas" con meta "Mejor valor por fila en verde" — tabla con una columna por corrida elegida, encabezado con la marca de color de su serie. Filas: `Precisión · {clase}` por cada clase, `Exhaustividad CR-01`, `Precisión media (mAP@0.5)`. Debajo, `Card` "Precisión por clase" con `GroupedBars`.
- **Aviso de conjunto distinto**: si las corridas elegidas no comparten `bench_split`, `Banner tone="warn"` — "Estás comparando corridas evaluadas contra conjuntos distintos ({a} y {b}). Los números no son comparables entre sí." El dato ya se carga hoy.

- [ ] **Step 1: Escribir los tests que fallan**

```tsx
it('lista las corridas por nombre, no por identificador crudo', async () => {
  render(<MemoryRouter><ComparePage /></MemoryRouter>)
  expect(await screen.findByText('Barrido diurno')).toBeTruthy()
})

it('avisa cuando se comparan conjuntos de evaluación distintos', async () => {
  render(<MemoryRouter><ComparePage /></MemoryRouter>)
  fireEvent.click(await screen.findByLabelText(/Barrido diurno/))
  fireEvent.click(screen.getByLabelText(/Interior pasillo norte/))
  expect(await screen.findByText(/conjuntos distintos/i)).toBeTruthy()
})

it('nombra las métricas en español con el nombre técnico entre paréntesis', async () => {
  // dos corridas del mismo bench_split elegidas
  expect(await screen.findByText('Precisión media (mAP@0.5)')).toBeTruthy()
  expect(screen.getByText('Exhaustividad CR-01')).toBeTruthy()
})

it('resalta el mejor valor de cada fila', async () => {
  const { container } = render(<MemoryRouter><ComparePage /></MemoryRouter>)
  // …elegir dos
  expect(container.querySelectorAll('.eo-best').length).toBeGreaterThan(0)
})

it('dibuja las barras solo con dos o más corridas elegidas', async () => {
  render(<MemoryRouter><ComparePage /></MemoryRouter>)
  expect(screen.getByText(/Elegí al menos dos corridas/)).toBeTruthy()
})
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/ComparePage.test.tsx`
Expected: FAIL.

- [ ] **Step 3: Reescribir `ComparePage.tsx`**

```tsx
const evaluables = (rows ?? []).filter((r) => r.evaluated)
const chosen = evaluables.filter((r) => selected.includes(r.run_id))
const splits = [...new Set(chosen.map((r) => r.bench_split).filter(Boolean))]
const mixedSplits = splits.length > 1

return (
  <>
    <PageHeader title="Comparar corridas"
                meta="Solo se comparan corridas ya evaluadas contra un conjunto anotado" />
    {mixedSplits && (
      <Banner tone="warn">
        Estás comparando corridas evaluadas contra conjuntos distintos
        (<span className="eo-mono">{splits.join('</span> y <span className="eo-mono">')}</span>).
        Los números no son comparables entre sí.
      </Banner>
    )}
    <div className="eo-compare">
      <Card title="Corridas evaluadas" meta={`${selected.length} de ${evaluables.length} elegidas`}>
        <ul className="eo-picklist">
          {evaluables.map((r) => (
            <li key={r.run_id}>
              <label>
                <input type="checkbox" checked={selected.includes(r.run_id)}
                       onChange={() => toggle(r.run_id)}
                       aria-label={r.name ?? r.run_id} />
                <span className="eo-picklist__name">{r.name ?? r.run_id}</span>
                <span className="eo-picklist__meta eo-mono">
                  {r.model ?? '—'} · {r.bench_split ?? 'sin conjunto'} · {hace(r.started_at, r.run_id)}
                </span>
              </label>
            </li>
          ))}
        </ul>
        <p className="eo-cap">
          Las corridas sin evaluación no aparecen acá: se evalúan desde el detalle de cada una.
        </p>
      </Card>

      <div className="eo-compare__right">
        {selected.length < 2 ? (
          <EmptyState hint="La comparación necesita al menos dos.">
            Elegí al menos dos corridas
          </EmptyState>
        ) : result && (
          <>
            <Card title="Métricas" meta="Mejor valor por fila en verde">
              <Table>
                <thead>
                  <tr>
                    <th>Métrica</th>
                    {result.runs.map((r, i) => (
                      <th key={r.run_id} className="eo-num">
                        <span className="eo-bars__key"
                              style={{ background: SERIES_COLORS[i % SERIES_COLORS.length] }} />
                        {r.label}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {result.classes.map((cls) => (
                    <MetricRow key={cls} name={<>Precisión · <span className="eo-mono">{cls}</span></>}
                               values={result.ap_by_class[cls]} />
                  ))}
                  <MetricRow name="Exhaustividad CR-01"
                             values={result.runs.map((r) => r.cr01_detection_recall)} />
                  <MetricRow name="Precisión media (mAP@0.5)"
                             values={result.runs.map((r) => r.mAP50)} />
                </tbody>
              </Table>
            </Card>
            <Card title="Precisión por clase">
              <div className="eo-card__body">
                <GroupedBars
                  groups={result.classes}
                  series={result.runs.map((_r, i) => result.classes.map((c) => result.ap_by_class[c][i]))}
                  labels={result.runs.map((r) => r.label)}
                />
                <p className="eo-cap">
                  0 es ninguna detección correcta y 1 es todas. El valor más alto de cada
                  clase queda resaltado.
                </p>
              </div>
            </Card>
          </>
        )}
        {result?.skipped?.length ? (
          <p className="eo-cap">
            Quedaron afuera {result.skipped.length} corridas sin métricas comparables:{' '}
            <span className="eo-mono">{result.skipped.join(', ')}</span>.
          </p>
        ) : null}
      </div>
    </div>
  </>
)
```

`MetricRow` se conserva del archivo actual, cambiando `name: string` a `name: ReactNode` y formateando los valores con coma decimal a 3 dígitos.

- [ ] **Step 4: Correr y verificar que pasa**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/ComparePage.test.tsx`
Expected: PASS.

- [ ] **Step 5: CSS en `src/styles/ui.css`**

```css
.eo-compare { display: grid; grid-template-columns: 340px 1fr; gap: 12px; align-items: start; }
@media (max-width: 980px) { .eo-compare { grid-template-columns: 1fr; } }
.eo-compare__right { display: flex; flex-direction: column; gap: 12px; }
.eo-picklist { list-style: none; margin: 0; padding: 0; }
.eo-picklist li { border-bottom: 1px solid var(--bd); }
.eo-picklist label { display: grid; grid-template-columns: auto 1fr;
                     gap: 4px 9px; padding: 9px 12px; cursor: pointer; }
.eo-picklist label:hover { background: var(--s2); }
.eo-picklist__name { font-size: 12.5px; }
.eo-picklist__meta { grid-column: 2; font-size: 10.5px; color: var(--tx3); }
.eo-card__body { padding: 12px; }
.eo-best { color: var(--ok); }
```

- [ ] **Step 6: Verificación visual**

```bash
S=/tmp/claude-1000/-home-simonll4-projects/700ff69c-0e0b-4099-8475-9aa7096b69ce/scratchpad
node $S/cdp-shoot.js 5173 $S/nuevo "06-comparar=/#/compare"
```

Checklist contra `$S/proto/06-comparar.png`: dos paneles · sin `run_id`s crudos en la lista · tabla con mejor valor resaltado · barras con eje, etiquetas de valor y leyenda nombrada.

- [ ] **Step 7: Suite, build. NO commitear. Reportar con la captura.**

---

### Task 11: Pantalla Detalle de experimento

Referencia: `proto-ref-03-experimentos-comparar.md` y `scratchpad/proto/05-detalle-exp.png`.

**Files:**
- Rewrite: `src/pages/ExperimentDetailPage.tsx`
- Modify: `src/styles/ui.css`
- Modify: `src/__tests__/ExperimentDetailPage.test.tsx`, `src/__tests__/ExperimentDetailPageRiskBanner.test.tsx`

**Interfaces:**
- Consumes: `Meter` (Task 3); `getExperiment(id)`, `getExperimentAlerts(id)`, `getExperimentReport(id)`; `conditionLabel`, `APPLICABILITY_STATUS`, `APPLICABILITY_CAUSE`, `applicabilityLabel` de `labels.ts`.

**Composición**:

1. Encabezado: nombre del manifiesto, veredicto como `Badge` (`"{n} criterios sin cumplir"` en tono `warn`, o `"Todos los criterios cumplidos"` en `ok`), id monoespaciado, antigüedad, acciones (Ver la corrida · Descargar reporte).
2. Tres tiles con `Meter`: **Criterios cumplidos** (`{ok} de {total}`, meter ok/error) · **Alertas emitidas** (`{n} en total`, meter segmentado por severidad alta/media/baja) · **Sin poder medir** (`{n} de {total}`, meter neutral), con el motivo abajo.
3. `Card` "Criterios del experimento": tabla **Criterio · Medido · Límite · Resultado · Por qué**. La columna "Por qué" es lo que hace defendible la tabla: un criterio que no cumple explica su causa; uno que no se pudo medir explica por qué no, vía `applicabilityLabel(cause, APPLICABILITY_CAUSE)`.
4. `Card` "Alertas emitidas": Alerta (mono) · Condición (`conditionLabel`) · Severidad (`Badge`) · Momento.
5. `Card` "Trazabilidad": corrida de video, corrida de reglas, manifiesto — todos monoespaciados.

Se mantiene la lectura tolerante del reporte: `row.name ?? row.metrica ?? row.metric` y equivalentes para valor/límite. No hay contrato fijo y no se toca el backend.

- [ ] **Step 1: Escribir los tests que fallan**

```tsx
it('el veredicto va en el encabezado y cuenta los criterios sin cumplir', async () => {
  render(<MemoryRouter initialEntries={['/experiments/exp_1']}><Routes>
    <Route path="/experiments/:id" element={<ExperimentDetailPage />} /></Routes></MemoryRouter>)
  expect(await screen.findByText('1 criterio sin cumplir')).toBeTruthy()
})

it('cada criterio muestra su valor medido junto al límite', async () => {
  expect(await screen.findByText('Latencia de alerta')).toBeTruthy()
  expect(screen.getByText('≤ 3 s')).toBeTruthy()
})

it('un criterio que no cumple explica por qué', async () => {
  expect(await screen.findByText(/disparó 3 alertas sin respaldo/)).toBeTruthy()
})

it('un criterio sin dato explica la causa en español, no con el código', async () => {
  expect(await screen.findByText('Sin dato')).toBeTruthy()
  expect(screen.getByText(/fuente no temporal/)).toBeTruthy()
  expect(screen.queryByText('non_temporal_source')).toBeNull()
})

it('las alertas nombran su condición además del código', async () => {
  expect(await screen.findByText(/CR-01 — Presencia de persona sin casco/)).toBeTruthy()
})
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/ExperimentDetailPage.test.tsx`
Expected: FAIL.

- [ ] **Step 3: Reescribir la página**

Fila de criterio:

```tsx
<tr key={key}>
  <td>{nombre}</td>
  <NumCell>{medido != null ? fmt(medido) : '—'}</NumCell>
  <NumCell>{limite ?? '—'}</NumCell>
  <td>
    {estado === 'computed'
      ? (cumple
          ? <Badge tone="ok">Cumple</Badge>
          : <Badge tone="error">No cumple</Badge>)
      : <Badge tone="neutral">Sin dato</Badge>}
  </td>
  <td className="eo-cell--why">
    {estado === 'computed'
      ? (cumple ? '—' : porQue ?? '—')
      : `${applicabilityLabel(estado, APPLICABILITY_STATUS)}: ${applicabilityLabel(causa, APPLICABILITY_CAUSE)}`}
  </td>
</tr>
```

Los tres tiles:

```tsx
<div className="eo-kpis">
  <div className="eo-kpi">
    <span className="eo-kpi__label">Criterios cumplidos</span>
    <span className="eo-kpi__value">{ok}<small> de {total}</small></span>
    <span className="eo-kpi__foot">
      <Meter total={total} segments={[
        { value: ok, tone: 'ok', label: 'cumplen' },
        { value: total - ok - sinDato, tone: 'error', label: 'no cumplen' },
      ]} />
      {primerFallo && <span className="eo-kpi__sub">{primerFallo}</span>}
    </span>
  </div>
  {/* Alertas emitidas y Sin poder medir, mismo patrón */}
</div>
```

- [ ] **Step 4: Correr y verificar que pasa**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/ExperimentDetailPage.test.tsx src/__tests__/ExperimentDetailPageRiskBanner.test.tsx`
Expected: PASS.

- [ ] **Step 5: CSS en `src/styles/ui.css`**

```css
.eo-cell--why { color: var(--tx3); font-size: 11.5px; }
.eo-trace-list { list-style: none; margin: 0; padding: 10px 12px; }
.eo-trace-list li { display: grid; grid-template-columns: 150px 1fr;
                    gap: 10px; padding: 4px 0; font-size: 12px; }
.eo-trace-list dt { color: var(--tx3); }
```

- [ ] **Step 6: Verificación visual**

**Ojo — hace falta ejecutar un experimento primero.** Verificado en este entorno: los 10 manifiestos de `/api/experiments/manifests` tienen `experiment_id: null` y `/api/experiments/current` devuelve 404. **No hay ningún experimento ejecutado**, así que `/#/experiments/:id` no tiene contra qué renderizar. Lanzar uno:

```bash
node -e "fetch('http://localhost:8090/api/experiments/run',{method:'POST',
  headers:{'content-type':'application/json'},body:JSON.stringify({slug:'diag_riesgo_activo'})})
  .then(r=>r.json()).then(j=>console.log(j))"
```

`diag_riesgo_activo` es el manifiesto correcto para esto: corre control y media, y ya tiene corridas exitosas en el banco. Esperar a que termine (`/api/experiments/current` deja de devolver el estado `running`) y usar el `experiment_id` que devolvió:

```bash
S=/tmp/claude-1000/-home-simonll4-projects/700ff69c-0e0b-4099-8475-9aa7096b69ce/scratchpad
node $S/cdp-shoot.js 5173 $S/nuevo "05-detalle-exp=/#/experiments/$EXP_ID"
```

Si lanzar el experimento no es viable en el momento (el motor de detección está con `mock` y el manifiesto puede pedir otro modelo), **decilo en el reporte** en vez de dar la pantalla por verificada: los tests con fixtures cubren la lógica, pero la composición visual queda sin confirmar hasta que haya un experimento real.

Checklist contra `$S/proto/05-detalle-exp.png`: veredicto como chip en el encabezado · tres tiles con medidor · tabla con Medido y Límite en columnas separadas · columna "Por qué" poblada · trazabilidad monoespaciada.

- [ ] **Step 7: Suite, build. NO commitear. Reportar con la captura.**

---

### Task 12: Cierre — inventario en cero y verificación visual completa

- [ ] **Step 1: Suite completa y build**

```bash
cd /home/simonll4/projects/e-ovrt_experimental-setup/webconsole/frontend
npm test 2>&1 | tail -30
npm run build 2>&1 | tail -10
```

Expected: **cero fallos**. Comparar contra `scratchpad/task1-fallos.txt`: todos los tests de ese inventario tienen que estar verdes ahora. Si alguno sigue rojo, es deuda de este plan, no una excusa.

- [ ] **Step 2: Suite del backend, para confirmar que no se tocó**

```bash
cd /home/simonll4/projects/e-ovrt_experimental-setup/webconsole/backend
.venv/bin/python -m pytest -q 2>&1 | tail -10
```

Expected: mismo resultado que antes de empezar. Hay un fallo preexistente conocido en `test_repo_frozen_sets_integrity` (dos YAML de prompts con enums viejos) que **no** es de este plan: si aparece, se reporta como preexistente, no se arregla acá.

- [ ] **Step 3: Capturar las 4 pantallas finales**

```bash
S=/tmp/claude-1000/-home-simonll4-projects/700ff69c-0e0b-4099-8475-9aa7096b69ce/scratchpad
node $S/cdp-shoot.js 5173 $S/final \
  "01-corridas=/#/" \
  "02-detalle-corrida=/#/runs/run_20260728_004753_dbe_grounding_dino_5fd207" \
  "06-comparar=/#/compare" \
  "05-detalle-exp=/#/experiments/$EXP_ID"
```

`$EXP_ID` sale del experimento lanzado en la Task 11. Si no se pudo lanzar ninguno, capturar solo las tres primeras y decir que la cuarta quedó sin verificación visual.

- [ ] **Step 4: Comparar cada una contra su equivalente del prototipo y reportar**

Mirar las 8 imágenes (`$S/final/*` contra `$S/proto/*`). Para cada pantalla, listar las diferencias que quedan y clasificarlas: **decisión deliberada** (paginación, borrado en línea, sin sparkline de latencia, leyenda por forma) contra **deuda**. Reportar ambas listas al usuario sin maquillar.

- [ ] **Step 5: NO commitear. Reportar el estado final.**

Informar: rama `feature/webconsole-consola-tesis`, suite verde, las 4 pantallas capturadas, la lista de diferencias deliberadas y la deuda restante. El `git commit` lo decide el usuario.

---

## Notas de verificación

- **HashRouter**: toda ruta capturada lleva `#/`. Sin el `#`, todas las capturas salen de la pantalla de Corridas — pasó durante el diseño y costó dos rondas descubrirlo.
- **El driver de capturas** está en `scratchpad/cdp-shoot.js` y se usa como `node cdp-shoot.js <puerto> <dir-salida> "nombre=/#/ruta" …`. Usa CDP sobre una sola instancia de Chrome; `--virtual-time-budget` se cuelga con el polling de la SPA y no sirve acá.
- **El validador de paletas** vive en la skill `dataviz`: `node scripts/validate_palette.js "<hex,…>" --mode dark --surface "#1a1a19"`. Correrlo si se toca cualquier color de serie.
