# Tramo 6 — Archivar lo que no es evidencia

Leé antes `01-reglas-codex.md` y `04-evidencia-diseno.md`.

Objetivo: que Corridas y Experimentos muestren **sólo evidencia** por defecto, con
lo archivado a un interruptor de distancia. Nada se borra ni se mueve.

El grueso del efecto está en Experimentos: **398 ejecuciones → ~13**.

---

## Parte A — Backend: el registro como servicio

### A.1 Lector del registro

Módulo nuevo, `webconsole/backend/src/eovrt_webconsole/evidence.py`.

Lee los cuatro CSV de `results/evidence-runs/collections/` — `dbe-datasets.csv`,
`dbe-video.csv`, `ebe-realtime.csv`, `shared.csv` — con columnas:

```
collection, result_id, role, plane, run_id, status, source_ref, artifact_path
```

Expone, como mínimo:

- `es_evidencia(run_id) -> bool`
- `relaciones(run_id) -> list[{collection, result_id, role, source_ref}]`
  (una corrida puede pertenecer a más de un resultado — por eso hay `shared.csv`)
- `resultados() -> list[{result_id, collection, n_runs, planes}]` — los **35**

**Cargalo una vez al arranque**, en `app.state`, como ya se hace con los clientes
httpx. Son 1.436 filas: releerlas por petición es desperdicio.

**Si el directorio no existe**, el lector devuelve vacío sin explotar y deja
constancia de que no está. El repositorio está gitignorado (§7 del diseño) y una
consola en otra máquina tiene que arrancar igual.

### A.2 Parámetro `vista` en los listados

En `GET /api/runs` y en el listado de experimentos:

```
vista = evidencia | archivadas | todas      (default: todas)
```

**`todas` es el default y no se discute.** El contrato congelado usa fixtures
sintéticas que no están en el registro; si el default filtrara, los cuatro flujos
se pondrían rojos. Ver `04-evidencia-diseno.md` §4.

Cada fila del listado gana un bloque:

```json
"evidence": {
  "is_evidence": true,
  "result_ids": ["clip_bench/t1_gdinotiny560_v2short_scene"],
  "collections": ["dbe_video"]
}
```

Aditivo: ningún campo existente cambia de forma ni de nombre.

El filtro se aplica **antes de hidratar**, igual que el filtro por estado que ya
está en `list_runs` — si no, buscar entre 472 corridas cuesta 472 lecturas al
motor.

### A.3 Clasificación de experimentos

El registro no cubre las ejecuciones de `runs/`. Regla, en este orden:

1. **Excepción explícita.** `results/evidence-runs/consola.yaml`, con
   `forzar_evidencia:` y `forzar_archivado:` (listas de slug o de id de
   ejecución). Si algo aparece ahí, manda.
2. **Regla derivada.** Una ejecución es evidencia si al menos una de las corridas
   que consolidó está en el registro. Un manifiesto es evidencia si tiene al
   menos una ejecución de evidencia.
3. Todo lo demás: archivado.

Creá `consola.yaml` con las dos listas **vacías** y un comentario explicando para
qué son. No lo llenes vos.

### ✎ 2026-09-10 — dos correcciones al texto original

**No son 19 manifiestos: la pantalla lista 11.** `_iter_umbrella_manifests` sólo
devuelve los `schema_version: experiment.manifest.v1`; los individuales viejos
(los doce de `bench_v2/`, `gdino`, `mock`, `yoloe`, …) **no se listan**, así que
clasificarlos no cambia nada de lo que se ve. Documentalos aparte si querés, pero
el filtro es sobre los **11 paraguas**.

**El clasificador tiene que escanear recursivamente.** `_ejecuciones_por_slug`
hace `runs_dir.iterdir()` —sólo el primer nivel— y con eso la regla da un falso
cero. Las ejecuciones de evidencia existen y viven a **profundidad 5**:

```
runs/t-alert-notification/official-20260813-03/integrated-video-02/
     repetition-{1,2,3}/consolidated/exp_…talert_repetition-N/
```

Sus corridas están en el registro bajo `realtime/t_alert_notification`. Y los
`run_id` no están junto al `manifest.effective.yaml` sino en `media/` y
`control/`, así que hay que recorrer **todo el subárbol** de cada ejecución.

**No toques `_ejecuciones_por_slug`**: es el listado, y cambiarlo mueve los
conteos de la pantalla. El clasificador es otra cosa y va aparte.

**Resultado esperado con la regla corregida** (medido):

| Slug paraguas | Ejec. | Con evidencia | Resultado |
|---|---:|---:|---|
| `talert_integrated_video` | 4 | **3** | `realtime/t_alert_notification` |
| `diag_riesgo_activo` | 5 | 0 | — |
| los otros nueve | 0 | 0 | — |

Las otras ~405 ejecuciones (`orq_*`, `gate_orq`, `gate`, `d1`,
`video16_clip10_gt`) tienen slugs que **no están en el catálogo de paraguas**:
son huérfanas y no cuelgan de ningún manifiesto listado.

**Decisión del usuario:** queda **sólo lo que tiene evidencia abrible**, es decir
`talert_integrated_video` y nada más. Los otros diez son recetas sin ejecución
consolidada: mostrarlos sería ofrecer algo que al abrirlo no tiene nada. Sus
corridas se van a ver en la vista Evidencia del tramo 7, que lee el archivo
curado. `consola.yaml` queda con las listas vacías.

### A.4 El reporte de clasificación — obligatorio

Al cerrar el tramo, imprimí la tabla completa: los **19 manifiestos** y cada
grupo de ejecuciones, con su veredicto y el motivo.

Que la regla sea automática no la vuelve correcta. `diag_riesgo_activo` (5
ejecuciones), `video16_clip10_gt` (3), `t_alert_notification`, `gate` y `d1` son
los candidatos reales y **pueden caer del lado equivocado**. Esa lista la revisa
el usuario; si algo quedó mal, se corrige con `consola.yaml`, no cambiando la
regla.

Referencia de lo que **sí** es ruido conocido, para contrastar tu salida:

```
orq_2a 78 · orq_1 78 · orq_alerts_502 77 · orq_alerts 77 · gate_orq 75   (= 385)
```

### A.5 Tests

- El lector con el repositorio ausente devuelve vacío y no rompe el arranque.
- `vista=todas` (y sin parámetro) devuelve exactamente lo que devolvía antes.
- `vista=evidencia` deja fuera una corrida que no está en el registro.
- `vista=archivadas` es el complemento exacto: `evidencia + archivadas = todas`,
  sin solapamiento.
- Una corrida en `shared.csv` reporta sus **dos** `result_id`.
- La precedencia de `consola.yaml` sobre la regla derivada, en los dos sentidos.

---

## Parte B — Frontend: el interruptor

- **Corridas** y **Experimentos** piden `vista=evidencia` por defecto.
- Un control de tres estados —**Evidencia · Archivadas · Todas**— con el lenguaje
  visual que ya existe (`SegmentedControl`).
- La elección **persiste** en `localStorage`, como el colapso de la barra lateral.
- Cuando la vista es `evidencia` y hay cosas ocultas, decilo sin ruido:
  «*385 ejecuciones archivadas*», con el número, junto al control. Que nadie crea
  que se perdieron.
- En la fila, cuando la corrida es evidencia, un distintivo discreto con su
  resultado. No un chip por cada `result_id` si son varios: uno y el resto en el
  `title`.

**No toques `nav.ts`.** Este tramo no agrega destinos.

---

## Cierre

```bash
cd webconsole/backend && ./.venv/bin/python -m pytest -q
cd webconsole/frontend && npm test && npm run build
```

- Backend **784 + los nuevos**, verdes.
- Frontend **454 + los nuevos**, verdes.
- **Contrato 10/10.** Si se puso rojo, es E-4: revisá que el default siguiera
  siendo `todas`.
- Capturas de Corridas y Experimentos en los tres estados del interruptor.
- **La tabla de clasificación de A.4 pegada en el reporte.** Sin eso el tramo no
  está cerrado.

Commit: `feat(webconsole): tramo 6 — archivar lo que no es evidencia`
