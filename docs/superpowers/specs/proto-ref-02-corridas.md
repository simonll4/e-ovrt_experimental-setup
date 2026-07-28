# proto-ref-02 — Corridas y Detalle de corrida

Análisis de las dos pantallas del prototipo (`rediseno-consola-eovrt/prototipo.html`,
funciones `screenRuns()` y `screenRun()`) cruzado contra la API real del BFF
(`http://localhost:8090`, 95 corridas reales, verificado 2026-07-26).

Convenciones de este documento:

- **HAY** — el dato existe; se indica el campo exacto.
- **DERIVABLE** — se calcula en el cliente con lo que hay; se explica cómo y con qué costo.
- **NO HAY** — no existe ni se deriva sin tocar el backend; se propone la degradación.

Las clases CSS citadas son las del prototipo, tal cual. El prototipo es la verdad
visual; las capturas de referencia son `proto-ref/runs.png` y `proto-ref/run.png`.

---

## 0. Lo que la API realmente entrega (base para todo lo que sigue)

### 0.1 `GET /api/runs` → `RunRow[]` (array plano, sin envoltura, sin parámetros)

```json
{"run_id":"run_20260725_202012_dbe_yoloe_e2bfe1","name":"yoloe_p3_live","status":"stopped",
 "model":"yoloe","source_type":"oak_d","prompt_set_id":"cr01_cr02_v2_short",
 "fps_effective":5.12,"total_detections":355,"duration_seconds":29.69,
 "started_at":"2026-07-25T20:20:12.534318+00:00","bench_split":null,
 "evaluated":false,"live":false,"topology":"single_host"}
```

**Trampa mayor — hidratación parcial.** `routers/runs.py::list_runs` hidrata con
`GET status(run_id)` solo las primeras `settings.hydration_limit` filas (hoy 50 de 95).
Las restantes 45 llegan **mínimas**:

```json
{"run_id":"…","name":null,"status":"succeeded","bench_split":"bench_v2_val",
 "evaluated":true,"live":false}
```

o sea **sin** `model`, `source_type`, `prompt_set_id`, `fps_effective`,
`total_detections`, `duration_seconds`, `started_at`, `topology`. Conteo medido sobre
las 95: esas claves están presentes en 50 filas y ausentes (no null: **ausentes**) en 45.
Todo el diseño de la tabla del prototipo asume 8 columnas siempre llenas.

Distribución real medida: `status` = 75 `succeeded` + 20 `stopped` (ninguna `running`);
`source_type` = 24 `image_folder`, 20 `oak_d`, 5 `video_file`, 1 `rtsp`, 45 ausente;
`model` = 39 `grounding_dino`, 11 `yoloe`, 45 ausente; `name` presente en 21 de 95;
`live` = false en todas; `bench_split` = 12 `bench_v2_test`, 10 `bench_v2_val`, 73 null.
El orden que devuelve el backend es descendente por fecha (los `run_id` son
`run_<YYYYMMDD>_<HHMMSS>_…`, ordenables lexicográficamente).

**Vocabulario de estado real** (`experiment/runner.py::TERMINAL_STATUSES` + `running`):
`running`, `succeeded`, `failed`, `error`, `stopped`. Son **cinco**, no los tres del
prototipo. `runview.ts` ya los traduce: en curso / completada / fallida / con error /
**detenida** (tono neutral: es una parada deliberada del operador, no un fallo).

### 0.2 `GET /api/runs/{id}` → `RunDetail`

Claves de primer nivel: `run_id`, `name`, `status`, `summary`, `bench_split`,
`evaluated`, `live`. Todo lo interesante vive en `summary` (`media.summary.v2`):

`schema_version, run_id, scenario, model_name, prompt_set_id, source_type,
source_count, units_processed, units_failed, total_detections, detections_by_label,
detections_by_prompt_id, avg_latency_ms, p50_latency_ms, p95_latency_ms,
p99_latency_ms, fps_effective, gpu_memory_peak_mb, device, duration_seconds,
started_at, finished_at, units_dropped, backpressure_wait_ms,
max_staleness_observed_ms, run_descriptor{scenario,topology,transport,rate_control,
source_kind,model,prompt_set,device,code_version}, source_clock, g2a{...},
prefilter{...}, status, stop_cause, error, name, experiment_id`
(`capture_to_host` aparece solo en corridas de cámara).

### 0.3 `GET /api/runs/{id}/trace?page=&page_size=` → `TracePage`

`page_size` máximo **1000** (5000 devuelve 422). Cabecera:

```json
{"media_run_id":"…","control_run_id":"control_live_…|null","topology":"single_host",
 "totals":{"frames":90,"detections":30,"dropped_by_reason":{"queue_full":60},
           "alerts":1,"received":30,"not_received":0},
 "control_error":null,"page":1,"page_size":3,"total":90,"frames":[…]}
```

Cada `frames[i]`: `frame_index` (**null en `image_folder`**), `unit_id`
(`frame_000062` / `img_000000`), `timestamp_ms` (**null en cuadros descartados y en
`image_folder`**), `detections[] {label, confidence, bbox_norm_xyxy}` (null si no se
procesó), `control` (string), `progress[]` (evento `control.pattern_progress.v1`
completo: `pattern_id, condition_id, mode, elapsed_ms, threshold_ms, elapsed_frames,
threshold_frames, progress` 0..1, `subject_key`, `source_id`), `alert[]` (evento
`control.alert.v1` completo: `alert_id, pattern_id, condition_id, severity, state,
evidence{subject, missing_class, rationale, subjects_in_evidence}, first_evidence_ms,
alert_registered_ms`), `active_patterns[]`.

Cuando la corrida no pasó por el motor de reglas (75 de 95: DBE puras),
`control_run_id` es `null`, `totals.received`/`not_received` son `null`,
`dropped_by_reason` es `{}` y `progress`/`alert` vienen vacíos en todos los cuadros.

Vocabulario de `control` **observado**: `received`, `dropped:queue_full`,
`not_received`. El prototipo asume `dropped:rate_gate` y `dropped:overload`. El enum
no está cerrado (README §Backend punto 2).

### 0.4 `GET /api/runs/{id}/detections` → `{page,page_size,total,items[]}`

Cada item es un evento `media.detection.v1` completo: `unit_id`,
`source{source_id, source_type, frame_index, timestamp_ms, width, height}`,
`model{name, model_id, device}`, `prompts{prompt_set_id}`,
`detections[{detection_id, label, prompt_id, source_prompt, confidence, bbox_xyxy,
bbox_norm_xyxy, area_px}]`, `timing{normalize_ms, inference_ms, postprocess_ms,
write_ms, total_ms}`. **`total` cuenta solo los cuadros con detecciones**, no los cuadros.

### 0.5 Otros

- `GET /api/runs/{id}/evaluate` → `{type, run_id, benchmark, iou_threshold,
  per_class[{class_name, AP50|null, n_gt, n_det}], cr01_detection_recall, evaluated_at}`.
  `POST` al mismo path dispara la evaluación.
- `GET /api/runs/{id}/artifacts/{path}` → streaming del archivo, soporta `Range`.
  **No existe endpoint de listado de artefactos.**
- `DELETE /api/runs/{id}` (409 si activo), `POST /api/runs/{id}/stop` (202).
- `WS /api/runs/{run_id}/stream` → `StreamEvent`: `metric {unit_id, fps,
  latency_total_ms, detections_count, gpu_memory_mb}`, `detection`, `error`, `state`.
  Solo suscribible si `status==='running' && live===true` (`runview.ts::isLive`).
- `GET /api/preflight` → `{ready, blockers[], media{service_url,healthy,ready,model},
  control{service_url,healthy,ready}}`. `GET /api/target` → el `media` de arriba.
- Artefactos reales en disco (`e-ovrt_media-plane/runs/<id>/`): `detections.jsonl`,
  `summary.json`, `metrics.jsonl`, `effective_config.yaml`, `errors.jsonl`,
  `run_manifest.json`, `run_provenance.json`, a veces `dropped_units.jsonl`,
  `eval_perception.json` y `previews/`. **Ningún run tiene `annotated.mp4`.**

---

## 1. Pantalla **Corridas** (`screenRuns()`)

### 1.1 Composición

Columna única, ancho completo del `.main`, todo scrollea con la página. Cinco bloques
apilados, en este orden:

1. `.crumbs` — migas + interruptor de prototipo (**no se implementa**, es andamio).
2. `<header class="rh">` — `<h1>Corridas</h1>` + `.meta` con contadores + `.acts` con
   el botón primario **Nueva corrida**.
3. `.pad > .banner` de corrida en vivo — **condicional**: solo si hay alguna en curso.
4. `.toolbar` — buscador + segmentado de estado + contador a la derecha (`margin-left:auto`).
5. `.pad > .card > .tw > table` — la tabla. Filas de 32 px, borde inferior, sin scroll
   propio (el `.tw` solo da `overflow-x:auto` para pantallas angostas).

No hay panel lateral ni nada fijo: es una sola pila vertical. La barra lateral y la
franja de servicios son del armazón (`Shell`), fuera del alcance de esta pantalla.

### 1.2 Bloque a bloque

#### Encabezado

```html
<header class="rh">
  <div><h1>Corridas</h1>
    <div class="meta"><span>9 en total</span>
      <span class="sep">·</span><span style="color:var(--live)">1 en curso</span></div></div>
  <div class="acts"><button class="btn pri" data-screen="compose">▶ Nueva corrida</button></div>
</header>
```

| Dato | Estado | Origen |
|---|---|---|
| «N en total» | **HAY** | `runs.length` de `GET /api/runs` |
| «N en curso» | **DERIVABLE** | `runs.filter(r => r.status === 'running').length`; ocultar el fragmento si es 0 (el prototipo ya lo hace) |

#### Banner de corrida en vivo

```html
<div class="pad" style="padding-bottom:0">
 <div class="banner" style="background:var(--live-bg);border-color:var(--live-bd)">
  <span class="ic"><span class="pulse" style="display:block;margin-top:5px"></span></span>
  <div style="flex:1"><b style="color:var(--live)">Ronda nocturna — cámara 04</b>
   <span style="color:var(--tx2)">está procesando ahora — 67 detecciones, 3 alertas confirmadas.</span></div>
  <button class="btn" data-run="…">Ver en vivo</button></div></div>
```

| Dato | Estado | Origen |
|---|---|---|
| Nombre de la corrida viva | **HAY** | `row.name ?? row.run_id` |
| «N detecciones» | **DERIVABLE** | acumulado de los eventos `metric.detections_count` del WS, o `GET /api/runs/{id}` → `summary.total_detections` con *polling* (una corrida `running` ya expone summary parcial) |
| «N alertas confirmadas» | **DERIVABLE, con costo** | `GET /api/runs/{id}/trace?page=1&page_size=1` → `totals.alerts`. Una petición extra por refresco. Si `control_run_id` es null, omitir el fragmento en vez de mostrar 0 |

#### Barra de herramientas

```html
<div class="toolbar">
  <div class="search"><span class="mg">…lupa…</span>
    <input id="qsearch" placeholder="Buscar por nombre o identificador" aria-label="Buscar corridas"></div>
  <div class="seg">
    <button data-fst="all" aria-pressed="true">Todas</button>
    <button data-fst="run">En curso</button>
    <button data-fst="ok">Completadas</button>
    <button data-fst="err">Fallidas</button></div>
  <span class="cnt">9 de 9</span>
</div>
```

`.search` es `flex:1; min-width:180px; max-width:300px`. `.seg` es un segmentado con
`aria-pressed`. `.cnt` va `margin-left:auto`, monoespaciada.

- **Búsqueda**: filtra por `(nm + " " + id).toLowerCase().includes(q)`. **DERIVABLE**
  en cliente. Con 95 filas alcanza; el README anticipa el límite de escala.
- **Segmentado**: el prototipo tiene 4 opciones para 3 estados. El vocabulario real
  tiene 5. **Propuesta**: `Todas · En curso · Completadas · Detenidas · Fallidas`,
  mapeando `failed`+`error` → «Fallidas» y `stopped` → «Detenidas» (tono neutral).
- **Contador «N de M»**: **DERIVABLE**.

#### Tabla

Columnas (`COLS`), todas ordenables por clic en el `<th class="s">` (`.n` = numérica,
alineada a la derecha, cifras tabulares). El indicador de orden es `<span class="ar">↑|↓</span>`.

```html
<tr class="rw" data-run="run_20260725_143012">
  <td><span class="rowname"><b>Ronda nocturna — cámara 04</b><span>run_20260725_143012</span></span></td>
  <td><span class="chip c-live"><span class="pulse"></span>En curso</span></td>
  <td class="mono">owlv2-base-patch16</td>
  <td>Cámara RTSP</td>
  <td class="mono">ps_perimetro_v3</td>
  <td class="n">2,4</td><td class="n">67</td><td class="n">24,8 s</td>
  <td class="act">…</td>
</tr>
```

| Columna / dato | Estado | Origen y notas |
|---|---|---|
| Corrida (`.rowname b`) | **HAY** | `row.name`; si es null cae al `run_id` (solo 21 de 95 tienen nombre) |
| Subtítulo (`.rowname span`) | **HAY / NO HAY** | Si hay nombre, muestra `run_id`. Si no, muestra «hace 4 min» ← `row.started_at`. **Está en la API** (corrige el punto 7 del README), pero **solo en las filas hidratadas**; en las 45 restantes no viene. Degradación: parsear la fecha del `run_id` (`run_YYYYMMDD_HHMMSS_…`), que es determinista, y marcarlo como derivado |
| Estado (`.chip c-live/c-ok/c-er`) | **HAY** | `row.status`, con `runStatusLabel`/`runStatusTone`. Faltan dos chips: `c-nt` para «Detenida» y `c-er` para «Con error» |
| Modelo | **HAY (parcial)** | `row.model`; ausente en 45 de 95 → celda «—» |
| Fuente | **HAY (parcial)** | `row.source_type` ∈ `image_folder｜video_file｜rtsp｜oak_d` → «Carpeta de imágenes｜Archivo de video｜Cámara RTSP｜Cámara OAK-D Pro»; ausente en 45 |
| Conjunto de prompts | **HAY (parcial)** | `row.prompt_set_id` |
| Cuadros/s | **HAY (parcial)** | `row.fps_effective`, un decimal, coma decimal |
| Detecciones | **HAY (parcial)** | `row.total_detections` |
| Duración | **HAY (parcial)** | `row.duration_seconds` + « s» |
| Celda de acción `.act` | **HAY** | `hace(...)` si está en curso; si no, botón Borrar → `DELETE /api/runs/{id}` |

**Consecuencia de diseño, no negociable**: con 45 de 95 filas sin métricas, el orden
por una columna numérica es engañoso. Degradación propuesta: ordenar los ausentes
siempre al final (independiente de la dirección), renderizar «—» en `var(--tx4)` y
poner una nota al pie de la tabla («N corridas sin métricas cargadas»). La alternativa
real es subir `hydration_limit` o paginar del lado del servidor (README punto 5).

#### Borrado en dos pasos

Al tocar `[data-del]` la celda cambia a confirmación en línea, sin modal:

```html
<span class="delc">¿Borrar?
  <button class="btn dg stay" data-delok="run_…">Sí, borrar</button>
  <button class="btn gh stay" data-delno="1">No</button></span>
```

Solo una fila puede estar en confirmación (`S.del` guarda un id). La clase `stay`
evita que el clic global cierre el estado. `DELETE` devuelve **409** si la corrida está
activa → mostrar el error en línea, no borrar la fila.

#### Vacíos

Dos textos distintos, en una celda `colspan="9"` con `.empty`:
sin resultados de filtro → «Ninguna corrida coincide con el filtro. / Probá con otro
texto o volvé a «Todas».»; lista realmente vacía → «Todavía no lanzaste ninguna
corrida. / Empezá por elegir una fuente y un conjunto de prompts.»

### 1.3 Interacciones

| Gesto | Efecto |
|---|---|
| Escribir en `#qsearch` | filtra (evento `input`, sin *debounce* en el prototipo); resetea la confirmación de borrado |
| Clic en `[data-fst]` | cambia el filtro de estado; resetea la confirmación |
| Clic en `th[data-sort]` | primer clic ordena ascendente; segundo invierte. Estado `{k, d}` |
| Clic en la fila `[data-run]` | navega al detalle |
| Clic en Borrar | confirmación en línea de dos pasos |
| Clic en «Nueva corrida» / «Ver en vivo» | navegación |

---

## 2. Pantalla **Detalle de corrida** (`screenRun()`)

### 2.1 Composición

Pila vertical de siete bloques; el único bloque con layout de dos columnas es el panel
de la pestaña Traza.

1. `.crumbs` — «Corridas / `run_id`».
2. `.pad > .banner er` — aviso de error de la pantalla (**condicional**).
3. `<header class="rh">` — título, `.meta` con chips y datos, `.acts` con
   **Detener · Archivos · Borrar**.
4. `.pad > .banner wn` — «el motor de reglas no responde» (**condicional**).
5. `.kpihd` + `.kpis` — grilla `repeat(auto-fit, minmax(146px, 1fr))`, 6 tarjetas en
   curso / 7 terminada.
6. `.tl` — línea de tiempo, ancho completo, tres carriles.
7. `.tabs` + contenido: `Traza` | `Resumen` | `Evaluación` | `Archivos`.

La pestaña Traza usa `.pane { display:grid; grid-template-columns: 300px minmax(0,1fr);
gap:12px; align-items:start }`: **columna izquierda fija de 300 px** con la lista de
cuadros (`.rows { max-height:492px; overflow-y:auto }` — **la única zona con scroll
propio de toda la pantalla**) y columna derecha elástica con el detalle del cuadro.
Bajo 900 px el `.pane` colapsa a una sola columna y los rótulos de los carriles de la
línea de tiempo se ocultan (`.lane .ln { display:none }`, `.lanes { padding-left:0 }`).

### 2.2 Encabezado

```html
<header class="rh"><div><h1>Ronda nocturna — cámara 04</h1><div class="meta">
  <span class="chip c-live"><span class="pulse"></span>En curso</span>
  <span class="chip c-nt">Un solo equipo</span>
  <span class="sep">·</span><span class="mono">run_20260725_143012</span>
  <span class="sep">·</span><span>Cámara cam-04</span>
  <span class="sep">·</span><span>24,8 s y contando</span></div></div>
 <div class="acts">
  <button class="btn dg">■ Detener</button>
  <button class="btn">⤓ Archivos</button>
  <button class="btn gh">Borrar</button></div></header>
```

| Dato | Estado | Origen |
|---|---|---|
| Título | **HAY** | `detail.name ?? run_id` |
| Chip de estado | **HAY** | `detail.status` |
| Chip de topología | **HAY** | `summary.run_descriptor.topology` → `topologyBadge()` («un solo equipo» / «dos equipos»); ocultar si falta |
| `run_id` | **HAY** | `detail.run_id` |
| «Cámara cam-04» | **DERIVABLE, con costo** | `summary.source_type` da el *tipo*, no el identificador. El `source_id` real (`rtsp_dvr_1`) aparece en `GET /api/runs/{id}/detections?page_size=1` → `items[0].source.source_id`, o en el artefacto `effective_config.yaml`. Degradación barata: mostrar solo la etiqueta del tipo de fuente |
| «24,8 s y contando» | **HAY / DERIVABLE** | Terminada: `summary.duration_seconds`. En curso: `Date.now() − Date.parse(summary.started_at)` |
| Detener | **HAY** | `POST /api/runs/{id}/stop`; visible solo si `status==='running'` |
| Archivos | **HAY** | ancla a la pestaña Archivos; deshabilitado en curso |
| Borrar | **HAY** | `DELETE /api/runs/{id}`; deshabilitado en curso (`title="No se puede borrar una corrida en curso"`) |

**Banner de motor de reglas caído** (`.banner wn`, condicional): **HAY** —
`trace.control_error` no nulo, o `preflight.control.healthy === false`. Texto del
prototipo: «El motor de reglas no responde. Los descartes de entrega y las alertas se
muestran como `sin dato`. La detección sobre el video sigue funcionando.»

### 2.3 Fila de indicadores (`kpis()` / `kpi()`)

Estructura de cada tarjeta:

```html
<div class="kpi">
  <div class="l"><i style="background:#4b95e8"></i>Cuadros por segundo</div>
  <div class="vr"><span class="v">2,4<small>ms</small></span>
    <span class="dl" style="color:var(--ok)">▲0,3</span></div>
  <div class="foot">…sparkline SVG… | <div class="mtr"><i style="width:75%"></i></div>
    <div class="sub">75 % de 8 192 MB</div></div>
</div>
```

`.kpihd` es el rótulo que corona la fila: «Variación comparada con los últimos 30 s»
(en curso) / «…con la corrida anterior» (terminada).

| # | Tarjeta | Valor | Complemento | Veredicto |
|---|---|---|---|---|
| 1 | Cuadros por segundo | `summary.fps_effective` — **HAY** | delta ▲0,3 — **NO HAY**; sparkline — **DERIVABLE con costo** | ver abajo |
| 2 | Latencia (mediana) | `summary.p50_latency_ms` — **HAY** | delta ▼56 ms — **NO HAY**; sparkline — **DERIVABLE con costo** | |
| 3 | Memoria de GPU | `summary.gpu_memory_peak_mb` — **HAY, pero es el PICO** | medidor «75 % de 8 192 MB» — **NO HAY**: la capacidad total de la GPU no la expone ni `/api/target` (`model.runtime` solo trae `half_precision`, `warmup`) ni el summary | |
| 4 | Detecciones | `summary.total_detections` — **HAY** | delta ▲12 — **NO HAY**; sparkline acumulada — **DERIVABLE con costo** | |
| 5 | Descartes de entrega (%) | **DERIVABLE** | `sum(trace.totals.dropped_by_reason) / trace.totals.frames`. Ojo: **no** es `summary.units_dropped`, que es descarte de *ingesta* (otro concepto, otro punto de la cadena). delta «▲1,8 pp» — **NO HAY** | |
| 6 | Alertas confirmadas | `trace.totals.alerts` — **HAY** | «Última hace 21,4 s» — **DERIVABLE con costo alto**: exige recorrer el trace completo buscando el último cuadro con `alert[]` y su `timestamp_ms` (que es **null** en `image_folder`) | |
| 7 | Latencia (p95), solo terminada | `summary.p95_latency_ms` — **HAY** | «Máximo observado 1 204 ms» — **NO HAY**: no se publica el máximo. Sustituir por `p99_latency_ms` («percentil 99 811 ms»), que sí está | |
| 8 | Duración, solo terminada | `summary.duration_seconds` — **HAY** | «N unidades procesadas» ← `summary.units_processed` — **HAY** | |

**Deltas y `.kpihd`: NO HAY, en bloque.** No existe el concepto de «corrida anterior
comparable» (README punto 4) ni ninguna serie de los últimos 30 s en el summary.
**Degradación**: eliminar el `.kpihd` y todos los `<span class="dl">`. El diseño no se
rompe — `.kpi .vr` es un flex que colapsa limpio con un solo hijo. No inventar la
comparación contra «la corrida inmediatamente anterior del listado»: distinto modelo,
distinta fuente y distinto conjunto de prompts hacen la cifra inútil o engañosa.

**Sparklines: DERIVABLE con costo, en dos regímenes.**
- Corrida terminada: el artefacto `metrics.jsonl` se sirve por
  `GET /api/runs/{id}/artifacts/metrics.jsonl` y trae la serie por unidad. Es una
  descarga completa (megabytes en corridas de 5000 cuadros) solo para dibujar 8 puntos.
  Recomendación: **no** hacerlo en la carga inicial; o se acepta y se hace perezoso, o
  se omite el `.foot` de esas tres tarjetas.
- Corrida en curso: **DERIVABLE barato** acumulando los eventos `metric` del WS
  (`fps`, `latency_total_ms`, `gpu_memory_mb`) en un buffer del cliente. Esta es la
  lectura fiel de «los últimos 30 s» y la única que el prototipo justifica.

**Degradación propuesta para la tarjeta 3 (memoria de GPU)**: conservar la tarjeta,
cambiar el rótulo a «Memoria de GPU (pico)», mostrar `gpu_memory_peak_mb` y **quitar
el `.mtr`**; el `.sub` pasa a decir el dispositivo (`summary.device`, p. ej. `cuda`).
Si la corrida está en vivo, el WS sí da `gpu_memory_mb` instantánea, pero tampoco el
total: el medidor porcentual no es recuperable sin backend.

### 2.4 Línea de tiempo (`timeline()`)

```html
<div class="tl">
 <div class="hd"><b>Línea de tiempo</b><span>60 cuadros · 24,8 s</span>
  <span class="lg">…4 entradas de leyenda con <i> de color…</span></div>
 <div class="lanes" id="lanes">
   <div class="lane lane-det"><span class="ln">Detecciones<br>por cuadro</span><svg/></div>
   <div class="lane"><span class="ln">Entrega al<br>motor de reglas</span>
     <div class="strip"><i style="background:…"></i>×N</div></div>
   <div class="lane lane-al"><span class="ln">Alertas</span><span class="almk" style="left:31.6%"></span>…</div>
   <div class="head" style="left:calc(31.6% + 82px)"></div>
 </div>
 <div class="axis"><span>0,0 s</span><span>12,4 s</span><span>24,8 s</span></div>
 <div class="ttip" id="ttip"></div></div>
```

`.lanes` tiene `padding-left:82px` (canaleta de rótulos) y `cursor:crosshair`; el
cabezal `.head` es una línea vertical de 1 px con un cuadradito arriba. `bindLanes()`
mapea la posición del mouse a índice de cuadro con
`round(((clientX − left − 82) / (width − 82)) × (F − 1))`, muestra `#ttip` con cuadro,
segundo, cantidad de detecciones, motivo de control y alerta, y en **clic selecciona el
cuadro** (mismo estado que la lista).

| Dato | Estado | Origen |
|---|---|---|
| «N cuadros» | **HAY** | `trace.totals.frames` |
| Duración del rótulo | **HAY** | `summary.duration_seconds` |
| Carril de detecciones por cuadro | **DERIVABLE con costo** | `frames[i].detections?.length ?? 0` de **todo** el trace |
| Carril de entrega (`.strip`) | **DERIVABLE con costo** | `frames[i].control` |
| Carril de alertas (`.almk`) | **DERIVABLE con costo** | índices con `frames[i].alert.length > 0` |
| Eje temporal `0,0 s / 12,4 s / 24,8 s` | **DERIVABLE, con hueco** | `timestamp_ms − timestamp_ms[0]`. Pero es **null** en cuadros descartados y en **todas** las corridas `image_folder` (24 de 95, incluida la de 5000 cuadros). Degradación: cuando `source_clock === 'none'` o el primer `timestamp_ms` es null, el eje pasa a índice de cuadro («0 / 2 500 / 5 000») y el rótulo omite los segundos |

**El costo, explícito**: no hay índice de actividad de la corrida completa (README
punto 1). Reconstruirlo cuesta `ceil(total / 1000)` peticiones al trace (5 para la
corrida de 5000 cuadros, 1 para las chicas). Es la petición más pesada de la pantalla y
la que habilita, de una sola vez, la línea de tiempo **y** los filtros de la lista de
cuadros **y** el card de alertas confirmadas. Implementarlo como una carga única en
segundo plano, con la línea de tiempo en estado de esqueleto mientras llega, y
`page_size=1000` fijo. Para una corrida en curso el índice se invalida en cada refresco:
recargarlo con intervalo, no por evento.

### 2.5 Pestañas

```html
<div class="tabs" role="tablist">
 <button class="tab" role="tab" data-tab="traza" aria-selected="true">Traza<span class="n">60</span></button>
 <button class="tab" role="tab" data-tab="resumen" aria-selected="false">Resumen</button>
 <button class="tab" role="tab" data-tab="eval" aria-selected="false">Evaluación</button>
 <button class="tab" role="tab" data-tab="arch" aria-selected="false">Archivos<span class="n">4</span></button>
</div>
```

- Contador de **Traza**: **HAY** (`trace.totals.frames`).
- Contador de **Archivos**: **NO HAY** — no existe endpoint de listado de artefactos.
  Degradación: omitir el `<span class="n">` hasta que la pestaña se abra y se sondeen
  los artefactos conocidos (§2.9); entonces mostrar el conteo de los que respondieron 200.

### 2.6 Traza — lista de cuadros (`frameList()`)

```html
<div class="flist">
 <div class="ft">
  <label class="tog"><input type="checkbox" id="fAct">Solo con actividad</label>
  <label class="tog"><input type="checkbox" id="fAl">Solo alertas</label>
  <span style="margin-left:auto;…">60 de 60</span></div>
 <div class="rows">
  <button class="fr" data-fr="19" data-sel="1" title="Entregado al motor de reglas">
   <span class="ix">19</span><span class="id">4a91c019</span>
   <span class="rt"><span class="chip c-sr">Alerta</span>
     <span class="dc">3</span><span class="st" style="background:var(--ok)"></span></span></button>
 </div></div>
```

`.fr` es `grid-template-columns: 46px 1fr auto`, alto `var(--row)` (32 px), con
`border-left: 2px solid transparent` que se pinta de acento cuando `data-sel="1"`.
Tras cada render, `render()` hace `scrollIntoView({block:'nearest'})` sobre el
seleccionado — es lo que mantiene sincronizada la lista con la selección hecha desde la
línea de tiempo.

| Dato | Estado | Origen |
|---|---|---|
| Índice `.ix` | **HAY / DERIVABLE** | `frames[i].frame_index`; **null en `image_folder`** → usar la posición en el arreglo |
| Identificador `.id` | **HAY** | `frames[i].unit_id` (`frame_000019`, `img_000000`) |
| Chip «Alerta» | **HAY** | `frames[i].alert.length > 0` |
| Conteo `.dc` | **HAY** | `frames[i].detections?.length ?? '—'` |
| Punto de estado `.st` | **HAY** | color por `frames[i].control` |
| `title` de la fila | **HAY (parcial)** | mapeo de `control` a texto largo; el enum no está cerrado → para un valor desconocido mostrar «descartado (motivo)» con el sufijo crudo en monoespaciada, nunca la cadena en inglés suelta |
| «60 de 60» | **DERIVABLE** | filtrados / `totals.frames` |
| Casillas de filtro | **DERIVABLE, depende del índice completo** | Con paginación server-side los filtros solo verían la página actual. Deben operar sobre el índice de §2.4. Si el índice todavía no cargó: deshabilitar las casillas con `title="Cargando la traza completa"` |

Reglas de las casillas: marcar «Solo alertas» desmarca y **deshabilita** «Solo con
actividad». «Con actividad» = tiene detecciones, o `control !== 'received'`, o hay
progreso, o hay alerta. Vacío: «Ningún cuadro coincide con el filtro. / Destildá las
casillas para ver la corrida completa.»

### 2.7 Traza — detalle del cuadro (`detail()`)

Cuatro piezas apiladas en `.detail` (flex, gap 12): banner de alerta (condicional),
visor, `.grid2` con dos tarjetas, y la tarjeta de alertas confirmadas.

#### Banner de alerta

```html
<div class="banner wn"><span class="ic" style="color:var(--sr)">⚠</span>
 <div><b style="color:var(--sr)">Alerta confirmada — <span class="mono">CR-01</span> · Presencia de persona</b><br>
 <span style="color:var(--tx2)">Se disparó en el cuadro 19 (8.0 s), cuando la condición llegó al 100 %.</span></div></div>
```

| Dato | Estado | Origen |
|---|---|---|
| Código de condición | **HAY** | `alert[0].condition_id` |
| Nombre legible («Presencia de persona») | **NO HAY** | El BFF no expone las definiciones del pattern set (README punto 3). **Degradación**: mostrar solo `CR-01` en monoespaciada y, en su lugar, la severidad traducida (`alert[0].severity`: high → «alta»). No cablear un diccionario `CR-01 → …` en el frontend: los pattern sets son configuración del control-plane y se versionan aparte |
| «cuando la condición llegó al 100 %» | **HAY, y mejor** | `alert[0].evidence.rationale` trae la explicación real («No se encontró evidencia 'helmet' en región 'upper_body' de 1 sujeto(s)»). Usar eso; conservar el número de cuadro y el segundo |

#### Visor

```html
<div class="viewer">
 <div class="vh"><span class="mono">Cuadro 19</span><span>·</span>
  <span>unidad <span class="mono">4a91c019</span></span><span>·</span><span>8.0 s</span>
  <span class="r"><span class="chip c-ok" title="Entregado al motor de reglas">Recibido</span>
   <button class="btn gh" onclick="nav(-1)" aria-label="Cuadro anterior">‹</button>
   <button class="btn gh" onclick="nav(1)" aria-label="Cuadro siguiente">›</button></span></div>
 <div class="stage"><svg viewBox="0 0 100 56" preserveAspectRatio="none">…</svg></div></div>
```

`.stage` es `aspect-ratio:16/9; max-height:326px`. Cada caja se dibuja como `<rect>` en
porcentajes más una etiqueta rellena con `label confianza` en monoespaciada.

| Dato | Estado | Origen |
|---|---|---|
| Cuadro / unidad / segundo | **HAY** | `frame_index` (o posición), `unit_id`, `timestamp_ms` relativo (null → omitir el segmento) |
| Chip de control | **HAY (enum abierto)** | `frames[i].control` |
| Cajas | **HAY, con conversión** | `detections[].bbox_norm_xyxy` es `[x0,y0,x1,y1]` normalizado; el prototipo usa `x, y, w, h` en % → `x=x0*100`, `y=y0*100`, `w=(x1−x0)*100`, `h=(y1−y0)*100` |
| Relación de aspecto real | **DERIVABLE** | `GET /detections` → `items[].source.width/height` (1920×1080 en las corridas medidas). El `16/9` del prototipo es una suposición |
| **Imagen de fondo del cuadro** | **NO HAY** | Solo 10 de 95 corridas tienen `previews/`, y está **submuestreado** (5 imágenes para 152 cuadros: `frame_000000`, `frame_000016`, `frame_000029`…). No existe imagen por cuadro. **Degradación**: mantener el lienzo sintético del prototipo (rejilla neutra) con el texto «sin vista previa de este cuadro» y dibujar las cajas encima — que es exactamente lo que el prototipo ya hace y el README declara simulado. Si `previews/<unit_id>.preview.jpg` responde 200 vía `/artifacts/`, usarla de fondo; si 404, lienzo neutro. La comprobación es por cuadro y debe fallar en silencio |

#### `.grid2` — Detecciones + Progreso de las condiciones

```html
<div class="card"><h3>Detecciones<span class="r">3</span></h3>
 <div class="dets"><div class="det"><span class="sw" style="background:#d95926"></span>
  <span class="lb">vehicle</span><span class="cf">0.59</span></div>…</div>
 <p class="cap">Los nombres de clase los define el conjunto de prompts y se muestran tal como están escritos ahí.</p></div>

<div class="card"><h3>Progreso de las condiciones</h3>
 <div class="plist"><div class="prow">
  <div class="ph"><span class="pcd">CR-01</span><span class="pnm">Presencia de persona</span><span class="ppc">41%</span></div>
  <div class="mtr"><i style="width:41%;background:var(--wn)"></i></div></div>…</div></div>
```

| Dato | Estado | Origen |
|---|---|---|
| Etiqueta y confianza | **HAY** | `detections[].label`, `.confidence` (2 decimales, punto decimal — es un valor literal, no interfaz) |
| Color por clase (`.sw`) | **DERIVABLE** | No viene del backend. Asignar una paleta estable indexada por el orden alfabético de las clases del `prompt_set_id`, para que el mismo `person` tenga el mismo color en el visor, en la lista y en «Detecciones por clase» |
| Progreso `%` | **HAY** | `progress[].progress` (0..1) × 100 |
| Código de condición | **HAY** | `progress[].condition_id` |
| Nombre legible de la condición | **NO HAY** | idem banner; degradación: reemplazar `.pnm` por `elapsed_ms / threshold_ms` formateado («2,4 s de 4,0 s»), que **sí** viene y es más informativo que un rótulo |
| Bloque completo, en corridas sin control-plane | **NO HAY** | 75 de 95 corridas tienen `control_run_id: null` → `progress` y `alert` siempre vacíos. **Degradación**: no mostrar la tarjeta vacía; reemplazarla por un `.empty` de una línea: «Esta corrida no pasó por el motor de reglas.» Lo mismo para la tarjeta de alertas y para el carril de alertas de la línea de tiempo |

#### Alertas confirmadas de la corrida

```html
<div class="card"><h3>Alertas confirmadas<span class="r">3</span></h3><div class="alist">
 <button class="al" data-fr="19"><span style="color:var(--sr)">⚠</span>
  <span class="w"><b><span class="mono">CR-01</span> — Presencia de persona</b>
   <span>cuadro 19 · 8.0 s · unidad 4a91c019</span></span>
  <span class="chip c-nt">Ver cuadro</span></button>…</div></div>
```

**DERIVABLE** del índice completo del trace (`frames` con `alert.length > 0`); el conteo
sale de `totals.alerts` (**HAY**). Cada entrada navega al cuadro. El nombre legible,
otra vez **NO HAY**.

### 2.8 Resumen (`tabResumen()`) y Evaluación (`tabEval()`)

**Resumen** — dos tarjetas `.card` con listas `<dl class="kv">` y una tercera con
detecciones por clase.

| Campo | Estado | Origen |
|---|---|---|
| Modelo | **HAY** | `summary.model_name` (o `run_descriptor.model`) |
| Dispositivo | **HAY** | `summary.device` |
| Conjunto de prompts | **HAY** | `summary.prompt_set_id` |
| Origen | **HAY (tipo) / DERIVABLE (identificador)** | `summary.source_type`; el `source_id` como en §2.2 |
| Despliegue | **HAY** | `run_descriptor.topology` |
| Conjunto de evaluación | **HAY** | `detail.bench_split` (null en 73 de 95 → «sin conjunto») |
| Cuadros por segundo / p50 / p95 | **HAY** | `fps_effective`, `p50_latency_ms`, `p95_latency_ms` |
| Unidades procesadas / Detecciones / Duración | **HAY** | `units_processed`, `total_detections`, `duration_seconds` |
| Detecciones por clase | **HAY** | `summary.detections_by_label` — mapa `{clase: n}` |

Extra disponible que el prototipo no muestra y conviene sumar al bloque de rendimiento:
`units_failed`, `units_dropped`, `avg_latency_ms`, `p99_latency_ms`, `stop_cause`
(«stop» cuando el operador detuvo la corrida), `error`, `run_descriptor.code_version`.

**Evaluación** — `GET /api/runs/{id}/evaluate`. Si `detail.evaluated === false`
(67 de 95), el `.empty` del prototipo se reusa cambiando el motivo: «Esta corrida
todavía no fue evaluada» + botón que dispara `POST /evaluate`.

| Dato del prototipo | Estado | Origen |
|---|---|---|
| Tabla por clase: Clase / Precisión / Cajas anotadas | **HAY** | `per_class[].class_name`, `.AP50` (puede ser **null**: clase sin GT → celda «sin dato»), `.n_gt` |
| Columna «Exhaustividad» por clase | **NO HAY** | El recall por clase no se publica. **Degradación**: reemplazar la columna por **«Detecciones» ← `n_det`**, que sí viene y sostiene la misma lectura (clase sobre/sub-marcada). El caso real `vest: AP50=null, n_gt=0, n_det=6193` es justamente el hallazgo F-G2.1 y merece verse |
| «Precisión media (mAP)» | **DERIVABLE** | media de los `AP50` no nulos. Declararlo en el `.cap`: «media de las clases con anotación» |
| «Exhaustividad CR-01» | **HAY** | `cr01_detection_recall` |
| «Cajas anotadas» (total) | **DERIVABLE** | `sum(per_class[].n_gt)` |
| Delta «▲0,021 comparado con la corrida anterior» | **NO HAY** | idem §2.3 → quitar el `.dl` y el `.sub` |
| Nombre del conjunto en `h3 .r` | **HAY** | `benchmark` (p. ej. `bench_stratum_shel5k`) + `iou_threshold`. **Importante**: es un **estrato** de `bench_v3`; el rótulo debe decir el estrato, nunca «el bench» a secas |
| Nota al pie de clase floja | **DERIVABLE** | regla de cliente: `AP50 < 0,5` o `n_gt < 100` → nota `.note` con `⚠` |

### 2.9 Archivos (`tabArch()`)

| Dato | Estado | Origen |
|---|---|---|
| Reproductor de video anotado | **NO HAY** | Ninguna de las 95 corridas tiene `annotated.mp4`. **Degradación**: no renderizar la tarjeta salvo que `GET /artifacts/annotated.mp4` responda 200 (sondeo con `Range: bytes=0-0`); si no, omitirla por completo — un marco vacío que dice «se genera al terminar» miente cuando la corrida ya terminó |
| Listado de archivos | **NO HAY (listado) / HAY (descarga)** | No existe endpoint que enumere artefactos. **Degradación**: lista **fija y conocida** — `summary.json`, `detections.jsonl`, `metrics.jsonl`, `effective_config.yaml`, `errors.jsonl`, `run_manifest.json`, `run_provenance.json`, `dropped_units.jsonl`, `eval_perception.json` — sondeada por `Range: bytes=0-0`; se listan solo los que responden 200/206 |
| Columna «Tamaño» | **DERIVABLE** | el `Content-Range` de ese mismo sondeo trae el total (`_FORWARD_HEADERS` reenvía `content-range` y `content-length`) |
| Columna «Contenido» | **DERIVABLE** | descripción fija por nombre de archivo, en el módulo de etiquetas |
| Botón de descarga | **HAY** | `GET /api/runs/{id}/artifacts/{path}` |
| `previews/` como fila | **HAY, con matiz** | existe en 10 de 95 corridas y está submuestreado; si se lista, decir «N imágenes de muestra», no «N vistas previas» |

### 2.10 Interacciones de la pantalla

| Gesto | Efecto |
|---|---|
| Clic en `[data-tab]` | cambia de pestaña (`aria-selected`) |
| Clic en `.fr[data-fr]` | selecciona el cuadro y fuerza la pestaña Traza |
| Clic en cualquier punto de `#lanes` | selecciona el cuadro correspondiente |
| Mover el mouse sobre `#lanes` | `#ttip` con cuadro, segundo, detecciones, motivo de control y alerta |
| `‹` / `›` (`nav(±1)`) | cuadro anterior/siguiente, con tope en los extremos |
| Flechas ← → del teclado | igual que `nav`, activas solo en la pestaña Traza y fuera de un `<input>` |
| `#fAct` / `#fAl` | filtros de la lista; «Solo alertas» inhibe «Solo con actividad» |
| Detener / Borrar | `POST /stop`, `DELETE` |

Nota de accesibilidad heredada del prototipo, a conservar: cada `.chip` lleva **icono +
texto**, nunca color solo; las flechas de navegación llevan `aria-label`; los carriles
de la línea de tiempo llevan `role="img"` con `aria-label` descriptivo.

---

## 3. Resumen de lo que **NO HAY** y su degradación

| # | Dato del prototipo | Pantalla | Degradación propuesta |
|---|---|---|---|
| 1 | Indicadores de variación (`▲0,3`, `▼56 ms`, `▲1,8 pp`, `▲0,021`) y el rótulo «Variación comparada con…» | Detalle (KPIs y Evaluación) | Eliminar `.kpihd` y todos los `<span class="dl">`. No sustituir por una comparación contra la corrida anterior del listado: no es comparable |
| 2 | Medidor «75 % de 8 192 MB» de memoria de GPU | Detalle (KPI 3) | Rotular «Memoria de GPU (pico)», mostrar `gpu_memory_peak_mb`, quitar el `.mtr`; el `.sub` pasa a `summary.device` |
| 3 | «Máximo observado 1 204 ms» | Detalle (KPI p95) | Sustituir por `p99_latency_ms` («percentil 99: 812 ms») |
| 4 | Nombre legible de la condición («Presencia de persona», «Permanencia en zona») | Detalle (banner, progreso, alertas) | Mostrar solo `CR-01` en monoespaciada + severidad traducida; en el progreso, `elapsed_ms / threshold_ms` en lugar del nombre. Backend: exponer el nombre de la definición del pattern set |
| 5 | Imagen real del cuadro en el visor | Detalle (Traza) | Lienzo neutro con «sin vista previa» + cajas de `bbox_norm_xyxy` encima; si `previews/<unit_id>.preview.jpg` responde 200, usarla de fondo |
| 6 | Contador «4» de la pestaña Archivos y listado de artefactos con tamaños | Detalle (Archivos) | Sondear una lista fija de artefactos conocidos con `Range: bytes=0-0`; listar los que respondan, tamaño de `Content-Range`, contador de la pestaña recién tras el sondeo |
| 7 | Reproductor de video anotado | Detalle (Archivos) | Omitir la tarjeta salvo que `annotated.mp4` exista (ninguna corrida actual lo tiene) |
| 8 | Columna «Exhaustividad» por clase | Detalle (Evaluación) | Reemplazar por «Detecciones» (`n_det`); conservar `cr01_detection_recall` como KPI |
| 9 | Métricas por fila en las 45 corridas no hidratadas (modelo, fuente, prompts, fps, detecciones, duración, «hace N») | Corridas (tabla) | «—» en `var(--tx4)`; ausentes siempre al final al ordenar; nota al pie con el conteo. La fecha se recupera parseando el `run_id`. Backend: subir `hydration_limit` o paginar del lado del servidor |
| 10 | Filtrar / ordenar / paginar del lado del servidor | Corridas | Todo en cliente sobre las 95 filas; documentar el techo |
| 11 | Enum cerrado de `control` (el prototipo asume `rate_gate` / `overload`; la API emite `queue_full`) | Detalle (lista, carril, chip) | Traducir los conocidos; para uno desconocido, «descartado (`motivo`)» con el sufijo crudo en monoespaciada — nunca la cadena en inglés suelta |
| 12 | Índice de actividad de la corrida completa (base de la línea de tiempo y de los filtros de la lista) | Detalle | Reconstruir con `ceil(total/1000)` llamadas a `/trace?page_size=1000`, en una carga única en segundo plano; esqueleto mientras llega y casillas de filtro deshabilitadas. Backend: endpoint de índice |
| 13 | Eje temporal de la línea de tiempo en corridas `image_folder` | Detalle | `timestamp_ms` es null → eje por índice de cuadro y rótulo sin segundos |
| 14 | Bloque «Progreso de las condiciones» y alertas en las 75 corridas sin control-plane | Detalle | Reemplazar por `.empty` de una línea: «Esta corrida no pasó por el motor de reglas» |
| 15 | Identificador de cámara en el encabezado («Cámara cam-04») | Detalle | Mostrar la etiqueta del tipo de fuente; el `source_id` real cuesta una llamada a `/detections?page_size=1` |
| 16 | Color por clase de detección | Detalle | Paleta del cliente indexada por el orden alfabético de las clases del `prompt_set_id`, estable entre bloques |
| 17 | Estados «En curso / Completada / Fallida» (tres) | Corridas y Detalle | El vocabulario real tiene cinco: agregar chip neutral «Detenida» (`stopped`, 20 de 95) y «Con error» (`error`); el segmentado pasa a cinco opciones |

### Conteo

| Veredicto | Cantidad |
|---|---|
| **HAY** | 41 |
| **DERIVABLE** | 19 (de los cuales 5 con costo alto: sparklines, índice de traza, «última alerta hace», tamaños de artefactos, `source_id`) |
| **NO HAY** | 17 |

---

## 4. Orden de implementación sugerido para estas dos pantallas

1. **Corridas** completa: solo necesita `GET /api/runs` y el módulo de etiquetas
   (estados, tipos de fuente). Ningún cambio de backend la bloquea; lo único que
   requiere decisión es cómo se muestran las 45 filas no hidratadas.
2. **Detalle, capa barata**: encabezado, KPIs sin deltas ni sparklines, Resumen,
   Evaluación. Todo sale de `GET /api/runs/{id}` + `GET /evaluate`.
3. **Detalle, capa de traza**: índice completo → línea de tiempo, lista de cuadros con
   filtros, detalle del cuadro, card de alertas. Es el bloque caro y el que más gana si
   el backend agrega el endpoint de índice.
4. **Archivos**: depende del sondeo por `Range`; es autónomo y puede ir último.
