# Rediseño fidelidad — Armazón + Corridas Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reconstruir el armazón de la consola (tokens, barra lateral con iconos y
contadores, barra superior móvil, encabezado de página) y la pantalla Corridas con
fidelidad estructural al prototipo del diseñador (`rediseno-consola-eovrt/prototipo.html`),
reemplazando el trabajo anterior que solo aplicó paleta/glosario sobre la estructura vieja.

**Architecture:** Reescritura de `tokens.css` y gran parte de `ui.css` con los nombres de
variable y clases del prototipo (adaptadas al prefijo `eo-*` ya establecido en el
código, no los nombres cortos del prototipo). Primitivas nuevas en `components/ui/`.
`Shell.tsx` pasa de "tonto" a consultar datos reales para contadores y estado de
motores. `RunsPage.tsx` se reescribe entera. Sin cambios de backend: cada dato que el
prototipo pide y la API no tiene está resuelto con una degradación explícita, citada
del documento de referencia.

**Tech Stack:** React 18 + TypeScript, Vite, Vitest + @testing-library/react (jsdom).
Sin dependencias nuevas.

## Documentos de referencia (léelos, no adivines)

- `docs/superpowers/specs/proto-ref-01-armazon-componentes.md` — armazón y componentes
  transversales, con HTML/CSS reales del prototipo.
- `docs/superpowers/specs/proto-ref-02-corridas.md` — composición exacta de Corridas y
  el cruce dato-por-dato contra la API real (HAY / DERIVABLE / NO HAY).

## Global Constraints

- No hay cambios de backend. Cuando un dato del prototipo no existe en la API real, se
  aplica la degradación que documenta `proto-ref-02.md §3` — nunca se inventa el dato,
  nunca se oculta en silencio sin nota.
- **Excepción de configuración** (no es cambio de código): al relanzar la consola al
  final de este plan, subir `EOVRT_CONSOLE_HYDRATION_LIMIT` (hoy 50) para que el
  listado de Corridas no muestre 45 de 95 filas en blanco. Es una variable de entorno
  ya soportada por el backend actual.
- El violeta (`--ac`) es siempre acción/selección/foco/nav-activa; el azul (`--live`)
  es siempre "en curso". Nunca se intercambian.
- Texto nunca blanco puro (`--tx: #f2f1ed`).
- Todo estado lleva icono/glifo + texto, nunca color solo — única excepción documentada:
  los dos puntos de estado de motores en la barra lateral colapsada (mitigado por tooltip).
- Identificadores, ids, nombres de archivo, nombres de clase → siempre `.eo-mono` (la
  clase `eo-mono` ya existe en `ui.css`), nunca traducidos.
- Sigue el prefijo de clases `eo-*` ya establecido en el código — NO copiar los nombres
  cortos del prototipo (`.kpi`, `.rh`, `.tw`) literalmente.
- Vocabulario de estado real de corridas: `running, succeeded, failed, error, stopped`
  (cinco, no tres) — ya está en `runview.ts` de un trabajo previo, no lo reinventes.
- Run `npm test` (Vitest) y `npm run build` desde `webconsole/frontend/` después de cada tarea.
- Nunca commitear salvo pedido explícito — los pasos "Commit" de este plan commitean
  localmente a la rama actual, sin push.

---

### Task 1: Tokens v2 + set de iconos

**Files:**
- Modify: `webconsole/frontend/src/styles/tokens.css`
- Create: `webconsole/frontend/src/components/ui/icons.tsx`
- Modify: `webconsole/frontend/src/components/ui/index.ts`
- Test: Create `webconsole/frontend/src/__tests__/ui/icons.test.tsx`

**Interfaces:**
- Produce las variables CSS que consumen TODAS las tareas siguientes:
  `--bg, --s1, --s2, --s3, --sunken, --bd, --bds, --tx, --tx2, --tx3, --tx4, --ac,
  --ac-tx, --ac-bg, --ac-bd, --live, --live-bg, --live-bd, --ok, --ok-bg, --ok-bd,
  --wn, --wn-bg, --wn-bd, --sr, --sr-bg, --sr-bd, --er, --er-bg, --er-bd, --nt,
  --fs, --fm, --r, --rc, --row`.
- Produce el módulo `icons.tsx` con componentes: `IconStop, IconPlay, IconWarn, IconCheck,
  IconDownload, IconClose, IconInfo, IconChevron, IconSearch, IconCircle`, más los ocho
  iconos de navegación: `IconNavRuns, IconNavExperiments, IconNavCompare, IconNavPrompts,
  IconNavCatalog, IconNavPlatform, IconNavCameras, IconNavClips`.

- [ ] **Step 1: Reemplazar `tokens.css` completo**

Copiar tal cual `proto-ref-01-armazon-componentes.md §0.1` (los tokens) y `§0.2` (reglas
globales), adaptado: mantené `--row: 32px` etc. igual, pero conservá también los
tokens que el código YA usa y que no están en el prototipo pero se siguen necesitando:
`--space-1..6` (espaciado), `--text-xs..xl` (si algún componente viejo no migrado en
esta tarea los sigue usando — grep `--space-` y `--text-` en `src/` antes de decidir si
podés borrarlos; si hay consumidores fuera del alcance de este plan, dejalos).

```css
:root{
  color-scheme: dark;
  /* superficies (5 niveles) */
  --bg:#121211;      /* lienzo de la página — el MÁS oscuro */
  --s1:#1a1a19;      /* tarjeta / barra lateral */
  --s2:#212120;      /* elevado: inputs, th, seg, chips neutros, hover de fila */
  --s3:#2a2a28;      /* emergente: popovers, tooltips, botón segmentado activo */
  --sunken:#0d0d0c;  /* hundido: fondo de medidor, visor, carril de línea de tiempo */
  /* bordes */
  --bd:rgba(255,255,255,.09);
  --bds:rgba(255,255,255,.17);
  /* texto */
  --tx:#f2f1ed; --tx2:#b3b1a8; --tx3:#82807a; --tx4:#5c5b56;
  /* acento = acción / selección / foco / navegación activa */
  --ac:#7d6ef2; --ac-tx:#a89df6; --ac-bg:rgba(125,110,242,.14); --ac-bd:rgba(125,110,242,.42);
  --ac-hover:#8b7df4;
  --ac-text-on:#150f3d;
  /* estados */
  --live:#4b95e8; --live-bg:rgba(75,149,232,.14); --live-bd:rgba(75,149,232,.4);
  --ok:#35b45a;   --ok-bg:rgba(53,180,90,.14);   --ok-bd:rgba(53,180,90,.4);
  --wn:#e0a217;   --wn-bg:rgba(224,162,23,.13);  --wn-bd:rgba(224,162,23,.38);
  --sr:#ee8a5c;   --sr-bg:rgba(238,138,92,.13);  --sr-bd:rgba(238,138,92,.38);
  --er:#f0625f;   --er-bg:rgba(240,98,95,.13);   --er-bd:rgba(240,98,95,.4);
  --nt:#8a8880;
  /* tipografía */
  --fs:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
  --fm:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  /* forma */
  --r:6px;
  --rc:10px;
  --row:32px;
  /* layout de armazón */
  --sidebar-width: 214px;
  --sidebar-width-collapsed: 54px;
  --content-max: 1600px;
}
```

- [ ] **Step 2: Escribir el test de iconos**

```tsx
import { describe, expect, it, afterEach } from 'vitest'
import { cleanup, render } from '@testing-library/react'
import { IconPlay, IconStop, IconNavRuns } from '../../components/ui/icons'

afterEach(() => cleanup())

describe('icons', () => {
  it('cada icono renderiza un svg 16x16 marcado aria-hidden', () => {
    for (const Icon of [IconPlay, IconStop, IconNavRuns]) {
      const { container } = render(<Icon />)
      const svg = container.querySelector('svg')
      expect(svg).toBeTruthy()
      expect(svg?.getAttribute('aria-hidden')).toBe('true')
    }
  })
})
```

- [ ] **Step 3: Correr el test, confirmar que falla**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/ui/icons.test.tsx`
Expected: FAIL — el módulo no existe.

- [ ] **Step 4: Implementar `icons.tsx`**

Cada icono es un componente sin props, SVG 16×16, `aria-hidden="true"`. Usá
`stroke="currentColor"` salvo donde el path del prototipo dice `fill`. Tomá los paths
EXACTOS de `proto-ref-01-armazon-componentes.md §0.3` (tabla de iconos) y de la lista de
iconos de navegación al final de `§2.4`. Estructura de cada uno:

```tsx
export function IconPlay() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">
      <path d="M4 3l9 5-9 5z" fill="currentColor" />
    </svg>
  )
}

export function IconStop() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">
      <rect x="4" y="4" width="8" height="8" rx="1" fill="currentColor" />
    </svg>
  )
}

export function IconWarn() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
      <path d="M8 2.6L14.4 13.9h-12.8z" />
      <path d="M8 6.6v3.1M8 11.6v.1" />
    </svg>
  )
}

export function IconCheck() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
      <path d="M3.5 8.5l3 3 6-7" />
    </svg>
  )
}

export function IconDownload() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true">
      <path d="M8 2.5v8M4.5 7.5L8 11l3.5-3.5M3 13.5h10" />
    </svg>
  )
}

export function IconClose() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
      <path d="M4 4l8 8M12 4l-8 8" />
    </svg>
  )
}

export function IconInfo() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
      <circle cx="8" cy="8" r="6" />
      <path d="M8 7.4v3.6M8 5.2v.1" />
    </svg>
  )
}

export function IconChevron() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true">
      <path d="M4 6.5L8 10.5l4-4" />
    </svg>
  )
}

export function IconSearch() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true">
      <circle cx="7" cy="7" r="4.6" />
      <path d="M10.4 10.4L14 14" />
    </svg>
  )
}

export function IconCircle() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true">
      <circle cx="8" cy="8" r="5.6" />
    </svg>
  )
}

export function IconNavRuns() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4" aria-hidden="true">
      <path d="M2.5 4h11M2.5 8h6M2.5 12h6" />
      <path d="M11.2 9.6l3 1.9-3 1.9z" />
    </svg>
  )
}

export function IconNavExperiments() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4" aria-hidden="true">
      <path d="M6.3 2v4.2L2.9 12a1.4 1.4 0 0 0 1.2 2.1h7.8A1.4 1.4 0 0 0 13.1 12L9.7 6.2V2" />
      <path d="M5.4 2h5.2M4.7 10h6.6" />
    </svg>
  )
}

export function IconNavCompare() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4" aria-hidden="true">
      <path d="M2.5 13.5h11" />
      <rect x="3.4" y="7" width="2.6" height="4.4" />
      <rect x="7.2" y="3.6" width="2.6" height="7.8" />
      <rect x="11" y="8.8" width="2.6" height="2.6" />
    </svg>
  )
}

export function IconNavPrompts() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4" aria-hidden="true">
      <path d="M2.4 3.6a1.2 1.2 0 0 1 1.2-1.2h8.8a1.2 1.2 0 0 1 1.2 1.2v6a1.2 1.2 0 0 1-1.2 1.2H6.6L3.4 13.4v-2.6a1.2 1.2 0 0 1-1-1.2z" />
      <path d="M5.2 5.6h5.6M5.2 7.8h3.4" />
    </svg>
  )
}

export function IconNavCatalog() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4" aria-hidden="true">
      <path d="M8 3.4L2.4 6 8 8.6 13.6 6z" />
      <path d="M2.4 9.2L8 11.8l5.6-2.6" />
      <path d="M2.4 12.2L8 14.8l5.6-2.6" />
    </svg>
  )
}

export function IconNavPlatform() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4" aria-hidden="true">
      <rect x="2.2" y="2.6" width="11.6" height="4.4" rx="1.2" />
      <rect x="2.2" y="9" width="11.6" height="4.4" rx="1.2" />
      <path d="M4.8 4.8v.01M4.8 11.2v.01" />
    </svg>
  )
}

export function IconNavCameras() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4" aria-hidden="true">
      <rect x="1.8" y="4.4" width="12.4" height="8.2" rx="1.4" />
      <circle cx="8" cy="8.5" r="2.4" />
      <path d="M5.6 4.4l.9-1.6h3l.9 1.6" />
    </svg>
  )
}

export function IconNavClips() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4" aria-hidden="true">
      <rect x="1.8" y="3.2" width="12.4" height="9.6" rx="1.4" />
      <path d="M5.2 3.2v9.6M10.8 3.2v9.6M1.8 8h12.4" />
    </svg>
  )
}
```

- [ ] **Step 5: Correr el test, confirmar que pasa**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/ui/icons.test.tsx`
Expected: PASS.

- [ ] **Step 5b: Exportar los iconos desde `index.ts`**

Agregar al final de `src/components/ui/index.ts`:

```ts
export {
  IconStop, IconPlay, IconWarn, IconCheck, IconDownload, IconClose, IconInfo,
  IconChevron, IconSearch, IconCircle, IconNavRuns, IconNavExperiments,
  IconNavCompare, IconNavPrompts, IconNavCatalog, IconNavPlatform,
  IconNavCameras, IconNavClips,
} from './icons'
```

- [ ] **Step 6: Correr la suite completa y el build**

Run: `cd webconsole/frontend && npm test && npm run build`
Expected: puede haber roturas visuales (nada rojo en tests todavía, ya que nada
consume los tokens nuevos por nombre viejo — pero SI algún test existente lee un valor
de color computado o una clase que dependía de un token viejo que borraste, va a
fallar; si eso pasa, no lo arregles en esta tarea — reportalo como
DONE_WITH_CONCERNS con el detalle, la Tarea 7 en adelante migra los consumidores).

- [ ] **Step 7: Commit**

```bash
cd webconsole/frontend
git add src/styles/tokens.css src/components/ui/icons.tsx src/components/ui/index.ts src/__tests__/ui/icons.test.tsx
git commit -m "design: tokens v2 (paleta exacta del prototipo) + set de iconos"
```

---

### Task 2: Chip/Badge con pulso + Banner

**Files:**
- Modify: `webconsole/frontend/src/components/ui/Badge.tsx`
- Modify: `webconsole/frontend/src/types.ts` (si `BadgeTone` necesita ajuste)
- Create: `webconsole/frontend/src/components/ui/Banner.tsx`
- Modify: `webconsole/frontend/src/components/ui/index.ts`
- Modify: `webconsole/frontend/src/styles/ui.css`
- Test: Create `webconsole/frontend/src/__tests__/ui/Banner.test.tsx`
- Test: Modify `webconsole/frontend/src/__tests__/ui/Badge.test.tsx`

**Interfaces:**
- `Badge` gana una prop opcional `pulse?: boolean` — pinta el punto latiente en vez del
  glifo de icono, para el tono `live`.
- Produce `Banner({ tone: 'warn' | 'error' | 'live', children, onClose?, action? }): JSX.Element`
  — el componente `.banner` del prototipo (§13.1/§13.2 de `proto-ref-01`).

- [ ] **Step 1: Escribir los tests**

Agregar a `src/__tests__/ui/Badge.test.tsx`:

```tsx
  it('con pulse=true en tono live, muestra el punto latiente en vez del icono', () => {
    render(<Badge tone="live" pulse>En curso</Badge>)
    expect(document.querySelector('.eo-badge__pulse')).toBeTruthy()
  })
```

Crear `src/__tests__/ui/Banner.test.tsx`:

```tsx
import { describe, expect, it, afterEach, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { Banner } from '../../components/ui'

afterEach(() => cleanup())

describe('Banner', () => {
  it('tono warn con boton de cerrar', () => {
    const onClose = vi.fn()
    render(<Banner tone="warn" onClose={onClose}>El motor de reglas no responde.</Banner>)
    expect(screen.getByText('El motor de reglas no responde.')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: /cerrar aviso/i }))
    expect(onClose).toHaveBeenCalled()
  })

  it('tono live con accion, sin boton de cerrar si no se pasa onClose', () => {
    render(
      <Banner tone="live" action={<button>Ver en vivo</button>}>
        Ronda nocturna — cámara 04 está procesando ahora.
      </Banner>,
    )
    expect(screen.getByRole('button', { name: 'Ver en vivo' })).toBeTruthy()
    expect(screen.queryByRole('button', { name: /cerrar aviso/i })).toBeNull()
  })

  it('tono error sin accion ni cierre no rompe', () => {
    render(<Banner tone="error">Hay una corrida en curso.</Banner>)
    expect(screen.getByText('Hay una corrida en curso.')).toBeTruthy()
  })
})
```

- [ ] **Step 2: Correr, confirmar que fallan**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/ui/Badge.test.tsx src/__tests__/ui/Banner.test.tsx`
Expected: FAIL.

- [ ] **Step 3: Implementar**

`Badge.tsx`:

```tsx
import type { ReactNode } from 'react'
import type { BadgeTone } from '../../types'

export default function Badge({
  tone,
  pulse,
  children,
}: {
  tone: BadgeTone
  pulse?: boolean
  children: ReactNode
}) {
  return (
    <span className={`eo-badge eo-badge--${tone}`}>
      {pulse ? <span className="eo-badge__pulse" aria-hidden="true" /> : null}
      {children}
    </span>
  )
}
```

`Banner.tsx`:

```tsx
import type { ReactNode } from 'react'
import { IconWarn } from './icons'

export default function Banner({
  tone,
  children,
  onClose,
  action,
}: {
  tone: 'warn' | 'error' | 'live'
  children: ReactNode
  onClose?: () => void
  action?: ReactNode
}) {
  return (
    <div className={`eo-banner eo-banner--${tone}`}>
      <span className="eo-banner__icon" aria-hidden="true">
        {tone === 'live' ? <span className="eo-badge__pulse" /> : <IconWarn />}
      </span>
      <div className="eo-banner__body">{children}</div>
      {action}
      {onClose && (
        <button type="button" className="eo-btn eo-btn--ghost" aria-label="Cerrar aviso" onClick={onClose}>
          ✕
        </button>
      )}
    </div>
  )
}
```

- [ ] **Step 4: Agregar el CSS**

En `src/styles/ui.css`, agregar (no borres las reglas `.eo-badge` existentes, agregá
la modificación del pulso y las reglas del banner):

```css
/* Punto que late — único elemento animado del sistema. */
.eo-badge__pulse {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--live);
  display: inline-block;
  animation: eo-pulse 2s ease-in-out infinite;
}
@keyframes eo-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: .35; }
}
@media (prefers-reduced-motion: reduce) {
  .eo-badge__pulse { animation: none; }
}

/* Banner — aviso de bloque ancho completo. */
.eo-banner {
  display: flex;
  align-items: flex-start;
  gap: 9px;
  border-radius: 8px;
  padding: 8px 11px;
  font-size: 12px;
  border: 1px solid;
  margin: 0 20px 12px;
}
.eo-banner--warn { background: var(--wn-bg); border-color: var(--wn-bd); }
.eo-banner--error { background: var(--er-bg); border-color: var(--er-bd); }
.eo-banner--live { background: var(--live-bg); border-color: var(--live-bd); }
.eo-banner__icon { flex: none; margin-top: 1px; color: var(--wn); display: flex; }
.eo-banner--error .eo-banner__icon { color: var(--er); }
.eo-banner--live .eo-banner__icon { padding-top: 4px; }
.eo-banner__body { flex: 1; color: var(--tx2); }
.eo-banner__body b { color: var(--tx); font-weight: 500; }
```

- [ ] **Step 5: Correr los tests, confirmar que pasan**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/ui/Badge.test.tsx src/__tests__/ui/Banner.test.tsx`
Expected: PASS.

- [ ] **Step 6: Exportar `Banner` desde `index.ts`, correr suite + build**

Agregar a `src/components/ui/index.ts`:

```ts
export { default as Banner } from './Banner'
```

Run: `cd webconsole/frontend && npm test && npm run build`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
cd webconsole/frontend
git add src/components/ui/Badge.tsx src/components/ui/Banner.tsx src/components/ui/index.ts src/styles/ui.css src/__tests__/ui/Badge.test.tsx src/__tests__/ui/Banner.test.tsx
git commit -m "design: Badge con pulso + primitivo Banner"
```

---

### Task 3: SearchInput + SegmentedControl

**Files:**
- Create: `webconsole/frontend/src/components/ui/SearchInput.tsx`
- Create: `webconsole/frontend/src/components/ui/SegmentedControl.tsx`
- Modify: `webconsole/frontend/src/components/ui/index.ts`
- Modify: `webconsole/frontend/src/styles/ui.css`
- Test: Create `webconsole/frontend/src/__tests__/ui/SearchInput.test.tsx`
- Test: Create `webconsole/frontend/src/__tests__/ui/SegmentedControl.test.tsx`

**Interfaces:**
- `SearchInput({ value, onChange, placeholder, ariaLabel }): JSX.Element`
- `SegmentedControl<T extends string>({ value, options, onChange }): JSX.Element` donde
  `options: Array<{ value: T; label: string }>`.

- [ ] **Step 1: Escribir los tests**

`SearchInput.test.tsx`:

```tsx
import { describe, expect, it, afterEach, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { SearchInput } from '../../components/ui'

afterEach(() => cleanup())

describe('SearchInput', () => {
  it('dispara onChange con cada tecleo', () => {
    const onChange = vi.fn()
    render(<SearchInput value="" onChange={onChange} placeholder="Buscar…" ariaLabel="Buscar corridas" />)
    fireEvent.change(screen.getByLabelText('Buscar corridas'), { target: { value: 'noc' } })
    expect(onChange).toHaveBeenCalledWith('noc')
  })
})
```

`SegmentedControl.test.tsx`:

```tsx
import { describe, expect, it, afterEach, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { SegmentedControl } from '../../components/ui'

afterEach(() => cleanup())

const OPTS = [
  { value: 'all', label: 'Todas' },
  { value: 'run', label: 'En curso' },
]

describe('SegmentedControl', () => {
  it('marca la opcion activa con aria-pressed', () => {
    render(<SegmentedControl value="all" options={OPTS} onChange={() => {}} />)
    expect(screen.getByRole('button', { name: 'Todas' }).getAttribute('aria-pressed')).toBe('true')
    expect(screen.getByRole('button', { name: 'En curso' }).getAttribute('aria-pressed')).toBe('false')
  })

  it('clic dispara onChange con el value de la opcion', () => {
    const onChange = vi.fn()
    render(<SegmentedControl value="all" options={OPTS} onChange={onChange} />)
    fireEvent.click(screen.getByRole('button', { name: 'En curso' }))
    expect(onChange).toHaveBeenCalledWith('run')
  })
})
```

- [ ] **Step 2: Correr, confirmar que fallan**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/ui/SearchInput.test.tsx src/__tests__/ui/SegmentedControl.test.tsx`
Expected: FAIL.

- [ ] **Step 3: Implementar**

`SearchInput.tsx`:

```tsx
import { IconSearch } from './icons'

export default function SearchInput({
  value,
  onChange,
  placeholder,
  ariaLabel,
}: {
  value: string
  onChange: (value: string) => void
  placeholder: string
  ariaLabel: string
}) {
  return (
    <div className="eo-search">
      <span className="eo-search__icon" aria-hidden="true">
        <IconSearch />
      </span>
      <input
        type="search"
        className="eo-search__input"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        aria-label={ariaLabel}
      />
    </div>
  )
}
```

`SegmentedControl.tsx`:

```tsx
export interface SegmentedOption<T extends string> {
  value: T
  label: string
}

export default function SegmentedControl<T extends string>({
  value,
  options,
  onChange,
}: {
  value: T
  options: Array<SegmentedOption<T>>
  onChange: (value: T) => void
}) {
  return (
    <div className="eo-segmented">
      {options.map((opt) => (
        <button
          key={opt.value}
          type="button"
          aria-pressed={opt.value === value}
          onClick={() => onChange(opt.value)}
        >
          {opt.label}
        </button>
      ))}
    </div>
  )
}
```

- [ ] **Step 4: Agregar el CSS**

```css
/* Buscador */
.eo-search { position: relative; flex: 1; min-width: 180px; max-width: 300px; }
.eo-search__input {
  width: 100%;
  height: 30px;
  background: var(--s2);
  border: 1px solid var(--bd);
  border-radius: var(--r);
  color: var(--tx);
  padding: 0 9px 0 30px;
  font-size: 12px;
  font-family: inherit;
}
.eo-search__input::placeholder { color: var(--tx4); }
.eo-search__icon {
  position: absolute;
  left: 9px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--tx3);
  display: flex;
}

/* Segmentado de filtro */
.eo-segmented {
  display: inline-flex;
  background: var(--s2);
  border: 1px solid var(--bd);
  border-radius: var(--r);
  padding: 2px;
}
.eo-segmented button {
  padding: 3px 10px;
  border-radius: 4px;
  font-size: 12px;
  color: var(--tx3);
  border: none;
  background: none;
}
.eo-segmented button:hover { color: var(--tx2); }
.eo-segmented button[aria-pressed="true"] { background: var(--s3); color: var(--tx); }

/* Barra de herramientas: buscador + segmentado + contador */
.eo-toolbar2 {
  display: flex;
  align-items: center;
  gap: 9px;
  flex-wrap: wrap;
  padding: 13px 20px 0;
}
.eo-toolbar2__count { margin-left: auto; font-size: 11px; color: var(--tx4); font-family: var(--fm); }
```

(Nombrá la clase de la barra de herramientas `eo-toolbar2` para no chocar con
`.eo-toolbar` si ya existe una regla con ese nombre en `ui.css` de un trabajo anterior
— revisá con `grep -n "\.eo-toolbar" src/styles/ui.css` antes de decidir el nombre
final; si `.eo-toolbar` está libre o es genérica y sirve, usá esa y no crees `eo-toolbar2`.)

- [ ] **Step 5: Correr los tests, confirmar que pasan**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/ui/SearchInput.test.tsx src/__tests__/ui/SegmentedControl.test.tsx`
Expected: PASS.

- [ ] **Step 5b: Exportar desde `index.ts`**

Agregar a `src/components/ui/index.ts`:

```ts
export { default as SearchInput } from './SearchInput'
export { default as SegmentedControl } from './SegmentedControl'
export type { SegmentedOption } from './SegmentedControl'
```

- [ ] **Step 6: Suite completa + build**

Run: `cd webconsole/frontend && npm test && npm run build`

- [ ] **Step 7: Commit**

```bash
cd webconsole/frontend
git add src/components/ui/SearchInput.tsx src/components/ui/SegmentedControl.tsx src/components/ui/index.ts src/styles/ui.css src/__tests__/ui/SearchInput.test.tsx src/__tests__/ui/SegmentedControl.test.tsx
git commit -m "design: primitivos SearchInput y SegmentedControl"
```

---

### Task 4: Tabla — encabezado ordenable, celda de nombre en dos líneas, confirmación de borrado en línea

**Files:**
- Modify: `webconsole/frontend/src/components/ui/Table.tsx`
- Create: `webconsole/frontend/src/components/ui/InlineDeleteConfirm.tsx`
- Modify: `webconsole/frontend/src/components/ui/index.ts`
- Modify: `webconsole/frontend/src/styles/ui.css`
- Test: Modify `webconsole/frontend/src/__tests__/ui/Table.test.tsx`
- Test: Create `webconsole/frontend/src/__tests__/ui/InlineDeleteConfirm.test.tsx`

**Interfaces:**
- `Table` gana `SortableHeader({ label, sortKey, sortState, onSort }): JSX.Element` y
  `RowNameCell({ title, subtitle }): JSX.Element` como exports nuevos del mismo archivo.
- `InlineDeleteConfirm({ onConfirm, onCancel }): JSX.Element` — reemplaza el botón
  "Borrar" mientras se confirma.

- [ ] **Step 1: Escribir los tests**

Agregar a `src/__tests__/ui/Table.test.tsx`:

```tsx
import { SortableHeader, RowNameCell } from '../../components/ui'

describe('SortableHeader', () => {
  it('muestra la flecha solo en la columna activa, en la direccion correcta', () => {
    render(
      <table><thead><tr>
        <SortableHeader label="Corrida" sortKey="nm" sortState={{ key: 'nm', dir: 'asc' }} onSort={() => {}} />
        <SortableHeader label="Cuadros/s" sortKey="fps" sortState={{ key: 'nm', dir: 'asc' }} onSort={() => {}} />
      </tr></thead></table>,
    )
    const ths = screen.getAllByRole('columnheader')
    expect(ths[0].textContent).toContain('↑')
    expect(ths[1].textContent).not.toContain('↑')
    expect(ths[1].textContent).not.toContain('↓')
  })

  it('clic dispara onSort con la clave de la columna', () => {
    const onSort = vi.fn()
    render(
      <table><thead><tr>
        <SortableHeader label="Corrida" sortKey="nm" sortState={null} onSort={onSort} />
      </tr></thead></table>,
    )
    fireEvent.click(screen.getByRole('columnheader'))
    expect(onSort).toHaveBeenCalledWith('nm')
  })
})

describe('RowNameCell', () => {
  it('con titulo y subtitulo, el subtitulo va en monoespaciada', () => {
    render(<table><tbody><tr><RowNameCell title="Ronda nocturna" subtitle="run_20260725_143012" /></tr></tbody></table>)
    expect(screen.getByText('Ronda nocturna')).toBeTruthy()
    expect(screen.getByText('run_20260725_143012').className).toContain('eo-mono')
  })
})
```

(Agregá los imports de `fireEvent`, `screen` si el archivo no los tiene ya — revisá el
encabezado del archivo existente antes de duplicar imports.)

Crear `src/__tests__/ui/InlineDeleteConfirm.test.tsx`:

```tsx
import { describe, expect, it, afterEach, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { InlineDeleteConfirm } from '../../components/ui'

afterEach(() => cleanup())

describe('InlineDeleteConfirm', () => {
  it('"Si, borrar" dispara onConfirm; "No" dispara onCancel', () => {
    const onConfirm = vi.fn()
    const onCancel = vi.fn()
    render(<InlineDeleteConfirm onConfirm={onConfirm} onCancel={onCancel} />)
    expect(screen.getByText('¿Borrar?')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: /sí, borrar/i }))
    expect(onConfirm).toHaveBeenCalled()
  })

  it('No dispara onCancel', () => {
    const onCancel = vi.fn()
    render(<InlineDeleteConfirm onConfirm={() => {}} onCancel={onCancel} />)
    fireEvent.click(screen.getByRole('button', { name: 'No' }))
    expect(onCancel).toHaveBeenCalled()
  })
})
```

- [ ] **Step 2: Correr, confirmar que fallan**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/ui/Table.test.tsx src/__tests__/ui/InlineDeleteConfirm.test.tsx`
Expected: FAIL.

- [ ] **Step 3: Implementar**

Agregar a `Table.tsx` (no borrar `Table`, `MonoCell`, `NumCell` existentes):

```tsx
export interface SortState {
  key: string
  dir: 'asc' | 'desc'
}

export function SortableHeader({
  label,
  sortKey,
  sortState,
  onSort,
  numeric,
}: {
  label: string
  sortKey: string
  sortState: SortState | null
  onSort: (key: string) => void
  numeric?: boolean
}) {
  const active = sortState?.key === sortKey
  return (
    <th
      className={numeric ? 'eo-th--sortable eo-th--numeric' : 'eo-th--sortable'}
      onClick={() => onSort(sortKey)}
    >
      {label}
      {active && <span className="eo-th__arrow">{sortState!.dir === 'asc' ? '↑' : '↓'}</span>}
    </th>
  )
}

export function RowNameCell({ title, subtitle }: { title: ReactNode; subtitle?: ReactNode }) {
  return (
    <td>
      <span className="eo-rowname">
        <b>{title}</b>
        {subtitle && <span className="eo-mono">{subtitle}</span>}
      </span>
    </td>
  )
}
```

(Necesitás importar `type { ReactNode }` si `Table.tsx` no lo tiene ya — revisá el
import existente antes de duplicarlo.)

`InlineDeleteConfirm.tsx`:

```tsx
import Button from './Button'

export default function InlineDeleteConfirm({
  onConfirm,
  onCancel,
}: {
  onConfirm: () => void
  onCancel: () => void
}) {
  return (
    <span className="eo-delete-confirm">
      ¿Borrar?
      <Button variant="danger" onClick={onConfirm}>Sí, borrar</Button>
      <Button variant="ghost" onClick={onCancel}>No</Button>
    </span>
  )
}
```

- [ ] **Step 4: Agregar el CSS**

```css
th.eo-th--sortable { cursor: pointer; user-select: none; }
th.eo-th--sortable:hover { color: var(--tx2); }
th.eo-th--numeric { text-align: right; }
.eo-th__arrow { margin-left: 4px; color: var(--ac-tx); }

.eo-rowname { display: flex; flex-direction: column; gap: 1px; min-width: 0; padding: 5px 0; }
.eo-rowname b {
  font-weight: 400;
  color: var(--tx);
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.eo-delete-confirm {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 11.5px;
  color: var(--tx2);
  white-space: nowrap;
}
```

- [ ] **Step 5: Correr los tests, confirmar que pasan**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/ui/Table.test.tsx src/__tests__/ui/InlineDeleteConfirm.test.tsx`
Expected: PASS.

- [ ] **Step 5b: Exportar desde `index.ts`**

Cambiar la línea existente `export { Table, MonoCell, NumCell } from './Table'` por:

```ts
export { Table, MonoCell, NumCell, SortableHeader, RowNameCell } from './Table'
export type { SortState } from './Table'
```

Agregar además:

```ts
export { default as InlineDeleteConfirm } from './InlineDeleteConfirm'
```

- [ ] **Step 6: Suite completa + build**

Run: `cd webconsole/frontend && npm test && npm run build`

- [ ] **Step 7: Commit**

```bash
cd webconsole/frontend
git add src/components/ui/Table.tsx src/components/ui/InlineDeleteConfirm.tsx src/components/ui/index.ts src/styles/ui.css src/__tests__/ui/Table.test.tsx src/__tests__/ui/InlineDeleteConfirm.test.tsx
git commit -m "design: encabezado ordenable, celda de nombre en dos lineas, confirmacion de borrado en linea"
```

---

### Task 5: Estados vacíos (inline y grande) + Encabezado de página

**Files:**
- Modify: `webconsole/frontend/src/components/ui/EmptyState.tsx`
- Create: `webconsole/frontend/src/components/ui/PageHeader.tsx`
- Modify: `webconsole/frontend/src/components/ui/index.ts`
- Modify: `webconsole/frontend/src/styles/ui.css`
- Test: Modify `webconsole/frontend/src/__tests__/ui/primitives.test.tsx` (o el archivo
  donde estén los tests de `EmptyState` — revisá con `grep -rln "EmptyState" src/__tests__/`)
- Test: Create `webconsole/frontend/src/__tests__/ui/PageHeader.test.tsx`

**Interfaces:**
- `EmptyState` gana una prop opcional `hint?: ReactNode` (segunda línea, atenuada) y
  mantiene su forma actual (`children` como texto principal) para no romper a sus
  consumidores actuales — revisá `grep -rln "EmptyState" src/pages/ src/components/`
  antes de decidir si migrás algún call-site en esta tarea (no es obligatorio: alcanza
  con que la prop nueva sea opcional).
- `PageHeader({ title, meta, actions }): JSX.Element` — el `.rh` del prototipo.

- [ ] **Step 1: Escribir los tests**

Agregar donde estén los tests actuales de `EmptyState`:

```tsx
  it('con hint, muestra una segunda linea atenuada', () => {
    render(<EmptyState hint="Probá con otro texto.">Ninguna corrida coincide.</EmptyState>)
    expect(screen.getByText('Ninguna corrida coincide.')).toBeTruthy()
    expect(screen.getByText('Probá con otro texto.').className).toContain('eo-empty__hint')
  })
```

Crear `src/__tests__/ui/PageHeader.test.tsx`:

```tsx
import { describe, expect, it, afterEach } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import { PageHeader } from '../../components/ui'

afterEach(() => cleanup())

describe('PageHeader', () => {
  it('renderiza titulo, meta y acciones', () => {
    render(
      <PageHeader
        title="Corridas"
        meta={<span>9 en total</span>}
        actions={<button>Nueva corrida</button>}
      />,
    )
    expect(screen.getByRole('heading', { name: 'Corridas' })).toBeTruthy()
    expect(screen.getByText('9 en total')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Nueva corrida' })).toBeTruthy()
  })

  it('sin acciones no rompe', () => {
    render(<PageHeader title="Catálogos" meta={<span>Todo lo disponible</span>} />)
    expect(screen.getByRole('heading', { name: 'Catálogos' })).toBeTruthy()
  })
})
```

- [ ] **Step 2: Correr, confirmar que fallan**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/ui/PageHeader.test.tsx`
(y el archivo de `EmptyState` que hayas identificado)
Expected: FAIL.

- [ ] **Step 3: Implementar**

`EmptyState.tsx`:

```tsx
import type { ReactNode } from 'react'

export default function EmptyState({ children, hint }: { children: ReactNode; hint?: ReactNode }) {
  return (
    <p className="eo-empty">
      {children}
      {hint && <><br /><span className="eo-empty__hint">{hint}</span></>}
    </p>
  )
}
```

`PageHeader.tsx`:

```tsx
import type { ReactNode } from 'react'

export default function PageHeader({
  title,
  meta,
  actions,
}: {
  title: string
  meta?: ReactNode
  actions?: ReactNode
}) {
  return (
    <header className="eo-pageheader">
      <div>
        <h1>{title}</h1>
        {meta && <div className="eo-pageheader__meta">{meta}</div>}
      </div>
      {actions && <div className="eo-pageheader__actions">{actions}</div>}
    </header>
  )
}
```

- [ ] **Step 4: Agregar el CSS**

```css
.eo-empty__hint { color: var(--tx4); }

.eo-pageheader {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 14px 20px 12px;
  border-bottom: 1px solid var(--bd);
  flex-wrap: wrap;
}
.eo-pageheader h1 {
  margin: 0;
  font-size: 20px;
  font-weight: 500;
  letter-spacing: -.015em;
  line-height: 1.2;
}
.eo-pageheader__meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 5px;
  flex-wrap: wrap;
  font-size: 11.5px;
  color: var(--tx3);
}
.eo-pageheader__meta .eo-sep { color: var(--tx4); }
.eo-pageheader__actions { margin-left: auto; display: flex; gap: 7px; align-items: center; }
@media (max-width: 760px) {
  .eo-pageheader__actions { margin-left: 0; width: 100%; }
}
```

- [ ] **Step 5: Correr los tests, confirmar que pasan**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/ui/PageHeader.test.tsx` (y el de EmptyState)
Expected: PASS.

- [ ] **Step 5b: Exportar `PageHeader` desde `index.ts`**

Agregar a `src/components/ui/index.ts`:

```ts
export { default as PageHeader } from './PageHeader'
```

(`EmptyState` ya está exportado — solo cambió su implementación interna, no su export.)

- [ ] **Step 6: Suite completa + build**

Run: `cd webconsole/frontend && npm test && npm run build`

- [ ] **Step 7: Commit**

```bash
cd webconsole/frontend
git add src/components/ui/EmptyState.tsx src/components/ui/PageHeader.tsx src/components/ui/index.ts src/styles/ui.css src/__tests__/ui/PageHeader.test.tsx
git commit -m "design: EmptyState con hint + primitivo PageHeader"
```

---

### Task 6: Shell — barra lateral con iconos, contadores y estado de motores

**Files:**
- Modify: `webconsole/frontend/src/components/Shell.tsx`
- Modify: `webconsole/frontend/src/nav.ts`
- Create: `webconsole/frontend/src/useSidebarCounts.ts`
- Create: `webconsole/frontend/src/useServiceHealth.ts`
- Modify: `webconsole/frontend/src/styles/ui.css`
- Test: Modify `webconsole/frontend/src/__tests__/Shell.test.tsx`
- Test: Create `webconsole/frontend/src/__tests__/useSidebarCounts.test.ts`
- Test: Create `webconsole/frontend/src/__tests__/useServiceHealth.test.ts`

**Interfaces:**
- `nav.ts`: cada `NavItem` gana `icon: ComponentType` y `countKey?: 'runs' | 'experiments'
  | 'promptSets'`.
- `useSidebarCounts(): { runs: number | null; experiments: number | null; promptSets: number | null }`
  — hook que trae los tres contadores. `runs` = corridas con `status === 'running'`
  (de `listRuns()`, ya cargado en otras pantallas — para este hook hacé su propio fetch
  liviano); `experiments` = `getExperimentManifests().length`; `promptSets` =
  `listPromptSets().length`. Un contador es `null` mientras carga o si el fetch falla —
  en ese caso el `.ct` simplemente no se muestra (nunca "0" a menos que el conteo real
  sea 0).
- `useServiceHealth(): { media: 'ok' | 'down' | 'checking'; control: 'ok' | 'down' | 'checking' }`
  — sondea `GET /api/target` (representa al motor de detección — si responde 200 es
  `ok`) y `GET /api/preflight` (`control.healthy` para el motor de reglas). Poll cada
  10s. Mirá `src/api.ts` para los nombres reales de las funciones ya existentes
  (`getTarget`, `getPreflight` o como se llamen — greppealos antes de inventar un
  nombre nuevo).

- [ ] **Step 1: Escribir los tests de los hooks**

Antes de escribir, leé `src/api.ts` completo para confirmar los nombres exactos de
`getTarget`/`getPreflight` (o equivalentes) y su forma de respuesta — no adivines.

`src/__tests__/useSidebarCounts.test.ts`:

```ts
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { useSidebarCounts } from '../useSidebarCounts'
import * as api from '../api'

vi.mock('../api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../api')>()),
  listRuns: vi.fn(),
  getExperimentManifests: vi.fn(),
  listPromptSets: vi.fn(),
}))

beforeEach(() => vi.clearAllMocks())

describe('useSidebarCounts', () => {
  it('cuenta las corridas en curso, los manifiestos y los conjuntos de prompts', async () => {
    vi.mocked(api.listRuns).mockResolvedValue([
      { run_id: 'r1', status: 'running' } as any,
      { run_id: 'r2', status: 'succeeded' } as any,
    ])
    vi.mocked(api.getExperimentManifests).mockResolvedValue([{ slug: 'a' } as any, { slug: 'b' } as any])
    vi.mocked(api.listPromptSets).mockResolvedValue([{ id: 'p1' } as any])
    const { result } = renderHook(() => useSidebarCounts())
    await waitFor(() => expect(result.current.runs).toBe(1))
    expect(result.current.experiments).toBe(2)
    expect(result.current.promptSets).toBe(1)
  })

  it('si un fetch falla, ese contador queda en null sin romper los demas', async () => {
    vi.mocked(api.listRuns).mockRejectedValue(new Error('x'))
    vi.mocked(api.getExperimentManifests).mockResolvedValue([{ slug: 'a' } as any])
    vi.mocked(api.listPromptSets).mockResolvedValue([])
    const { result } = renderHook(() => useSidebarCounts())
    await waitFor(() => expect(result.current.experiments).toBe(1))
    expect(result.current.runs).toBeNull()
  })
})
```

`src/__tests__/useServiceHealth.test.ts` — escribilo siguiendo el mismo patrón, mockeando
las funciones reales de `api.ts` que encontraste (no `getTarget`/`getPreflight` a ciegas
si se llaman distinto). Casos mínimos: ambos motores operativos → `{media:'ok',
control:'ok'}`; el motor de reglas cae (`control.healthy === false` o el fetch de
preflight rechaza) → `{media:'ok', control:'down'}`.

- [ ] **Step 2: Correr, confirmar que fallan**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/useSidebarCounts.test.ts src/__tests__/useServiceHealth.test.ts`
Expected: FAIL — los módulos no existen.

- [ ] **Step 3: Implementar los hooks**

`useSidebarCounts.ts`:

```ts
import { useEffect, useState } from 'react'
import { listRuns, getExperimentManifests, listPromptSets } from './api'

export interface SidebarCounts {
  runs: number | null
  experiments: number | null
  promptSets: number | null
}

export function useSidebarCounts(): SidebarCounts {
  const [counts, setCounts] = useState<SidebarCounts>({ runs: null, experiments: null, promptSets: null })

  useEffect(() => {
    let alive = true
    listRuns()
      .then((rows) => {
        if (alive) setCounts((c) => ({ ...c, runs: rows.filter((r) => r.status === 'running').length }))
      })
      .catch(() => {
        /* el contador queda en null: no se muestra "0" por un fetch que fallo */
      })
    getExperimentManifests()
      .then((rows) => {
        if (alive) setCounts((c) => ({ ...c, experiments: rows.length }))
      })
      .catch(() => {})
    listPromptSets()
      .then((rows) => {
        if (alive) setCounts((c) => ({ ...c, promptSets: rows.length }))
      })
      .catch(() => {})
    return () => {
      alive = false
    }
  }, [])

  return counts
}
```

`useServiceHealth.ts` — implementalo con la misma forma (`useEffect` + `setInterval`
de 10s + limpieza en el cleanup), consumiendo las funciones reales que confirmaste en
el Step 1. Si `getPreflight`/`getTarget` no existen con esos nombres, usá los reales y
anotá en el reporte cuáles usaste.

- [ ] **Step 4: Correr los tests, confirmar que pasan**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/useSidebarCounts.test.ts src/__tests__/useServiceHealth.test.ts`
Expected: PASS.

- [ ] **Step 5: Reescribir `nav.ts`**

Agregá `icon` y `countKey` a cada `NavItem`. Mantené `crumbsFor` y las rutas
`STANDALONE` exactamente como están hoy (no son parte de esta tarea).

```ts
import type { ComponentType } from 'react'
import {
  IconNavRuns, IconNavExperiments, IconNavCompare, IconNavPrompts,
  IconNavCatalog, IconNavPlatform, IconNavCameras, IconNavClips,
} from './components/ui/icons'

export type NavItem = { to: string; label: string; icon: ComponentType; countKey?: 'runs' | 'experiments' | 'promptSets' }
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
```

(Dejá el resto del archivo — `STANDALONE`, `crumbsFor` — sin tocar, solo agregando
lo de arriba y ajustando el tipo `NavItem`.)

- [ ] **Step 6: Reescribir `Shell.tsx`**

Estructura completa siguiendo `proto-ref-01-armazon-componentes.md §1, §2, §3`, con
las clases traducidas al prefijo `eo-*`:

```tsx
import { useEffect, useState, type ReactNode } from 'react'
import { Link, NavLink } from 'react-router-dom'
import { NAV_GROUPS } from '../nav'
import Breadcrumbs from './Breadcrumbs'
import LiveRunPill from './LiveRunPill'
import TargetBadge from './TargetBadge'
import { useSidebarCounts } from '../useSidebarCounts'
import { useServiceHealth } from '../useServiceHealth'

const COLLAPSE_KEY = 'eovrt-sidebar-collapsed'

export default function Shell({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false)
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem(COLLAPSE_KEY) === '1')
  const counts = useSidebarCounts()
  const health = useServiceHealth()
  const close = () => setOpen(false)

  useEffect(() => {
    localStorage.setItem(COLLAPSE_KEY, collapsed ? '1' : '0')
  }, [collapsed])

  const countFor = (key?: 'runs' | 'experiments' | 'promptSets') => {
    if (!key) return null
    const v = counts[key]
    return v === null || v === 0 ? null : v
  }

  return (
    <div className="eo-shell">
      <aside className={['eo-sidebar', open ? 'eo-sidebar--open' : '', collapsed ? 'eo-sidebar--collapsed' : ''].filter(Boolean).join(' ')} aria-label="Navegación principal">
        <div className="eo-sidebar__brand">
          <b>E-OVRT</b><span className="eo-sidebar__brand-sub">consola</span>
          <button
            type="button"
            className="eo-sidebar__collapse"
            aria-label="Colapsar barra lateral"
            onClick={() => setCollapsed((c) => !c)}
          >
            <svg width="15" height="15" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4" aria-hidden="true">
              <rect x="1.8" y="2.8" width="12.4" height="10.4" rx="1.6" /><path d="M6.4 2.8v10.4" />
            </svg>
          </button>
        </div>
        <Link to="/compose" className="eo-sidebar__action" onClick={close}>
          <span>+ Nueva corrida</span>
          <span className="eo-tip">Nueva corrida</span>
        </Link>
        <nav className="eo-sidebar__nav">
          {NAV_GROUPS.map((group) => (
            <div key={group.title} className="eo-sidebar__group">
              <span className="eo-sidebar__group-title">{group.title}</span>
              {group.items.map((item) => {
                const Icon = item.icon
                const count = countFor(item.countKey)
                return (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    end={item.to === '/'}
                    onClick={close}
                    className={({ isActive }) =>
                      isActive ? 'eo-sidebar__link eo-sidebar__link--active' : 'eo-sidebar__link'
                    }
                  >
                    <Icon />
                    <span className="eo-sidebar__link-label">{item.label}</span>
                    {count !== null && <span className="eo-sidebar__count">{count}</span>}
                    <span className="eo-tip">{item.label}</span>
                  </NavLink>
                )
              })}
            </div>
          ))}
        </nav>
        <LiveRunPill />
        <div className="eo-sidebar__services" aria-label="Estado de los servicios">
          <div className="eo-service">
            <span className="eo-service__dot" style={{ background: health.media === 'ok' ? 'var(--ok)' : health.media === 'down' ? 'var(--er)' : 'var(--nt)' }} />
            <span className="eo-service__label">Motor de detección</span>
            <code>:8080</code>
            <span className="eo-tip">Motor de detección — {health.media === 'ok' ? 'operativo' : health.media === 'down' ? 'sin respuesta' : 'verificando…'}</span>
          </div>
          <div className="eo-service">
            <span className="eo-service__dot" style={{ background: health.control === 'ok' ? 'var(--ok)' : health.control === 'down' ? 'var(--er)' : 'var(--nt)' }} />
            <span className="eo-service__label">Motor de reglas</span>
            <code>:8081</code>
            <span className="eo-tip">Motor de reglas — {health.control === 'ok' ? 'operativo' : health.control === 'down' ? 'sin respuesta' : 'verificando…'}</span>
          </div>
        </div>
      </aside>
      <div className="eo-main">
        <header className="eo-topbar">
          <button
            type="button"
            className="eo-topbar__menu"
            aria-label="Abrir navegación"
            aria-expanded={open}
            onClick={() => setOpen((o) => !o)}
          >
            ☰
          </button>
          <Breadcrumbs />
          <div className="eo-topbar__right"><TargetBadge /></div>
        </header>
        <main className="eo-content">{children}</main>
      </div>
    </div>
  )
}
```

Nota: se conserva el drawer off-canvas de la tarea de un plan anterior (clase
`eo-sidebar--open`, botón `☰`) — no lo saques, solo agregale la clase
`eo-sidebar--collapsed` en paralelo (son dos mecanismos distintos: uno para pantallas
chicas, otro para el colapso manual en pantallas grandes).

- [ ] **Step 7: Actualizar los tests existentes de `Shell.test.tsx`**

Los tests actuales renderizan `<Shell>` sin mockear `listRuns`/`getExperimentManifests`/
`listPromptSets` — ahora Shell los llama. Agregá esos mocks al `vi.mock('../api', ...)`
existente (revisá el archivo primero) resolviendo a arrays vacíos por default en cada
test, para que los hooks nuevos no rompan lo que ya pasaba. Ajustá cualquier aserción
de texto si cambiaste el label de algún ítem (no debería cambiar ninguno — solo se
agregan icono y contador).

- [ ] **Step 8: Agregar el CSS del armazón completo**

Tomá tal cual `proto-ref-01-armazon-componentes.md §1, §2, §3` (las reglas `.app`,
`.side`, `.brand`, `.nav`, `.tip`, `.svcs`, `.topbar` etc.) y traducí cada clase al
prefijo `eo-*` usado arriba (`.side` → `.eo-sidebar`, `.brand` → `.eo-sidebar__brand`,
`.nav` → `.eo-sidebar__link`, `.nav .ct` → `.eo-sidebar__count`, `.tip` → `.eo-tip`,
`.svcs` → `.eo-sidebar__services`, `.svc` → `.eo-service`, etc.). Conservá los breakpoints
exactos (1100px, 760px, 420px) y la transición de 160ms sobre `grid-template-columns`.
No dupliques reglas `.eo-sidebar`/`.eo-topbar` que ya existan de un plan anterior —
extendelas en vez de repetirlas (grep antes de pegar).

- [ ] **Step 9: Correr la suite completa y el build**

Run: `cd webconsole/frontend && npm test && npm run build`
Expected: PASS.

- [ ] **Step 10: Commit**

```bash
cd webconsole/frontend
git add src/components/Shell.tsx src/nav.ts src/useSidebarCounts.ts src/useServiceHealth.ts src/styles/ui.css src/__tests__/Shell.test.tsx src/__tests__/useSidebarCounts.test.ts src/__tests__/useServiceHealth.test.ts
git commit -m "design: barra lateral con iconos, contadores reales y estado de motores"
```

---

### Task 7: Reconstruir `RunsPage.tsx` con fidelidad al prototipo

**Files:**
- Modify: `webconsole/frontend/src/pages/RunsPage.tsx`
- Modify: `webconsole/frontend/src/runview.ts` (si hace falta una función de formateo
  de fuente — ver abajo)
- Test: Modify `webconsole/frontend/src/__tests__/RunsPage.test.tsx`

**Interfaces:**
- Consume `PageHeader`, `Banner`, `SearchInput`, `SegmentedControl`, `Table`,
  `SortableHeader`, `RowNameCell`, `NumCell`, `InlineDeleteConfirm`, `Badge`, `EmptyState`,
  `Button` de `../components/ui` (todas ya existen tras las tareas 1-5).

- [ ] **Step 1: Leer `proto-ref-02-corridas.md §1` completo antes de tocar código**

Es la fuente de verdad de esta tarea: composición exacta, HAY/DERIVABLE/NO HAY por
dato, y la tabla de columnas. No reinventes ninguna decisión que ya esté ahí.

- [ ] **Step 2: Agregar el mapeo de fuente legible a `runview.ts`**

```ts
const SOURCE_LABELS: Record<string, string> = {
  image_folder: 'Carpeta de imágenes',
  video_file: 'Archivo de video',
  rtsp: 'Cámara RTSP',
  oak_d: 'Cámara OAK-D Pro',
}

export function sourceLabel(sourceType: string | null | undefined): string {
  if (!sourceType) return '—'
  return SOURCE_LABELS[sourceType] ?? sourceType
}
```

Agregar el test correspondiente en `src/__tests__/runview.test.ts`:

```ts
describe('sourceLabel', () => {
  it('traduce los tipos de fuente conocidos', () => {
    expect(sourceLabel('oak_d')).toBe('Cámara OAK-D Pro')
    expect(sourceLabel('rtsp')).toBe('Cámara RTSP')
  })
  it('sin dato muestra guion, tipo desconocido cae al codigo crudo', () => {
    expect(sourceLabel(null)).toBe('—')
    expect(sourceLabel('algo_nuevo')).toBe('algo_nuevo')
  })
})
```

- [ ] **Step 3: Escribir los tests nuevos de `RunsPage.test.tsx`**

El archivo actual ya tiene tests sobre el listado/badges/borrado con el layout viejo.
Agregá estos, sin borrar los que sigan siendo válidos (algunos van a necesitar ajuste
de selector porque cambia el DOM — hacelo en el Step 6, después de ver qué rompe):

```tsx
  it('el encabezado muestra el total y, si hay alguna en curso, el conteo en vivo', async () => {
    vi.mocked(api.listRuns).mockResolvedValue([
      { run_id: 'r1', status: 'running', model: 'gdino' } as any,
      { run_id: 'r2', status: 'succeeded', model: 'gdino' } as any,
    ])
    renderPage()
    await waitFor(() => expect(screen.getByText('2 en total')).toBeTruthy())
    expect(screen.getByText('1 en curso')).toBeTruthy()
  })

  it('sin corridas en curso, no muestra el fragmento "en curso"', async () => {
    vi.mocked(api.listRuns).mockResolvedValue([{ run_id: 'r1', status: 'succeeded', model: 'gdino' } as any])
    renderPage()
    await waitFor(() => expect(screen.getByText('1 en total')).toBeTruthy())
    expect(screen.queryByText(/en curso/)).toBeNull()
  })

  it('la busqueda filtra por nombre e identificador', async () => {
    vi.mocked(api.listRuns).mockResolvedValue([
      { run_id: 'run_a', name: 'Ronda nocturna', status: 'succeeded', model: 'gdino' } as any,
      { run_id: 'run_b', name: 'Barrido diurno', status: 'succeeded', model: 'gdino' } as any,
    ])
    renderPage()
    await waitFor(() => expect(screen.getByText('Ronda nocturna')).toBeTruthy())
    fireEvent.change(screen.getByLabelText('Buscar corridas'), { target: { value: 'nocturna' } })
    expect(screen.queryByText('Barrido diurno')).toBeNull()
    expect(screen.getByText('Ronda nocturna')).toBeTruthy()
  })

  it('el segmentado filtra por estado y el contador N de M se actualiza', async () => {
    vi.mocked(api.listRuns).mockResolvedValue([
      { run_id: 'run_a', status: 'running', model: 'gdino' } as any,
      { run_id: 'run_b', status: 'succeeded', model: 'gdino' } as any,
    ])
    renderPage()
    await waitFor(() => expect(screen.getByText('2 de 2')).toBeTruthy())
    fireEvent.click(screen.getByRole('button', { name: 'En curso' }))
    expect(screen.getByText('1 de 2')).toBeTruthy()
  })

  it('clic en el encabezado de una columna numerica ordena, segundo clic invierte', async () => {
    vi.mocked(api.listRuns).mockResolvedValue([
      { run_id: 'run_a', status: 'succeeded', model: 'gdino', fps_effective: 1.5 } as any,
      { run_id: 'run_b', status: 'succeeded', model: 'gdino', fps_effective: 5.5 } as any,
    ])
    renderPage()
    await waitFor(() => expect(screen.getByText('run_a')).toBeTruthy())
    fireEvent.click(screen.getByRole('columnheader', { name: /cuadros\/s/i }))
    let rows = screen.getAllByRole('row').slice(1)
    expect(rows[0].textContent).toContain('run_a') // ascendente: menor primero
    fireEvent.click(screen.getByRole('columnheader', { name: /cuadros\/s/i }))
    rows = screen.getAllByRole('row').slice(1)
    expect(rows[0].textContent).toContain('run_b') // descendente: mayor primero
  })

  it('la fuente se muestra traducida', async () => {
    vi.mocked(api.listRuns).mockResolvedValue([
      { run_id: 'run_a', status: 'succeeded', model: 'gdino', source_type: 'oak_d' } as any,
    ])
    renderPage()
    await waitFor(() => expect(screen.getByText('Cámara OAK-D Pro')).toBeTruthy())
  })

  it('borrar pide confirmacion en linea antes de llamar a la API', async () => {
    vi.mocked(api.listRuns).mockResolvedValue([{ run_id: 'run_a', status: 'succeeded', model: 'gdino' } as any])
    renderPage()
    await waitFor(() => expect(screen.getByText('run_a')).toBeTruthy())
    fireEvent.click(screen.getByRole('button', { name: 'Borrar' }))
    expect(screen.getByText('¿Borrar?')).toBeTruthy()
    expect(api.deleteRun).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: /sí, borrar/i }))
    await waitFor(() => expect(api.deleteRun).toHaveBeenCalledWith('run_a'))
  })

  it('lista vacia por falta de datos muestra un texto distinto que vacia por filtro', async () => {
    vi.mocked(api.listRuns).mockResolvedValue([])
    renderPage()
    await waitFor(() => expect(screen.getByText(/todavía no lanzaste ninguna corrida/i)).toBeTruthy())
  })
```

- [ ] **Step 4: Correr, confirmar que fallan**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/RunsPage.test.tsx`
Expected: FAIL (muchos, porque la pantalla todavía no tiene esta estructura).

- [ ] **Step 5: Reescribir `RunsPage.tsx` completo**

Seguí `proto-ref-02-corridas.md §1.1-§1.3` para la composición y las reglas de
degradación de datos. Estructura:

```tsx
import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { deleteRun, getTrace, listRuns } from '../api'
import type { RunRow } from '../types'
import {
  Badge, Banner, Button, EmptyState, ErrorBanner, InlineDeleteConfirm,
  PageHeader, RowNameCell, SearchInput, SegmentedControl, SortableHeader,
  Table, NumCell,
} from '../components/ui'
import type { SortState } from '../components/ui'
import { isRunning, runStatusTone, runStatusLabel, sourceLabel } from '../runview'

const SEGMENTS = [
  { value: 'all', label: 'Todas' },
  { value: 'running', label: 'En curso' },
  { value: 'succeeded', label: 'Completadas' },
  { value: 'stopped', label: 'Detenidas' },
  { value: 'failed', label: 'Fallidas' },
] as const
type Segment = (typeof SEGMENTS)[number]['value']

// hace(): antigüedad legible cuando la fila no tiene nombre.
function hace(startedAt: string | null | undefined): string {
  if (!startedAt) return '—'
  const min = Math.floor((Date.now() - new Date(startedAt).getTime()) / 60000)
  if (min < 1) return 'recién'
  if (min < 60) return `hace ${min} min`
  const h = Math.floor(min / 60)
  if (h < 24) return `hace ${h} h`
  return `hace ${Math.floor(h / 24)} d`
}

function numOrNull(v: number | null | undefined): number {
  return v == null ? -Infinity : v
}

export default function RunsPage() {
  const [rows, setRows] = useState<RunRow[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [confirmId, setConfirmId] = useState<string | null>(null)
  const [deleteError, setDeleteError] = useState<string | null>(null)
  const [query, setQuery] = useState('')
  const [segment, setSegment] = useState<Segment>('all')
  const [sort, setSort] = useState<SortState | null>(null)
  const [liveAlerts, setLiveAlerts] = useState<number | null>(null)

  const refresh = () =>
    listRuns()
      .then((r) => {
        setRows(r)
        setError(null)
        return r
      })
      .catch((e) => {
        setError(String(e))
        return null
      })

  useEffect(() => {
    let alive = true
    let timer: ReturnType<typeof setTimeout>
    const tick = () =>
      refresh().then((r) => {
        if (alive && r && r.some((row) => row.status === 'running')) timer = setTimeout(tick, 4000)
      })
    tick()
    return () => {
      alive = false
      clearTimeout(timer)
    }
  }, [])

  const liveRun = rows?.find((r) => r.status === 'running') ?? null

  // Resumen de la corrida en vivo: totals.alerts de la traza, un pedido liviano
  // (page_size=1) — se omite si control_run_id es null (no evaluada por el motor de reglas).
  useEffect(() => {
    if (!liveRun) {
      setLiveAlerts(null)
      return
    }
    let alive = true
    getTrace(liveRun.run_id, 1, 1)
      .then((t) => {
        if (alive) setLiveAlerts(t.control_run_id ? t.totals.alerts : null)
      })
      .catch(() => {
        if (alive) setLiveAlerts(null)
      })
    return () => {
      alive = false
    }
  }, [liveRun?.run_id])

  const handleDelete = async (row: RunRow) => {
    setConfirmId(null)
    setDeletingId(row.run_id)
    setDeleteError(null)
    try {
      const result = await deleteRun(row.run_id)
      if (result?.errors) {
        setDeleteError(
          `Borrado parcial de ${row.run_id}: ${Object.entries(result.errors)
            .map(([plane, detail]) => `${plane}: ${detail}`)
            .join('; ')}`,
        )
      } else {
        setDeleteError(null)
      }
    } catch (e) {
      setDeleteError(`No se pudo borrar ${row.run_id}: ${String(e)}`)
    } finally {
      setDeletingId(null)
      await refresh()
    }
  }

  const filtered = useMemo(() => {
    if (!rows) return null
    const q = query.trim().toLowerCase()
    return rows.filter((r) => {
      if (segment !== 'all') {
        if (segment === 'failed' ? !['failed', 'error'].includes(r.status) : r.status !== segment) return false
      }
      if (q && !`${r.name ?? ''} ${r.run_id}`.toLowerCase().includes(q)) return false
      return true
    })
  }, [rows, query, segment])

  const sorted = useMemo(() => {
    if (!filtered) return filtered
    if (!sort) return filtered
    const dir = sort.dir === 'asc' ? 1 : -1
    const key = sort.key as keyof RunRow
    return [...filtered].sort((a, b) => {
      const av = a[key]
      const bv = b[key]
      if (typeof av === 'number' || typeof bv === 'number') {
        return (numOrNull(av as number) - numOrNull(bv as number)) * dir
      }
      return String(av ?? '').localeCompare(String(bv ?? '')) * dir
    })
  }, [filtered, sort])

  const onSort = (key: string) => {
    setSort((s) => (s?.key === key ? { key, dir: s.dir === 'asc' ? 'desc' : 'asc' } : { key, dir: 'asc' }))
  }

  if (error) return <ErrorBanner>{error}</ErrorBanner>
  if (!rows) return <p className="eo-empty">Cargando…</p>

  const runningCount = rows.filter((r) => r.status === 'running').length

  return (
    <div>
      <PageHeader
        title="Corridas"
        meta={
          <>
            <span>{rows.length} en total</span>
            {runningCount > 0 && (
              <>
                <span className="eo-sep">·</span>
                <span style={{ color: 'var(--live)' }}>{runningCount} en curso</span>
              </>
            )}
          </>
        }
        actions={<Button variant="primary" as="a">▶ Nueva corrida</Button>}
      />
      {liveRun && (
        <Banner
          tone="live"
          action={
            <Button variant="secondary" as="a" href={`/runs/${liveRun.run_id}`}>
              Ver en vivo
            </Button>
          }
        >
          <b>{liveRun.name || liveRun.run_id}</b>{' '}
          está procesando ahora
          {liveAlerts !== null ? ` — ${liveAlerts} alertas confirmadas.` : '.'}
        </Banner>
      )}
      {deleteError && <ErrorBanner>{deleteError}</ErrorBanner>}
      <div className="eo-toolbar2">
        <SearchInput
          value={query}
          onChange={setQuery}
          placeholder="Buscar por nombre o identificador"
          ariaLabel="Buscar corridas"
        />
        <SegmentedControl value={segment} options={SEGMENTS} onChange={setSegment} />
        <span className="eo-toolbar2__count">{sorted!.length} de {rows.length}</span>
      </div>
      <Table>
        <thead>
          <tr>
            <SortableHeader label="Corrida" sortKey="name" sortState={sort} onSort={onSort} />
            <SortableHeader label="Estado" sortKey="status" sortState={sort} onSort={onSort} />
            <th>Modelo</th>
            <th>Fuente</th>
            <th>Conjunto de prompts</th>
            <SortableHeader label="Cuadros/s" sortKey="fps_effective" sortState={sort} onSort={onSort} numeric />
            <SortableHeader label="Detecciones" sortKey="total_detections" sortState={sort} onSort={onSort} numeric />
            <SortableHeader label="Duración" sortKey="duration_seconds" sortState={sort} onSort={onSort} numeric />
            <th></th>
          </tr>
        </thead>
        <tbody>
          {sorted!.map((r) => (
            <tr key={r.run_id} className="eo-row--clickable">
              <RowNameCell
                title={
                  <Link to={`/runs/${r.run_id}`}>{r.name || r.run_id}</Link>
                }
                subtitle={r.name ? r.run_id : hace(r.started_at)}
              />
              <td>
                <Badge tone={runStatusTone(r)} pulse={isRunning(r)}>{runStatusLabel(r)}</Badge>
              </td>
              <td className={r.model ? 'eo-mono' : undefined}>{r.model ?? '—'}</td>
              <td>{sourceLabel(r.source_type)}</td>
              <td className={r.prompt_set_id ? 'eo-mono' : undefined}>{r.prompt_set_id ?? '—'}</td>
              <NumCell>{r.fps_effective ?? '—'}</NumCell>
              <NumCell>{r.total_detections ?? '—'}</NumCell>
              <NumCell>{r.duration_seconds != null ? `${r.duration_seconds} s` : '—'}</NumCell>
              <td className="eo-cell--actions">
                {confirmId === r.run_id ? (
                  <InlineDeleteConfirm
                    onConfirm={() => void handleDelete(r)}
                    onCancel={() => setConfirmId(null)}
                  />
                ) : (
                  !isRunning(r) && (
                    <Button
                      variant="ghost"
                      disabled={deletingId === r.run_id}
                      onClick={() => setConfirmId(r.run_id)}
                    >
                      Borrar
                    </Button>
                  )
                )}
              </td>
            </tr>
          ))}
          {sorted!.length === 0 && (
            <tr>
              <td colSpan={9}>
                {query || segment !== 'all' ? (
                  <EmptyState hint="Probá con otro texto o volvé a «Todas».">
                    Ninguna corrida coincide con el filtro.
                  </EmptyState>
                ) : (
                  <EmptyState hint="Empezá por elegir una fuente y un conjunto de prompts.">
                    Todavía no lanzaste ninguna corrida.
                  </EmptyState>
                )}
              </td>
            </tr>
          )}
        </tbody>
      </Table>
    </div>
  )
}
```

**Nota de implementación importante — `Button as="a"`**: si el `Button` actual (Tarea
1 del plan de fundación) no soporta renderizar como enlace (`as="a" href="..."`),
NO le agregues esa capacidad en esta tarea — es un cambio de primitiva fuera de
alcance. En su lugar usá `<Link to="/compose"><Button variant="primary" as="span">…`
no funciona tampoco por las mismas razones; la solución más simple: dejá el botón
"Nueva corrida" como está hoy (probablemente ya navega con `useNavigate` o similar —
revisá el `RunsPage.tsx` ACTUAL antes de escribir esta parte) y react-router `<Link>`
envolviendo un `<Button>` con `onClick` que dispare la navegación, o directamente
`<Link to="/compose" className="eo-btn eo-btn--primary">▶ Nueva corrida</Link>` sin
pasar por el componente `Button`. Elegí la opción más simple que no te obligue a tocar
`Button.tsx`, y anotá cuál elegiste en el reporte.

- [ ] **Step 6: Ajustar los tests viejos que rompan por el cambio de DOM**

Correr la suite, ver qué falla, y actualizar SOLO las aserciones que dependían de la
estructura vieja (p. ej. si algún test buscaba `getByRole('button', { name: 'Borrar'
})` y hacía clic esperando el borrado inmediato — ahora hay un paso de confirmación en
el medio). No borres cobertura, adaptala.

- [ ] **Step 7: Correr la suite completa y el build**

Run: `cd webconsole/frontend && npm test && npm run build`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
cd webconsole/frontend
git add src/pages/RunsPage.tsx src/runview.ts src/__tests__/RunsPage.test.tsx src/__tests__/runview.test.ts
git commit -m "design: reconstruir Corridas con fidelidad al prototipo (buscador, segmentado, orden, confirmacion en linea)"
```

---

### Task 8: Verificación final contra datos reales y relanzamiento

**Files:** ninguno (solo verificación y despliegue).

- [ ] **Step 1: Suite completa, typecheck y build**

Run: `cd webconsole/frontend && npx tsc --noEmit && npm test && npm run build`
Expected: todo limpio.

- [ ] **Step 2: Verificación visual headless contra el BFF real**

El BFF real corre en `http://localhost:8090` con 95 corridas reales (o el puerto que
esté activo en ese momento — confirmalo con `ss -tlnp | grep 8090` o equivalente antes
de asumirlo). Detené el proceso de la consola vieja si sigue corriendo apuntando al
`dist/` viejo, y arrancá uno nuevo apuntando al `dist/` de este worktree:

```bash
cd /home/simonll4/projects/e-ovrt_experimental-setup/webconsole/backend
EOVRT_CONSOLE_HYDRATION_LIMIT=100 EOVRT_CONSOLE_SPA_DIST=/home/simonll4/projects/e-ovrt_experimental-setup/.worktrees/rediseno-fundacion-corridas/webconsole/frontend/dist \
  .venv/bin/uvicorn eovrt_webconsole.app:create_app --factory --host 127.0.0.1 --port 8090 &
sleep 3
```

Con el navegador headless disponible en
`/home/simonll4/.cache/ms-playwright/chromium_headless_shell-1228/chrome-headless-shell-linux64/chrome-headless-shell`,
capturá la pantalla de Corridas y confirmá visualmente (no solo por grep) que aparecen:
barra lateral con iconos y contadores, encabezado con "N en total", banner de corrida
en vivo si corresponde, buscador + segmentado + contador, tabla con encabezados
ordenables y la celda de nombre en dos líneas.

- [ ] **Step 3: Reportar discrepancias, no arreglarlas en esta tarea**

Si algo no coincide con `proto-ref-02-corridas.md`, anotalo en el reporte con captura
y cita de la sección — no lo arregles vos: este plan termina en Corridas a propósito
(el usuario calibra antes de seguir con las 10 pantallas restantes).

- [ ] **Step 4: Reporte final**

Escribí un resumen en el reporte del task-runner: qué quedó igual al prototipo, qué
quedó degradado (con la cita de `proto-ref-02.md §3` correspondiente a cada
degradación), y el estado de los tests/build.

---

## After this plan

Esto cubre el armazón (barra lateral, barra superior, encabezado de página, controles
de filtro, tabla, banner, estados vacíos) y una sola pantalla completa (Corridas). El
usuario revisa contra el prototipo antes de continuar. Quedan pendientes, en el orden
de prioridad ya acordado: Detalle de corrida (que necesita además los componentes de
KPI tiles, línea de tiempo y lista de cuadros — `proto-ref-01 §8, §12, §14` y
`proto-ref-02 §2` — no cubiertos por este plan), Comparar, Experimentos, y el resto de
pantallas de menor prioridad (`proto-ref-03` y `proto-ref-04`). Cada una necesita su
propio plan, siguiendo el mismo patrón: leer la referencia, no un resumen propio.
