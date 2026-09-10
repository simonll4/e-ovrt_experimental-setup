# Adopción del diseño de `front-design` en la consola operativa

**Fecha:** 2026-09-09
**Rama de trabajo:** nueva, desde `feature/webconsole-consola-tesis`
**Ejecuta:** Codex, un tramo por vez — ver `01-reglas-codex.md` y `tramo-*.md`

Este documento es el **por qué**: qué se adopta, qué se midió y qué se decidió.
El **qué hacer** vive en los archivos de tramo, uno por tarea.

---

## 1. Qué es `front-design`

La rama `origin/front-design` contiene **un solo commit**, `d042ad1`, de
**MattGoode7**, del 29-jul-2026, apoyado sobre `159167b` — el punto exacto donde
estaba la rama operativa ese día. Son 120 archivos, +6.964 / −2.351.

**No es un rediseño visual paralelo.** El rediseño del armazón (tokens,
primitivas, las once pantallas migradas, los `proto-ref-01..04`) ya está en la
rama operativa: son commits del 28-jul anteriores al punto común. Lo que
`d042ad1` agrega encima es otra cosa, y hay que nombrarla bien porque condiciona
todo el trabajo:

| Capa | Contenido |
|---|---|
| **Datos** | Migración a **TanStack Query**. `src/api/` con 12 archivos (endpoints, keys, queryClient, 8 módulos de queries). Borra los 6 hooks a mano. Polling condicional (4 s en curso / 2 s riesgo activo / 10 s salud) en vez de `setTimeout` reagendado siempre. Sin reintento en 4xx/501 ni en mutaciones. |
| **Listado** | **TanStack Table** con orden, filtro y paginación **server-side** (`X-Total-Count`). Antes bajaba todas las corridas y filtraba en el cliente. |
| **Visual** | `ui.css` 1.174 → 1.537 líneas. Componentes nuevos: `.eo-flow`, `.eo-hero`, `.eo-launch`, `.eo-compose`, `.eo-cams`, `.eo-bigempty`, `.eo-blockers`, `.eo-chk`, `.eo-cls`, `.eo-adv`, `.eo-crumbsbar`. Reescribe `ComposePage` (+649), `RunsPage` (+516), `RunDetailPage` (+391), `CamerasPage`, `PlatformPage`. |
| **Color** | `palette.ts`: el sistema de color como código. `TONE_VAR` (live/ok/warn/alert/error/accent/neutral) + 8 series categóricas validadas CVD. Antes la tabla tono→variable CSS estaba escrita **tres veces** — en `Sparkline`, `RunKpiStrip` y `TraceSection` — con uniones de tono casi iguales. |
| **Backend** | 13 archivos de `src/` + 11 suites de test nuevas, con TDD. Cuatro rutas nuevas y varios campos nuevos. Ninguna ruta existente cambia de forma. |
| **Tooling** | `webconsole/tools/seed_dev_data.py`: genera corridas mock marcadas `[seed]` para desarrollar la UI **sin hardware**. `--purge` sólo puede borrar lo que él creó. |

**Rutas nuevas del BFF:** `GET /api/catalog/conditions`,
`GET /api/runs/{id}/comparison`, `GET /api/runs/{id}/trace/index`,
`GET /api/runs/{id}/artifacts`. Además `GET /api/runs` gana
`estado · q · orden · direccion · pagina · page_size` y devuelve `X-Total-Count`.

**Campos nuevos:** `created_at` en `RunRow`; `RunSummary` tipado en vez de un
objeto genérico en `RunDetail`; `diff` en `PromptSetDetail`; `disabled_reason` en
`IngestPlugin`; `passed` / `threshold` / `threshold_direction` en cada resultado
del reporte.

---

## 2. Estado medido

Todo lo de esta sección se midió ejecutando, no leyendo.

**Líneas de base:**

| | Frontend | Backend |
|---|---|---|
| Rama operativa (`50b666b`) | 55 archivos / **387** ✅ | **668** ✅ |
| `front-design` (`d042ad1`) | 56 / 420 ✅ + 1 ❌ | 664 ✅ + 15 skipped |

**El port aplica limpio.** `git cherry-pick d042ad1` sobre `50b666b` produjo
**cero conflictos** en los 120 archivos. El árbol resultante quedó guardado como
**árbol de referencia**: worktree `.worktrees/front-design`, commit `3500923`.

**El árbol de referencia está a dos defectos de verde:**

| Resultado | Lectura |
|---|---|
| Backend: 742 pasan, 2 fallan, 17 skipped | |
| → `test_runner_distribution::test_subprocess_failure_does_not_expose_child_output` | **No es regresión.** Falla igual en la rama operativa sin tocar, corrida desde un worktree: `resolve_distribution_executable` busca el binario en `_repo_root().parent / e-ovrt_alert-distribution`, que desde `.worktrees/` no existe. Artefacto del entorno. |
| → `test_report_generator::test_t_alert_system_y_clasificacion_se_proyectan_desde_evaluacion_temporal` | **Regresión real.** Pasa en el control, falla mezclado. Ver §5.1. |
| Frontend: 426 pasan, 1 falla | `GroupedBars.test.tsx` importa `SERIES_COLORS` de `components/charts/GroupedBars`, de donde ya no se exporta (se mudó a `palette.ts`). Ver §5.2. |

**Lo que sobrevivió al merge:** los *outcomes de distribución* (ADR-019/020), que
es la única feature de la rama operativa posterior al punto común y que
`front-design` no tiene. En el árbol de referencia `ExperimentDetailPage.tsx`
conserva sus 66 referencias y sus tests están verdes. Los 22 commits posteriores
tocaron el frontend en apenas 5 archivos, +330 líneas, todo aditivo, todo la
misma feature.

**Superficie de choque en el backend:** de los 13 archivos de `src/` que toca
`d042ad1`, sólo tres los tocaron también los 22 commits posteriores —
`experiment/report.py`, `prompt_store.py`, `routers/experiments.py`. El grueso de
ADR-019/020 (`distribution_http.py`, `runner.py` +621, `preflight.py` +111) no se
pisa.

**La navegación no cambia.** `nav.ts` es **idéntico** entre ramas: los mismos tres
grupos, los mismos ocho destinos, las mismas dos acciones. `App.tsx` conserva las
doce rutas en el mismo orden — incluido el comentario que fija `/experiments/new`
antes de `/experiments/:id`. Lo único que suma es un catch-all a `NotFoundPage`.

**Verificaciones puntuales, para no repetirlas:**

- `SERIES_COLORS` en `palette.ts` es **byte a byte** el de `GroupedBars.tsx` de
  hoy: mismos ocho valores, mismo orden, mismos comentarios. Unificar no cambia
  ningún color.
- `palette.ts` no importa nada. `types.ts` sólo le toma `BadgeTone`.
  `runview.ts` sólo importa `BadgeTone` y `RunSummary` de `types.ts`.
  `src/api/**` sólo usa `isRunning` de `runview`, que existe igual en ambas ramas.
- **No hay herramienta de capturas en el repo.** Se buscó (`chromium`, `headless`,
  `screenshot`, `puppeteer`, `playwright` en README, Makefile, `package.json` y
  los specs del rediseño) y no existe. Hay que hacerla; ver `01-reglas-codex.md`.

---

## 3. El invariante: el contrato congelado

El criterio del trabajo es: **mejorar visualmente y reordenar, con las
funcionalidades idénticas.** Eso hay que poder afirmarlo, no prometerlo.

Se escribe una suite de contrato **antes de tocar código**, que pasa contra la
consola de hoy y tiene que seguir pasando en cada corte de tramo.

### 3.1 Qué afirma

1. **Las peticiones HTTP que dispara cada acción** — método, ruta y forma del
   payload. Eso es "funciona igual" de verdad: si lanzar una corrida deja de
   mandar el mismo `POST` con la misma composición, el contrato se pone rojo.
2. **Qué puede hacer la persona**, buscado por **rol y nombre accesible**
   (`getByRole('button', { name: /lanzar/i })`).

### 3.2 Qué NO afirma — y por qué

**Nunca** clases CSS, jerarquía de DOM, orden de columnas ni posición en
pantalla. Un contrato estructural bloquearía exactamente el rediseño que se
quiere hacer. El trabajo tiene que poder re-maquetar, reordenar y re-estilar
libremente y ver el contrato verde.

### 3.3 Flujos cubiertos

Los cuatro entran, completos:

- **Nueva corrida → lanzar.** Preflight de los servicios, bloqueos que gatean el
  botón, armado de la composición (fuente + modelo + conjunto de prompts +
  destino), `POST` de lanzamiento, navegación al detalle.
- **Corrida en vivo.** Anuncio de corrida viva, polling mientras corre, visor en
  vivo, panel de prompts, riesgo activo, botón Detener.
- **Detalle, traza y evaluación.** KPIs, línea de tiempo, inspector de cuadros,
  disparar evaluación, ver resultados.
- **Experimentos y distribución.** Nuevo experimento, derivar, orquestación
  control → distribución → medios, outcomes de distribución, comparar, reporte.

---

## 4. Decisiones tomadas

| # | Decisión |
|---|---|
| **D-1** | **Alcance: las tres capas** — backend, datos y visual. El visual de MattGoode7 depende de campos nuevos y de react-query; separarlo obligaría a reescribir sus pantallas. |
| **D-2** | **Port por tramos con contrato congelado**, no cherry-pick de un golpe. 120 archivos en un commit no son revisables, y el cherry-pick limpio no garantiza paridad: §5.1 lo demuestra. |
| **D-3** | **La píldora de corrida viva se conserva.** MattGoode7 la borra a propósito (comentario en `Shell.tsx`: el banner del listado ya lo anuncia, «para no decir lo mismo en dos lugares»). Pero ver desde cualquier pantalla que algo está corriendo es capacidad, no decoración, sobre todo en rodaje EBE. Se re-maqueta con el lenguaje nuevo; no se va. |
| **D-4** | **Umbrales de métrica: se adoptan.** `report.py` suma `passed` / `threshold` / `threshold_direction` a cada resultado. Es aditivo: `value` no cambia, así que ninguna cifra del informe se mueve. |
| **D-5** | **Salud del distribuidor `:8082` en la barra lateral: entra en este trabajo.** Hoy muestra dos servicios; desde ADR-019/020 son tres, y la consola exige el distribuidor arriba sin decir si lo está. |
| **D-6** | **Un commit por tramo**, al cerrar con el contrato verde. El merge lo hace el usuario. |
| **D-7** | **Puerto de Vite: queda en 5173.** El `:5174` de `d042ad1` está justificado en su propio comentario por los puertos ocupados en la máquina de MattGoode7 — entorno personal filtrado al repo. Se adopta **sólo** `strictPort: true`, que sí es una mejora real: falla el arranque en vez de saltar de puerto en silencio. |

---

## 5. Los dos defectos conocidos

### 5.1 `report.py` — regresión semántica que git no vio

`generate_report` ahora agrega `passed`, `threshold` y `threshold_direction` a
cada entrada de `resultados`. El test
`test_t_alert_system_y_clasificacion_se_proyectan_desde_evaluacion_temporal`
compara el dict de `t_alert-system` **por igualdad exacta**, así que las tres
claves de más lo rompen.

Es el caso de estudio de por qué existe el contrato: git mezcló sin un solo
conflicto y el comportamiento cambió igual.

**Arreglo (D-4):** actualizar ese test para esperar las tres claves nuevas.
`value` no cambia —sigue siendo `2.5`— así que ninguna cifra publicada se mueve.

**Prohibido:** aflojar el test a comparación parcial, o marcarlo `xfail`. La
igualdad exacta es lo que lo hace útil sobre una métrica que va al informe.

### 5.2 `GroupedBars.test.tsx` — import roto

`GroupedBars.tsx` pasó a importar `SERIES_COLORS` desde `../../palette` y dejó de
reexportarlo; el test siguió importándolo del lugar viejo y recibe `undefined`.

**Arreglo:** que el test importe `SERIES_COLORS` desde `../../palette`. Una línea.
Va en el mismo tramo que trae `GroupedBars.tsx` (tramo 3).

---

## 6. Los tramos

Uno por archivo, en orden. Cada uno es una tarea independiente para Codex.

| Tramo | Archivo | Qué |
|---|---|---|
| 0 | `tramo-0.md` | Contrato congelado. No toca código de producción. |
| 1 | `tramo-1.md` | Backend + `seed_dev_data.py`. Aditivo. |
| 2 | `tramo-2.md` | Capa de datos. Cero cambio visual. |
| 3 | `tramo-3.md` | `ui.css` + las tres pantallas troncales. |
| 4 | `tramo-4.md` | Resto de pantallas + armazón. |
| 5 | `tramo-5.md` | Salud del distribuidor + repaso de punta a punta. |

---

## 7. Fuera de alcance

- Endpoints adicionales de UX más allá de las cuatro rutas de `d042ad1` y de
  `distribution` en el preflight (D-5). Se evalúan después, con la consola nueva
  andando.
- Cualquier cambio a los tres servicios (`media-plane`, `control-plane`,
  `alert-distribution`). Este trabajo vive entero en `webconsole/`.
- El merge a `main`. Lo hace el usuario.
- La rama `feature/webconsole-rediseno-fundacion` y su worktree, que quedan como
  están.
