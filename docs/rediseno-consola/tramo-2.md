# Tramo 2 — Capa de datos, sin quitar nada y sin tocar el aspecto

Leé antes `01-reglas-codex.md`.

Este es el tramo más importante y el menos vistoso. Agrega toda la
infraestructura de TanStack Query **sin borrar los hooks viejos, sin tocar una
sola pantalla y sin tocar una sola regla de `ui.css`**.

Eso es lo que hace que los tramos 3 y 4 sean un intercambio de una pantalla por
vez, y lo que permite afirmar después: si algo se rompió, fue el **cómo se piden
los datos** o el **cómo se dibujan**, nunca los dos a la vez.

---

## Archivos, desde `3500923`

```
webconsole/frontend/src/palette.ts                    (nuevo)
webconsole/frontend/src/types.ts
webconsole/frontend/src/runview.ts
webconsole/frontend/src/test-utils.tsx                (nuevo)
webconsole/frontend/src/main.tsx
webconsole/frontend/src/api/endpoints.ts              (nuevo)
webconsole/frontend/src/api/index.ts                  (nuevo)
webconsole/frontend/src/api/keys.ts                   (nuevo)
webconsole/frontend/src/api/queryClient.ts            (nuevo)
webconsole/frontend/src/api/queries/cameras.ts        (nuevo)
webconsole/frontend/src/api/queries/catalog.ts        (nuevo)
webconsole/frontend/src/api/queries/clips.ts          (nuevo)
webconsole/frontend/src/api/queries/experiments.ts    (nuevo)
webconsole/frontend/src/api/queries/platform.ts       (nuevo)
webconsole/frontend/src/api/queries/promptSets.ts     (nuevo)
webconsole/frontend/src/api/queries/runs.ts           (nuevo)
webconsole/frontend/src/api/queries/sidebar.ts        (nuevo)
webconsole/frontend/src/__tests__/queryClient.test.ts (nuevo)
webconsole/frontend/package.json
webconsole/frontend/package-lock.json
```

El cierre de dependencias se calculó y se verificó:

- `palette.ts` no importa nada.
- `types.ts` sólo le toma `BadgeTone` a `palette`.
- `runview.ts` sólo importa `BadgeTone` y `RunSummary` de `types`.
- `src/api/**` sólo usa `isRunning` de `runview`, que existe igual en las dos
  ramas.

---

## Lo que NO se hace en este tramo

- **No se borra ningún hook.** `useFullTrace`, `useLiveRun`, `usePreflight`,
  `useServiceHealth`, `useSidebarCounts` y `useTarget` siguen existiendo y las
  pantallas los siguen usando. Se van en los tramos 3 y 4.
- **No se toca ninguna pantalla ni componente.** Ni siquiera para que importen
  `palette.ts`: las copias locales de la tabla tono→variable en `Sparkline`,
  `RunKpiStrip` y `TraceSection` se quedan donde están hasta que llegue su tramo.
  `palette.ts` entra como archivo nuevo, sin consumidores nuevos.
- **No se toca `ui.css`.** Va entero en el tramo 3.
- **No se arregla `GroupedBars.test.tsx`.** Ese defecto se arregla en el tramo 3,
  que es el que trae `GroupedBars.tsx`.

---

## Desviación explícita: el puerto de Vite

`webconsole/frontend/vite.config.ts` **no se copia tal cual**. El árbol de
referencia lo pone en `5174`, y su propio comentario dice por qué: en la máquina
de MattGoode7 los puertos 3000 y 5173 estaban tomados por otro proyecto. Es
entorno personal filtrado al repo.

Decisión D-7: **el puerto queda en 5173**, y se adopta **sólo** `strictPort:
true`, que sí es una mejora real — hace que el arranque falle en vez de saltar de
puerto en silencio dejando la pestaña apuntando al servidor viejo.

---

## Herramienta de capturas

No existe en el repo — se buscó y no está. La instala este tramo.

Un script chico en `webconsole/tools/`, que levante la consola, recorra las doce
rutas de `src/App.tsx` y escriba un PNG por ruta a un directorio **gitignorado**.
Nada sofisticado: es para poder comparar antes y después en los tramos 3 y 4.

---

## Cierre

```bash
cd webconsole/frontend && npm test && npm run build
cd webconsole/backend && ./.venv/bin/python -m pytest -q
```

- Frontend: **387 + contrato + `queryClient.test.ts`**, verdes.
- `npm run build` pasa (esto es lo que prueba que el cierre de dependencias está
  bien; si `tsc` se queja por un módulo faltante, traelo de `3500923` y anotalo —
  no lo parchees a mano).
- Backend: sin cambios respecto al tramo 1.
- **Capturas antes y después de este tramo: indistinguibles.** Si alguna cambió,
  algo se coló que no debía. Pegá las dos en el reporte.

Commit: `feat(webconsole): tramo 2 — capa de datos TanStack Query, sin cambio visual`
