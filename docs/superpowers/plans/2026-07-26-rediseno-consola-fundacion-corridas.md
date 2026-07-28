# Rediseño de la consola — Fundación + Corridas Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the shared design foundation (tokens, primitives, glossary, responsive
shell) for the E-OVRT webconsole redesign and re-skin the highest-priority screen
(Corridas) on top of it, with no backend changes.

**Architecture:** Additive changes to the existing Vite/React SPA
(`e-ovrt_experimental-setup/webconsole/frontend`). No new routing, no new data-fetching
patterns — only new design tokens, three new UI primitives (`Button`, `Select`,
`Table`), a glossary module, a responsive `Shell`, and `RunsPage` re-skinned to use all
of the above.

**Tech Stack:** React 18 + TypeScript, Vite, Vitest + @testing-library/react (jsdom),
react-router-dom v6. No new dependencies.

## Global Constraints

- No backend/BFF changes of any kind (spec decision — see
  `docs/superpowers/specs/2026-07-26-rediseno-consola-design.md`).
- Dark-only theme, no light theme.
- Text color is never pure white (`#f2f1ed`, not `#ffffff`).
- Never encode state with color alone — every status always pairs an icon/glyph with
  text.
- Identifiers (`run_id`, ids, paths, metrics) and condition codes (`CR-01`, `CR-02`)
  are never translated and always render in the monospace font — only the human name
  next to a condition code gets translated.
- Follow the existing `eo-*` CSS class naming convention in `styles/ui.css`; no CSS
  modules, no styled-components.
- Every new/changed page or module keeps or extends its existing Vitest test file in
  `src/__tests__/` (or `src/__tests__/ui/` for primitives) — never rewritten from
  scratch.
- Run `npm test` (Vitest) from `webconsole/frontend/` after every task.
- Never commit unless explicitly instructed — this plan's "Commit" steps stage and
  commit locally as part of the working pattern, but do not push.

---

### Task 1: Design tokens — five surfaces, violet/blue split, six status colors

**Files:**
- Modify: `webconsole/frontend/src/styles/tokens.css`
- Test: none (no existing convention for testing a pure CSS token file in this repo —
  verified by the full suite still passing in Step 3, and visually in later tasks that
  consume the new tokens)

**Interfaces:**
- Produces: CSS custom properties consumed by every later task —
  `--bg`, `--surface`, `--surface-raised`, `--surface-emergent`, `--surface-sunken`,
  `--text`, `--text-secondary`, `--text-muted`, `--border`, `--border-strong`,
  `--accent`, `--accent-hover`, `--status-live`, `--status-ok`, `--status-warn`,
  `--status-alert`, `--status-error`, `--status-neutral`, `--sidebar-width`,
  `--sidebar-width-collapsed`.

- [ ] **Step 1: Replace `tokens.css` with the five-surface, split-accent token set**

```css
:root {
  color-scheme: dark;

  /* Superficies y texto — el lienzo es más oscuro que la tarjeta a propósito:
     con mucha tabla, los contenedores se leen como objetos, no como parches. */
  --bg: #121211;
  --surface: #1a1a19;
  --surface-raised: #212120;
  --surface-emergent: #2a2a28;
  --surface-sunken: #0d0d0c;
  --border: #2c2c2a;
  --border-strong: #383835;
  --text: #f2f1ed;
  --text-secondary: #c3c2b7;
  --text-muted: #898781;

  /* Acento — violeta es acción/selección/foco/nav activa. El azul de "en curso"
     vive aparte en --status-live: antes compartían color y un botón primario y
     una corrida activa se veían iguales. */
  --accent: #7d6ef2;
  --accent-hover: #8f82f5;

  /* Estado — recalibrados para fondo oscuro, todos >= 4,5:1 de contraste como
     texto (no solo como punto de color). */
  --status-live: #4b95e8;
  --status-ok: #35b45a;
  --status-warn: #e0a217;
  --status-alert: #ee8a5c;
  --status-error: #f0625f;
  --status-neutral: #8a8880;

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
  --sidebar-width-collapsed: 0px;
  --content-max: 1600px;
}
```

- [ ] **Step 2: Update the one consumer of `--surface` as page background to use `--bg`**

Search for where the page background is set (likely `styles/base.css`) and swap
`background: var(--surface)` for `background: var(--bg)` on the `body`/root element,
since `--surface` now means "card", not "canvas".

```bash
grep -n "background" webconsole/frontend/src/styles/base.css
```

Edit the matching rule (typically `body { background: var(--surface); ... }`) to read
`background: var(--bg);`.

- [ ] **Step 3: Run the full test suite to confirm nothing broke**

Run: `cd webconsole/frontend && npm test`
Expected: all existing tests PASS (this task only changes CSS custom property values
and names; no component logic changed). If any test fails because it asserted on an
inline style value that referenced an old token, note it — none are expected, since
tests in this codebase assert on class names and text content, not computed styles.

- [ ] **Step 4: Commit**

```bash
cd webconsole/frontend
git add src/styles/tokens.css src/styles/base.css
git commit -m "design: five-surface tokens with violet/blue accent split"
```

---

### Task 2: Sixth status tone — `alert` (alerta confirmada), distinct from `warn`

**Files:**
- Modify: `webconsole/frontend/src/types.ts` (the `BadgeTone` union)
- Modify: `webconsole/frontend/src/styles/ui.css` (`.eo-badge--*` rules)
- Test: Modify `webconsole/frontend/src/__tests__/ui/Badge.test.tsx`

**Interfaces:**
- Consumes: `--status-alert` token from Task 1.
- Produces: `BadgeTone` now includes `'alert'`, so `<Badge tone="alert">` is valid
  everywhere `Badge` is used (this tone isn't consumed by any screen yet in this plan
  — it's used starting with the Run Detail phase, which is a separate follow-up plan).

- [ ] **Step 1: Write the failing test**

Add to `src/__tests__/ui/Badge.test.tsx`, inside the existing `describe('Badge', ...)`:

```tsx
  it('soporta el tono alert (alerta confirmada, distinto de warn)', () => {
    render(<Badge tone="alert">alerta</Badge>)
    expect(screen.getByText('alerta').className).toContain('eo-badge--alert')
  })
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/ui/Badge.test.tsx`
Expected: FAIL — TypeScript error / test failure, because `'alert'` is not yet a
valid `BadgeTone` and `.eo-badge--alert` doesn't exist.

- [ ] **Step 3: Add the `alert` tone to the type and the stylesheet**

In `src/types.ts`, change:

```ts
export type BadgeTone = 'live' | 'ok' | 'warn' | 'error' | 'neutral'
```

to:

```ts
export type BadgeTone = 'live' | 'ok' | 'warn' | 'alert' | 'error' | 'neutral'
```

In `src/styles/ui.css`, in the Badge section, add a line after `.eo-badge--warn`:

```css
.eo-badge--alert { color: var(--status-alert); }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/ui/Badge.test.tsx`
Expected: PASS (all Badge tests, including the new one).

- [ ] **Step 5: Commit**

```bash
cd webconsole/frontend
git add src/types.ts src/styles/ui.css src/__tests__/ui/Badge.test.tsx
git commit -m "design: add alert badge tone (alerta confirmada vs warn/degradado)"
```

---

### Task 3: `Button` primitive

**Files:**
- Create: `webconsole/frontend/src/components/ui/Button.tsx`
- Modify: `webconsole/frontend/src/components/ui/index.ts`
- Modify: `webconsole/frontend/src/styles/ui.css`
- Test: Create `webconsole/frontend/src/__tests__/ui/Button.test.tsx`

**Interfaces:**
- Produces: `Button({ variant?: 'primary' | 'secondary' | 'danger' | 'ghost', children,
  ...rest }: { variant?: ButtonVariant } & ButtonHTMLAttributes<HTMLButtonElement>)`,
  default export from `components/ui/Button.tsx`, re-exported as `Button` from
  `components/ui/index.ts`. `variant` defaults to `'secondary'`.

- [ ] **Step 1: Write the failing test**

Create `src/__tests__/ui/Button.test.tsx`:

```tsx
import { describe, expect, it, afterEach, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { Button } from '../../components/ui'

afterEach(() => cleanup())

describe('Button', () => {
  it('por defecto es variant secondary', () => {
    render(<Button>Guardar</Button>)
    expect(screen.getByRole('button', { name: 'Guardar' }).className).toContain('eo-btn--secondary')
  })

  it('variant primary', () => {
    render(<Button variant="primary">Lanzar</Button>)
    expect(screen.getByRole('button', { name: 'Lanzar' }).className).toContain('eo-btn--primary')
  })

  it('variant danger', () => {
    render(<Button variant="danger">Borrar</Button>)
    expect(screen.getByRole('button', { name: 'Borrar' }).className).toContain('eo-btn--danger')
  })

  it('variant ghost', () => {
    render(<Button variant="ghost">Cancelar</Button>)
    expect(screen.getByRole('button', { name: 'Cancelar' }).className).toContain('eo-btn--ghost')
  })

  it('siempre lleva la clase base eo-btn y pasa props nativas (disabled, onClick, type)', () => {
    const onClick = vi.fn()
    render(<Button onClick={onClick} disabled type="submit">X</Button>)
    const btn = screen.getByRole('button', { name: 'X' }) as HTMLButtonElement
    expect(btn.className).toContain('eo-btn')
    expect(btn.disabled).toBe(true)
    expect(btn.type).toBe('submit')
    fireEvent.click(btn)
    expect(onClick).not.toHaveBeenCalled() // disabled: no debe disparar
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/ui/Button.test.tsx`
Expected: FAIL with "Cannot find module" or "Button is not exported".

- [ ] **Step 3: Implement `Button.tsx`**

Create `src/components/ui/Button.tsx`:

```tsx
import type { ButtonHTMLAttributes } from 'react'

export type ButtonVariant = 'primary' | 'secondary' | 'danger' | 'ghost'

export default function Button({
  variant = 'secondary',
  className,
  ...rest
}: { variant?: ButtonVariant } & ButtonHTMLAttributes<HTMLButtonElement>) {
  const cls = ['eo-btn', `eo-btn--${variant}`, className].filter(Boolean).join(' ')
  return <button className={cls} {...rest} />
}
```

- [ ] **Step 4: Export it from `components/ui/index.ts`**

Add: `export { default as Button } from './Button'`

- [ ] **Step 5: Add the CSS variants to `styles/ui.css`**

The file already has `.eo-btn--primary` and `.eo-btn--danger` rules (from the old
`eo-actions` section) but no base `.eo-btn` or `.eo-btn--secondary`/`.eo-btn--ghost`.
Add, near the existing `.eo-btn--primary`/`.eo-btn--danger` rules:

```css
.eo-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  height: 30px;
  padding: 0 var(--space-3);
  border-radius: var(--radius);
  border: 1px solid var(--border);
  background: var(--surface-raised);
  color: var(--text);
  font-size: var(--text-sm);
  font-weight: 500;
  cursor: pointer;
}
.eo-btn:hover:not(:disabled) { background: var(--surface-emergent); }
.eo-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.eo-btn--secondary { background: var(--surface-raised); }
.eo-btn--ghost { background: transparent; border-color: transparent; }
.eo-btn--ghost:hover:not(:disabled) { background: var(--surface-raised); }
```

(`.eo-btn--primary` and `.eo-btn--danger` already exist from before — leave them as
they are, they already reference `--accent` and `--status-error`, which still resolve
correctly after Task 1's token rename.)

- [ ] **Step 6: Run test to verify it passes**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/ui/Button.test.tsx`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
cd webconsole/frontend
git add src/components/ui/Button.tsx src/components/ui/index.ts src/styles/ui.css src/__tests__/ui/Button.test.tsx
git commit -m "design: add Button primitive (primary/secondary/danger/ghost)"
```

---

### Task 4: `Select` primitive (custom dropdown with disabled-option reason)

**Files:**
- Create: `webconsole/frontend/src/components/ui/Select.tsx`
- Modify: `webconsole/frontend/src/components/ui/index.ts`
- Modify: `webconsole/frontend/src/styles/ui.css`
- Test: Create `webconsole/frontend/src/__tests__/ui/Select.test.tsx`

**Interfaces:**
- Produces:
  ```ts
  export interface SelectOption {
    value: string
    label: string
    disabled?: boolean
    disabledReason?: string
  }
  export default function Select(props: {
    value: string
    options: SelectOption[]
    onChange: (value: string) => void
    placeholder?: string
  }): JSX.Element
  ```
  Re-exported as `Select`/`SelectOption` from `components/ui/index.ts`. This is what
  Task 8 (Corridas status filter) consumes.

- [ ] **Step 1: Write the failing test**

Create `src/__tests__/ui/Select.test.tsx`:

```tsx
import { describe, expect, it, afterEach, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { Select } from '../../components/ui'
import type { SelectOption } from '../../components/ui'

afterEach(() => cleanup())

const OPTIONS: SelectOption[] = [
  { value: 'all', label: 'Todas' },
  { value: 'running', label: 'En curso' },
  { value: 'archived', label: 'Archivadas', disabled: true, disabledReason: 'sin acceso' },
]

describe('Select', () => {
  it('muestra la etiqueta del valor seleccionado, cerrado por defecto', () => {
    render(<Select value="all" options={OPTIONS} onChange={() => {}} />)
    expect(screen.getByText('Todas')).toBeTruthy()
    expect(screen.queryByRole('listbox')).toBeNull()
  })

  it('abre la lista al hacer click en el control', () => {
    render(<Select value="all" options={OPTIONS} onChange={() => {}} />)
    fireEvent.click(screen.getByRole('button'))
    expect(screen.getByRole('listbox')).toBeTruthy()
    expect(screen.getByRole('option', { name: 'En curso' })).toBeTruthy()
  })

  it('elegir una opción llama a onChange con su value y cierra la lista', () => {
    const onChange = vi.fn()
    render(<Select value="all" options={OPTIONS} onChange={onChange} />)
    fireEvent.click(screen.getByRole('button'))
    fireEvent.click(screen.getByRole('option', { name: 'En curso' }))
    expect(onChange).toHaveBeenCalledWith('running')
    expect(screen.queryByRole('listbox')).toBeNull()
  })

  it('una opción deshabilitada no dispara onChange y muestra el motivo', () => {
    const onChange = vi.fn()
    render(<Select value="all" options={OPTIONS} onChange={onChange} />)
    fireEvent.click(screen.getByRole('button'))
    const disabledOpt = screen.getByRole('option', { name: 'Archivadas' })
    expect(disabledOpt.getAttribute('title')).toBe('sin acceso')
    fireEvent.click(disabledOpt)
    expect(onChange).not.toHaveBeenCalled()
  })

  it('Escape cierra la lista', () => {
    render(<Select value="all" options={OPTIONS} onChange={() => {}} />)
    fireEvent.click(screen.getByRole('button'))
    expect(screen.getByRole('listbox')).toBeTruthy()
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(screen.queryByRole('listbox')).toBeNull()
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/ui/Select.test.tsx`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement `Select.tsx`**

Create `src/components/ui/Select.tsx`:

```tsx
import { useEffect, useRef, useState } from 'react'

export interface SelectOption {
  value: string
  label: string
  disabled?: boolean
  disabledReason?: string
}

export default function Select({
  value,
  options,
  onChange,
  placeholder,
}: {
  value: string
  options: SelectOption[]
  onChange: (value: string) => void
  placeholder?: string
}) {
  const [open, setOpen] = useState(false)
  const rootRef = useRef<HTMLDivElement>(null)
  const selected = options.find((o) => o.value === value)

  useEffect(() => {
    if (!open) return
    const onDocClick = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false)
    }
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', onDocClick)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDocClick)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  const pick = (opt: SelectOption) => {
    if (opt.disabled) return
    onChange(opt.value)
    setOpen(false)
  }

  return (
    <div className="eo-select" ref={rootRef}>
      <button
        type="button"
        className="eo-select__control"
        aria-haspopup="listbox"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
      >
        <span>{selected ? selected.label : placeholder ?? 'Elegir…'}</span>
        <span className="eo-select__caret" aria-hidden="true">▾</span>
      </button>
      {open && (
        <ul className="eo-select__list" role="listbox">
          {options.map((opt) => (
            <li
              key={opt.value}
              role="option"
              aria-selected={opt.value === value}
              aria-disabled={opt.disabled}
              title={opt.disabled ? opt.disabledReason : undefined}
              className={
                'eo-select__option' +
                (opt.value === value ? ' eo-select__option--selected' : '') +
                (opt.disabled ? ' eo-select__option--disabled' : '')
              }
              onClick={() => pick(opt)}
            >
              <span>{opt.label}</span>
              {opt.disabled && opt.disabledReason ? (
                <span className="eo-select__reason">{opt.disabledReason}</span>
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
```

- [ ] **Step 4: Export it from `components/ui/index.ts`**

Add: `export { default as Select } from './Select'` and
`export type { SelectOption } from './Select'`

- [ ] **Step 5: Add the CSS**

Add to `styles/ui.css`:

```css
/* Select — desplegable propio: el <select> nativo rompe el lenguaje visual. */
.eo-select { position: relative; display: inline-block; min-width: 160px; }
.eo-select__control {
  width: 100%;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  padding: 0 var(--space-3);
  background: var(--surface-raised);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  color: var(--text);
  font-size: var(--text-sm);
  cursor: pointer;
}
.eo-select__control:hover { background: var(--surface-emergent); }
.eo-select__caret { color: var(--text-muted); font-size: 0.8em; }
.eo-select__list {
  position: absolute;
  z-index: 20;
  top: calc(100% + 4px);
  left: 0;
  right: 0;
  margin: 0;
  padding: var(--space-1) 0;
  list-style: none;
  background: var(--surface-emergent);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius);
  max-height: 240px;
  overflow-y: auto;
}
.eo-select__option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  font-size: var(--text-sm);
  cursor: pointer;
}
.eo-select__option:hover { background: var(--surface-raised); }
.eo-select__option--selected { color: var(--accent); font-weight: 600; }
.eo-select__option--disabled { color: var(--text-muted); cursor: not-allowed; }
.eo-select__option--disabled:hover { background: transparent; }
.eo-select__reason { font-size: var(--text-xs); color: var(--text-muted); }
```

- [ ] **Step 6: Run test to verify it passes**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/ui/Select.test.tsx`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
cd webconsole/frontend
git add src/components/ui/Select.tsx src/components/ui/index.ts src/styles/ui.css src/__tests__/ui/Select.test.tsx
git commit -m "design: add Select primitive (custom dropdown, disabled option + reason)"
```

---

### Task 5: `Table` primitives (console density: 32px rows, monospace cells)

**Files:**
- Create: `webconsole/frontend/src/components/ui/Table.tsx`
- Modify: `webconsole/frontend/src/components/ui/index.ts`
- Modify: `webconsole/frontend/src/styles/ui.css`
- Test: Create `webconsole/frontend/src/__tests__/ui/Table.test.tsx`

**Interfaces:**
- Produces:
  ```ts
  export function Table(props: TableHTMLAttributes<HTMLTableElement>): JSX.Element
  export function MonoCell(props: { children: ReactNode; title?: string }): JSX.Element
  export function NumCell(props: { children: ReactNode }): JSX.Element
  ```
  Re-exported from `components/ui/index.ts`. `Table` renders a `<table>` with the
  existing `eo-table` class plus a new `eo-table--dense` class (32px rows). `MonoCell`
  and `NumCell` are `<td>` wrappers — this is what Task 8 (Corridas) consumes for the
  `run_id` and numeric columns.

- [ ] **Step 1: Write the failing test**

Create `src/__tests__/ui/Table.test.tsx`:

```tsx
import { describe, expect, it, afterEach } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import { Table, MonoCell, NumCell } from '../../components/ui'

afterEach(() => cleanup())

describe('Table', () => {
  it('renderiza un <table> con las clases eo-table y eo-table--dense', () => {
    const { container } = render(
      <Table>
        <tbody><tr><td>fila</td></tr></tbody>
      </Table>,
    )
    const table = container.querySelector('table')
    expect(table?.className).toContain('eo-table')
    expect(table?.className).toContain('eo-table--dense')
  })
})

describe('MonoCell', () => {
  it('renderiza un <td> monoespaciado con el contenido y title opcional', () => {
    render(
      <table><tbody><tr><MonoCell title="run_20260726_100000">run_20260726_100000</MonoCell></tr></tbody></table>,
    )
    const cell = screen.getByText('run_20260726_100000')
    expect(cell.tagName).toBe('TD')
    expect(cell.className).toContain('eo-mono')
    expect(cell.getAttribute('title')).toBe('run_20260726_100000')
  })
})

describe('NumCell', () => {
  it('renderiza un <td> alineado a la derecha con cifras tabulares', () => {
    render(<table><tbody><tr><NumCell>42</NumCell></tr></tbody></table>)
    expect(screen.getByText('42').className).toContain('eo-num')
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/ui/Table.test.tsx`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement `Table.tsx`**

Create `src/components/ui/Table.tsx`:

```tsx
import type { ReactNode, TableHTMLAttributes } from 'react'

export function Table({ className, ...rest }: TableHTMLAttributes<HTMLTableElement>) {
  const cls = ['eo-table', 'eo-table--dense', className].filter(Boolean).join(' ')
  return <table className={cls} {...rest} />
}

export function MonoCell({ children, title }: { children: ReactNode; title?: string }) {
  return (
    <td className="eo-mono" title={title}>
      {children}
    </td>
  )
}

export function NumCell({ children }: { children: ReactNode }) {
  return <td className="eo-num">{children}</td>
}
```

- [ ] **Step 4: Export from `components/ui/index.ts`**

Add: `export { Table, MonoCell, NumCell } from './Table'`

- [ ] **Step 5: Add the CSS**

Add to `styles/ui.css`, near the existing `.eo-table` rules:

```css
/* Densidad de consola: filas de 32px, no tarjeta por fila. */
.eo-table--dense th,
.eo-table--dense td {
  height: 32px;
  padding: 0 var(--space-3);
}

/* Monoespaciada para identificadores literales (run_id, unit_id, rutas, métricas). */
.eo-mono {
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  color: var(--text);
  font-variant-numeric: tabular-nums;
}
```

- [ ] **Step 6: Run test to verify it passes**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/ui/Table.test.tsx`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
cd webconsole/frontend
git add src/components/ui/Table.tsx src/components/ui/index.ts src/styles/ui.css src/__tests__/ui/Table.test.tsx
git commit -m "design: add Table/MonoCell/NumCell primitives (console density)"
```

---

### Task 6: Glossary module — condition names + resilient control-reason labels

**Files:**
- Create: `webconsole/frontend/src/labels.ts`
- Modify: `webconsole/frontend/src/traceview.ts` (`controlLabel`)
- Test: Create `webconsole/frontend/src/__tests__/labels.test.ts`
- Test: Modify `webconsole/frontend/src/__tests__/traceview.test.ts`

**Interfaces:**
- Produces:
  ```ts
  export const CONDITION_NAMES: Record<string, string>
  export function conditionLabel(code: string): string
  export const CONTROL_DROP_REASONS: Record<string, string>
  ```
  from `src/labels.ts`. `traceview.ts#controlLabel` now imports and uses
  `CONTROL_DROP_REASONS`. Both are consumed starting with the Run Detail phase (a
  separate follow-up plan); `controlLabel`'s existing callers (if any beyond
  `traceview.test.ts`) keep working since its signature is unchanged.

- [ ] **Step 1: Write the failing tests**

Create `src/__tests__/labels.test.ts`:

```ts
import { describe, expect, it } from 'vitest'
import { conditionLabel, CONDITION_NAMES, CONTROL_DROP_REASONS } from '../labels'

describe('conditionLabel', () => {
  it('agrega el nombre legible a un código de condición conocido', () => {
    expect(conditionLabel('CR-01')).toBe('CR-01 — Presencia de persona sin casco')
    expect(conditionLabel('CR-02')).toBe('CR-02 — Presencia de persona sin chaleco')
  })

  it('cae al código crudo si no hay nombre mapeado (no inventa uno)', () => {
    expect(conditionLabel('CR-99')).toBe('CR-99')
  })
})

describe('CONDITION_NAMES / CONTROL_DROP_REASONS', () => {
  it('trae los nombres de las dos condiciones vigentes', () => {
    expect(Object.keys(CONDITION_NAMES).sort()).toEqual(['CR-01', 'CR-02'])
  })

  it('trae traducciones para los motivos de descarte conocidos', () => {
    expect(CONTROL_DROP_REASONS.rate_gate).toBe('límite de tasa')
    expect(CONTROL_DROP_REASONS.overload).toBe('sobrecarga')
  })
})
```

Update `src/__tests__/traceview.test.ts`: replace the existing `describe('controlLabel', ...)`
block (lines 15-22) with:

```ts
describe('controlLabel', () => {
  it('traduce un motivo de descarte conocido', () => {
    expect(controlLabel('dropped:rate_gate')).toBe('límite de tasa')
    expect(controlLabel('dropped:overload')).toBe('sobrecarga')
  })

  it('cae al código crudo para un motivo de descarte no reconocido (sin vocabulario cerrado del backend)', () => {
    expect(controlLabel('dropped:queue_full')).toBe('queue_full')
  })

  it('recibido / no recibido / sin dato', () => {
    expect(controlLabel('received')).toBe('recibido')
    expect(controlLabel('not_received')).toBe('no recibido')
    expect(controlLabel('n/d')).toBe('n/d')
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/labels.test.ts src/__tests__/traceview.test.ts`
Expected: `labels.test.ts` FAILs (module doesn't exist). `traceview.test.ts` FAILs on
the `controlLabel` block (current implementation returns raw `rate_gate`/`overload`,
not the translated strings).

- [ ] **Step 3: Implement `labels.ts`**

Create `src/labels.ts`:

```ts
// Glosario de interfaz — nombres legibles para códigos que hoy solo existen como
// identificadores crudos en la API. Ver docs/superpowers/specs/2026-07-26-rediseno-consola-design.md §3.
// Los códigos (CR-01, CR-02) nunca se traducen ni se ocultan: se acompañan con su
// nombre, nunca se reemplazan por él.

export const CONDITION_NAMES: Record<string, string> = {
  'CR-01': 'Presencia de persona sin casco',
  'CR-02': 'Presencia de persona sin chaleco',
}

export function conditionLabel(code: string): string {
  const name = CONDITION_NAMES[code]
  return name ? `${code} — ${name}` : code
}

// El backend no garantiza un vocabulario cerrado para los motivos de "dropped:*".
// Un código no reconocido acá cae a mostrarse crudo (ver traceview.ts#controlLabel) —
// nunca en blanco, nunca una cadena en inglés suelta.
export const CONTROL_DROP_REASONS: Record<string, string> = {
  rate_gate: 'límite de tasa',
  overload: 'sobrecarga',
}
```

- [ ] **Step 4: Update `controlLabel` in `traceview.ts` to use the glossary**

Change the top of `src/traceview.ts` from:

```ts
import type { BadgeTone, TraceFrame } from './types'
import { SERIES_COLORS } from './components/GroupedBars'
```

to:

```ts
import type { BadgeTone, TraceFrame } from './types'
import { SERIES_COLORS } from './components/GroupedBars'
import { CONTROL_DROP_REASONS } from './labels'
```

And change `controlLabel`:

```ts
export function controlLabel(control: string): string {
  if (control.startsWith('dropped:')) {
    const reason = control.slice('dropped:'.length)
    return CONTROL_DROP_REASONS[reason] ?? reason
  }
  if (control === 'received') return 'recibido'
  if (control === 'not_received') return 'no recibido'
  return control
}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/labels.test.ts src/__tests__/traceview.test.ts`
Expected: both PASS.

- [ ] **Step 6: Run the full suite** (this module is imported nowhere else yet, but
  confirm no regression)

Run: `cd webconsole/frontend && npm test`
Expected: all PASS.

- [ ] **Step 7: Commit**

```bash
cd webconsole/frontend
git add src/labels.ts src/traceview.ts src/__tests__/labels.test.ts src/__tests__/traceview.test.ts
git commit -m "design: glossary module (condition names, resilient drop-reason labels)"
```

---

### Task 7: Responsive `Shell` — collapsible sidebar as an off-canvas drawer

**Files:**
- Modify: `webconsole/frontend/src/components/Shell.tsx`
- Modify: `webconsole/frontend/src/styles/ui.css`
- Test: Modify `webconsole/frontend/src/__tests__/Shell.test.tsx`

**Interfaces:**
- Produces: `Shell` gains internal state only — no prop changes, so every existing
  caller (`App.tsx`) keeps working unchanged. New CSS class `eo-sidebar--open` toggled
  on the `<aside>`, and a new `eo-topbar__menu` button in the top bar.

- [ ] **Step 1: Write the failing tests**

Add to `src/__tests__/Shell.test.tsx`, inside `describe('Shell', ...)`:

```tsx
  it('la barra lateral empieza cerrada (modo pantalla chica)', () => {
    renderShell()
    const aside = screen.getByRole('complementary')
    expect(aside.className).not.toContain('eo-sidebar--open')
  })

  it('el botón de menú abre la barra lateral', () => {
    renderShell()
    fireEvent.click(screen.getByRole('button', { name: /navegación/i }))
    expect(screen.getByRole('complementary').className).toContain('eo-sidebar--open')
  })

  it('elegir un destino de la nav cierra la barra lateral', () => {
    renderShell()
    fireEvent.click(screen.getByRole('button', { name: /navegación/i }))
    fireEvent.click(screen.getByRole('link', { name: 'Experimentos' }))
    expect(screen.getByRole('complementary').className).not.toContain('eo-sidebar--open')
  })
```

Add `fireEvent` to the existing import line at the top of the file:

```tsx
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/Shell.test.tsx`
Expected: FAIL — no button named "navegación" exists yet, `<aside>` never has the
`eo-sidebar--open` class.

- [ ] **Step 3: Implement the drawer state in `Shell.tsx`**

Replace the full contents of `src/components/Shell.tsx` with:

```tsx
import { useState, type ReactNode } from 'react'
import { Link, NavLink } from 'react-router-dom'
import { NAV_GROUPS } from '../nav'
import Breadcrumbs from './Breadcrumbs'
import LiveRunPill from './LiveRunPill'
import TargetBadge from './TargetBadge'

export default function Shell({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false)
  const close = () => setOpen(false)

  return (
    <div className="eo-shell">
      <aside className={open ? 'eo-sidebar eo-sidebar--open' : 'eo-sidebar'}>
        <div className="eo-sidebar__brand">
          <h1>E-OVRT</h1>
        </div>
        <Link to="/compose" className="eo-sidebar__action" onClick={close}>+ Nueva corrida</Link>
        <Link to="/experiments/new" className="eo-sidebar__action" onClick={close}>+ Nuevo experimento</Link>
        <nav className="eo-sidebar__nav">
          {NAV_GROUPS.map((group) => (
            <div key={group.title} className="eo-sidebar__group">
              <span className="eo-sidebar__group-title">{group.title}</span>
              {group.items.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.to === '/'}
                  onClick={close}
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
        <LiveRunPill />
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

- [ ] **Step 4: Add the responsive CSS**

Add to `styles/ui.css`, replacing/extending the existing `/* Shell */` section (keep
the existing `.eo-shell`, `.eo-sidebar`, etc. rules as they are — only add the
following new rules after them):

```css
.eo-topbar__menu {
  display: none;
  background: none;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  color: var(--text);
  width: 30px;
  height: 30px;
  cursor: pointer;
  font-size: var(--text-md);
}

@media (max-width: 900px) {
  .eo-topbar__menu { display: inline-flex; align-items: center; justify-content: center; }
  .eo-sidebar {
    position: fixed;
    z-index: 30;
    left: 0;
    top: 0;
    transform: translateX(-100%);
    transition: transform 0.15s ease;
    box-shadow: 4px 0 16px rgba(0, 0, 0, 0.4);
  }
  .eo-sidebar--open { transform: translateX(0); }
}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/Shell.test.tsx`
Expected: all PASS, including the pre-existing ones (the new `onClick={close}` on nav
links doesn't change their href/label/active-class behavior).

- [ ] **Step 6: Run the full suite**

Run: `cd webconsole/frontend && npm test`
Expected: all PASS (Shell is used by every page via `App.tsx`, so this confirms no
other page's tests broke).

- [ ] **Step 7: Commit**

```bash
cd webconsole/frontend
git add src/components/Shell.tsx src/styles/ui.css src/__tests__/Shell.test.tsx
git commit -m "design: responsive Shell (off-canvas sidebar drawer on small screens)"
```

---

### Task 8: Corridas (`RunsPage`) — dense table, status filter, updated glossary labels

**Files:**
- Modify: `webconsole/frontend/src/runview.ts` (`runStatusLabel`)
- Modify: `webconsole/frontend/src/pages/RunsPage.tsx`
- Test: Modify `webconsole/frontend/src/__tests__/runview.test.ts`
- Test: Modify `webconsole/frontend/src/__tests__/RunsPage.test.tsx`
- Test: Modify `webconsole/frontend/src/__tests__/RunDetailPage.test.tsx` (shares
  `runStatusLabel` with `RunsPage` — see note in Step 1)

**Interfaces:**
- Consumes: `Button`, `Select`/`SelectOption`, `Table`/`MonoCell`/`NumCell` from
  `components/ui` (Tasks 3-5); `runStatusLabel`/`runStatusTone`/`isRunning` from
  `runview.ts`.
- Produces: no new exports — this is a leaf page component.

- [ ] **Step 1: Update the glossary status labels and their tests**

`runStatusLabel` is shared by both `RunsPage` and `RunDetailPage` (the latter is a
separate, later phase of the redesign, but the glossary term change applies to all
interface text immediately, per the spec). Update `src/__tests__/runview.test.ts`:
find the three assertions

```ts
expect(runStatusLabel({ status: 'running' })).toBe('vivo')
...
expect(runStatusLabel({ status: 'succeeded' })).toBe('OK')
...
expect(runStatusLabel({ status: 'failed' })).toBe('fallo')
```

and change them to:

```ts
expect(runStatusLabel({ status: 'running' })).toBe('en curso')
...
expect(runStatusLabel({ status: 'succeeded' })).toBe('completada')
...
expect(runStatusLabel({ status: 'failed' })).toBe('fallida')
```

Also update `src/__tests__/RunDetailPage.test.tsx:57`, changing:

```ts
await waitFor(() => expect(screen.getByText('OK').className).toContain('eo-badge--ok'))
```

to:

```ts
await waitFor(() => expect(screen.getByText('completada').className).toContain('eo-badge--ok'))
```

And update `src/__tests__/RunsPage.test.tsx` lines 26-27, changing:

```ts
expect(screen.getByText('vivo').className).toContain('eo-badge--live')
expect(screen.getByText('OK').className).toContain('eo-badge--ok')
```

to:

```ts
expect(screen.getByText('en curso').className).toContain('eo-badge--live')
expect(screen.getByText('completada').className).toContain('eo-badge--ok')
```

- [ ] **Step 2: Run the affected tests to verify they fail**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/runview.test.ts src/__tests__/RunsPage.test.tsx src/__tests__/RunDetailPage.test.tsx`
Expected: FAIL — `runStatusLabel` still returns the old strings.

- [ ] **Step 3: Update `runStatusLabel` in `runview.ts`**

Change:

```ts
export function runStatusLabel(run: { status: string; live?: boolean }): string {
  if (isRunning(run)) return 'vivo'
  if (run.status === 'succeeded') return 'OK'
  if (run.status === 'failed') return 'fallo'
  return run.status
}
```

to:

```ts
export function runStatusLabel(run: { status: string; live?: boolean }): string {
  if (isRunning(run)) return 'en curso'
  if (run.status === 'succeeded') return 'completada'
  if (run.status === 'failed') return 'fallida'
  return run.status
}
```

- [ ] **Step 4: Run the affected tests to verify they pass**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/runview.test.ts src/__tests__/RunsPage.test.tsx src/__tests__/RunDetailPage.test.tsx`
Expected: PASS.

- [ ] **Step 5: Write the failing test for the new status filter on `RunsPage`**

Add to `src/__tests__/RunsPage.test.tsx`, inside `describe('RunsPage', ...)`:

```tsx
  it('el filtro de estado por defecto muestra todas, y filtra al elegir un estado', async () => {
    vi.mocked(api.listRuns).mockResolvedValue([
      { run_id: 'r_running', status: 'running', model: 'gdino', live: true } as any,
      { run_id: 'r_ok', status: 'succeeded', model: 'gdino' } as any,
      { run_id: 'r_failed', status: 'failed', model: 'gdino' } as any,
    ])
    renderPage()
    await waitFor(() => expect(screen.getByText('r_running')).toBeTruthy())
    expect(screen.getByText('r_ok')).toBeTruthy()
    expect(screen.getByText('r_failed')).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: 'Todas' }))
    fireEvent.click(screen.getByRole('option', { name: 'En curso' }))

    expect(screen.getByText('r_running')).toBeTruthy()
    expect(screen.queryByText('r_ok')).toBeNull()
    expect(screen.queryByText('r_failed')).toBeNull()
  })
```

- [ ] **Step 6: Run test to verify it fails**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/RunsPage.test.tsx`
Expected: FAIL — no `Select` filter exists yet in `RunsPage`.

- [ ] **Step 7: Re-skin `RunsPage.tsx`**

Replace the full contents of `src/pages/RunsPage.tsx` with:

```tsx
import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { deleteRun, listRuns } from '../api'
import type { RunRow } from '../types'
import { Badge, Button, EmptyState, ErrorBanner, Select, Table, MonoCell, NumCell } from '../components/ui'
import type { SelectOption } from '../components/ui'
import { isRunning, runStatusTone, runStatusLabel } from '../runview'

const HEADERS = ['corrida', 'estado', 'modelo', 'fuente', 'prompts', 'FPS', 'dets', 'dur (s)', '']

const STATUS_OPTIONS: SelectOption[] = [
  { value: 'all', label: 'Todas' },
  { value: 'running', label: 'En curso' },
  { value: 'succeeded', label: 'Completadas' },
  { value: 'failed', label: 'Fallidas' },
]

export default function RunsPage() {
  const [rows, setRows] = useState<RunRow[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [deleteError, setDeleteError] = useState<string | null>(null)
  const [statusFilter, setStatusFilter] = useState('all')

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
        // refresco solo mientras hay actividad (el resto es historial estático)
        if (alive && r && r.some((row) => row.status === 'running')) timer = setTimeout(tick, 4000)
      })
    tick()
    return () => {
      alive = false
      clearTimeout(timer)
    }
  }, [])

  const handleDelete = async (row: RunRow) => {
    if (!window.confirm(`¿Borrar el run ${row.run_id}? No se puede deshacer.`)) return
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

  const visibleRows = useMemo(() => {
    if (!rows) return rows
    if (statusFilter === 'all') return rows
    return rows.filter((r) => r.status === statusFilter)
  }, [rows, statusFilter])

  if (error) return <ErrorBanner>{error}</ErrorBanner>
  if (!rows) return <p className="eo-empty">Cargando…</p>
  return (
    <div>
      {deleteError && <ErrorBanner>{deleteError}</ErrorBanner>}
      <div className="eo-clips__head">
        <Select value={statusFilter} options={STATUS_OPTIONS} onChange={setStatusFilter} />
      </div>
      <Table>
        <thead>
          <tr>{HEADERS.map((h) => <th key={h}>{h}</th>)}</tr>
        </thead>
        <tbody>
          {visibleRows!.map((r) => (
            <tr key={r.run_id}>
              <MonoCell title={r.run_id}>
                <Link to={`/runs/${r.run_id}`}>{r.name || r.run_id}</Link>
                {r.name && <><br /><small>{r.run_id}</small></>}
              </MonoCell>
              <td>
                <Badge tone={runStatusTone(r)}>{runStatusLabel(r)}</Badge>
                {r.topology === 'two_node' ? <small> two-node</small> : null}
              </td>
              <td>{r.model ?? '—'}</td>
              <td>{r.source_type ?? '—'}</td>
              <td>{r.prompt_set_id ?? '—'}</td>
              <NumCell>{r.fps_effective ?? '—'}</NumCell>
              <NumCell>{r.total_detections ?? '—'}</NumCell>
              <NumCell>{r.duration_seconds ?? '—'}</NumCell>
              <td>
                {!isRunning(r) && (
                  <Button
                    variant="danger"
                    disabled={deletingId === r.run_id}
                    onClick={() => void handleDelete(r)}
                  >
                    Borrar
                  </Button>
                )}
              </td>
            </tr>
          ))}
          {visibleRows!.length === 0 && (
            <tr><td colSpan={9}><EmptyState>Sin corridas todavía.</EmptyState></td></tr>
          )}
        </tbody>
      </Table>
    </div>
  )
}
```

Note: the empty-state text stays "Sin corridas todavía." even when the *filter*
(not the underlying data) produces zero rows — this is a pre-existing string this
plan doesn't need to disambiguate further; a "sin corridas con este estado" variant
is a nice-to-have left for a later pass, not required by the spec.

- [ ] **Step 8: Run test to verify it passes**

Run: `cd webconsole/frontend && npx vitest run src/__tests__/RunsPage.test.tsx`
Expected: PASS, including the new filter test.

- [ ] **Step 9: Run the full suite**

Run: `cd webconsole/frontend && npm test`
Expected: all PASS.

- [ ] **Step 10: Type-check and build**

Run: `cd webconsole/frontend && npm run build`
Expected: succeeds with no TypeScript errors (this catches any prop-type mismatch
between `RunsPage.tsx` and the new primitives that Vitest's jsdom run wouldn't).

- [ ] **Step 11: Commit**

```bash
cd webconsole/frontend
git add src/runview.ts src/pages/RunsPage.tsx src/__tests__/runview.test.ts src/__tests__/RunsPage.test.tsx src/__tests__/RunDetailPage.test.tsx
git commit -m "design: re-skin Corridas (dense table, status filter, glossary labels)"
```

---

## After this plan

This plan intentionally stops at Corridas. The design's remaining screens — Detalle
de corrida (with the fetch-all-pages trace timeline), Comparar, Experimentos +
Detalle de experimento, and the lower-priority rest (Prompt sets, Catálogos,
Plataforma, Cámaras, Clips) — each get their own follow-up plan in this same
`docs/superpowers/plans/` directory, built on top of the tokens/primitives/glossary/
Shell foundation this plan establishes, in the priority order confirmed in the design
doc.
