# Tramo 3 — `ui.css` y las tres pantallas troncales

Leé antes `01-reglas-codex.md`. Acá entra el rediseño visual de verdad.

---

## Archivos, desde `3500923`

### Estilos

```
webconsole/frontend/src/styles/ui.css        ← con desviación, ver abajo
```

### Pantallas

```
webconsole/frontend/src/pages/ComposePage.tsx
webconsole/frontend/src/pages/RunsPage.tsx
webconsole/frontend/src/pages/RunDetailPage.tsx
```

### Componentes y vistas que arrastran

```
webconsole/frontend/src/traceview.ts
webconsole/frontend/src/components/EvalSection.tsx
webconsole/frontend/src/components/TraceSection.tsx
webconsole/frontend/src/components/LivePromptPanel.tsx
webconsole/frontend/src/components/RunKpiStrip.tsx
webconsole/frontend/src/components/RunTimeline.tsx
webconsole/frontend/src/components/LiveViewer.tsx
webconsole/frontend/src/components/TargetBadge.tsx
webconsole/frontend/src/components/charts/ActivityTimeline.tsx
webconsole/frontend/src/components/charts/GroupedBars.tsx
webconsole/frontend/src/components/charts/Meter.tsx
webconsole/frontend/src/components/charts/Sparkline.tsx
webconsole/frontend/src/components/ui/Table.tsx
webconsole/frontend/src/components/ui/icons.tsx
webconsole/frontend/src/components/ui/index.ts
```

### Tests

```
webconsole/frontend/src/__tests__/ComposePage.test.tsx
webconsole/frontend/src/__tests__/RunsPage.test.tsx
webconsole/frontend/src/__tests__/RunDetailPage.test.tsx
webconsole/frontend/src/__tests__/EvalSection.test.tsx
webconsole/frontend/src/__tests__/TraceSection.test.tsx
webconsole/frontend/src/__tests__/RunKpiStrip.test.tsx
webconsole/frontend/src/__tests__/LiveViewer.test.tsx
webconsole/frontend/src/__tests__/traceview.test.ts
webconsole/frontend/src/__tests__/charts/ActivityTimeline.test.tsx   (nuevo)
webconsole/frontend/src/__tests__/api.endpoints.test.ts              (renombre de src/api.test.ts)
webconsole/frontend/src/__tests__/api.test.ts
```

Estos tests **sustituyen** a los viejos de esos mismos archivos. Eso está bien:
los tests de MattGoode7 se adoptan **además** del contrato, nunca en lugar del
contrato. El contrato del tramo 0 es el que sigue diciendo si el comportamiento
cambió.

---

## Desviación explícita: `.eo-livepill` se conserva

El `ui.css` de la referencia **borra** las reglas `.eo-livepill`,
`.eo-livepill__dot`, `.eo-livepill:hover`, `.eo-livepill__id` y
`.eo-livepill__meta`, porque MattGoode7 eliminó la píldora de corrida viva.

**Decisión D-3: la píldora se conserva.** Al traer `ui.css`, **mantené esas
reglas**. Sin ellas la píldora queda rota durante los tramos 3 y 4, y el contrato
—que cubre "corrida en vivo"— se pondría rojo.

La píldora se re-maqueta con el lenguaje visual nuevo en el tramo 4, junto con
`Shell.tsx`.

---

## El defecto que hay que arreglar acá

`src/__tests__/charts/GroupedBars.test.tsx` va a fallar.

MattGoode7 **nunca tocó ese archivo**: movió `SERIES_COLORS` de
`components/charts/GroupedBars` a `palette.ts` y dejó de reexportarlo, pero el
test siguió importándolo del lugar viejo y recibe `undefined`.

**Arreglo:** que el test importe `SERIES_COLORS` desde `../../palette`. Una línea.
Los valores son byte a byte los mismos —se verificó—, así que ninguna aserción de
color cambia.

---

## Si se cae una pantalla del tramo 4

`ui/Table.tsx`, `ui/icons.tsx` y `ui/index.ts` son compartidos. Puede pasar que
traerlos rompa la compilación de una pantalla que todavía es la vieja
(`ClipsPage`, `ComparePage`, …).

- **Sí:** traé también esa pantalla desde `3500923`, y **decilo en el reporte**
  como archivo movido de tramo.
- **No:** parchear la pantalla vieja a mano para que compile.

---

## Borrado de hooks

Regla mecánica, no lista fija: **borrá un hook cuando nadie lo importe.**

```bash
grep -rn "useFullTrace\|useLiveRun\|usePreflight\|useServiceHealth\|useSidebarCounts\|useTarget" webconsole/frontend/src --include=*.ts --include=*.tsx
```

Si el único resultado es el archivo del hook y su propio test, borrá los dos. Si
todavía lo importa una pantalla que no es de este tramo, **dejalo**: se va en el
tramo 4.

---

## Cierre

```bash
cd webconsole/frontend && npm test && npm run build
```

- **Contrato verde.** Éste es el corte que importa: las tres pantallas del flujo
  troncal cambiaron de aspecto y la consola tiene que seguir haciendo lo mismo.
- Suite completa verde.
- Capturas de `/compose`, `/` y `/runs/:id`, antes y después.
- **Además**, capturas de una pantalla que este tramo *no* rediseñó —
  `/prompts` sirve—. `ui.css` también modifica selectores del armazón compartido,
  así que hay que ver qué le cambió por arrastre y dejarlo dicho en el reporte.

Commit: `feat(webconsole): tramo 3 — ui.css y las pantallas troncales`
