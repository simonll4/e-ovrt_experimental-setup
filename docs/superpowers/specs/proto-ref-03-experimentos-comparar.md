# proto-ref-03 — Nueva corrida, Experimentos, Detalle de experimento, Comparar

Análisis de referencia del prototipo del diseñador (`/home/simonll4/projects/rediseno-consola-eovrt/prototipo.html`)
cruzado contra la API real del BFF (`http://localhost:8090`, verificada el 2026-07-26 con datos reales:
95 corridas, 28 evaluadas, 10 manifiestos paraguas, 87 experimentos consolidados en disco).

Fuentes: `screenCompose()` (L865-925), `screenExps()` (L941-969), `screenExpD()` (L1243-1278),
`screenCmp()` (L1207-1234) + auxiliares `pasos()` L846, `falta()` L864, `lanzar()` L921,
`bloqueos()` L935, `kpi()` L645, `barras()` L1172, `conflicto()` L1451.
Capturas: `compose.png`, `exps.png`, `expd.png`, `cmp.png`.

Convención de clasificación por dato:
- **HAY** — campo exacto en un endpoint existente.
- **DERIVABLE** — se calcula en el cliente a partir de campos existentes (se indica cómo).
- **NO HAY** — no existe; se propone la degradación más honesta.

---

## 0. Hallazgos transversales (leer antes que nada)

1. **`/api/datasets` NO existe** (404). La ruta real es **`/api/catalog/datasets`**. Idem
   prompt-sets: existen las dos (`/api/prompt-sets` y `/api/catalog/prompt-sets`); la de
   `/api/prompt-sets` es la de gestión (POST/PUT/freeze/derive).
2. **`experiment_id` es `null` en los 10 manifiestos paraguas.** Verificado uno por uno.
   El campo existe en el schema pero nunca está poblado: el id se genera al disparar
   (`generate_experiment_id(slug, now)` → `exp_<ISO8601Z>_<slug>`) y **no se persiste de vuelta
   en el manifiesto**. Esto vacía la columna "Última ejecución" de la pantalla Experimentos.
3. **No existe endpoint de listado de ejecuciones de experimento.** `GET /api/experiments/{id}`
   lee el estado **en memoria** del `ExperimentManager` (`manager.get`) → 404 para todo experimento
   anterior al arranque del proceso BFF. Verificado: los 87 `exp_*` en disco dan 404.
   Solo `GET /api/experiments/{id}/report` funciona históricamente, porque lee
   `<repo_root>/runs/<experiment_id>/report/report.json` del disco.
4. **`GET /api/experiments/{id}/alerts` también depende del estado en memoria**
   (necesita `state["control_run_id"]`) → 404 para experimentos históricos, aunque
   `runs/<exp_id>/control/alerts.jsonl` esté en disco.
5. **El reporte NO tiene criterios ni umbrales.** `manifest.report` es `{}` en los 10 manifiestos.
   `report.resultados[]` es `{name, value, unit, status, cause}` — no hay `limite`, ni
   `cumple/no cumple`. Este es el mayor desvío del prototipo (ver §3).
6. `GET /api/runs` (lista) **no expone `experiment_id`**; sí lo expone `GET /api/runs/{id}`
   dentro de `summary.experiment_id`. Relevante para reconstruir la relación manifiesto↔ejecución.

---

## 1. Nueva corrida (`screenCompose`)

### 1.1 Composición

Layout `.compose` = grilla de dos columnas: `.steps` (izquierda, tres tarjetas numeradas) y
`.rail` (derecha, panel "Antes de lanzar" pegado arriba).

```
.crumbs  Corridas / Nueva corrida
header.rh  h1 "Nueva corrida" + .meta subtítulo
.compose
├── .steps
│   ├── .card  <h3><span class="num on">1</span>Fuente</h3>  → .srcgrid + campos condicionales
│   ├── .card  <h3><span class="num on">2</span>Qué buscar<span class="r">chip</span></h3>
│   └── .card  <h3><span class="num">3</span>Identificación</h3>  → nombre + <details class="adv">
└── .rail
    ├── .card  <h3>Antes de lanzar</h3> → 4× .chk + .launch
    ├── .banner.wn  (solo si C.err)
    └── p.note  (aviso fuentes en vivo)
```

El paso 3 **nunca** enciende su `.num` (no es una precondición, es opcional).
El paso 1 enciende con `ps[1].ok`; el 2 con `ps[2].ok && ps[3].ok` (conjunto **y** clases).

### 1.2 Bloque 1 — Fuente

```html
<div class="srcgrid">
  <button class="src" data-plugin="image_folder" aria-pressed="true">
    <b>Carpeta de imágenes</b><span>Un directorio del catálogo o una ruta del disco</span>
  </button>
  ... (4 botones; disabled si !x.on)
</div>
```

| Dato del prototipo | Estado | Origen real |
|---|---|---|
| lista de fuentes (id, label, descripción) | **HAY** | `GET /api/catalog/ingest-plugins` → `[{id, kind, available, description, enabled}]`. Los 4 ids coinciden exactamente: `image_folder`, `video_file`, `rtsp`, `oak_d`. |
| `x.d` (descripción bajo el título) | **HAY** | `description`. Ojo: la API devuelve textos más secos ("Carpeta de imágenes (datasets)"); el prototipo los reescribió en tono explicativo. **Usar el copy del prototipo, hardcodeado por `id`**, y `description` solo como fallback para plugins desconocidos. |
| `x.l` (título legible) | **DERIVABLE** | No hay campo `label`; mapear por `id` (mismo diccionario del punto anterior). |
| `x.vivo` (fuente en vivo → corrida sin fin) | **HAY** | `kind === "live"` (`rtsp`, `oak_d`) vs `"bounded"`. |
| `x.on` (habilitado) | **HAY** | `available && enabled`. En el target actual los 4 están `true` (el prototipo muestra `oak_d` deshabilitado como caso ilustrativo). |
| razón de la deshabilitación ("no tiene instalado el SDK DepthAI") | **NO HAY** | No hay campo de motivo. Degradación: título genérico `title="No disponible en el motor de detección actual"` sobre el botón deshabilitado. |

**Campos de fuente acotada** (`!p.vivo`):

| Dato | Estado | Origen |
|---|---|---|
| `DATASETS` (conjuntos del catálogo) | **HAY** | `GET /api/catalog/datasets` → `[{id, description, path, available}]`. Reales: `bench_v2_test`, `bench_v2_val`, `chv`, `demo_v2`, `video_sample`. |
| sufijo " — no montado" | **HAY** | `available === false`. |
| descripción del dataset | **HAY (no usada)** | `description` existe y es rica; **oportunidad**: mostrarla como `.hint` bajo el desplegable. |
| `C.path` (ruta manual) | **HAY** | Va a `ingest.config.path`. |

**Campos de fuente en vivo** (`p.vivo`):

| Dato | Estado | Origen |
|---|---|---|
| `C.rtsp` dirección | **HAY** | `GET /api/cameras` → `[{id, name, plugin, config:{url, fps}}]`. Hoy hay 2 (`oak_d_lab`, `rtsp_dvr_1`). |
| "No tenés cámaras guardadas para esta fuente" | **DERIVABLE** | filtrar `cameras.filter(c => c.plugin === plugin)`. **Con datos reales hay cámaras**, así que el estado vacío del prototipo no es el habitual: hay que implementar la variante *con* lista (desplegable de cámaras + opción "escribir a mano"), que el prototipo no dibuja. |
| dirección enmascarada `***` | **HAY, pero por otra vía** | `GET /api/cameras` devuelve la contraseña **en claro** (`rtsp://admin:KBXBIN@…`). El enmascarado aparece en **manifiestos guardados**. Mantener el chequeo `url.includes("***")` como validación de composición cargada desde manifiesto, no de la cámara. |
| `C.warm` (descartar primeros cuadros) | **HAY** | `ingest.config.warmup_frames` (aparece en `derive-defaults` como `warmup_frames: 20`). **Default por-run es 0** (trampa conocida, doc 69): el placeholder "20" del prototipo no es el default real. |

### 1.3 Bloque 2 — Qué buscar

```html
<div class="fld"><label>Conjunto de prompts</label> {dd("cset", …)} </div>
<div class="clsw">
  <button class="cls" data-cls="person" aria-pressed="true">person</button> …
</div>
<p class="cap">Las clases desactivadas no se buscan…</p>
```
Estado vacío: `<div class="empty" style="padding:16px 12px">Elegí un conjunto para ver sus clases.</div>`

| Dato | Estado | Origen |
|---|---|---|
| lista de conjuntos | **HAY** | `GET /api/prompt-sets` → `[{id, description, status, track, derives_from, n_classes, n_phrases}]`. Reales: `cr01_cr02_bench_v2`, `cr01_cr02_v2_safety_vest`, `cr01_cr02_v2_short`, `edir_v1`, `eind_v1`. |
| `s.cong` (congelado) | **DERIVABLE** | `status === "frozen"`. **Ojo: hay 4 estados reales**, no 2: `exploratory`, `draft`, `frozen`, `frozen_pending_review`. El chip binario Congelado/Editable del prototipo pierde `frozen_pending_review`. Degradación mínima: tres chips — `Editable` (exploratory/draft), `Pendiente de revisión` (frozen_pending_review), `Congelado` (frozen), reusando la paleta `c-nt`/`c-wn`/`c-ok`. |
| `s.cls` (clases del conjunto) | **HAY** | `GET /api/prompt-sets/{id}` → `classes: [{id, role, strategy, phrasings}]`. |
| clases activas por defecto | **PARCIAL** | `types.ts` declara `enabled_by_default`, pero la respuesta real **no lo trae**. Degradación: activar todas al elegir el conjunto (que es lo que el usuario espera y lo que hacen los manifiestos reales: `active_ids` = las 4 clases). |
| chip Congelado/Editable | ver arriba | |

### 1.4 Bloque 3 — Identificación y opciones avanzadas

| Dato | Estado | Origen |
|---|---|---|
| `C.nom` nombre de corrida | **HAY** | `run.name` (`RunParams.name`). |
| `C.stride` | **HAY** | `run.stride`. |
| `C.max` | **HAY** | `run.max_units`. |
| `C.anot` video anotado | **HAY** | `run.save_annotated_video` (default `false`). |
| `run.save_previews` | **NO EXPUESTO en el prototipo** | Existe en `RunParams` (default `true`). Dejarlo implícito en `true`. |
| Guardar como manifiesto | **HAY** | `POST /api/manifests` con `{name, group, overwrite, composition}`. **El prototipo no ofrece `group`** aunque la API lo acepta — agregarlo o mandar `null`. |
| mensaje "Guardado en experiments/X.yaml" | **DERIVABLE** | de la respuesta 201; usar el path que devuelva, no armarlo a mano. |
| `manifest_model_ref` / `confirm_target_model` | **NO EXPUESTO** | `Composition` los acepta; sirven cuando el manifiesto pide otro modelo que el cargado. El prototipo no tiene ese diálogo. **Deuda**: al cargar una composición desde manifiesto con otro `model_ref`, hoy no hay UI de confirmación. |

### 1.5 Panel "Antes de lanzar" y lógica de habilitación

```html
<div class="chk">        <!-- .chk.no cuando !ok -->
  <span class="m" style="color:var(--ok)">{check svg}</span>
  <span class="w"><b>El motor de detección está listo</b><span>owlv2-cuda · modelo cargado</span></span>
</div>
<div class="launch">
  <button class="btn pri" data-launch="1" disabled>{play}Lanzar corrida</button>
  <span class="why">Falta: elegiste un origen</span>
</div>
```

`pasos()` devuelve **exactamente 4 chequeos, en orden fijo**:

| # | Condición prototipo | `ok` | Subtexto |
|---|---|---|---|
| 1 | Motor listo | `true` (hardcodeado) | `"owlv2-cuda · modelo cargado"` |
| 2 | Origen | acotada: `!!(C.dataset \|\| C.path)`; viva: `plugin==="rtsp" && C.rtsp && !C.rtsp.includes("***")` | conjunto / ruta / motivo del faltante |
| 3 | Conjunto de prompts | `!!C.set` | "Congelado, no se puede editar" / "Editable" / "Sin elegir" |
| 4 | Al menos una clase | `C.cls.length > 0` | `"N de M activas"` |

**Regla de lanzamiento** (`falta()` + `lanzar()`):
- `falta()` = **el primer paso no-ok**; el botón se deshabilita si hay alguno y `.why` muestra
  `"Falta: " + label.toLowerCase()`. Si no falta nada: `"Todo listo. La corrida arranca en cuanto confirmes."`
- `lanzar()` corta dos veces: (a) `if (falta()) return;` (b) si hay corrida activa,
  setea `C.err` con el banner "Ya hay una corrida activa (run_…)…" y **no navega**.
- El error de concurrencia se muestra como `.banner.wn` **debajo** de la tarjeta, no como modal.

Cruce con la API:

| Chequeo | Estado | Origen real |
|---|---|---|
| paso 1 — motor listo | **HAY** | `GET /api/preflight` → `media.ready`, `media.healthy`. Subtexto: `media.model.ref` + `media.model.device` → hoy `"grounding-dino/gdino-tiny-560 · cuda"`. **El paso 1 debe poder fallar** (el prototipo lo tiene siempre en `true`): si `!media.ready`, `.chk.no` con subtexto `blockers[0]`. |
| paso 2 — origen | **DERIVABLE** | estado local del formulario; el server revalida en `POST /api/compose/validate` (mismo validador que `POST /api/runs`, `errors: [{field, message}]`). |
| paso 3 / 4 | **DERIVABLE** | estado local. |
| corrida activa bloqueante | **HAY** | `GET /api/runs` → alguna con `status === "running"` (hoy: 0; estados reales observados `succeeded` 75 / `stopped` 20). Autoridad final: `POST /api/runs` → **409** con `{detail, active_run_id}`. |
| motor de reglas caído | **HAY (no usado acá)** | `preflight.control.healthy/ready`. El prototipo **no** lo chequea en Nueva corrida (solo en Experimentos), lo cual es correcto: una corrida de solo media no lo necesita. |

**Validación server-side sin equivalente en el prototipo**: `validate_composition` produce errores por
campo (`ingest.plugin` no soportado / no disponible, `ingest.config.url` faltante o sin `rtsp://`,
`_target` servicio inaccesible). El prototipo solo tiene la lista de 4 chequeos. Degradación:
mapear `errors[].field` al paso correspondiente y pintar ese `.chk` en rojo con `message` como subtexto;
`_target` va al paso 1.

---

## 2. Experimentos (`screenExps`)

### 2.1 Composición

```
.crumbs  Trabajo / Experimentos   [+ .protoc conmutador — SOLO PROTOTIPO, no implementar]
header.rh  h1 "Experimentos" + "N manifiestos versionados en el repositorio"
[.banner.er  si S.err]
.pad (flex column, gap 12)
├── .card  <h3>Antes de ejecutar<span class="r">1 bloqueo</span></h3>  → N× .blk
├── .toolbar  → .search (#qsearch) + <span class="cnt">5 de 5</span>
└── .card > .tw > table  (7 columnas)
```

### 2.2 Bloque "Antes de ejecutar"

```html
<div class="blk">
  <span style="color:var(--wn);flex:none;margin-top:1px">{warn}</span>
  <span><b style="font-weight:400;color:var(--tx)">Hay una corrida en curso</b><br>
        <span style="font-size:10.5px;color:var(--tx4)">run_… está usando el motor de detección</span></span>
</div>
```
Estado feliz: un solo `.blk` con check verde y "Los dos motores responden y no hay nada ocupando el modelo…".
El `<span class="r">` del header cuenta bloqueos (`"1 bloqueo"` / `"N bloqueos"` / `"Todo listo"`).

| Bloqueo prototipo | Estado | Origen |
|---|---|---|
| "Hay una corrida en curso" | **DERIVABLE** | `GET /api/runs` con `status === "running"` (o `GET /api/experiments/current` ≠ 404). Subtexto = `run_id`. |
| "El motor de reglas no responde" | **HAY** | `preflight.control.healthy === false` (o `.ready === false`). |
| bloqueos adicionales | **HAY** | `preflight.blockers: string[]` — es la lista canónica del servidor. **Preferirla**: renderizar un `.blk` por cada `blocker`, más el de corrida activa. Hoy `ready: true, blockers: []`. |
| experimento ya en curso | **HAY** | `GET /api/experiments/current` → 200 con `{experiment_id, status}` o 404 "No hay experimento activo". Es un 5º bloqueo que el prototipo no contempla; el server lo aplica igual (409 `ExperimentBusy`). |

### 2.3 Tabla de manifiestos

Columnas: `Manifiesto | Grupo | Última ejecución | Estado | Corridas (n) | Cuándo | (acciones)`.
Fila clicable solo si `x.ult` (`<tr class="rw" data-expd="…">`); sin ejecución, el slug va en
`<span class="mono" style="color:var(--tx3)" title="Todavía no se ejecutó…">`.

```html
<td class="act">
  <button class="btn gh" data-expdup="perimetro_nocturno_v3">Partir de este</button>
  <button class="btn" data-explaunch="perimetro_nocturno_v3" disabled>Ejecutar</button>
</td>
```

| Columna | Estado | Origen |
|---|---|---|
| **Manifiesto** (slug) | **HAY** | `GET /api/experiments/manifests` → `slug`. 10 reales: `diag_riesgo_activo`, `ebe_oakd_live`, `ebe_p1/p2/p3_live`, `rt-01`, `video16_clip10_gt`, `yoloe_p1/p2/p3_live`. |
| **Grupo** | **NO HAY** | El listado devuelve solo `{slug, experiment_id, sequencing, runs}`; `GET /api/experiments/manifests/{slug}` tampoco trae `group`. (`/api/catalog/experiments` sí tiene `group`, pero es **otro catálogo** — configs de corrida sueltas tipo `bench_v2/b2_g_e1_gdino_t_val` — no los manifiestos paraguas.) **Degradación**: reemplazar la columna Grupo por **Linaje**, mostrando `derives_from` (que sí existe y está poblado en 6 de 10: `ebe_p1_live → ebe_oakd_live`, `yoloe_p1_live → ebe_p1_live`, …). Conserva la intención —agrupar manifiestos emparentados— con un dato real, y encima habilita ordenar por familia. |
| **Última ejecución** | **NO HAY** | `experiment_id` es `null` en los 10. No existe endpoint que liste ejecuciones pasadas por slug. **Degradación en dos niveles**: (a) *mínima*: eliminar la columna y las de Estado/Corridas/Cuándo, dejando la tabla como catálogo puro (Manifiesto · Linaje · Secuenciación · acciones) — honesto y barato; (b) *preferible*: derivar en el cliente con `GET /api/runs` + `GET /api/runs/{id}` (`summary.experiment_id`, formato `exp_<ts>Z_<slug>`) y agrupar por sufijo de slug — cuesta N+1 llamadas sobre 95 corridas, así que solo vale si se agrega antes un campo `experiment_id` a `RunSummary` en el BFF (cambio de una línea, recomendado). |
| **Estado** (Completado / Fallido / Sin ejecutar) | **NO HAY** | Depende de "última ejecución". Además `GET /api/experiments/{id}` (que sí tiene `status: succeeded\|failed\|running`) solo responde para experimentos vivos en memoria. **Degradación**: derivar de la existencia de `report.json` — si `GET /api/experiments/{id}/report` responde 200, el experimento terminó y consolidó; si no, "sin reporte". Es un estado más pobre pero verdadero. |
| **Corridas** (n) | **DERIVABLE (parcial)** | El prototipo cuenta ejecuciones del manifiesto. Lo único trivialmente disponible es `manifests[].runs` → `["control","media"]`, que es **cuántos planos participan**, no cuántas veces se corrió. **No reusar el número**: renombrar la columna a **Planos** (`media+control`) o eliminarla. |
| **Cuándo** (`hace(min)`) | **NO HAY** | Idem "última ejecución". Con la derivación (b) sale de `run.started_at`. |
| `sequencing` | **HAY, no usado** | `control_first` / `media_first`. Vale una columna: explica el orden de arranque (bus PUB/SUB) y hoy no se ve en ningún lado. |
| `clip_id`, `ground_truth` | **HAY, no usados** | Poblados en `video16_clip10_gt`. Útiles como chip "con GT" — que además es la precondición de que el reporte traiga métricas temporales (§3). |

### 2.4 Interacciones

| Acción | Prototipo | API real |
|---|---|---|
| clic en fila / slug (`data-expd`) | `S.screen = "expd"` | navegar a `/experiments/{experiment_id}`; **requiere** resolver el id (ver arriba). |
| **Ejecutar** (`data-explaunch`) | deshabilitado si `bloqueos().length`; en el prototipo solo muestra un banner | **HAY**: `POST /api/experiments/run` con el manifiesto/slug → **202** `{experiment_id}`. Errores reales a manejar: **503** `{detail:"Plataforma no lista: …", preflight}` (gate de preflight sincrónico) y **409** `{detail, active_experiment_id}`. El deshabilitado del cliente es cortesía; **la autoridad es el 503/409**, así que el banner de error debe renderizar `detail` del server, no un texto local. |
| **Partir de este** (`data-expdup`) | navega a `screenCompose` | **Diverge de la API real.** La derivación de manifiestos paraguas es una operación propia: `GET /api/experiments/manifests/{slug}/derive-defaults` → `{warmup_frames, fps, camera_id, prompt_set_id, stride, max_units, pattern_set_file, pattern_active_ids}` y luego `POST /api/experiments/manifests/{slug}/derive` con `{new_slug, overrides, changes}` → 201. **No pasa por Nueva corrida** y toca los dos planos (media+control), cosa que `screenCompose` no modela (no tiene pattern set). **Degradación**: "Partir de este" abre un diálogo propio precargado con `derive-defaults` (slug nuevo + overrides de cámara/prompt-set/warmup/fps + nota `changes`), no la pantalla de Nueva corrida. |
| búsqueda `#qsearch` | filtra por `slug + grupo` | filtrar por `slug + derives_from` (sin grupo). |
| conmutador `.protoc` | artefacto del prototipo | **no implementar**. |

---

## 3. Detalle de experimento (`screenExpD`)

### 3.1 Composición

```
.crumbs  Experimentos / exp_20260725_1120
header.rh  h1 slug + .meta (chip resultado · id mono · hace) + .acts (Ver la corrida | Descargar reporte)
.kpihd  "Resultado frente a los criterios definidos en el manifiesto"
.kpis   3× kpi()
.pad
├── .card  Criterios del experimento   (tabla 5 col)
├── .card  Alertas emitidas <span class="r">3</span>  (tabla 5 col)
└── .card  Trazabilidad  (<dl class="kv">)
```

### 3.2 Cabecera y KPIs

`kpi({l, dot, v, u, col, meter|segs, mcol, sub})` renderiza `.kpi > .l / .vr > .v > small / .foot > .mtr + .sub`.

| Dato | Estado | Origen |
|---|---|---|
| título = slug del manifiesto | **DERIVABLE** | sufijo de `experiment_id` (`exp_<ts>Z_<slug>`), o del manifiesto si se navegó desde él. |
| chip "N criterios sin cumplir" / "Todos cumplen" | **NO HAY** | No existe noción de cumplimiento (§0.5). |
| `exp_…` id | **HAY** | `report.identificacion.experiment_id`. |
| "hace 3 h" | **HAY** | `report.identificacion.fecha_inicio` / `fecha_fin` (ISO con tz). |
| KPI 1 "Criterios cumplidos 2 de 3" | **NO HAY** | Ver §3.3. **Degradación**: **"Métricas calculadas — N de M"**, con `N = resultados.filter(status==="computed").length` y `M = resultados.filter(status!=="not_applicable").length`. Medidor con el mismo porcentaje. Subtexto: la primera métrica `applicable_not_computed` ("`t_compute-budget` no se pudo calcular: `missing_join_key`"). |
| KPI 2 "Alertas emitidas 3 en total" | **HAY** | `report.eventos.alerts_count` (real: 2 en `exp_20260718T175011Z_video16_clip10_gt`). |
| desglose "1 alta · 1 media · 1 baja" + `segs` tricolor | **PARCIAL** | El reporte solo trae el total. El desglose por severidad exige `/{id}/alerts`, que **404 para experimentos históricos** (§0.4). **Degradación**: si `/alerts` responde, `segs` reales por severidad (`high/medium/low` → `--er/--sr/--wn`); si 404, un único segmento neutro y subtexto `"N alertas · desglose no disponible"`. |
| KPI 3 "Sin poder medir 1 de 4" | **DERIVABLE** | `resultados.filter(m => m.status === "not_applicable").length` sobre `resultados.length` (23 métricas reales, no 4). Subtexto: la `cause` más frecuente traducida (`no_ground_truth`, `non_temporal_source`, `no_distribution`, `dbe_media_time`, `missing_join_key`). |
| "El conjunto no es temporal…" | **HAY** | `report.non_temporal` (lo agrega el BFF) + `report.temporalidad.criterio_relojes`, que ya viene redactado en prosa —**usarlo tal cual como subtexto**, es exactamente el registro de voz del prototipo. |
| botón "Ver la corrida" | **HAY** | `report.identificacion.media_run_id` → `/runs/{id}`. Puede ser `null` (fixtures de gate). |
| botón "Descargar reporte" | **NO HAY** | Existe `runs/<exp>/report/report.md` en disco pero **ninguna ruta lo sirve** (`/api/runs/{id}/artifacts/…` es de corridas de media, no de experimentos). **Degradación**: descargar en el cliente el JSON de `GET /{id}/report` como `report.json` (Blob), y anotar como deuda un `GET /api/experiments/{id}/report.md`. |

### 3.3 Tabla "Criterios del experimento" — el desvío grande

Prototipo: `Criterio | Medido | Límite | Resultado | Por qué`, con `stChip`: `Cumple` (c-ok) /
`No cumple` (c-er) / `Sin dato` (c-nt).

Realidad (`report.resultados[]`, 23 entradas, verificado sobre los 87 reportes en disco):

```json
{"name": "SDR", "value": 0.997206, "unit": "ratio", "status": "computed", "cause": null}
{"name": "mAP", "value": null, "unit": "ratio", "status": "not_applicable", "cause": "no_ground_truth"}
```

- `name` ∈ {`G2A`, `t_alert-system`, `t_capture->alert`, `t_compute-budget`, `t_alert-notification`,
  `TTFD`, `SDR`, `TTFA interna`, `ΔFP_tracker`, `latencia_media_p50/p95/p99_ms`, `fps_efectivo`,
  `drops_media`, `latencia_control_avg_ms`, `bus_dropped_events`, `latencia_control_p50/p95/p99_ms`,
  `mAP`, `AP por clase`, `recall CR-01`, `re_alerts`}
- `status` ∈ {`computed`, `applicable_not_computed`, `not_applicable`, `not_interpretable`}
- `cause` ∈ {`null`, `no_ground_truth`, `non_temporal_source`, `missing_join_key`,
  `no_distribution`, `dbe_media_time`}

| Columna | Estado | Resolución |
|---|---|---|
| Criterio | **HAY** | `name`. Necesita un diccionario `name → etiqueta en castellano` (el registro del prototipo: "Latencia de alerta", "Exhaustividad CR-01"). Sin él la tabla queda en jerga. |
| Medido | **HAY** | `value` + `unit` (`ms`→`s` con 1 decimal si >1000; `ratio`→3 decimales con coma; `count`/`fps` tal cual). `—` si `null`. |
| **Límite** | **NO HAY** | `manifest.report` es `{}` en los 10 manifiestos; el reporte no persiste umbrales. **Degradación**: eliminar la columna y reemplazarla por **Unidad** (`unit`, que sí existe y es lo que el operador necesita para leer el número). |
| **Resultado** (Cumple/No cumple) | **NO HAY** | **Degradación**: chip de **estado de medición**, no de juicio: `Medido` (c-ok, `computed`), `No calculado` (c-wn, `applicable_not_computed`), `No aplica` (c-nt, `not_applicable`), `No interpretable` (c-wn, `not_interpretable`). Preserva la intención del diseño —tres tonos, chip con icono, lectura de un golpe— sin inventar un veredicto que el sistema no emite. |
| Por qué | **HAY** | `cause` traducida: `no_ground_truth` → "No hay ground truth anotado para este experimento"; `non_temporal_source` → "La fuente no es temporal: no hay secuencia sobre la que medir"; `missing_join_key` → "Faltó la clave de correlación entre los dos planos"; `no_distribution` → "No hubo distribución de notificaciones"; `dbe_media_time` → "El reloj es de medio (tiempo de video), no de pared". `—` si `null`. |
| ordenar la tabla | — | Recomendado: `computed` primero, luego `applicable_not_computed`, luego `not_applicable`. Con 23 filas (vs 4 del prototipo) hace falta: colapsar `not_applicable` bajo un `<details>` "N métricas que no aplican". |

**Bloque nuevo sugerido** (dato valioso que el prototipo no dibuja porque no lo conocía):
`report.eventos.hitos` = `{primera_evidencia, patron_confirmado, alerta_registrada, notificacion_entregada}`
booleanos. Es la **cadena de evidencia** de la tesis, y se renderiza natural como cuatro `.chk`
en el `.rail` — mismo componente del panel "Antes de lanzar". También `report.anti_drift`
(`{media:{checked, reason}, control:{…}}`) y `report.observaciones: string[]`.

### 3.4 Tabla "Alertas emitidas"

```html
<tr><td class="mono">alr_0001</td>
    <td><span class="mono" style="color:var(--tx)">CR-01</span> · Presencia de persona</td>
    <td><span class="chip c-er">Alta</span></td>
    <td class="n">41,2 s</td>
    <td class="act"><button class="btn gh" data-run="run_…">Ver el cuadro</button></td></tr>
```

| Dato | Estado | Origen |
|---|---|---|
| lista de alertas | **PARCIAL** | `GET /api/experiments/{id}/alerts` proxya el control-plane vía `state["control_run_id"]` → **solo para el experimento vivo**; 404 histórico. Los datos existen en `runs/<exp>/control/alerts.jsonl` (schema `control.alert.v1`). **Degradación**: si 404, tarjeta con `report.eventos.alerts_count` y el texto "El detalle de las alertas no está disponible para experimentos ya cerrados"; **deuda a abrir**: que `/alerts` caiga a leer `alerts.jsonl` del consolidado cuando no haya estado en memoria (es simétrico a lo que ya hace `/report`). |
| `alert_id` | **HAY** | `alert_id` (UUID real, no `alr_0001`; la celda `.mono` va a necesitar truncado + `title`). |
| `condition_id` (CR-01/CR-02) | **HAY** | `condition_id` / `pattern_id`. |
| nombre legible de la condición | **DERIVABLE** | El `COND` del prototipo ("Presencia de persona", "Permanencia en zona") **no corresponde** a CR-01/CR-02 reales, que son **"Persona sin casco"** y **"Persona sin chaleco"**. Corregir el diccionario. |
| severidad | **HAY** | `severity` — valores reales `high`/`medium`/`low` (no `alta`/`media`/`baja`). Mapear. |
| momento | **HAY** | `timestamp_ms` (real: `4000.0`). También `frame_index`, `first_evidence_ms`, `alert_registered_ms`. |
| "Ver el cuadro" | **DERIVABLE** | `unit_id` (`frame_000120`) o `frame_index` + `report.identificacion.media_run_id` → deep-link a la traza de la corrida en ese cuadro. |
| campos ricos no usados | **HAY** | `evidence.rationale` ("No se encontró evidencia 'helmet' en región 'upper_body' de 4 sujeto(s)"), `evidence.missing_class`, `evidence.subject.bbox_xyxy`, `subjects_in_evidence`. La `rationale` es el "por qué" de la alerta en prosa: candidata natural a fila expandible. |

### 3.5 Trazabilidad

`<dl class="kv">` con tres pares. Todos **HAY** desde `report.identificacion`:
`media_run_id`, `control_run_id`, y el manifiesto (**DERIVABLE**: sufijo del `experiment_id`).
Agregables sin costo: `clip_id`, `ground_truth_path`, `report.modelo.{model_name, prompt_set_id,
pattern_set_id, active_pattern_ids}`, `report.hardware_entorno.{device, gpu_memory_peak_mb, topology}`,
`report.entrada.{source_type, source_count, scenario}`.

---

## 4. Comparar (`screenCmp`)

### 4.1 Composición

Layout `.two`: columna izquierda fija (selector) + columna derecha (resultado o vacío).

```
.crumbs  Trabajo / Comparar
header.rh  h1 "Comparar corridas" + "Solo se comparan corridas ya evaluadas contra un conjunto anotado"
.two
├── .card  <h3>Corridas evaluadas<span class="r">2 de 4 elegidas</span></h3>
│          N× <label class="pick"> + p.cap
└── div
    ├── (sel<2)  .card > .bigempty  "Elegí al menos dos corridas"
    └── (sel>=2) flex column gap 12
        ├── [.banner.wn  conflicto de conjuntos]
        ├── .card  Métricas  (tabla, celda ganadora .n.best)
        └── .card  Precisión por clase  (.leg + barras() SVG)
```

### 4.2 Selector de corridas

```html
<label class="pick">
  <input type="checkbox" data-cmp="run_20260725_121840" checked>
  <span class="w"><b>Barrido diurno</b><span>owlv2-base-patch16 · seguridad / nocturno · hace 2 h</span></span>
</label>
```

| Dato | Estado | Origen |
|---|---|---|
| universo = corridas **evaluadas** | **HAY** | `GET /api/runs` → filtrar `evaluated === true`. Reales: **28 de 95**. |
| `r.lb` (nombre legible) | **DERIVABLE** | `run.name ?? run.run_id`. Ojo: en 6 de las 28 evaluadas `name` es `null` → fallback al id en `.mono`, más angosto que el `<b>` del prototipo. |
| `r.mo` (modelo) | **HAY** | `run.model` (`yoloe`, `grounding_dino`). |
| `r.sp` (conjunto anotado) | **PARCIAL** | `run.bench_split` — distribución real: `bench_v2_val` 10, `bench_v2_test` 12, **`null` 6**. Para los `null` mostrar `"conjunto sin identificar"` en `--tx4`, no ocultarlos. |
| "hace 2 h" | **HAY** | `run.started_at`. |
| tope de selección | **HAY (server)** | `MAX_COMPARE_RUNS = 8` → 422 si se excede. El prototipo no lo contempla: deshabilitar checkboxes al llegar a 8 con `.cap` explicativo. La paleta `SERIE` solo tiene 4 colores (`SERIE[i%4]`) → **con 5-8 corridas se repiten**; agregar 4 colores o limitar a 4 en la UI. |
| `p.cap` "Las corridas sin evaluación no aparecen acá…" | **HAY** | verdadero: se evalúa con `POST /api/runs/{id}/evaluate`. |

### 4.3 Interacciones

- **Selección**: `S.cmp` es un array de ids; el `change` en `[data-cmp]` hace concat/filter y
  re-renderiza (`L1622-1623`). Sin límite en el prototipo.
- **Umbral de 2**: con `sel.length < 2` se muestra `.bigempty` ("Elegí al menos dos corridas /
  La comparación necesita dos o más corridas evaluadas sobre el mismo conjunto…"). Mantener.
- **Aviso de conflicto**: `sel.some(r => r.sp !== sel[0].sp)` → `.banner.wn` con
  "Estás comparando corridas de **conjuntos distintos**. Los números no son directamente
  comparables entre sí." **Implementable tal cual** con `bench_split`, con una salvedad: si algún
  `bench_split` es `null`, el aviso debe dispararse igual (desconocido ≠ igual) y el texto sumar
  "…o de conjunto desconocido". Verificado contra la API: `/api/compare` con un `bench_v2_val` y
  un `bench_v2_test` responde **200 sin advertir nada** — el conflicto es responsabilidad del cliente.
- **Cambio de selección** dispara `GET /api/compare?runs=id1,id2,…` (coma-separado, dedupe y
  descarte de vacíos en el server).

### 4.4 Tabla de métricas y gráfico — cruce con `/api/compare`

Respuesta real verificada:

```json
{"runs":[{"run_id":"…","label":"grounding_dino · bench_v2_val","model":"grounding_dino",
          "bench_split":"bench_v2_val","mAP50":0.0273,"cr01_detection_recall":0.2}, …],
 "classes":["person","helmet","vest","bare_head"],
 "ap_by_class":{"person":[0.0909,0.0101],"helmet":[0,0],"vest":[0,0],"bare_head":[0.0182,0]},
 "skipped":[]}
```

| Dato del prototipo | Estado | Origen |
|---|---|---|
| filas `Precisión · <clase>` | **HAY** | `classes[]` × `ap_by_class[clase][i]`. **Las clases reales son `person`, `helmet`, `vest`, `bare_head`** (4), no `person/vehicle/backpack` (3) del prototipo: `CLASES` deja de ser constante y viene de la respuesta. El SVG de `barras()` calcula `gw = pw/CLASES.length` → soporta N clases sin tocarlo. |
| fila `Exhaustividad CR-01` | **HAY** | `runs[i].cr01_detection_recall`. Frecuentemente `null` o `0` — la fila debe tolerar `—`. |
| fila `Precisión media (mAP)` | **HAY** | `runs[i].mAP50`. **Puede ser `null`** aun con evaluación válida (verificado: dos runs yoloe con `per_class` completo y `mAP50: null`). Ya está contemplado (`v == null ? "—"`). |
| encabezado por corrida | **HAY** | `runs[i].label`, ya formateado `"<model> · <bench_split>"`. Degrada a `"<run_id> · ?"` cuando el eval no trae `model`/`bench_split` (caso real y frecuente). **Preferir el label local** del selector (`name ?? run_id`) para la cabecera, y dejar el `label` del server como `title`. |
| mejor valor por fila (`.n.best`, verde) | **DERIVABLE** | `max` ignorando `null`. Ya implementado en `cuerpo`. **Bug a no replicar**: `barras()` usa `r.ap[c] == null ? 0 : …`, o sea pinta una barra de 0 y una etiqueta "0,00" para una clase sin GT — indistinguible de "midió 0". Con datos reales (`vest: [0.2434, null]`) esto miente. Corregir: `null` → sin barra y etiqueta `—` en `--tx4`. |
| `skipped[]` | **NO EXISTE EN EL PROTOTIPO** | La API devuelve los ids que no pudo resolver (`UnknownRun`). **Agregar** un `.banner.wn` "N corridas no se pudieron incluir: …". |
| leyenda `.leg` + `SERIE` | **HAY** | ver límite de 4 colores en §4.2. |
| filas de latencia/fps para comparar | **NO HAY en `/compare`** | `/api/compare` es solo percepción (BENCH). Los datos de rendimiento están en `GET /api/runs` (`fps_effective`, `duration_seconds`, `total_detections`). **Oportunidad barata**: agregar esas 3 filas a la tabla desde el listado que ya se tiene en memoria, marcadas visualmente como "no BENCH". |

---

## 5. Tabla resumen — datos NO HAY y degradación propuesta

| # | Pantalla | Dato del prototipo | Por qué no hay | Degradación propuesta |
|---|---|---|---|---|
| 1 | Nueva corrida | Motivo de fuente deshabilitada ("no tiene el SDK DepthAI") | `ingest-plugins` no trae razón | Botón `disabled` con `title` genérico "No disponible en el motor de detección actual" |
| 2 | Nueva corrida | Clases activas por defecto (`enabled_by_default`) | Declarado en `types.ts`, ausente en la respuesta | Activar todas las clases al elegir el conjunto |
| 3 | Nueva corrida | Chip binario Congelado/Editable | Hay 4 estados reales (`exploratory`, `draft`, `frozen`, `frozen_pending_review`) | Tres chips: Editable / Pendiente de revisión / Congelado |
| 4 | Experimentos | **Columna Grupo** | `manifests` devuelve solo `slug, experiment_id, sequencing, runs` | Reemplazar por **Linaje** (`derives_from`, poblado en 6/10) |
| 5 | Experimentos | **Última ejecución** (`exp_…`) | `experiment_id` siempre `null`; no hay endpoint de ejecuciones por slug | (a) quitar la columna → catálogo puro; (b) preferible: exponer `experiment_id` en `RunSummary` (1 línea en el BFF) y agrupar por sufijo de slug |
| 6 | Experimentos | **Estado** Completado/Fallido/Sin ejecutar | `GET /api/experiments/{id}` es estado en memoria (404 histórico) | Derivar de la existencia de `report.json` (200/404 en `/report`): "Con reporte" / "Sin reporte" |
| 7 | Experimentos | **Corridas (n)** = veces ejecutado | `manifests[].runs` es la lista de planos, no un contador | Renombrar a **Planos** (`media+control`) o eliminar |
| 8 | Experimentos | **Cuándo** (`hace N`) | Depende de #5 | Cae con #5; con la derivación (b) sale de `run.started_at` |
| 9 | Experimentos | "Partir de este" → Nueva corrida | La derivación es de manifiesto paraguas (dos planos), no de composición de media | Diálogo propio precargado con `GET …/derive-defaults` → `POST …/derive` |
| 10 | Detalle exp. | **Columna Límite** | `manifest.report == {}`; el reporte no persiste umbrales | Reemplazar por **Unidad** (`unit`) |
| 11 | Detalle exp. | **Resultado Cumple / No cumple** | El sistema no emite veredictos, emite `status` de medición | Chips de estado de medición: Medido / No calculado / No aplica / No interpretable |
| 12 | Detalle exp. | KPI "Criterios cumplidos N de M" | Idem #11 | KPI **"Métricas calculadas N de M"** (`computed` / `!= not_applicable`) |
| 13 | Detalle exp. | Desglose de alertas por severidad | `/alerts` requiere estado en memoria → 404 histórico | Si 404: total desde `report.eventos.alerts_count`, medidor neutro, "desglose no disponible". Deuda: que `/alerts` lea `alerts.jsonl` del consolidado |
| 14 | Detalle exp. | Tabla de alertas completa | Idem #13 | Tarjeta con el conteo + aviso; deuda igual que #13 |
| 15 | Detalle exp. | Botón "Descargar reporte" (.md) | `report.md` está en disco pero ninguna ruta lo sirve | Descargar el JSON de `/report` como Blob; deuda: `GET /api/experiments/{id}/report.md` |
| 16 | Detalle exp. | Nombres de condición ("Presencia de persona") | Las condiciones reales son CR-01 = sin casco, CR-02 = sin chaleco | Corregir el diccionario `COND` |
| 17 | Comparar | Nombre legible de corrida | `run.name` es `null` en 6 de las 28 evaluadas | Fallback a `run_id` en `.mono` |
| 18 | Comparar | Conjunto anotado por corrida | `bench_split` es `null` en 6 de las 28 | Mostrar "conjunto sin identificar"; **disparar igual** el aviso de conflicto |
| 19 | Comparar | Métricas de rendimiento comparadas | `/api/compare` es solo percepción BENCH | Agregar filas `fps_effective` / `duration_seconds` / `total_detections` desde `GET /api/runs`, marcadas como "no BENCH" |
| 20 | Comparar | (falta en el prototipo) `skipped[]` | — | Agregar `.banner.wn` con los ids no incluidos |
| 21 | Transversal | Paleta `SERIE` de 4 colores con tope de 8 corridas | `MAX_COMPARE_RUNS = 8` | Agregar 4 colores o limitar la selección a 4 |

### Deudas de backend que valdría abrir (baratas, desbloquean lo de arriba)

1. `RunSummary` + `summary.experiment_id` en `GET /api/runs` → desbloquea #5, #6, #8.
2. `GET /api/experiments/{id}/alerts` con fallback a `runs/<id>/control/alerts.jsonl`
   (simétrico a lo que ya hace `/report`) → desbloquea #13, #14.
3. `GET /api/experiments/{id}/report.md` → desbloquea #15.
4. `group` (o al menos `description`) en `ExperimentManifestSummary` → desbloquea #4 con el
   diseño original.
