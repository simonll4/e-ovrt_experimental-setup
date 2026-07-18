# Rediseño webconsole — Tramo 1: fundamentos + shell — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reemplazar los estilos inline ad-hoc de la webconsole por un sistema de tokens CSS dark-only + un kit de componentes, y reorganizar la navegación en un shell con sidebar agrupado por rol, breadcrumbs y píldora de corrida viva.

**Architecture:** Un `tokens.css` con custom properties es la única fuente de verdad de color/espaciado/tipografía. Un `ui.css` global define clases con prefijo `eo-` que consumen esos tokens; los componentes son wrappers finos que aplican esas clases. El shell reemplaza el header horizontal de `App.tsx` por un sidebar de 3 grupos + acción primaria. Las rutas no cambian.

**Tech Stack:** React 18, Vite 5, TypeScript strict, react-router-dom 6, Vitest 2 + Testing Library + jsdom. **Sin dependencias nuevas.**

**Spec:** `docs/superpowers/specs/2026-07-17-webconsole-frontend-redesign-design.md`

## Global Constraints

- **Cero dependencias nuevas.** El repo tiene 3 deps de runtime (`react`, `react-dom`, `react-router-dom`). No agregar Tailwind, ni CSS-in-JS, ni librería de charting, ni `@testing-library/jest-dom`, ni `user-event`.
- **CSS global con prefijo `eo-`.** No CSS modules: Vitest corre con `css: false` por defecto y stubea los imports, lo que volvería frágiles los tests. Clases globales prefijadas, sin configuración extra.
- **Dark-only.** Un solo tema. No escribir media queries de `prefers-color-scheme` ni overrides `[data-theme]`.
- **Ningún hex literal en `.tsx` / `.ts`.** Todo color sale de un token en CSS. Excepción única y explícita: `SERIES_COLORS` en `GroupedBars.tsx` (Task 12), que es una paleta de datos validada y vive en TS porque la consume la geometría del SVG.
- **Tests:** `cd webconsole/frontend && npm test`. Se usa `fireEvent` (no `user-event`) y `.toBeTruthy()`/`.toBeNull()` (no `jest-dom`). Seguir ese patrón.
- **Superficie oscura de referencia:** `#1a1a19`. Toda paleta se valida contra ella.
- **Idioma:** la UI está en español. Mantenerlo.
- **MODO SIN COMMITS.** No ejecutar `git commit` **nunca** — regla de `projects/CLAUDE.md` y convención establecida de este repo (las 4 features previas del ledger se ejecutaron así). Todo queda en el working tree; el usuario commitea cuando quiera. Los pasos "Commit" de cada tarea son **puntos de corte lógicos, no instrucciones a ejecutar**: al llegar a uno, dar la tarea por terminada y reportar. Los diffs de review se generan con `git add -N <paths del task>` + `git diff`.

---

## File Structure

**Crear:**
- `frontend/src/styles/tokens.css` — custom properties (única fuente de color/espacio/tipografía)
- `frontend/src/styles/base.css` — reset + estilos de elemento (`body`, `a`, `table`, `input`)
- `frontend/src/styles/ui.css` — clases `eo-*` del kit
- `frontend/src/components/ui/Badge.tsx`
- `frontend/src/components/ui/Card.tsx`
- `frontend/src/components/ui/StatTile.tsx`
- `frontend/src/components/ui/EmptyState.tsx`
- `frontend/src/components/ui/ErrorBanner.tsx`
- `frontend/src/components/ui/Field.tsx`
- `frontend/src/components/ui/index.ts` — barrel
- `frontend/src/nav.ts` — definición de navegación (datos puros, testeable sin render)
- `frontend/src/components/Breadcrumbs.tsx`
- `frontend/src/components/Shell.tsx`
- `frontend/src/components/LiveRunPill.tsx`
- `frontend/src/useLiveRun.ts`

**Modificar:**
- `frontend/src/main.tsx` — importar los CSS
- `frontend/src/App.tsx` — usar `Shell`
- `frontend/src/types.ts` — agregar `BadgeTone` (hogar del vocabulario de estado; ver Task 2)
- `frontend/src/experimentview.ts` — `alertSeverityColor` → `alertSeverityTone`
- `frontend/src/runview.ts` — agregar `isRunning`, `runStatusTone`, `runStatusLabel` (**sin tocar `isLive`**, ver Task 4)
- `frontend/src/components/TargetBadge.tsx`, `GroupedBars.tsx`, `Sparkline.tsx`, `EvalSection.tsx`, `PromptSetEditor.tsx`
- Las 9 páginas en `frontend/src/pages/`
- `frontend/src/__tests__/experimentview.test.ts` — se rompe por diseño (Task 2)
- `frontend/src/__tests__/runview.test.ts` — se le agregan tests (los existentes no se tocan)

**Los dos módulos de lógica pura (`runview.ts`, `experimentview.ts`) son el hogar de todo mapeo estado→tono.** Ninguna página define su propio mapeo: es el patrón que el repo ya tiene y que este tramo extiende, no una convención nueva.

**Desvío del spec (a validar por el reviewer):** el spec pide 7 componentes incluyendo `Table`. Este plan implementa **6 componentes + una clase `.eo-table`**. Razón: un `<Table>` que solo agrega un `className` no puede estilar los `<th>`/`<td>` que cada página anida, mientras que `.eo-table th, .eo-table td {…}` en CSS elimina las `CELL` de los 6 archivos sin componente alguno. Sirve la intención del spec (matar la duplicación) con menos código.

---

### Task 1: Tokens y base CSS

**Files:**
- Create: `frontend/src/styles/tokens.css`
- Create: `frontend/src/styles/base.css`
- Modify: `frontend/src/main.tsx`
- Test: `frontend/src/__tests__/App.test.tsx`

**Interfaces:**
- Produces: las custom properties que consume todo el resto — `--surface`, `--surface-raised`, `--border`, `--text`, `--text-muted`, `--accent`, `--status-live|ok|warn|error|neutral`, `--space-1..6`, `--text-xs|sm|md|lg|xl`, `--radius`, `--font`.

Los valores de estado salen de la paleta de status de la skill `dataviz` (fija, nunca tematizada) y todos superan 3:1 contra `#1a1a19`. `--status-live` usa el azul categórico slot 1 (`#3987e5`): "en curso" tiene que leerse distinto de "terminó bien" (verde).

- [ ] **Step 1: Escribir el test que falla**

`frontend/src/__tests__/App.test.tsx` (archivo nuevo — hoy `App.tsx` no tiene ningún test):

```tsx
import { describe, expect, it, vi, afterEach } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import App from '../App'

vi.mock('../api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../api')>()),
  getTarget: vi.fn().mockResolvedValue(null),
  listRuns: vi.fn().mockResolvedValue([]),
}))

afterEach(() => cleanup())

describe('App', () => {
  it('renderiza el título de la consola', () => {
    render(<MemoryRouter><App /></MemoryRouter>)
    expect(screen.getByText('E-OVRT Console')).toBeTruthy()
  })
})
```

Este test cubre un hueco que existe hoy: `App.tsx` no tiene ningún test. Assertea el título **actual** (`E-OVRT Console`) para quedar verde desde ya; Task 6 lo actualiza a `E-OVRT` junto con el sidebar que lo cambia. Ningún test queda rojo entre tareas.

- [ ] **Step 2: Correr el test para verificar que pasa (test de caracterización)**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/App.test.tsx`
Expected: PASS — es un test de caracterización: fija el comportamiento actual antes de refactorizar, para que Task 6 tenga una red de seguridad.

- [ ] **Step 3: Escribir `tokens.css`**

`frontend/src/styles/tokens.css`:

```css
:root {
  color-scheme: dark;

  /* Superficies y texto */
  --surface: #1a1a19;
  --surface-raised: #232322;
  --surface-sunken: #0d0d0d;
  --border: #2c2c2a;
  --border-strong: #383835;
  --text: #ffffff;
  --text-secondary: #c3c2b7;
  --text-muted: #898781;

  /* Acento (acción primaria, link, selección) */
  --accent: #3987e5;
  --accent-hover: #5598e7;

  /* Estado — paleta de status de dataviz, validada >= 3:1 sobre --surface */
  --status-live: #3987e5;
  --status-ok: #0ca30c;
  --status-warn: #fab219;
  --status-serious: #ec835a;
  --status-error: #d03b3b;
  --status-neutral: #898781;

  /* Espaciado */
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 24px;
  --space-6: 32px;

  /* Escala tipográfica */
  --text-xs: 11px;
  --text-sm: 12px;
  --text-md: 14px;
  --text-lg: 18px;
  --text-xl: 22px;

  --radius: 6px;
  --font: system-ui, -apple-system, 'Segoe UI', sans-serif;
  --font-mono: ui-monospace, 'SF Mono', Menlo, monospace;

  /* Layout */
  --sidebar-width: 208px;
  --content-max: 1600px;
}
```

- [ ] **Step 4: Escribir `base.css`**

`frontend/src/styles/base.css`:

```css
* { box-sizing: border-box; }

body {
  margin: 0;
  background: var(--surface-sunken);
  color: var(--text);
  font-family: var(--font);
  font-size: var(--text-md);
  line-height: 1.5;
}

a { color: var(--accent); text-decoration: none; }
a:hover { color: var(--accent-hover); text-decoration: underline; }

h1, h2, h3 { margin: 0; font-weight: 600; }
h1 { font-size: var(--text-xl); }
h2 { font-size: var(--text-lg); }
h3 { font-size: var(--text-md); }

small { font-size: var(--text-sm); color: var(--text-muted); }

input, select, textarea, button { font-family: inherit; font-size: var(--text-md); }

input, select, textarea {
  background: var(--surface-sunken);
  color: var(--text);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius);
  padding: var(--space-1) var(--space-2);
}
input:focus, select:focus, textarea:focus {
  outline: 2px solid var(--accent);
  outline-offset: 1px;
}

button {
  background: var(--surface-raised);
  color: var(--text);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius);
  padding: var(--space-1) var(--space-3);
  cursor: pointer;
}
button:hover:not(:disabled) { border-color: var(--accent); }
button:disabled { opacity: 0.5; cursor: default; }
```

- [ ] **Step 5: Importar los CSS en `main.tsx`**

`frontend/src/main.tsx` — agregar los tres imports **antes** de `App` (el orden importa: tokens primero):

```tsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import { HashRouter } from 'react-router-dom'
import './styles/tokens.css'
import './styles/base.css'
import './styles/ui.css'
import App from './App'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <HashRouter>
      <App />
    </HashRouter>
  </React.StrictMode>,
)
```

- [ ] **Step 6: Crear `ui.css` vacío para que el import resuelva**

`frontend/src/styles/ui.css`:

```css
/* Kit de componentes — clases eo-*. Se puebla en Tasks 2-4. */
```

- [ ] **Step 7: Verificar que compila**

Run: `cd webconsole/frontend && npx tsc --noEmit && npm run build`
Expected: build OK, sin errores de TS.

- [ ] **Step 8: Verificación visual**

Run: `cd webconsole && make dev-frontend`
Expected: la app carga con fondo oscuro (`#0d0d0d`) y texto blanco. La nav vieja sigue ahí y se ve rota — es esperado, la arregla Task 6.

---

### Task 2: Badge y migración de severidad a tonos

Esta tarea rompe `experimentview.test.ts` **por diseño** y lo arregla en el mismo commit: hoy assertea hex literales (`alertSeverityColor('high') === '#b00'`), y el spec exige que el color salga por token, no por hex en TS.

**Files:**
- Create: `frontend/src/components/ui/Badge.tsx`
- Create: `frontend/src/components/ui/index.ts`
- Modify: `frontend/src/styles/ui.css`
- Modify: `frontend/src/experimentview.ts`
- Modify: `frontend/src/__tests__/experimentview.test.ts`
- Test: `frontend/src/__tests__/ui/Badge.test.tsx`

**Interfaces:**
- Produces: `type BadgeTone = 'live' | 'ok' | 'warn' | 'error' | 'neutral'` — **definido en `types.ts`**, no en `Badge.tsx`; `Badge({ tone, children }: { tone: BadgeTone; children: ReactNode })`; `alertSeverityTone(severity: string): BadgeTone`.
- Consumes: los tokens `--status-*` de Task 1.

**Por qué `BadgeTone` vive en `types.ts` y no en `Badge.tsx`:** lo consumen los módulos de lógica pura (`runview.ts`, `experimentview.ts`), cuyo motivo de existir es ser testeables sin React. Si el tipo viviera en `Badge.tsx`, esos módulos importarían de un `.tsx` — hoy sería inocuo porque `import type` se borra al compilar, pero deja la arquitectura a un carácter de distancia de romperse (basta que alguien saque el `type`). `types.ts` ya es el módulo de tipos compartidos del frontend.

- [ ] **Step 1: Escribir el test que falla**

`frontend/src/__tests__/ui/Badge.test.tsx` (crear el directorio `ui/`):

```tsx
import { describe, expect, it, afterEach } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import Badge from '../../components/ui/Badge'

afterEach(() => cleanup())

describe('Badge', () => {
  it('aplica la clase del tono', () => {
    render(<Badge tone="error">falló</Badge>)
    expect(screen.getByText('falló').className).toContain('eo-badge--error')
  })

  it('siempre lleva la clase base', () => {
    render(<Badge tone="ok">listo</Badge>)
    const el = screen.getByText('listo')
    expect(el.className).toContain('eo-badge')
    expect(el.className).toContain('eo-badge--ok')
  })
})
```

- [ ] **Step 2: Actualizar el test de `experimentview` al contrato nuevo**

`frontend/src/__tests__/experimentview.test.ts` — reemplazar el `describe('alertSeverityColor')` (líneas 11-17) por:

```ts
describe('alertSeverityTone', () => {
  it('high error, medium warn, otro ok', () => {
    expect(alertSeverityTone('high')).toBe('error')
    expect(alertSeverityTone('medium')).toBe('warn')
    expect(alertSeverityTone('low')).toBe('ok')
  })
})
```

Y el import de la línea 2:

```ts
import { isNonTemporal, alertSeverityTone, experimentStatusLabel } from '../experimentview'
```

- [ ] **Step 3: Correr los tests para verificar que fallan**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/ui/Badge.test.tsx src/__tests__/experimentview.test.ts`
Expected: FAIL — `Cannot find module '../../components/ui/Badge'` y `alertSeverityTone is not a function`.

- [ ] **Step 4: Definir `BadgeTone` en `types.ts` e implementar `Badge`**

Agregar al final de `frontend/src/types.ts`:

```ts
/** Vocabulario de estado de la UI. Vive acá —y no en Badge.tsx— porque lo consumen
 *  runview.ts y experimentview.ts, que son lógica pura y no deben importar de un .tsx. */
export type BadgeTone = 'live' | 'ok' | 'warn' | 'error' | 'neutral'
```

`frontend/src/components/ui/Badge.tsx`:

```tsx
import type { ReactNode } from 'react'
import type { BadgeTone } from '../../types'

export default function Badge({ tone, children }: { tone: BadgeTone; children: ReactNode }) {
  return <span className={`eo-badge eo-badge--${tone}`}>{children}</span>
}
```

- [ ] **Step 5: Agregar las clases a `ui.css`**

Agregar a `frontend/src/styles/ui.css`:

```css
/* Badge */
.eo-badge {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  padding: 1px var(--space-2);
  border-radius: 999px;
  font-size: var(--text-sm);
  font-weight: 500;
  white-space: nowrap;
  border: 1px solid currentColor;
}
.eo-badge::before { content: '●'; font-size: 0.7em; }
.eo-badge--live { color: var(--status-live); }
.eo-badge--ok { color: var(--status-ok); }
.eo-badge--warn { color: var(--status-warn); }
.eo-badge--error { color: var(--status-error); }
.eo-badge--neutral { color: var(--status-neutral); }
```

- [ ] **Step 6: Migrar `experimentview.ts`**

`frontend/src/experimentview.ts` — reemplazar `alertSeverityColor` (líneas 7-11). El archivo queda:

```ts
import type { BadgeTone, ExperimentReport, ExperimentRunState } from './types'

export function isNonTemporal(report: ExperimentReport | null): boolean {
  return report?.non_temporal === true
}

export function alertSeverityTone(severity: string): BadgeTone {
  if (severity === 'high') return 'error'
  if (severity === 'medium') return 'warn'
  return 'ok'
}

export function experimentStatusLabel(state: ExperimentRunState | null): string {
  if (state === null) return '—'
  if (state.status === 'running') return 'corriendo'
  if (state.status === 'succeeded' || state.ok === true) return 'OK'
  if (state.status === 'failed') return 'fallo'
  return state.status
}
```

- [ ] **Step 7: Crear el barrel**

`frontend/src/components/ui/index.ts`:

```ts
export { default as Badge } from './Badge'
```

`BadgeTone` **no** se re-exporta desde el barrel: su hogar es `types.ts` y los consumidores lo importan de ahí. Un solo camino por tipo.

- [ ] **Step 8: Actualizar el consumidor de `alertSeverityColor`**

Run: `cd webconsole/frontend && grep -rn "alertSeverityColor" src/`
Expected: solo `ExperimentDetailPage.tsx`. Reemplazar ahí el uso del color inline por `<Badge tone={alertSeverityTone(a.severity)}>{a.severity}</Badge>` y agregar los imports. La migración completa de esa página es **Task 9**; acá solo se hace que compile.

- [ ] **Step 9: Correr los tests**

Run: `cd webconsole/frontend && npm test`
Expected: PASS — toda la suite verde.

- [ ] **Step 10: Commit (pedir confirmación primero)**

```bash
git add webconsole/frontend/src/components/ui webconsole/frontend/src/styles webconsole/frontend/src/experimentview.ts webconsole/frontend/src/__tests__
git commit -m "feat(webconsole): tokens CSS dark-only y Badge; severidad por tono"
```

---

### Task 3: Primitivos de presentación

**Files:**
- Create: `frontend/src/components/ui/Card.tsx`, `ErrorBanner.tsx`, `EmptyState.tsx`, `StatTile.tsx`, `Field.tsx`
- Modify: `frontend/src/styles/ui.css`, `frontend/src/components/ui/index.ts`
- Test: `frontend/src/__tests__/ui/primitives.test.tsx`

**Interfaces:**
- Produces:
  - `Card({ title?, children }: { title?: ReactNode; children: ReactNode })`
  - `ErrorBanner({ children }: { children: ReactNode })`
  - `EmptyState({ children }: { children: ReactNode })`
  - `StatTile({ label, value, unit? }: { label: string; value: ReactNode; unit?: string })`
  - `Field({ label, hint?, error?, children }: { label: string; hint?: string; error?: string; children: ReactNode })`

- [ ] **Step 1: Escribir el test que falla**

`frontend/src/__tests__/ui/primitives.test.tsx`:

```tsx
import { describe, expect, it, afterEach } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import { Card, ErrorBanner, EmptyState, StatTile, Field } from '../../components/ui'

afterEach(() => cleanup())

describe('Card', () => {
  it('muestra título y contenido', () => {
    render(<Card title="Métricas"><p>hola</p></Card>)
    expect(screen.getByText('Métricas')).toBeTruthy()
    expect(screen.getByText('hola')).toBeTruthy()
  })
  it('sin título no renderiza encabezado', () => {
    render(<Card><p>solo</p></Card>)
    expect(screen.queryByRole('heading')).toBeNull()
  })
})

describe('ErrorBanner', () => {
  it('marca el mensaje con role alert', () => {
    render(<ErrorBanner>algo falló</ErrorBanner>)
    expect(screen.getByRole('alert').textContent).toContain('algo falló')
  })
})

describe('EmptyState', () => {
  it('muestra el mensaje', () => {
    render(<EmptyState>Sin corridas todavía.</EmptyState>)
    expect(screen.getByText('Sin corridas todavía.')).toBeTruthy()
  })
})

describe('StatTile', () => {
  it('muestra label, valor y unidad', () => {
    render(<StatTile label="FPS" value={42} unit="fps" />)
    expect(screen.getByText('FPS')).toBeTruthy()
    expect(screen.getByText('42')).toBeTruthy()
    expect(screen.getByText('fps')).toBeTruthy()
  })
  it('sin unidad no rompe', () => {
    render(<StatTile label="dets" value={7} />)
    expect(screen.getByText('7')).toBeTruthy()
  })
})

describe('Field', () => {
  // Ojo: `screen.getByText('Stride')` devuelve el <span> que contiene el texto, NO el
  // <label> que lo envuelve — RTL matchea el nodo de texto directo. Hay que ir por
  // container.querySelector. Y ya que estamos, se assertea lo que de verdad importa:
  // que el label ENVUELVE al control (es el motivo de no usar htmlFor/id).
  it('envuelve el control en un <label>', () => {
    const { container } = render(<Field label="Stride"><input id="stride" /></Field>)
    const label = container.querySelector('label')
    expect(label?.textContent).toContain('Stride')
    expect(label?.querySelector('#stride')).toBeTruthy()
  })
  it('muestra el error cuando lo hay', () => {
    render(<Field label="Fuente" error="requerido"><input /></Field>)
    expect(screen.getByText('requerido')).toBeTruthy()
  })
  it('sin error no muestra nada de error', () => {
    render(<Field label="Fuente"><input /></Field>)
    expect(screen.queryByText('requerido')).toBeNull()
  })
})
```

- [ ] **Step 2: Correr el test para verificar que falla**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/ui/primitives.test.tsx`
Expected: FAIL — no existen los módulos.

- [ ] **Step 3: Implementar los cinco componentes**

`frontend/src/components/ui/Card.tsx`:

```tsx
import type { ReactNode } from 'react'

export default function Card({ title, children }: { title?: ReactNode; children: ReactNode }) {
  return (
    <section className="eo-card">
      {title ? <h3 className="eo-card__title">{title}</h3> : null}
      {children}
    </section>
  )
}
```

`frontend/src/components/ui/ErrorBanner.tsx`:

```tsx
import type { ReactNode } from 'react'

export default function ErrorBanner({ children }: { children: ReactNode }) {
  return <div className="eo-error" role="alert">{children}</div>
}
```

`frontend/src/components/ui/EmptyState.tsx`:

```tsx
import type { ReactNode } from 'react'

export default function EmptyState({ children }: { children: ReactNode }) {
  return <p className="eo-empty">{children}</p>
}
```

`frontend/src/components/ui/StatTile.tsx`:

```tsx
import type { ReactNode } from 'react'

export default function StatTile({ label, value, unit }: { label: string; value: ReactNode; unit?: string }) {
  return (
    <div className="eo-stat">
      <span className="eo-stat__label">{label}</span>
      <span className="eo-stat__value">
        {value}
        {unit ? <span className="eo-stat__unit">{unit}</span> : null}
      </span>
    </div>
  )
}
```

`frontend/src/components/ui/Field.tsx`:

```tsx
import type { ReactNode } from 'react'

export default function Field({
  label,
  hint,
  error,
  children,
}: {
  label: string
  hint?: string
  error?: string
  children: ReactNode
}) {
  return (
    <label className="eo-field">
      <span className="eo-field__label">{label}</span>
      {children}
      {hint && !error ? <span className="eo-field__hint">{hint}</span> : null}
      {error ? <span className="eo-field__error">{error}</span> : null}
    </label>
  )
}
```

- [ ] **Step 4: Agregar las clases a `ui.css`**

```css
/* Card */
.eo-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: var(--space-4);
  margin-bottom: var(--space-4);
}
.eo-card__title {
  margin-bottom: var(--space-3);
  color: var(--text-secondary);
  font-size: var(--text-sm);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

/* ErrorBanner */
.eo-error {
  border: 1px solid var(--status-error);
  border-left-width: 3px;
  border-radius: var(--radius);
  background: color-mix(in srgb, var(--status-error) 12%, transparent);
  color: var(--text);
  padding: var(--space-2) var(--space-3);
  margin-bottom: var(--space-3);
}

/* EmptyState */
.eo-empty {
  color: var(--text-muted);
  padding: var(--space-5);
  text-align: center;
}

/* StatTile */
.eo-stat {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  background: var(--surface-raised);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: var(--space-2) var(--space-3);
  min-width: 96px;
}
.eo-stat__label {
  font-size: var(--text-xs);
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.eo-stat__value { font-size: var(--text-lg); font-weight: 600; }
.eo-stat__unit {
  font-size: var(--text-sm);
  font-weight: 400;
  color: var(--text-muted);
  margin-left: var(--space-1);
}
.eo-stats-row { display: flex; gap: var(--space-2); flex-wrap: wrap; margin-bottom: var(--space-4); }

/* Field */
.eo-field { display: grid; gap: var(--space-1); margin-bottom: var(--space-3); max-width: 560px; }
.eo-field__label { font-size: var(--text-sm); color: var(--text-secondary); }
.eo-field__hint { font-size: var(--text-sm); color: var(--text-muted); }
.eo-field__error { font-size: var(--text-sm); color: var(--status-error); }
```

- [ ] **Step 5: Exportar en el barrel**

`frontend/src/components/ui/index.ts`:

```ts
export { default as Badge } from './Badge'
export { default as Card } from './Card'
export { default as ErrorBanner } from './ErrorBanner'
export { default as EmptyState } from './EmptyState'
export { default as StatTile } from './StatTile'
export { default as Field } from './Field'
```

- [ ] **Step 6: Correr los tests**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/ui/`
Expected: PASS — 11 tests (2 de `Badge` + 9 de primitivos).

- [ ] **Step 7: Commit (pedir confirmación primero)**

```bash
git add webconsole/frontend/src/components/ui webconsole/frontend/src/styles/ui.css webconsole/frontend/src/__tests__/ui
git commit -m "feat(webconsole): primitivos Card/ErrorBanner/EmptyState/StatTile/Field"
```

---

### Task 4: Clase de tabla, estado de corrida en `runview`, y migración de RunsPage

`RunsPage` es el primer consumidor real: prueba tokens + `.eo-table` + `Badge` + `EmptyState` + `ErrorBanner` de una.

**⚠️ Contexto que no se puede ignorar.** `runview.ts` **ya tiene** `isLive`, y su semántica es **AND**, no OR:

```ts
export function isLive(run: { status: string; live?: boolean }): boolean {
  // live=true solo lo emite el servicio para SU run activo en memoria — el único
  // suscribible por WS. Un running externo (two-node) con WS abierto entra en
  // reconnect-loop infinito (spec 2026-07-06 §3.4).
  return run.status === 'running' && run.live === true
}
```

**No modificar `isLive` ni ampliar su semántica**: protege contra un reconnect-loop real y documentado. Lo que hace falta es un predicado **distinto** para la UI de listado y la píldora, que solo linkean y nunca abren un WS — y que sí tienen que mostrar un `running` externo de two-node, porque EBE es two-node y es justo el escenario a vigilar. Dos predicados, nombres distintos, razón explícita.

**Files:**
- Modify: `frontend/src/styles/ui.css`
- Modify: `frontend/src/runview.ts`
- Modify: `frontend/src/pages/RunsPage.tsx`
- Test: `frontend/src/__tests__/runview.test.ts` (existente, 6 tests), `frontend/src/__tests__/RunsPage.test.tsx` (nuevo)

**Interfaces:**
- Produces:
  - la clase `.eo-table` (estila `th`/`td` anidados). Reemplaza la constante `CELL` en los 6 archivos que la duplican.
  - `isRunning(run: { status: string }): boolean` — en `runview.ts`, junto a `isLive`.
  - `runStatusTone(run: { status: string; live?: boolean }): BadgeTone` y `runStatusLabel(run: { status: string; live?: boolean }): string` — en `runview.ts`, para que `RunsPage` (Task 4) y `RunDetailPage` (Task 11) no dupliquen el mapeo.
- Consumes: `Badge`, `BadgeTone`, `EmptyState`, `ErrorBanner` de Task 2-3.

- [ ] **Step 0: Agregar los tests de la lógica nueva a `runview.test.ts`**

Agregar a `frontend/src/__tests__/runview.test.ts` (no tocar los describes existentes de `isLive`/`topologyBadge`):

```ts
import { isRunning, runStatusTone, runStatusLabel } from '../runview'

describe('isRunning', () => {
  it('true para cualquier running, incluso sin live (two-node externo)', () => {
    expect(isRunning({ status: 'running' })).toBe(true)
  })
  it('false para terminados', () => {
    expect(isRunning({ status: 'succeeded' })).toBe(false)
    expect(isRunning({ status: 'failed' })).toBe(false)
  })
  it('no es isLive: isRunning no exige live=true', () => {
    const externo = { status: 'running' as const }
    expect(isRunning(externo)).toBe(true)
    expect(isLive(externo)).toBe(false)
  })
})

describe('runStatusTone / runStatusLabel', () => {
  it('running es live', () => {
    expect(runStatusTone({ status: 'running' })).toBe('live')
    expect(runStatusLabel({ status: 'running' })).toBe('vivo')
  })
  it('succeeded es ok', () => {
    expect(runStatusTone({ status: 'succeeded' })).toBe('ok')
    expect(runStatusLabel({ status: 'succeeded' })).toBe('OK')
  })
  it('failed es error', () => {
    expect(runStatusTone({ status: 'failed' })).toBe('error')
    expect(runStatusLabel({ status: 'failed' })).toBe('fallo')
  })
  it('desconocido cae a neutral y muestra el status crudo', () => {
    expect(runStatusTone({ status: 'weird' })).toBe('neutral')
    expect(runStatusLabel({ status: 'weird' })).toBe('weird')
  })
})
```

Asegurate de que `isLive` esté en el import existente del archivo.

- [ ] **Step 0b: Implementar la lógica en `runview.ts`**

Agregar al final de `frontend/src/runview.ts` (sin tocar `isLive` ni `topologyBadge`):

```ts
import type { BadgeTone } from './types'

// Distinto de isLive a propósito: acá alcanza con que esté corriendo, incluso un
// running externo (two-node) que NO es suscribible por WS. Lo usan el listado y la
// píldora, que solo linkean; quien decide abrir el WS es el detalle, y ahí manda isLive.
export function isRunning(run: { status: string }): boolean {
  return run.status === 'running'
}

export function runStatusTone(run: { status: string; live?: boolean }): BadgeTone {
  if (isRunning(run)) return 'live'
  if (run.status === 'succeeded') return 'ok'
  if (run.status === 'failed') return 'error'
  return 'neutral'
}

export function runStatusLabel(run: { status: string; live?: boolean }): string {
  if (isRunning(run)) return 'vivo'
  if (run.status === 'succeeded') return 'OK'
  if (run.status === 'failed') return 'fallo'
  return run.status
}
```

- [ ] **Step 0c: Correr los tests de runview**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/runview.test.ts`
Expected: PASS — los 6 existentes + 7 nuevos = 13.

- [ ] **Step 1: Escribir el test que falla**

`frontend/src/__tests__/RunsPage.test.tsx` (archivo nuevo — hoy no existe):

```tsx
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import RunsPage from '../pages/RunsPage'
import * as api from '../api'

vi.mock('../api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../api')>()),
  listRuns: vi.fn(),
}))

beforeEach(() => vi.clearAllMocks())
afterEach(() => cleanup())

const renderPage = () => render(<MemoryRouter><RunsPage /></MemoryRouter>)

describe('RunsPage', () => {
  it('lista corridas y marca la viva con badge', async () => {
    vi.mocked(api.listRuns).mockResolvedValue([
      { run_id: 'r_1', status: 'running', model: 'gdino', live: true } as any,
      { run_id: 'r_2', status: 'succeeded', model: 'gdino' } as any,
    ])
    renderPage()
    await waitFor(() => expect(screen.getByText('r_1')).toBeTruthy())
    expect(screen.getByText('vivo').className).toContain('eo-badge--live')
    expect(screen.getByText('OK').className).toContain('eo-badge--ok')
  })

  it('estado vacío cuando no hay corridas', async () => {
    vi.mocked(api.listRuns).mockResolvedValue([])
    renderPage()
    await waitFor(() => expect(screen.getByText('Sin corridas todavía.')).toBeTruthy())
  })

  it('muestra el error con role alert', async () => {
    vi.mocked(api.listRuns).mockRejectedValue(new Error('boom'))
    renderPage()
    await waitFor(() => expect(screen.getByRole('alert')).toBeTruthy())
  })
})
```

- [ ] **Step 2: Correr el test para verificar que falla**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/RunsPage.test.tsx`
Expected: FAIL — hoy el estado se renderiza como texto `🟢 running`, no como `Badge`.

- [ ] **Step 3: Agregar las clases de tabla a `ui.css`**

```css
/* Table */
.eo-table {
  border-collapse: collapse;
  width: 100%;
  font-size: var(--text-md);
}
.eo-table th,
.eo-table td {
  padding: var(--space-2) var(--space-3);
  border-bottom: 1px solid var(--border);
  text-align: left;
}
.eo-table th {
  background: var(--surface-raised);
  color: var(--text-secondary);
  font-size: var(--text-xs);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  position: sticky;
  top: 0;
}
.eo-table tbody tr:hover { background: var(--surface-raised); }
.eo-table td.eo-num { text-align: right; font-variant-numeric: tabular-nums; }
```

- [ ] **Step 4: Migrar `RunsPage.tsx`**

Reemplazar el archivo entero:

```tsx
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { listRuns } from '../api'
import type { RunRow } from '../types'
import { Badge, EmptyState, ErrorBanner } from '../components/ui'
import { runStatusTone, runStatusLabel } from '../runview'

const HEADERS = ['run', 'estado', 'modelo', 'fuente', 'prompts', 'FPS', 'dets', 'dur (s)']

export default function RunsPage() {
  const [rows, setRows] = useState<RunRow[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => {
    let alive = true
    let timer: ReturnType<typeof setTimeout>
    const tick = () =>
      listRuns()
        .then((r) => {
          if (!alive) return
          setRows(r)
          setError(null)
          // refresco solo mientras hay actividad (el resto es historial estático)
          if (r.some((row) => row.status === 'running')) timer = setTimeout(tick, 4000)
        })
        .catch((e) => alive && setError(String(e)))
    tick()
    return () => {
      alive = false
      clearTimeout(timer)
    }
  }, [])

  if (error) return <ErrorBanner>Error listando runs: {error}</ErrorBanner>
  if (!rows) return <p className="eo-empty">Cargando…</p>
  return (
    <div>
      <table className="eo-table">
        <thead>
          <tr>{HEADERS.map((h) => <th key={h}>{h}</th>)}</tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.run_id}>
              <td><Link to={`/runs/${r.run_id}`}>{r.run_id}</Link></td>
              <td>
                <Badge tone={runStatusTone(r)}>{runStatusLabel(r)}</Badge>
                {r.topology === 'two_node' ? <small> two-node</small> : null}
              </td>
              <td>{r.model ?? '—'}</td>
              <td>{r.source_type ?? '—'}</td>
              <td>{r.prompt_set_id ?? '—'}</td>
              <td className="eo-num">{r.fps_effective ?? '—'}</td>
              <td className="eo-num">{r.total_detections ?? '—'}</td>
              <td className="eo-num">{r.duration_seconds ?? '—'}</td>
            </tr>
          ))}
          {rows.length === 0 && (
            <tr><td colSpan={8}><EmptyState>Sin corridas todavía.</EmptyState></td></tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
```

Nota: se elimina el link `➕ Nueva corrida` de la línea 35 — pasa a ser la acción primaria del sidebar (Task 6, D4 del spec).

- [ ] **Step 5: Correr los tests**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/RunsPage.test.tsx`
Expected: PASS — 3 tests.

- [ ] **Step 6: Verificar que la suite entera sigue verde**

Run: `cd webconsole/frontend && npm test`
Expected: PASS — toda la suite verde.

- [ ] **Step 7: Commit (pedir confirmación primero)**

```bash
git add webconsole/frontend/src/styles/ui.css webconsole/frontend/src/pages/RunsPage.tsx webconsole/frontend/src/__tests__/RunsPage.test.tsx
git commit -m "feat(webconsole): clase .eo-table y migración de RunsPage"
```

---

### Task 5: Definición de navegación y breadcrumbs

`nav.ts` es data pura: se testea sin render y es la fuente de verdad tanto del sidebar como de los breadcrumbs.

**Files:**
- Create: `frontend/src/nav.ts`
- Create: `frontend/src/components/Breadcrumbs.tsx`
- Modify: `frontend/src/styles/ui.css`
- Test: `frontend/src/__tests__/nav.test.ts`

**Interfaces:**
- Produces:
  - `type NavItem = { to: string; label: string }`
  - `type NavGroup = { title: string; items: NavItem[] }`
  - `const NAV_GROUPS: NavGroup[]`
  - `function crumbsFor(pathname: string): NavItem[]`
- Consumido por: `Shell` (Task 6).

- [ ] **Step 1: Escribir el test que falla**

`frontend/src/__tests__/nav.test.ts`:

```ts
import { describe, expect, it } from 'vitest'
import { NAV_GROUPS, crumbsFor } from '../nav'

describe('NAV_GROUPS', () => {
  it('tiene los tres grupos por rol del spec', () => {
    expect(NAV_GROUPS.map((g) => g.title)).toEqual(['Trabajo', 'Definiciones', 'Sistema'])
  })

  it('cubre los 6 destinos y NO incluye /compose (es acción, no destino)', () => {
    const tos = NAV_GROUPS.flatMap((g) => g.items.map((i) => i.to))
    expect(tos).toEqual(['/', '/experiments', '/compare', '/prompts', '/catalog', '/platform'])
    expect(tos).not.toContain('/compose')
  })

  it('ningún destino aparece dos veces', () => {
    const tos = NAV_GROUPS.flatMap((g) => g.items.map((i) => i.to))
    expect(new Set(tos).size).toBe(tos.length)
  })
})

describe('crumbsFor', () => {
  it('raíz devuelve solo Corridas', () => {
    expect(crumbsFor('/')).toEqual([{ to: '/', label: 'Corridas' }])
  })

  it('detalle de corrida encadena Corridas > id', () => {
    expect(crumbsFor('/runs/r_42')).toEqual([
      { to: '/', label: 'Corridas' },
      { to: '/runs/r_42', label: 'r_42' },
    ])
  })

  it('detalle de experimento encadena Experimentos > id', () => {
    expect(crumbsFor('/experiments/exp_7')).toEqual([
      { to: '/experiments', label: 'Experimentos' },
      { to: '/experiments/exp_7', label: 'exp_7' },
    ])
  })

  it('compose tiene su propio crumb aunque no esté en la nav', () => {
    expect(crumbsFor('/compose')).toEqual([{ to: '/compose', label: 'Nueva corrida' }])
  })

  it('ruta desconocida no rompe', () => {
    expect(crumbsFor('/nope')).toEqual([])
  })
})
```

- [ ] **Step 2: Correr el test para verificar que falla**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/nav.test.ts`
Expected: FAIL — `Cannot find module '../nav'`.

- [ ] **Step 3: Implementar `nav.ts`**

```ts
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
    items: [{ to: '/platform', label: 'Plataforma' }],
  },
]

// Rutas que no viven en la nav pero necesitan crumb propio.
const STANDALONE: Record<string, string> = { '/compose': 'Nueva corrida' }

export function crumbsFor(pathname: string): NavItem[] {
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
  if (STANDALONE[pathname]) return [{ to: pathname, label: STANDALONE[pathname] }]
  for (const group of NAV_GROUPS) {
    const item = group.items.find((i) => i.to === pathname)
    if (item) return [item]
  }
  return []
}
```

- [ ] **Step 4: Implementar `Breadcrumbs.tsx`**

```tsx
import { Link, useLocation } from 'react-router-dom'
import { crumbsFor } from '../nav'

export default function Breadcrumbs() {
  const { pathname } = useLocation()
  const crumbs = crumbsFor(pathname)
  if (crumbs.length === 0) return null
  return (
    <nav className="eo-crumbs" aria-label="Ruta de navegación">
      {crumbs.map((c, i) => (
        <span key={c.to}>
          {i > 0 ? <span className="eo-crumbs__sep"> / </span> : null}
          {i === crumbs.length - 1 ? (
            <span className="eo-crumbs__current" aria-current="page">{c.label}</span>
          ) : (
            <Link to={c.to}>{c.label}</Link>
          )}
        </span>
      ))}
    </nav>
  )
}
```

- [ ] **Step 5: Agregar las clases a `ui.css`**

```css
/* Breadcrumbs */
.eo-crumbs { font-size: var(--text-md); color: var(--text-muted); }
.eo-crumbs__sep { color: var(--border-strong); }
.eo-crumbs__current { color: var(--text); font-weight: 600; }
```

- [ ] **Step 6: Correr los tests**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/nav.test.ts`
Expected: PASS — 8 tests.

- [ ] **Step 7: Commit (pedir confirmación primero)**

```bash
git add webconsole/frontend/src/nav.ts webconsole/frontend/src/components/Breadcrumbs.tsx webconsole/frontend/src/styles/ui.css webconsole/frontend/src/__tests__/nav.test.ts
git commit -m "feat(webconsole): definición de navegación por rol y breadcrumbs"
```

---

### Task 6: Shell con sidebar

**Files:**
- Create: `frontend/src/components/Shell.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/TargetBadge.tsx`
- Modify: `frontend/src/styles/ui.css`
- Test: `frontend/src/__tests__/Shell.test.tsx`, `frontend/src/__tests__/App.test.tsx`

**Interfaces:**
- Produces: `Shell({ children }: { children: ReactNode })` — sidebar + header + área de contenido.
- Consumes: `NAV_GROUPS` (Task 5), `Breadcrumbs` (Task 5), `TargetBadge`, `LiveRunPill` (Task 7 lo monta acá).

- [ ] **Step 1: Escribir el test que falla**

`frontend/src/__tests__/Shell.test.tsx`:

```tsx
import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import Shell from '../components/Shell'

vi.mock('../api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../api')>()),
  getTarget: vi.fn().mockResolvedValue(null),
  listRuns: vi.fn().mockResolvedValue([]),
}))

afterEach(() => cleanup())

const renderShell = (path = '/') =>
  render(
    <MemoryRouter initialEntries={[path]}>
      <Shell><p>contenido</p></Shell>
    </MemoryRouter>,
  )

describe('Shell', () => {
  it('renderiza los tres títulos de grupo', () => {
    renderShell()
    expect(screen.getByText('Trabajo')).toBeTruthy()
    expect(screen.getByText('Definiciones')).toBeTruthy()
    expect(screen.getByText('Sistema')).toBeTruthy()
  })

  it('renderiza los 6 destinos', () => {
    renderShell()
    for (const label of ['Corridas', 'Experimentos', 'Comparar', 'Prompt sets', 'Catálogos', 'Plataforma']) {
      expect(screen.getAllByText(label).length).toBeGreaterThan(0)
    }
  })

  it('"Nueva corrida" es acción primaria y apunta a /compose', () => {
    renderShell()
    const link = screen.getByRole('link', { name: /nueva corrida/i })
    expect(link.getAttribute('href')).toContain('/compose')
    expect(link.className).toContain('eo-sidebar__action')
  })

  it('marca el destino activo', () => {
    renderShell('/prompts')
    const active = screen.getByRole('link', { name: 'Prompt sets' })
    expect(active.className).toContain('eo-sidebar__link--active')
  })

  it('renderiza el contenido hijo', () => {
    renderShell()
    expect(screen.getByText('contenido')).toBeTruthy()
  })
})
```

- [ ] **Step 2: Correr el test para verificar que falla**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/Shell.test.tsx`
Expected: FAIL — `Cannot find module '../components/Shell'`.

- [ ] **Step 3: Implementar `Shell.tsx`**

Usa `NavLink` de react-router (ya disponible) para el estado activo. `end` en `/` evita que la raíz quede activa en toda ruta.

```tsx
import type { ReactNode } from 'react'
import { Link, NavLink } from 'react-router-dom'
import { NAV_GROUPS } from '../nav'
import Breadcrumbs from './Breadcrumbs'
import TargetBadge from './TargetBadge'

export default function Shell({ children }: { children: ReactNode }) {
  return (
    <div className="eo-shell">
      <aside className="eo-sidebar">
        <div className="eo-sidebar__brand">
          <h1>E-OVRT</h1>
        </div>
        <Link to="/compose" className="eo-sidebar__action">+ Nueva corrida</Link>
        <nav className="eo-sidebar__nav">
          {NAV_GROUPS.map((group) => (
            <div key={group.title} className="eo-sidebar__group">
              <span className="eo-sidebar__group-title">{group.title}</span>
              {group.items.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.to === '/'}
                  className={({ isActive }) =>
                    isActive ? 'eo-sidebar__link eo-sidebar__link--active' : 'eo-sidebar__link'
                  }
                >
                  {item.label}
                </NavLink>
              ))}
            </div>
          ))}
        </nav>
      </aside>
      <div className="eo-main">
        <header className="eo-topbar">
          <Breadcrumbs />
          <div className="eo-topbar__right"><TargetBadge /></div>
        </header>
        <main className="eo-content">{children}</main>
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Agregar las clases a `ui.css`**

```css
/* Shell */
.eo-shell { display: flex; min-height: 100vh; }

.eo-sidebar {
  width: var(--sidebar-width);
  flex-shrink: 0;
  background: var(--surface);
  border-right: 1px solid var(--border);
  padding: var(--space-4) var(--space-3);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  position: sticky;
  top: 0;
  height: 100vh;
}
.eo-sidebar__brand h1 { font-size: var(--text-lg); letter-spacing: 0.02em; }

.eo-sidebar__action {
  display: block;
  text-align: center;
  background: var(--accent);
  color: #fff;
  border-radius: var(--radius);
  padding: var(--space-2) var(--space-3);
  font-weight: 600;
  font-size: var(--text-md);
}
.eo-sidebar__action:hover { background: var(--accent-hover); color: #fff; text-decoration: none; }

.eo-sidebar__nav { display: flex; flex-direction: column; gap: var(--space-4); }
.eo-sidebar__group { display: flex; flex-direction: column; gap: 2px; }
.eo-sidebar__group-title {
  font-size: var(--text-xs);
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-bottom: var(--space-1);
}
.eo-sidebar__link {
  color: var(--text-secondary);
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius);
  border-left: 2px solid transparent;
}
.eo-sidebar__link:hover { background: var(--surface-raised); color: var(--text); text-decoration: none; }
.eo-sidebar__link--active {
  background: var(--surface-raised);
  color: var(--text);
  border-left-color: var(--accent);
  font-weight: 600;
}

.eo-main { flex: 1; min-width: 0; display: flex; flex-direction: column; }
.eo-topbar {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  padding: var(--space-3) var(--space-5);
  border-bottom: 1px solid var(--border);
  background: var(--surface);
}
.eo-topbar__right { margin-left: auto; }
.eo-content { padding: var(--space-5); max-width: var(--content-max); width: 100%; }
```

- [ ] **Step 5: Migrar `App.tsx`**

```tsx
import { Route, Routes } from 'react-router-dom'
import Shell from './components/Shell'
import CatalogPage from './pages/CatalogPage'
import ComparePage from './pages/ComparePage'
import ComposePage from './pages/ComposePage'
import ExperimentDetailPage from './pages/ExperimentDetailPage'
import ExperimentsPage from './pages/ExperimentsPage'
import PlatformPage from './pages/PlatformPage'
import PromptSetsPage from './pages/PromptSetsPage'
import RunDetailPage from './pages/RunDetailPage'
import RunsPage from './pages/RunsPage'

export default function App() {
  return (
    <Shell>
      <Routes>
        <Route path="/" element={<RunsPage />} />
        <Route path="/compose" element={<ComposePage />} />
        <Route path="/catalog" element={<CatalogPage />} />
        <Route path="/compare" element={<ComparePage />} />
        <Route path="/runs/:id" element={<RunDetailPage />} />
        <Route path="/platform" element={<PlatformPage />} />
        <Route path="/experiments" element={<ExperimentsPage />} />
        <Route path="/experiments/:id" element={<ExperimentDetailPage />} />
        <Route path="/prompts" element={<PromptSetsPage />} />
      </Routes>
    </Shell>
  )
}
```

- [ ] **Step 6: Migrar `TargetBadge.tsx` a tokens**

Reemplaza los hex por `Badge`:

```tsx
import { useEffect, useState } from 'react'
import { getTarget } from '../api'
import type { TargetStatus } from '../types'
import { Badge } from './ui'

export default function TargetBadge() {
  const [target, setTarget] = useState<TargetStatus | null>(null)
  useEffect(() => {
    let alive = true
    const tick = () =>
      getTarget().then((t) => alive && setTarget(t)).catch(() => alive && setTarget(null))
    tick()
    const timer = setInterval(tick, 5000)
    return () => {
      alive = false
      clearInterval(timer)
    }
  }, [])
  if (!target) return <Badge tone="error">BFF inaccesible</Badge>
  if (!target.healthy) return <Badge tone="error">servicio caído</Badge>
  if (!target.ready) return <Badge tone="warn">cargando modelo…</Badge>
  return (
    <Badge tone="ok">
      {target.model?.ref} <small>({target.model?.device ?? '?'})</small>
    </Badge>
  )
}
```

- [ ] **Step 7: Actualizar `App.test.tsx` al título nuevo**

El `Shell` cambia el `h1` de `E-OVRT Console` a `E-OVRT`, así que el test de caracterización de Task 1 se rompe acá — es exactamente su trabajo: avisar que el refactor cambió comportamiento visible. Actualizar el assert en `frontend/src/__tests__/App.test.tsx`:

```tsx
    expect(screen.getByText('E-OVRT')).toBeTruthy()
```

- [ ] **Step 8: Correr los tests**

Run: `cd webconsole/frontend && npm test`
Expected: PASS — toda la suite, incluidos los 5 tests nuevos de `Shell`.

- [ ] **Step 9: Verificación visual**

Run: `cd webconsole && make dev-frontend`
Expected: sidebar oscuro a la izquierda con 3 grupos y el botón azul "+ Nueva corrida"; breadcrumb arriba; badge del target arriba a la derecha; la tabla de corridas ocupa el ancho.

- [ ] **Step 10: Commit (pedir confirmación primero)**

```bash
git add webconsole/frontend/src/components/Shell.tsx webconsole/frontend/src/components/TargetBadge.tsx webconsole/frontend/src/App.tsx webconsole/frontend/src/styles/ui.css webconsole/frontend/src/__tests__/Shell.test.tsx webconsole/frontend/src/__tests__/App.test.tsx
git commit -m "feat(webconsole): shell con sidebar agrupado por rol"
```

---

### Task 7: Píldora de corrida viva

**Files:**
- Create: `frontend/src/useLiveRun.ts`
- Create: `frontend/src/components/LiveRunPill.tsx`
- Modify: `frontend/src/components/Shell.tsx`, `frontend/src/styles/ui.css`
- Test: `frontend/src/__tests__/LiveRunPill.test.tsx`

**Interfaces:**
- Produces: `useLiveRun(): RunRow | null` — poll de `listRuns()` cada 5000 ms (mismo patrón que `useTarget`), devuelve la primera corrida corriendo o `null`.
- Consumes: `listRuns` de `api.ts`, `RunRow` de `types.ts`, **`isRunning` de `runview.ts` (Task 4)**.

**No crear un predicado nuevo acá.** `isRunning` ya existe en `runview.ts` desde Task 4 y está testeado; usarlo. Tampoco usar `isLive` para la píldora: escondería los runs two-node externos, que son justo el escenario EBE a vigilar (ver el bloque de contexto de Task 4).

- [ ] **Step 1: Escribir el test que falla**

`frontend/src/__tests__/LiveRunPill.test.tsx`:

```tsx
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import LiveRunPill from '../components/LiveRunPill'
import * as api from '../api'

vi.mock('../api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../api')>()),
  listRuns: vi.fn(),
}))

beforeEach(() => vi.clearAllMocks())
afterEach(() => cleanup())

const renderPill = () => render(<MemoryRouter><LiveRunPill /></MemoryRouter>)

describe('LiveRunPill', () => {
  it('no renderiza nada si no hay corrida viva', async () => {
    vi.mocked(api.listRuns).mockResolvedValue([{ run_id: 'r_1', status: 'succeeded' } as any])
    const { container } = renderPill()
    await waitFor(() => expect(vi.mocked(api.listRuns)).toHaveBeenCalled())
    expect(container.textContent).toBe('')
  })

  it('muestra el run vivo con fps y linkea a su detalle', async () => {
    vi.mocked(api.listRuns).mockResolvedValue([
      { run_id: 'r_9', status: 'running', live: true, fps_effective: 42 } as any,
    ])
    renderPill()
    await waitFor(() => expect(screen.getByText('r_9')).toBeTruthy())
    expect(screen.getByText(/42/)).toBeTruthy()
    expect(screen.getByRole('link').getAttribute('href')).toContain('/runs/r_9')
  })

  it('toma running aunque live no venga', async () => {
    vi.mocked(api.listRuns).mockResolvedValue([{ run_id: 'r_x', status: 'running' } as any])
    renderPill()
    await waitFor(() => expect(screen.getByText('r_x')).toBeTruthy())
  })
})
```

- [ ] **Step 2: Correr el test para verificar que falla**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/LiveRunPill.test.tsx`
Expected: FAIL — no existe el módulo.

- [ ] **Step 3: Implementar `useLiveRun.ts`**

```ts
import { useEffect, useState } from 'react'
import { listRuns } from './api'
import { isRunning } from './runview'
import type { RunRow } from './types'

export function useLiveRun(): RunRow | null {
  const [run, setRun] = useState<RunRow | null>(null)
  useEffect(() => {
    let alive = true
    const tick = () =>
      listRuns()
        .then((rows) => alive && setRun(rows.find(isRunning) ?? null))
        .catch(() => alive && setRun(null))
    tick()
    const timer = setInterval(tick, 5000)
    return () => {
      alive = false
      clearInterval(timer)
    }
  }, [])
  return run
}
```

- [ ] **Step 4: Implementar `LiveRunPill.tsx`**

```tsx
import { Link } from 'react-router-dom'
import { useLiveRun } from '../useLiveRun'

export default function LiveRunPill() {
  const run = useLiveRun()
  if (!run) return null
  return (
    <Link to={`/runs/${run.run_id}`} className="eo-livepill">
      <span className="eo-livepill__dot" aria-hidden="true">●</span>
      <span className="eo-livepill__id">{run.run_id}</span>
      <span className="eo-livepill__meta">
        {run.fps_effective != null ? `${run.fps_effective} fps` : 'corriendo'}
      </span>
    </Link>
  )
}
```

- [ ] **Step 5: Agregar las clases a `ui.css`**

```css
/* Live run pill */
.eo-livepill {
  margin-top: auto;
  display: grid;
  gap: 2px;
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--status-live);
  border-radius: var(--radius);
  background: color-mix(in srgb, var(--status-live) 12%, transparent);
  color: var(--text);
}
.eo-livepill:hover { text-decoration: none; background: color-mix(in srgb, var(--status-live) 20%, transparent); }
.eo-livepill__dot { color: var(--status-live); font-size: 0.7em; }
.eo-livepill__id { font-family: var(--font-mono); font-size: var(--text-sm); }
.eo-livepill__meta { font-size: var(--text-xs); color: var(--text-muted); }
```

- [ ] **Step 6: Montar en el `Shell`**

En `frontend/src/components/Shell.tsx`, importar `LiveRunPill` y agregarlo como último hijo de `<aside className="eo-sidebar">`, después de `</nav>`:

```tsx
        </nav>
        <LiveRunPill />
      </aside>
```

Import a agregar: `import LiveRunPill from './LiveRunPill'`

- [ ] **Step 7: Correr los tests**

Run: `cd webconsole/frontend && npm test`
Expected: PASS — 3 tests nuevos.

- [ ] **Step 8: Commit (pedir confirmación primero)**

```bash
git add webconsole/frontend/src/useLiveRun.ts webconsole/frontend/src/components/LiveRunPill.tsx webconsole/frontend/src/components/Shell.tsx webconsole/frontend/src/styles/ui.css webconsole/frontend/src/__tests__/LiveRunPill.test.tsx
git commit -m "feat(webconsole): píldora de corrida viva en el sidebar"
```

---

### Task 8: Migrar ComparePage y EvalSection

**Files:**
- Modify: `frontend/src/pages/ComparePage.tsx`, `frontend/src/components/EvalSection.tsx`
- Test: los existentes `__tests__/ComparePage.test.tsx` (2 tests), `__tests__/EvalSection.test.tsx` (4 tests)

**Interfaces:**
- Consumes: `.eo-table`, `Card`, `EmptyState`, `ErrorBanner`, `Badge`.

- [ ] **Step 1: Correr los tests existentes como red de seguridad**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/ComparePage.test.tsx src/__tests__/EvalSection.test.tsx`
Expected: PASS — 6 tests. **Estos tests no deben cambiar**: son de comportamiento, y la migración es puramente visual. Si se rompen, la migración cambió comportamiento y eso es un bug.

- [ ] **Step 2: Migrar `ComparePage.tsx`**

Aplicar estas tres sustituciones mecánicas:

1. Borrar `const CELL: CSSProperties = { padding: '4px 10px', borderBottom: '1px solid #ddd' }` y el `import type { CSSProperties } from 'react'` si queda sin uso.
2. `<table style={{ borderCollapse: 'collapse', width: '100%' }}>` → `<table className="eo-table">`; borrar todos los `style={CELL}` de `<td>`/`<th>`; los `<th>` con `style={{ ...CELL, textAlign: 'left', background: '#f5f5f5' }}` → `<th>` pelado.
3. Los valores numéricos van con `className="eo-num"`. El resalte del mejor (`fontWeight: 'bold'`) → `className="eo-num eo-best"`.
4. El `skipped` (línea ~91) hoy es `<p style={{ color: '#a60' }}>Sin evaluación (omitidos): {result.skipped.join(', ')}</p>` — la línea entera en ámbar. Migra a **un badge por id salteado**, que es como el kit usa `Badge` en todo el resto (etiqueta un valor de dato, no una palabra fija):

```tsx
{result.skipped.length > 0 && (
  <p>
    Sin evaluación (omitidos):{' '}
    {result.skipped.map((id) => <Badge key={id} tone="warn">{id}</Badge>)}
  </p>
)}
```

No poner `<Badge tone="warn">skipped</Badge>`: mete una palabra inglesa en una frase en español, es redundante con "omitidos" y no etiqueta ningún dato.
5. El estado vacío (`<p>No hay runs evaluados todavía…</p>`) → `<EmptyState>`, igual que `RunsPage`. Es el mismo caso y debe usar la misma primitiva.

Agregar a `ui.css`:

```css
.eo-best { font-weight: 700; color: var(--status-ok); }
```

- [ ] **Step 3: Migrar `EvalSection.tsx`**

Mismas sustituciones: borrar `CELL`, `<table className="eo-table">`, `<td>`/`<th>` pelados, errores por `ErrorBanner`, envolver la sección en `<Card title="Evaluación">`.

- [ ] **Step 4: Verificar que los tests siguen verdes sin tocarlos**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/ComparePage.test.tsx src/__tests__/EvalSection.test.tsx`
Expected: PASS — los mismos 6 tests, sin modificar.

- [ ] **Step 5: Commit (pedir confirmación primero)**

```bash
git add webconsole/frontend/src/pages/ComparePage.tsx webconsole/frontend/src/components/EvalSection.tsx webconsole/frontend/src/styles/ui.css
git commit -m "refactor(webconsole): migrar ComparePage y EvalSection al kit"
```

---

### Task 9: Migrar ExperimentsPage, ExperimentDetailPage y PlatformPage

**Files:**
- Modify: `frontend/src/pages/ExperimentsPage.tsx`, `ExperimentDetailPage.tsx`, `PlatformPage.tsx`
- Test: los existentes `ExperimentsPage.test.tsx` (2), `ExperimentDetailPage.test.tsx` (4), `PlatformPage.test.tsx` (3), `spec44c_gate.test.tsx` (3)

**Interfaces:**
- Consumes: `.eo-table`, `Card`, `Badge`, `alertSeverityTone` (Task 2), `EmptyState`, `ErrorBanner`.

- [ ] **Step 1: Correr los tests existentes como red de seguridad**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/ExperimentsPage.test.tsx src/__tests__/ExperimentDetailPage.test.tsx src/__tests__/PlatformPage.test.tsx src/__tests__/spec44c_gate.test.tsx`
Expected: PASS — 12 tests. Ninguno debe cambiar: `spec44c_gate` es el gate de integración de spec 44 §5.2 y usa `getByRole`/`getByText`, así que sobrevive el retema. **Si se rompe, la migración rompió comportamiento.**

- [ ] **Step 2: Migrar `ExperimentDetailPage.tsx`** (16 `style=`, el más cargado)

1. Borrar `CELL`/`ROW`. Tabla → `className="eo-table"`.
2. El color de severidad: reemplazar todo uso de `alertSeverityColor(...)` como `style={{ color: ... }}` por `<Badge tone={alertSeverityTone(a.severity)}>{a.severity}</Badge>`.
3. El badge no-temporal (ADR-013) → `<Badge tone="neutral">no-temporal</Badge>`. **Conservar el texto exacto** que matchea `/no.?temporal/i` en `spec44c_gate.test.tsx:75`.
4. Secciones → `<Card title="Alertas">`, `<Card title="Reporte">`.
5. `experimentStatusLabel(state)` sigue igual; envolverlo en `<Badge>` con tono derivado: `succeeded`→`ok`, `failed`→`error`, `running`→`live`, resto `neutral`.

- [ ] **Step 3: Migrar `ExperimentsPage.tsx`** (9 `style=`) y `PlatformPage.tsx` (12 `style=`)

Mismas sustituciones mecánicas: borrar `CELL`/`ROW`, `.eo-table`, errores por `ErrorBanner`, vacíos por `EmptyState`, estados por `Badge`. En `ExperimentsPage` **conservar** el texto del botón que matchea `/ejecutar experimento/i` (`spec44c_gate.test.tsx:52`) y el mapeo de 409/422/502 intacto (D7 del spec).

- [ ] **Step 4: Verificar que los tests siguen verdes sin tocarlos**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/ExperimentsPage.test.tsx src/__tests__/ExperimentDetailPage.test.tsx src/__tests__/PlatformPage.test.tsx src/__tests__/spec44c_gate.test.tsx`
Expected: PASS — los mismos 12 tests, sin modificar.

- [ ] **Step 5: Commit (pedir confirmación primero)**

```bash
git add webconsole/frontend/src/pages/ExperimentsPage.tsx webconsole/frontend/src/pages/ExperimentDetailPage.tsx webconsole/frontend/src/pages/PlatformPage.tsx
git commit -m "refactor(webconsole): migrar páginas de experimentos y plataforma al kit"
```

---

### Task 10: Migrar ComposePage y PromptSetEditor

Acá desaparecen los 3 `className` muertos (`prompt-sets-page`, `badge badge-${status}`, `prompt-set-editor`): o se les da CSS real, o se borran.

**Files:**
- Modify: `frontend/src/pages/ComposePage.tsx`, `frontend/src/pages/PromptSetsPage.tsx`, `frontend/src/components/PromptSetEditor.tsx`
- Modify: `frontend/src/styles/ui.css`
- Test: los existentes `ComposePage.test.tsx` (5), `PromptSetEditor.test.tsx` (5), `PromptSetsPage.test.tsx` (2)

**Interfaces:**
- Consumes: `Field`, `Card`, `Badge`, `ErrorBanner`, `EmptyState`.

- [ ] **Step 1: Correr los tests existentes como red de seguridad**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/ComposePage.test.tsx src/__tests__/PromptSetEditor.test.tsx src/__tests__/PromptSetsPage.test.tsx`
Expected: PASS — 12 tests.

- [ ] **Step 2: Migrar `ComposePage.tsx`** (13 `style=`, la `ROW` más usada)

1. Borrar `const ROW: CSSProperties = { display: 'grid', gap: 4, marginBottom: 14, maxWidth: 560 }` — `.eo-field` ya la reemplaza.
2. Cada `<div style={ROW}><label>X</label><input …/></div>` → `<Field label="X"><input …/></Field>`.
3. Los `FieldError[]` que vuelven de `validateComposition()` se pasan al prop `error` del `Field` correspondiente, matcheando por nombre de campo. **No cambiar la lógica de validación** (D7).
4. Agrupar en `<Card title="Ingesta">`, `<Card title="Prompts">`, `<Card title="Parámetros">`.
5. **No tocar** el efecto de prefill (`useSearchParams` + guard `lastPrefilledFrom`): es la costura que usa el Tramo 2.

- [ ] **Step 3: Migrar `PromptSetsPage.tsx` y `PromptSetEditor.tsx`**

- `className="prompt-sets-page"` → borrar (el layout lo da `.eo-content`).
- `className={`badge badge-${s.status}`}` → `<Badge tone={promptStatusTone(s.status)}>{s.status}</Badge>`, con:

```tsx
import type { BadgeTone } from '../types'

function promptStatusTone(status: string): BadgeTone {
  if (status === 'frozen') return 'ok'
  if (status === 'frozen_pending_review') return 'warn'
  return 'neutral' // exploratory y cualquier estado nuevo
}
```

- `className="prompt-set-editor"` → `<Card title="Editar prompt set">`.
- Los campos del editor → `Field`.

- [ ] **Step 4: Verificar que los tests siguen verdes sin tocarlos**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/ComposePage.test.tsx src/__tests__/PromptSetEditor.test.tsx src/__tests__/PromptSetsPage.test.tsx`
Expected: PASS — los mismos 12 tests.

- [ ] **Step 5: Verificar que no quedan className muertos**

Run: `cd webconsole/frontend && grep -rn "prompt-sets-page\|prompt-set-editor\|badge badge-" src/`
Expected: sin resultados.

- [ ] **Step 6: Commit (pedir confirmación primero)**

```bash
git add webconsole/frontend/src/pages/ComposePage.tsx webconsole/frontend/src/pages/PromptSetsPage.tsx webconsole/frontend/src/components/PromptSetEditor.tsx webconsole/frontend/src/styles/ui.css
git commit -m "refactor(webconsole): migrar compositor y prompt sets al kit; eliminar className muertos"
```

---

### Task 11: Migrar CatalogPage y RunDetailPage

**Files:**
- Modify: `frontend/src/pages/CatalogPage.tsx`, `frontend/src/pages/RunDetailPage.tsx`
- Test: `frontend/src/__tests__/RunDetailPage.test.tsx` (nuevo — hoy no existe)

**Interfaces:**
- Consumes: `.eo-table`, `Card`, `StatTile`, `Badge`, `ErrorBanner`, `EmptyState`.

`RunDetailPage` es donde `StatTile` gana su densidad: fps, latencia, detecciones y duración pasan de texto suelto a una fila de tiles legible de un vistazo.

- [ ] **Step 1: Escribir el test que falla**

`frontend/src/__tests__/RunDetailPage.test.tsx`:

```tsx
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import RunDetailPage from '../pages/RunDetailPage'
import * as api from '../api'

vi.mock('../api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../api')>()),
  getRun: vi.fn(),
  getDetections: vi.fn().mockResolvedValue({ items: [], total: 0 }),
  getEvaluation: vi.fn().mockResolvedValue(null),
}))

beforeEach(() => vi.clearAllMocks())
afterEach(() => cleanup())

const renderPage = (id = 'r_1') =>
  render(
    <MemoryRouter initialEntries={[`/runs/${id}`]}>
      <Routes><Route path="/runs/:id" element={<RunDetailPage />} /></Routes>
    </MemoryRouter>,
  )

describe('RunDetailPage', () => {
  it('muestra el estado del run como badge', async () => {
    vi.mocked(api.getRun).mockResolvedValue({ run_id: 'r_1', status: 'succeeded', live: false } as any)
    renderPage()
    await waitFor(() => expect(screen.getByText('OK').className).toContain('eo-badge--ok'))
  })

  it('muestra tiles de métricas cuando hay summary', async () => {
    vi.mocked(api.getRun).mockResolvedValue({
      run_id: 'r_1',
      status: 'succeeded',
      live: false,
      summary: { fps_effective: 24, total_detections: 100, duration_seconds: 5 },
    } as any)
    renderPage()
    await waitFor(() => expect(screen.getByText('24')).toBeTruthy())
    expect(screen.getByText('100')).toBeTruthy()
  })
})
```

- [ ] **Step 2: Correr el test para verificar que falla**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/RunDetailPage.test.tsx`
Expected: FAIL — el estado hoy es texto plano, no `Badge`.

- [ ] **Step 3: Migrar `RunDetailPage.tsx`** (8 `style=`)

**Trampa de TS strict:** `RunDetail.summary` está tipado `Record<string, unknown>` (`types.ts:112`), así que `summary.fps_effective` da `unknown` y **no compila** al renderizarlo en JSX. No resolver esto con `as any`. Agregar un lector tipado arriba del componente:

```tsx
function num(summary: Record<string, unknown> | undefined, key: string): number | null {
  const v = summary?.[key]
  return typeof v === 'number' ? v : null
}
```

Y usar `num(run.summary, 'fps_effective')` para cada tile, con `?? '—'` en el render.

1. Estado → `<Badge tone={runStatusTone(run)}>{runStatusLabel(run)}</Badge>`, importando de `runview.ts` (Task 4). **No redefinir el mapeo acá.**
2. Métricas → fila de `StatTile` dentro de `<div className="eo-stats-row">`: FPS, latencia (`p50_latency_ms`), detecciones (`total_detections`), duración (`duration_seconds`) — todas vía `num()`.
3. Tabla de detecciones → `.eo-table`.
4. Botón "■ Detener" → conservar texto y lógica; solo hereda el estilo de `base.css`.
5. Errores → `ErrorBanner`. Artefactos (video/previews) → `<Card title="Artefactos">`.
6. **No tocar** `useRunStream` ni la lógica del WS.

- [ ] **Step 4: Migrar `CatalogPage.tsx`** (read-only, 4 catálogos)

Cada catálogo → `<Card title="…">` con `.eo-table` adentro. Vacíos → `EmptyState`.

- [ ] **Step 5: Correr toda la suite**

Run: `cd webconsole/frontend && npm test`
Expected: PASS.

- [ ] **Step 6: Commit (pedir confirmación primero)**

```bash
git add webconsole/frontend/src/pages/CatalogPage.tsx webconsole/frontend/src/pages/RunDetailPage.tsx webconsole/frontend/src/__tests__/RunDetailPage.test.tsx
git commit -m "refactor(webconsole): migrar catálogos y detalle de corrida; tiles de métricas"
```

---

### Task 12: Retematizar los gráficos

La paleta de abajo **ya está validada** con `scripts/validate_palette.js` de la skill `dataviz` contra la superficie `#1a1a19`: los 8 slots pasan banda de luminosidad, piso de croma, separación CVD (peor par adyacente ΔE 8.4 protan, target ≥8), piso de visión normal (19.3, piso ≥15) y contraste ≥3:1. **No cambiar estos hex sin volver a correr el validador.**

**Files:**
- Modify: `frontend/src/components/GroupedBars.tsx`, `frontend/src/components/Sparkline.tsx`
- Test: el existente `__tests__/GroupedBars.test.tsx` (4 tests)

**Interfaces:**
- Produces: `SERIES_COLORS: string[]` — la paleta categórica de 8 slots, orden fijo.

- [ ] **Step 1: Correr el test existente como red de seguridad**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/GroupedBars.test.tsx`
Expected: PASS — 4 tests. El único test de color (`rects[0].color === SERIES_COLORS[1]`) va **a través de la constante**, así que cambiar los valores no lo rompe. Los otros 3 son geometría pura.

- [ ] **Step 2: Reemplazar `SERIES_COLORS` en `GroupedBars.tsx`**

```tsx
// Paleta categórica de 8 slots (skill dataviz), stepped para superficie oscura #1a1a19.
// Validada: banda L, croma, CVD adyacente (peor ΔE 8.4 protan), visión normal (19.3), contraste >=3:1.
// El ORDEN es el mecanismo de seguridad CVD, no cosmética: no reordenar sin re-validar.
export const SERIES_COLORS = [
  '#3987e5', // azul
  '#008300', // verde
  '#d55181', // magenta
  '#c98500', // amarillo
  '#199e70', // aqua
  '#d95926', // naranja
  '#9085e9', // violeta
  '#e66767', // rojo
]
```

- [ ] **Step 3: Retematizar el chrome de `GroupedBars.tsx`**

Ejes, grilla y texto salen de tokens vía `currentColor` o `var()`:
- gridlines → `stroke="var(--border)"`
- baseline/eje → `stroke="var(--border-strong)"`
- labels de eje → `fill="var(--text-muted)"`, `fontSize="var(--text-xs)"`

**Regla de dataviz:** el texto usa tokens de texto, nunca el color de la serie. La identidad la carga la marca de color al lado, no la tipografía.

- [ ] **Step 4: Retematizar `Sparkline.tsx`**

Es serie única → **sin leyenda** (el título la nombra). Línea a 2px con `--accent`:

```tsx
stroke="var(--accent)"
strokeWidth={2}
fill="none"
```

- [ ] **Step 5: Verificar que los tests siguen verdes sin tocarlos**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/GroupedBars.test.tsx`
Expected: PASS — los mismos 4 tests.

- [ ] **Step 6: Verificación visual de los gráficos**

Run: `cd webconsole && make dev-frontend`, ir a `/compare` con 2+ runs.
Expected: barras legibles sobre fondo oscuro, series distinguibles, ejes recesivos. Chequear contra `references/anti-patterns.md` de la skill `dataviz`.

- [ ] **Step 7: Commit (pedir confirmación primero)**

```bash
git add webconsole/frontend/src/components/GroupedBars.tsx webconsole/frontend/src/components/Sparkline.tsx
git commit -m "feat(webconsole): paleta de series validada para superficie oscura"
```

---

### Task 13: Barrido final y verificación de criterios

Esta tarea verifica los 8 criterios de éxito del spec §10. No introduce features.

**Files:**
- Modify: lo que aparezca en los greps
- Test: toda la suite

- [ ] **Step 1: Criterio 1 — ningún hex literal en TSX/TS**

Run:
```bash
cd webconsole/frontend && grep -rnE "#[0-9a-fA-F]{3,6}\b" src/ --include=*.tsx --include=*.ts | grep -v "SERIES_COLORS" | grep -v "__tests__"
```
Expected: sin resultados. La única excepción permitida es el bloque `SERIES_COLORS` de `GroupedBars.tsx` (paleta de datos validada).
Si aparece algo, migrarlo a un token.

- [ ] **Step 2: Criterio 2 — `CELL` y `ROW` no existen**

Run: `cd webconsole/frontend && grep -rn "CELL\|const ROW" src/`
Expected: sin resultados.

- [ ] **Step 3: Criterio 3 — sin `className` muertos**

Run: `cd webconsole/frontend && grep -rn "prompt-sets-page\|prompt-set-editor\|badge badge-" src/`
Expected: sin resultados.

- [ ] **Step 4: Criterio — no quedan `style={{}}` de layout ad-hoc**

Run: `cd webconsole/frontend && grep -rc "style={{" src/ --include=*.tsx | grep -v ":0"`
Expected: solo sobreviven los `style` que calculan geometría (SVG en `Sparkline`/`GroupedBars`) o dimensiones dinámicas. Cualquier `style` con color, padding o border es una fuga: migrarlo.

- [ ] **Step 5: Criterios 4-7 — verificación funcional en la app**

Run: `cd webconsole && make build && make serve`, abrir `http://localhost:8090`.

Verificar a mano:
- [ ] Criterio 4: los 6 destinos están en 3 grupos; "+ Nueva corrida" es botón, no link de nav.
- [ ] Criterio 7: lanzar una corrida y confirmar que la píldora aparece en el sidebar desde cualquier pantalla, con fps, y que linkea al detalle.
- [ ] Breadcrumbs correctos en `/runs/:id` y `/experiments/:id`.
- [ ] Criterios 5 y 6 (comparar sin tipear ids, relanzar variando) **quedan para el Tramo 2** — no se verifican acá.

- [ ] **Step 6: Criterio 8 — suite completa verde**

Run: `cd webconsole/frontend && npm test`
Expected: PASS. Baseline: **62** tests previos. Nuevos de este tramo: `App` (1), `Badge` (2), primitivos (9), `runview` (7), `RunsPage` (3), `nav` (8), `Shell` (5), `LiveRunPill` (3), `RunDetailPage` (2) = **+40 → 102 tests**.

**De los 62 previos, se modifica exactamente uno**: el `it` de `alertSeverityColor` en `experimentview.test.ts` (Task 2), que asserteaba hex literales y ahora assertea tonos. Los otros **61 pasan sin tocarse**.

(`App.test.tsx` también cambia en Task 6, pero es un test que nace en este tramo — Task 1 —, no parte del baseline.)

Esa es la línea que separa un retema de una regresión: si algún otro test previo se rompe, la migración cambió comportamiento y **eso es un bug, no un ajuste de test**. No editarlo para que pase.

- [ ] **Step 7: Typecheck y build de producción**

Run: `cd webconsole/frontend && npx tsc --noEmit && npm run build`
Expected: sin errores; el build emite en el dir que sirve el BFF.

- [ ] **Step 8: Correr también los tests del backend (no deberían verse afectados)**

Run: `cd webconsole/backend && .venv/bin/pytest -q`
Expected: PASS — este tramo no toca el backend.

- [ ] **Step 9: Commit final (pedir confirmación primero)**

```bash
git add -A webconsole/
git commit -m "chore(webconsole): barrido final del rediseño tramo 1"
```

---

## Notas para el Tramo 2

Estas costuras quedan preparadas y **no hay que romperlas**:
- El efecto de prefill de `ComposePage` (`useSearchParams` + guard `lastPrefilledFrom`) es el punto de entrada de `?fromRun=`.
- `runview.ts` centraliza los predicados y el mapeo estado→tono (`isLive`, `isRunning`, `runStatusTone`, `runStatusLabel`) — los filtros de Corridas se construyen sobre eso, sin redefinir nada. Ojo con la distinción `isLive` (suscribible por WS) vs `isRunning` (corriendo, incluso two-node externo): no colapsarlas.
- `.eo-table` ya tiene `th` sticky, lo que hace viable una tabla larga con filtros.
