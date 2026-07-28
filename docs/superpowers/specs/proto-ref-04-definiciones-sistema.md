# proto-ref-04 — Definiciones y Sistema: Conjuntos de prompts, Catálogos, Plataforma, Cámaras, Clips

Análisis de las cinco pantallas de los grupos **Definiciones** y **Sistema** del prototipo
(`rediseno-consola-eovrt/prototipo.html`), cruzado contra la API real del BFF verificada en
vivo sobre `http://localhost:8090` el **2026-07-26**.

Fuentes:

- Prototipo: `screenPsets()` (l. 1348), `editorPsets()` (1311), `abrirEditor()` (1294),
  `nuevoConjunto()` (1298), `errEditor()` (1301), `screenCat()` (1385), `screenPlatform()`
  (1422), `screenCams()` (1058), `camViewer()` (1040), `camConectar()` (1100),
  `panelGrabacion()` (1025), `estadoGrabacion()` (999), `grabarIniciar()` (979),
  `grabarDetener()` (993), `screenClips()` (1118).
- Tipos: `webconsole/frontend/src/types.ts` (worktree `rediseno-fundacion-corridas`).
- Backend: `webconsole/backend/src/eovrt_webconsole/` (`prompt_store.py`,
  `routers/platform.py`, `routers/recordings.py`, `clips/inventory.py`, `clips/clip_yaml.py`).
- Capturas: `proto-ref/{psets,cat,platform,cams,clips}.png`.

**Corrección de rutas respecto del encargo.** Los endpoints reales no son los enunciados;
`/api/instances`, `/api/datasets` y `/api/masters` devuelven **404**. Los verdaderos son:

| Enunciado | Real | Estado verificado |
|---|---|---|
| `GET /api/instances` | `GET /api/platform/instances` | **501** (ver §3) |
| `GET /api/datasets` | `GET /api/catalog/datasets` | 200, 5 filas |
| `GET /api/masters` | `GET /api/clips/masters` | 200, 30+ masters |
| `GET /api/prompt-sets` | igual | 200, 5 sets |
| `GET /api/cameras` | igual | 200, 2 presets |
| `GET /api/preview` | igual | 200, `status: "idle"` |
| `GET /api/clips` | igual | 200, 16 clips |
| `GET /api/target` | igual | 200 |

Convención de este documento: **HAY** = campo exacto de la API; **DERIVABLE** = se calcula
en el cliente o con un fan-out de llamadas ya disponibles; **NO HAY** = requiere cambio de
backend, y se propone la degradación más honesta.

---

## 0. Dos hallazgos que condicionan el resto

### 0.1 Las frases POR BACKEND existen de verdad — la pregunta abierta del README se responde: NO

El README dice que el editor asume que "en la práctica solo se usa `default`". **Es falso.**
Barrido de los 5 conjuntos del repositorio (`GET /api/prompt-sets/{id}` uno por uno):

| Conjunto | `status` | Claves de `phrasings` | Clases | Frases/clase |
|---|---|---|---|---|
| `cr01_cr02_bench_v2` | `exploratory` | `default` | 4 | 1 |
| `cr01_cr02_v2_safety_vest` | `draft` | `default` | 3 | 1 |
| `cr01_cr02_v2_short` | `frozen` | `default` | 3 | 1 |
| `edir_v1` | `frozen_pending_review` | `default` | 8 | 1 |
| **`eind_v1`** | `frozen_pending_review` | **`default`, `gdino`, `yoloe`** | 3 | **3 (una por clave)** |

`eind_v1` es la pista doble GDINO-tiny / YOLOE-26s de la enmienda doc 12 §3 y guarda,
literalmente:

```json
{"id":"helmet","role":"ppe","strategy":"canonical_positive","condition_id":"CR-01",
 "phrasings":{"default":["helmet"],"gdino":["helmet"],"yoloe":["helmet"]}}
```

Consecuencias, en orden de gravedad:

1. **El editor de una sola lista SÍ esconde información.** Para `eind_v1` mostraría 3 frases
   por clase sin decir que son tres *claves distintas* con el mismo valor. Hoy los valores
   coinciden, así que no se pierde semántica al *leer*; pero la estructura es real y es
   deliberada (aísla el A/B por backend).
2. **Un guardado ingenuo destruye datos.** Si el editor lee `phrasings` aplanado y escribe
   `{"default": [...]}`, borra `gdino` y `yoloe`. Hoy `eind_v1` está protegido por accidente
   (`update_set` rechaza todo lo que no sea `exploratory`, `prompt_store.py:201`), pero
   **cualquier conjunto derivado de él nace `exploratory` con las tres claves** —
   `derive_set` copia el bloque `classes` tal cual — y ahí el editor sí lo puede aplastar.
3. El contador "N frases" del listado (`n_phrases` de `list_sets`) **suma todas las claves**:
   `eind_v1` reporta `n_phrases: 9` para 3 clases. Un editor que muestre 9 frases planas
   sobre 3 clases y luego guarde 3 pierde 6 sin avisar.

**Decisión propuesta (bloqueante antes de implementar el editor):** el editor muestra por
defecto la lista de `phrasings.default`, pero:

- si el conjunto tiene **más de una clave**, muestra un selector de backend por clase
  (`default` / `gdino` / `yoloe` / …) y una banda informativa "Este conjunto define frases
  distintas por detector";
- si tiene **una sola clave** (`default`), se comporta exactamente como el prototipo — el
  desglose no aparece y el diseño se preserva intacto para el 80 % de los casos;
- el guardado hace **merge sobre las claves no editadas**, nunca reemplazo del dict.

Corolario para el bloque "Clases y frases" (solo lectura): la vista `<div class="phr">`
debe renderizar `phrasings.default`, y agregar un chip discreto `+2 detectores` cuando haya
más claves. Nunca concatenar todas las claves en una sola línea de `«…» · «…»`.

### 0.2 `status` real es un vocabulario de 3 valores… y el disco tiene un cuarto

`prompt_store.Status = Literal["exploratory", "frozen_pending_review", "frozen"]`. El
prototipo usa `PST = {exploratory, pending, frozen}` — el mapeo es 1:1 salvo el nombre
(`pending` ↔ `frozen_pending_review`).

Pero `cr01_cr02_v2_safety_vest` está en disco con **`status: "draft"`**, que no pertenece al
Literal. `list_sets()` y `get_set()` leen el YAML **crudo, sin validar**, así que el valor
sale a la API tal cual. Un `PST[x.st]` sin defensa **rompe la pantalla con un `undefined`**.

Y peor: un conjunto en `draft` es **inoperable** — `update_set`, `delete_set` y
`request_freeze` exigen `== "exploratory"` y devuelven 409. La UI tiene que poder explicar
por qué no hay ninguna acción disponible.

**Degradación:** mapa de estados con `default` explícito → chip `c-nt` con el valor crudo en
monoespaciada y el texto "Estado no reconocido", y el bloque de acciones reemplazado por una
nota: "Este conjunto tiene un estado fuera del ciclo (`draft`). No se puede editar, congelar
ni eliminar desde la consola; corregí el `status` en el YAML."

---

## 1. Conjuntos de prompts (`screenPsets`)

### 1.1 Composición

Migas `Definiciones / Conjuntos de prompts` → `header.rh` con `h1` + `.meta` de una línea y
`.acts` con **Nuevo conjunto** (`btn pri`, `data-enew`) → banner de error opcional
(`.banner wn`, `S.err`) → layout **`.two`** (dos columnas):

- **Izquierda:** una sola tarjeta `Conjuntos` con el contador en `<span class="r">`.
- **Derecha:** columna `flex` con `gap:12px` que es **excluyente**: o bien el editor
  (`editorPsets()`, si `E.on`), o bien las tres tarjetas de detalle: *ciclo de vida*,
  *Clases y frases*, y *Origen* (esta última solo si `s.de`).

La captura confirma: izquierda angosta con 3 filas seleccionables, derecha con la tarjeta de
ciclo (título = id en mono + chip de estado a la derecha), la tira de pasos, el párrafo
explicativo y la fila de botones; luego la tabla de clases; luego Origen.

### 1.2 Bloques

**Lista de conjuntos.** `<div class="card"><h3>Conjuntos<span class="r">N</span></h3>` +
por fila `<button class="lrow" data-pset="{id}" aria-current="{bool}">` con
`<span class="w"><b>{id}</b><span>{track} · {n} clases · {m} frases</span></span>` y
`<span class="chip {tono}">{etiqueta de estado}</span>`.

| Dato | Cruce |
|---|---|
| `{id}` | **HAY** — `PromptSetSummary.id` |
| `{track}` (proto: "Perímetro") | **HAY** con salvedad — `track` es `"core" \| "demo" \| null`, no un nombre de escenario. Etiquetar `core` → "Núcleo", `demo` → "Demostración", `null` → omitir el segmento |
| `{n} clases` | **HAY** — `n_classes` |
| `{m} frases` | **HAY** — `n_phrases`, **pero suma todas las claves de backend** (§0.1) |
| chip de estado | **HAY** — `status`, con el default defensivo de §0.2 |
| contador `N` | **HAY** — largo del array |

**Ciclo de vida.** `<h3><span class="mono">{id}</span><span class="r"><span class="chip …">`
+ `<div class="flow">` con tres `<span class="fstep {done|on|''}">` separados por
`<span class="farrow">→</span>` + `<p class="cap">{explicación}</p>` + `.fld` en fila con
los botones según estado.

Los tres pasos y las transiciones **calzan exactamente** con `prompt_store`:

| Estado | Acciones del prototipo | Endpoint real |
|---|---|---|
| `exploratory` | Editar clases y frases / Congelar el conjunto / Eliminar | `PUT /api/prompt-sets/{id}` · `POST .../freeze-request` · `DELETE .../{id}` — **HAY los tres** |
| `frozen_pending_review` | Confirmar el congelado / **Volver a exploración** | `POST .../freeze` — HAY. **"Volver a exploración" NO HAY**: no existe endpoint inverso |
| `frozen` | Derivar uno nuevo | `POST .../derive` con `{new_id, changes}` — **HAY** |

**"Volver a exploración" es el único agujero de acción de la pantalla.** Degradación honesta:
quitar el botón y reemplazar el texto explicativo por "Ya no se puede editar. Revisá las
frases y confirmá el congelado. Si algo está mal, hay que corregir el YAML a mano o derivar
un conjunto nuevo." — es exactamente lo que hoy puede hacer el usuario, sin prometer de más.
Si se quiere el botón, cuesta ~10 líneas de backend (`POST .../unfreeze-request`, válido
solo desde `frozen_pending_review`).

Nota de flujo: `derive` **abre un formulario**, no es un click seco — `new_id` y `changes`
son obligatorios en `DeriveBody`. El prototipo no lo contempla; hace falta un modal o una
sección con dos campos (identificador nuevo + descripción del cambio), con la misma
validación de id que `errEditor` (`^[a-z0-9_]+$`, `_SET_ID_RE`).

**Clases y frases.** `<h3>Clases y frases<span class="r">{n} clases · {m} frases</span></h3>`
+ por clase `<div class="phr"><b>{id}</b><span>«f1» · «f2»</span></div>` + `<p class="cap">`
con el aviso de editable / solo lectura.

| Dato | Cruce |
|---|---|
| id de clase | **HAY** — `PromptClassSpec.id` |
| frases | **HAY** — `phrasings.default`; ver §0.1 para el resto de las claves |
| `role`, `strategy`, `condition_id` | **HAY y el prototipo los ignora**. Son datos valiosos: `edir_v1` distingue `direct_absence` / `observable_state` / `presence_template` y ata clases a `CR-01`/`CR-02`. Recomendación: agregar a `.phr` una segunda línea con `{strategy}` y, si existe, el chip `CR-01 — …` |
| `enabled_by_default` | **HAY** — `cr01_template` de `edir_v1` lo trae en `false` (clase diagnóstica apagada). El prototipo no lo muestra: una clase apagada se ve idéntica a una activa. Degradación mínima: atenuar la fila y agregar el texto "no activa por defecto" |

**Origen.** `<div class="card"><h3>Origen</h3><dl class="kv">` con `Deriva de` y `Cambios`.

| Dato | Cruce |
|---|---|
| Deriva de | **HAY** — `derives_from` (poblado en `cr01_cr02_v2_safety_vest` y `eind_v1`) |
| Cambios = "2 clases nuevas, 4 frases" | **DERIVABLE, no HAY como tal.** `changes` existe pero es **prosa libre** (`edir_v1`: "Primera versión. Fuente literal: tabla…"). El diff estructurado del prototipo se calcula en el cliente pidiendo `GET /api/prompt-sets/{derives_from}` y comparando `classes`/`phrasings` |

Propuesta: mostrar **las dos cosas** — `Cambios` con el texto declarado por el autor (que es
el registro de intención y es lo que el proyecto valora), y debajo el diff calculado
("2 clases nuevas · 4 frases · 1 frase modificada") como dato derivado. Resuelve el punto 10
del README **sin tocar el backend**.

### 1.3 El editor (`editorPsets`)

Estructura: `card` → `h3` ("Nuevo conjunto" | "Editando `{id}`") → `.esec` "Datos del
conjunto" → `.fld` Identificador (`input.inp`, `.bad` si vacío, `disabled` si no es nuevo) →
`.fld` Descripción (`textarea.inp`) → `.esec` "Clases" con contador → N × `.eclase`
{`.eclh` cabecera con "Quitar", `.clshd` grid con Identificador + desplegable Estrategia,
`hint` solo en la primera, bloque Frases con `.frwrap` de `.frchip` + `input.frnew`} →
botón "Agregar otra clase" → `.esec` de validación (verde "Listo para guardar" / ámbar con
el error de `errEditor`) → `.fld` con `btn pri` (Crear/Guardar) + `btn gh` Cancelar.

Cruce campo por campo:

| Campo del editor | Cruce |
|---|---|
| Identificador de conjunto | **HAY** — `id`. La regla del prototipo (inmutable si no es nuevo) es correcta: `update_set` exige `payload.id == set_id` |
| Descripción | **HAY** — `description` |
| Identificador de clase | **HAY** — `PromptClassSpec.id` |
| Estrategia (`ESTRAT`: `""`, `canonical_positive`, `observable_state`) | **HAY pero INCOMPLETA.** `STRATEGY_VALUES` tiene **cinco**: `canonical_positive`, `syntactic_negation`, `specificity`, `observable_state`, `presence_template`. `edir_v1` usa `direct_absence`… que **no está en el frozenset** — o sea que `edir_v1` no pasaría `_validate` hoy. El desplegable debe traer las 5 y tolerar un valor desconocido leído del YAML (opción extra deshabilitada con su motivo, que el componente `dd()` ya soporta) |
| Frases (`.frwrap` + `.frnew`) | **HAY con la reserva de §0.1**: es `phrasings.default`, y hace falta el selector de backend cuando haya más claves |
| `role`, `condition_id`, `canonical`, `enabled_by_default` | **HAY en el modelo y AUSENTES en el editor.** Un guardado desde el editor del prototipo los borraría. **El editor debe preservarlos** (merge, no reemplazo) aunque no los exponga; exponer al menos `condition_id` y `enabled_by_default` es barato y evita que el usuario tenga que ir al YAML |
| Validaciones de `errEditor` | **HAY equivalentes en backend**: id vacío / duplicado (`PromptSetExists`, 409), sin clases y clase sin frases (`PromptSetInvalid`, 422). El id además debe cumplir `^[a-z0-9_]+$` — validación que `errEditor` **no** hace y hay que agregar, o el usuario recibe un 422 después de escribir todo |
| `track` (`core`/`demo`) y `language` | **HAY en el modelo, no en el editor.** Un conjunto creado desde la consola nace sin `track`, y el listado muestra el segmento vacío. Agregar los dos campos al bloque "Datos del conjunto" |

**Regla que el prototipo ya respeta y hay que conservar:** el editor solo se abre desde el
estado `exploratory`. El backend lo hace cumplir con 409, así que la UI no es la única
defensa — pero el botón debe seguir sin aparecer en los otros estados.

---

## 2. Catálogos (`screenCat`)

### 2.1 Composición

Migas `Definiciones / Catálogos` → header sin acciones → `.pad` en columna con **cuatro
bloques en este orden**: tarjeta destacada `.tgt` "Modelo en uso"; tabla "Orígenes de
imágenes"; tabla "Conjuntos de imágenes"; tabla "Conjuntos de prompts". Sin columnas: ancho
completo. Es una pantalla de solo lectura, y la captura lo confirma (no hay un solo botón).

### 2.2 Bloques

**Modelo en uso** — `<div class="tgt">` con `.lbl` "Modelo en uso", `.nm` con el ref, y una
fila separada por `border-top` con cuatro celdas (Adaptador / Dispositivo / Confianza mínima
/ Solapamiento máximo), más `<p class="cap">` de cierre.

Fuente: `GET /api/target` → `{service_url, healthy, ready, model:{ref, name, adapter, device,
thresholds:{box,text,confidence,iou}, runtime:{half_precision,warmup}}}`.

| Dato | Cruce |
|---|---|
| Nombre grande (`owlv2-base-patch16`) | **HAY** — `model.ref` (valor real hoy: `grounding-dino/gdino-tiny-560`). El ref lleva `/`; el `.nm` tiene que tolerar la barra sin cortar |
| Adaptador | **HAY** — `model.adapter` (`grounding_dino`) |
| Dispositivo (`cuda:0`) | **HAY parcialmente** — `model.device` = `"cuda"`, **sin índice**. Degradación: mostrar `cuda` a secas; no inventar el `:0` |
| Confianza mínima | **HAY, con ambigüedad** — hay tres umbrales candidatos (`box: 0.3`, `text: 0.25`, `confidence: 0.25`). Degradación: mostrar los **tres** rotulados (Caja / Texto / Confianza), no elegir uno arbitrariamente |
| Solapamiento máximo | **HAY** — `thresholds.iou` (0.5) |
| `runtime` (`half_precision`, `warmup`) | **HAY y sin usar.** Cabe como dos celdas más o como pie del bloque |

**Orígenes de imágenes** — `card` + `h3` con contador "N de M disponibles" + `.tw > table`,
columnas Origen / Tipo / Disponibilidad / Por qué.

Fuente: `GET /api/catalog/ingest-plugins` → `[{id, kind, available, description, enabled}]`.
Hoy los 4 (`image_folder`, `video_file`, `rtsp`, `oak_d`) vienen `available:true,
enabled:true`.

| Columna | Cruce |
|---|---|
| Origen (etiqueta legible) | **HAY** — `description` ("Carpeta de imágenes (datasets)"). El `id` va aparte, en mono |
| Tipo "En vivo"/"Acotado" | **HAY** — `kind` = `live` \| `bounded`, mapeo 1:1 |
| Disponibilidad | **HAY** — `available` (y `enabled`, que hoy es redundante; si divergen, `available` es capacidad y `enabled` es política — mostrar "No disponible" vs "Deshabilitado") |
| **Por qué** ("El motor de detección no tiene instalado el SDK DepthAI") | **NO HAY** — es el punto 6 del README. `available` es un booleano pelado |

Degradación para "Por qué": con `available:true` la celda muestra `description` (que es
justamente lo que el prototipo pone: "Un video acotado, se procesa de principio a fin"). Con
`available:false`, texto genérico **sin inventar la causa**: "No disponible en el motor de
detección activo" + el `id` del plugin en mono, para que el operador pueda buscarlo. Nunca
escribir "falta el SDK DepthAI" mientras el backend no lo diga.

**Conjuntos de imágenes** — misma estructura, columnas Conjunto / Disponibilidad / Por qué.
Fuente `GET /api/catalog/datasets` → `[{id, description, path, available}]` (5 filas hoy,
todas `available:true`).

| Columna | Cruce |
|---|---|
| Conjunto | **HAY** — `id` en mono |
| Disponibilidad "Montado"/"Sin montar" | **HAY** — `available` |
| **Por qué** ("El directorio no está accesible…") | **NO HAY como texto, pero hay algo mejor: `path`.** Degradación: mostrar siempre el `path` en mono (`../e-ovrt_datasets/datasets/raw/chv/...`) y, si `available:false`, prefijarlo con "No accesible:". Es más accionable que la frase genérica del prototipo |
| `description` | **HAY y sin usar** — la fila gana mucho con ella; el prototipo la desaprovecha |

**Conjuntos de prompts** — tabla Conjunto / Estado / Clases / Clases que define.

| Columna | Cruce |
|---|---|
| Conjunto, Estado, Clases | **HAY** — `id`, `status`, `n_classes` desde el listado |
| **Clases que define** (`person, vehicle, …`) | **DERIVABLE** — el resumen no trae los ids de clase; hace falta `GET /api/prompt-sets/{id}` por fila (5 llamadas hoy). Aceptable y en paralelo. Alternativa sin fan-out: dejar la columna con `n_classes` y `track` |

---

## 3. Plataforma (`screenPlatform`)

### 3.1 Verificación de `/api/platform/instances`: **501 en este entorno**

```
GET /api/platform/instances → 501
{"detail":"Orquestación no habilitada (definí EOVRT_CONSOLE_COMPOSE_DIR)"}
```

No es un error transitorio: `routers/platform.py::_manager()` levanta 501 cuando
`app.state.target_manager` es `None`, lo que ocurre siempre que no esté definida
`EOVRT_CONSOLE_COMPOSE_DIR`. **Las tres rutas del grupo caen igual**: `GET /instances`,
`POST /instances/{name}/activate`, `POST /platform/stop`.

**Qué implica para la pantalla, sin ambigüedad:** en el despliegue de un solo equipo — el
que se está usando hoy y el del rodaje — **la tabla "Instancias del servicio" no tiene datos
y el botón "Apagar" no tiene a quién apagar**. La mitad inferior de la captura es, en este
entorno, aire.

Y no se puede ni siquiera conocer la forma de la respuesta: como el manager no existe, no
hay schema en el OpenAPI (`GET /instances` está declarado como `list[dict]` sin modelo). O
sea que **los campos de cada instancia son desconocidos**: `name`, `model`, `activa` del
prototipo son una apuesta, no un contrato.

**Degradación propuesta (la más honesta que preserva la intención):** la pantalla se
construye en **dos mitades con destinos distintos**.

- La mitad de arriba (instancia activa + salud de los planos) se alimenta de `/api/target` y
  `/api/preflight`, que **funcionan siempre**. Esta mitad es la que da valor real hoy.
- La mitad de abajo (tabla de instancias) se pide una vez y, ante **501**, se reemplaza por
  un estado vacío explicativo dentro de la misma tarjeta:
  `<div class="card"><h3>Instancias del servicio</h3><div class="bigempty">` con el título
  "La orquestación no está habilitada" y el texto "Esta consola apunta a un motor de
  detección fijo (`{service_url}`). El cambio de instancia requiere el despliegue de dos
  equipos. Para usar otro modelo, reiniciá el motor con otro `EOVRT_MODEL_REF`."
  **Un 501 no es un error rojo**: es una capacidad ausente y se comunica como tal (chip
  `c-nt`, nunca `c-er`).
- El botón **Apagar** del bloque hero se oculta con el mismo criterio (depende de
  `POST /api/platform/stop`, igual de 501).

Distinguir **501** (capacidad ausente, estado vacío) de **502/504** (`ComposeError` /
`SwitchFailed`, que sí son fallas y van en banner rojo) es obligatorio: son ramas distintas
del mismo router.

### 3.2 Composición y bloques

Migas `Sistema / Plataforma` (sin `header.rh`: la pantalla arranca directo en `.pad`) →
banner de error opcional → `.hero` en dos columnas {`.tgt` instancia activa | `.planes`} →
tarjeta "Instancias del servicio" → `<p class="note">` de cierre.

**Hero — instancia activa** (`.tgt`): `.lbl` "Instancia activa", `.nm` con el nombre, fila de
chips (Operativa + "1 corrida en curso" + ref del modelo en mono), y fila de métricas
separada por `border-top` con Encendida hace / Memoria de GPU / Corridas hoy + botón
`btn dg` **Apagar** empujado con `margin-left:auto`.

| Dato | Cruce |
|---|---|
| Nombre de la instancia (`owlv2-cuda`) | **NO HAY** sin orquestación. Degradación: usar `target.service_url` (`http://localhost:8080`) como identidad, rotulada "Motor de detección activo" en vez de "Instancia activa" |
| Chip "Operativa" | **HAY** — `preflight.media.healthy && .ready` (hoy ambos `true`) |
| Chip "1 corrida en curso" | **DERIVABLE** — `GET /api/runs` filtrando por estado activo, o `GET /api/experiments/current`. Sin dato → omitir el chip, no mostrar "0 corridas" |
| Ref del modelo | **HAY** — `target.model.ref` |
| **Encendida hace 2 h 14 m** | **NO HAY** — no hay uptime en ningún endpoint. Degradación: reemplazar la celda por **Adaptador** (`model.adapter`), que sí existe y ocupa el mismo lugar |
| **Memoria de GPU 6 142 MB** | **NO HAY** — `model.runtime` solo trae `half_precision` y `warmup`. Degradación: reemplazar por **Dispositivo** (`model.device`) + **Precisión** (`half_precision ? "media" : "completa"`). Es honesto y sigue hablando de la GPU |
| **Corridas hoy: 14** | **DERIVABLE** — contar `GET /api/runs` con `started_at` del día. `RunRow.started_at` existe |
| Botón **Apagar** | **NO HAY** en este entorno (501). Ocultar, §3.1 |

**Planes** (`.planes` con dos `.plane`): chip de estado + `.w` con nombre y `host:puerto`.

| Dato | Cruce |
|---|---|
| Motor de detección + `localhost:8080` | **HAY** — `preflight.media.service_url` + `healthy`/`ready` |
| Motor de reglas + `localhost:8081` | **HAY** — `preflight.control.service_url` + `healthy`/`ready` |
| Banda de degradación cuando cae el control | **HAY** — se dispara con `!control.healthy`. El texto del prototipo ("la correlación queda en `sin dato` y no se confirman alertas") es correcto y se conserva |
| Botón "Simular caída" | Instrumento del prototipo, **no se implementa** |
| `preflight.blockers` | **HAY y sin usar en esta pantalla** — array de bloqueos. Encaja como lista dentro de la banda |

**Tabla de instancias**: ver §3.1. Si algún día responde, las columnas Instancia / Modelo /
Estado / Acción y el 409 `PlatformBusy` (que ya devuelve `{detail, run_id}`) cubren
exactamente el mensaje de `conflicto()` del prototipo — **ese texto sí sale del backend**,
con el `run_id` incluido. Buen detalle a preservar.

---

## 4. Cámaras (`screenCams`)

### 4.1 Composición

Migas `Sistema / Cámaras` → header con `h1`, `.meta` y `.acts` (botón **Agregar cámara**,
solo si ya hay cámaras y el formulario está cerrado) → banner `K.err` → **dos ramas**:

- **Sin cámaras y sin formulario** → `.pad > .card > .bigempty` con el icono SVG de cámara,
  título, párrafo y botón "Agregar la primera cámara". **Es lo que muestra la captura**
  (`CAMS = []` en el prototipo).
- **Con cámaras** → `.two`: columna izquierda con {formulario si `K.form`, tarjeta "Cámaras
  guardadas", **panel de grabación**} y columna derecha con {`camViewer()`, tarjeta "Qué
  mostrar"}.

Es la pantalla más densa de las cinco: tres bloques a la izquierda, dos a la derecha, y el
visor manda el alto.

### 4.2 Bloques

**Cámaras guardadas** — `.card` + filas `.lrow` (no botón: es un `div`, la acción está en
`.ac`) con `<b>{nombre}</b><span>{RTSP|OAK-D} · {dirección}</span>` y dos botones: "Probar" /
"Desconectar" (`data-camconn` / `data-camdis`) + eliminar (`data-camdel`).

Fuente `GET /api/cameras` → `[{id, name, plugin, config}]`. Hoy: `oak_d_lab`
(`plugin:"oak_d"`, `config:{url:"169.254.31.137", fps:30}`) y `rtsp_dvr_1`
(`plugin:"rtsp"`, `config:{url:"rtsp://admin:KBXBIN@169.254.31.140:554/..."}`).

| Dato | Cruce |
|---|---|
| Nombre | **HAY** — `name` |
| Tipo RTSP / OAK-D | **HAY** — `plugin` (`rtsp` \| `oak_d`), mismos dos valores del prototipo |
| Dirección | **HAY** — `config.url`. Ojo: el modelo real es `plugin` + `config` **dict**, no `tipo` + `dir` string; `oak_d` además trae `fps`, que el prototipo no contempla |
| `id` | **HAY y ausente del prototipo** — es la clave para `PUT`/`DELETE` y para `StartRecordingBody.camera_id`; conviene mostrarlo en mono bajo el nombre |

**Fuga de credenciales — corregir el texto del prototipo.** El formulario promete: "El
usuario y la clave se guardan ocultos en los manifiestos". `GET /api/cameras` devuelve
**`rtsp://admin:KBXBIN@…` en claro** (verificado en esta corrida). La función
`redact_rtsp_credentials` existe, pero protege el sidecar de grabación y los `detail` de
error 422 — **no el listado**. La UI no debe afirmar algo falso: o el BFF redacta en el
listado (cambio chico, la función ya está), o el `hint` pasa a decir "La contraseña queda
guardada en el preset y `cameras/` está fuera del control de versiones". Anotado también en
`CLAUDE.md` del repo (`cameras/` gitignorado por credenciales en claro).

**Formulario de cámara** — `card` + `.fld` Nombre + `.fld` Tipo (`.seg` de dos botones) +
`.fld` Dirección (etiqueta, placeholder y `hint` cambian según el tipo) + `.fld` en fila con
Guardar (deshabilitado si falta nombre o dirección) y Cancelar.
Endpoints: `POST /api/cameras`, `PUT /api/cameras/{id}`, `DELETE /api/cameras/{id}` — **HAY
los tres**. El único ajuste: el campo Dirección alimenta `config.url`, y para `oak_d` hace
falta además `config.fps` (hoy 30 en el preset real) → agregar un campo numérico opcional
visible solo con OAK-D.

**Visor** (`camViewer`) — `.viewer` > `.vh` (chip `c-live` con `.pulse` "Conectada", nombre en
mono, "9,8 cuadros/s", botón Desconectar a la derecha) + `.stage` con el SVG y las cajas.

| Dato | Cruce |
|---|---|
| Estado conectado / desconectado | **HAY** — `GET /api/preview` → `{status:'idle'\|'streaming'\|'error', preview_id, mode, error}` (hoy `idle`). El estado `error` del contrato **no existe en el prototipo** y hay que agregarlo: `.stage` con el texto de `error` |
| Imagen y cajas | **HAY** — WS `previewStreamUrl()` (`/api/preview/stream`) con `PreviewFrameHeader {seq, ts, width, height, mode, detections[{label, score, bbox_norm_xyxy}]}`. El SVG sintético del prototipo se reemplaza por el frame real; el `bbox_norm_xyxy` normalizado calza con el dibujo por porcentajes |
| **"9,8 cuadros/s"** | **DERIVABLE** — no viene como campo; se calcula con la media móvil de `Δseq/Δts` sobre los últimos N headers |
| Nombre de la cámara conectada | **DERIVABLE** — la consola sabe qué preset lanzó; `PreviewStatus` solo trae `preview_id` |
| Segmento "Imagen directa / Con detecciones" | **HAY** — `PreviewStartBody.mode: 'raw'\|'detect'`; `PreviewStatus.mode` lo refleja |
| Umbral "Confianza mínima" | **HAY** — `PreviewStartBody.params.score_threshold`. Cambiarlo exige `DELETE` + `POST` (reiniciar la vista previa): el slider debe aplicar con debounce o con un botón, no en cada `input` |
| Chips de clase (`LAB` = person/vehicle/backpack) | **NO HAY como catálogo global.** Las clases salen del conjunto de prompts que se pasa en `prompts.set_inline` al arrancar la vista previa. Degradación: la tarjeta "Qué mostrar" incorpora un selector de conjunto de prompts (`GET /api/prompt-sets`) y los chips se generan de las clases de ese conjunto — más fiel al sistema real que una lista fija |
| `camConectar` bloquea si hay corrida en curso | **HAY** — es la misma exclusión que el backend aplica en grabación (`check_media_plane_free`, 409). Un `POST /api/preview` con el motor ocupado falla; el chequeo previo evita el error feo |

### 4.3 Panel de grabación (`panelGrabacion` + `estadoGrabacion`)

`.card` con `h3` "Grabar una toma" (+ `<span class="r">Grabando</span>` en rojo cuando
`R.st==="rec"`) → banner `R.err` → si no hay cámaras, `.empty` → si las hay: desplegable
Cámara, fila de dos desplegables (Escenario `P1..P8` / Variante `a|b|c`), `hint` con el
nombre de la próxima toma en mono, y `estadoGrabacion()`.

**Máquina de estados del prototipo:** `idle` → `starting` (1,6 s simulados; aviso ámbar "no
cortes todavía" + Cancelar) → `rec` (banda roja con `.recdot`, `{s} s · {MB}`, botón
`btn dg` Detener, y aviso si `secs < 30`) → vuelta a `idle` con la tarjeta verde "Última
toma".

**Contrato real:** `RecordingStatus.state: 'idle' | 'starting' | 'recording' | 'finished' |
'error'`, con `basename, elapsed_ms, size_bytes, duration_ms, fps, resolution, truncated,
suspected_substream, error`. Endpoints `GET/POST/DELETE /api/recordings` y
`GET /api/recordings/next?scenario=&variant=`.

| Dato / estado | Cruce |
|---|---|
| `idle` / `starting` / `rec` | **HAY** — `rec` es `recording`. El comentario del tipo confirma la razón del estado `starting`: "la OAK-D PoE tarda ~9 s en conectar" — el prototipo simula 1,6 s; en la UI real el aviso debe aguantar ~10 s sin parecer colgado |
| **`finished`** | **NO HAY en el prototipo.** El proto salta de `rec` a `idle` y sintetiza `R.last`. Real: `finished` **es un estado del backend** con `basename/duration_ms/size_bytes/fps/resolution`. Se implementa como la tarjeta verde "Última toma" pero leída del estado, no inventada |
| **`error`** | **NO HAY en el prototipo.** Hay que agregarlo: banda roja con `status.error`. Trampa conocida del rodaje: "el error de OAK-D tapa la causa" — mostrar el `error` crudo en mono, sin reformular |
| Tiempo transcurrido | **HAY** — `elapsed_ms` (el prototipo cuenta con `setInterval` propio: usar el del backend como verdad y el timer solo para interpolar) |
| Tamaño en MB | **HAY** — `size_bytes` (el prototipo lo inventa: `secs*2.1`) |
| Nombre de la próxima toma | **HAY** — `GET /api/recordings/next?scenario=&variant=` → `{basename}`. Verificado: sin los dos parámetros devuelve 422 |
| Escenarios `P1..P8` y variantes `a/b/c` | **NO HAY catálogo** — no hay endpoint que los liste. Degradación: mantener la lista fija en el frontend (coincide con el guion de campo, doc 69) y dejar que el 422 de `InvalidTakeId` sea la validación final |
| **Mínimo de 30 s (`MINTOMA`)** | **NO HAY en el backend** — `StartRecordingBody` solo tiene `max_duration_s`. Es una **regla de producto del frontend**: se conserva tal cual (aviso, no bloqueo — el prototipo acierta al dejar cortar igual) |
| Exclusión "probar" vs "grabar" | **HAY, y del lado del servidor**: `POST /api/recordings` llama `check_media_plane_free` y devuelve **409** "el media-plane está ocupado por {ocupante}: grabar y correr son secuenciales". El chequeo optimista del prototipo (`if(K.conn) …`) se conserva como cortesía, y el 409 se muestra tal cual |
| **`truncated` y `suspected_substream`** | **HAY y el prototipo los ignora.** Son señales de calidad de la toma; `suspected_substream` significa que se grabó el substream de baja resolución. Deben aparecer como chips ámbar en la tarjeta de "Última toma": una toma en substream no sirve para el rodaje y descubrirlo tarde cuesta una escena |
| `camera_id` en el arranque | **HAY** — `StartRecordingBody.camera_id`; el router resuelve el preset y rellena `plugin`/`config`/`label` |
| Cancelar durante `starting` / Detener | **HAY** — `DELETE /api/recordings` |

---

## 5. Clips (`screenClips`)

### 5.1 Composición

Migas `Sistema / Clips` → header con `h1` y `.meta` ("N materiales · M clips recortados") →
`.toolbar` con `.search` (`#qsearch`) y `.cnt` a la derecha → `.two` (`padding-top:11px`):
columna izquierda con **dos tarjetas apiladas** (Materiales, Clips), columna derecha con un
**panel contextual de tres caras**.

El panel derecho depende de `L.panel`:

1. `{k:"trim"}` → tarjeta **Recortar** (reproductor del master + Desde/Hasta/Nombre + Cortar).
2. `{k:"clip"}` → tarjeta **Clip** (reproductor + `dl.kv` + Usar en una corrida / Descargar).
3. `null` → `.bigempty` "Elegí un material o un clip".

La captura muestra la tercera. El buscador filtra las dos listas a la vez (`m.n + escenario +
clips` para masters; `c.id` para clips) — puramente cliente, correcto para 30 masters + 16
clips.

### 5.2 Bloques

**Materiales** — `.card` + `h3` "Materiales <span class="r">N de M</span>" + filas
`<button class="lrow" data-master="{n}" aria-current disabled?>` con
`<b>{nombre}</b><span>{escenario|Sin escenario} · {duración} · {N clips|sin clips}</span>` y,
si es ilegible, `<span class="chip c-er">Ilegible</span>` + `disabled`.

Fuente `GET /api/clips/masters` → `{masters:[{name, scenario, size_bytes, duration_ms,
readable, clips[]}]}`. Datos reales: mezcla de `1.1.mp4` (lote de internet, `scenario:null`)
y `P1-a-take2.mp4` (rodaje, `scenario:"P1"`).

| Dato | Cruce |
|---|---|
| Nombre | **HAY** — `name` |
| Escenario | **HAY** — `scenario` (nulo en el lote de internet: el fallback "Sin escenario" del prototipo es exactamente lo que hace falta) |
| Duración | **HAY** — `duration_ms` |
| N clips | **HAY** — `clips[]` (ids de los clips derivados) |
| Chip "Ilegible" + fila deshabilitada | **HAY** — `readable:false` |
| `size_bytes` | **HAY y sin usar** — vale la pena: hay masters de 6 MB junto a otros de 923 MB, y esa diferencia es la señal de substream |

**Clips** — misma estructura; filas `<button class="lrow" data-clip="{id}">` con
`<b>{clip_id}</b><span>{duración} · desde {inicio}</span>`.

Fuente `GET /api/clips` → `{clips:[{clip_id, fps, duration_ms, n_frames, resolution,
has_yaml, master, warnings}]}`.

| Dato | Cruce |
|---|---|
| `clip_id` | **HAY** |
| Duración | **HAY** — `duration_ms` |
| **"desde 41,2 s"** (offset dentro del master) | **NO HAY** — `ClipEntry` no expone el inicio. Existe en disco: `clip_yaml.write_clip_yaml` guarda `episode_draft.onset_ms` / `end_ms`, y `inventory.list_clips` **ya abre ese YAML** pero solo levanta `master` y `warnings`. Es el cambio de backend más barato de todo este documento: dos claves más en el dict. Degradación mientras tanto: reemplazar "desde X s" por `{resolution} · {fps} fps`, que sí está |
| `has_yaml` | **HAY y sin usar** — un clip sin YAML no tiene GT ni master asociado (`a_p1_c01`, `ensayo-g2-tomaA`). Merece chip ámbar "sin metadatos" |
| `warnings[]` | **HAY y sin usar** — vienen de `episode_draft.warnings` del recorte. Deben mostrarse en el panel de detalle |
| `master` | **HAY** — con prefijo `raw/` (`"raw/1.1.mp4"`); hay que quitarlo para cruzar con `MasterEntry.name` |

**Panel Recortar** — `h3` "Recortar <span class="r mono">{master}</span>" + contenedor
16:9 del reproductor + `.fld` en fila con Desde (s) / Hasta (s) + `.fld` Nombre del clip +
`.fld` con **Cortar clip** (deshabilitado sin nombre) y un `hint` que calcula la duración en
vivo.

| Dato | Cruce |
|---|---|
| Reproductor del master | **HAY** — `GET /api/clips/media/master/{name}`; el placeholder gris pasa a ser un `<video>` real |
| Desde / Hasta / Nombre → Cortar | **HAY, 1:1** — `POST /api/clips` con `GenerateClipBody {master, t_event_s, t_end_s, scenario?, clip_id?}`. Los nombres de campo del prototipo calzan exactamente |
| Campo `scenario` | **HAY en el body y ausente del formulario.** Si el master trae `scenario`, precargarlo; si es `null` (lote de internet), pedirlo |
| Respuesta del corte | **HAY y el prototipo no la contempla**: `GenerateClipResult {clip_id, info{fps,duration_ms,n_frames,resolution}, warnings, regenerated, invalidated}`. **`regenerated`** (se rehizo un clip existente) y **`invalidated`** (lista de artefactos que quedaron obsoletos) exigen UI: confirmación previa si el `clip_id` ya existe, y aviso posterior con lo invalidado. Ignorarlos es pisar GT en silencio |
| Marcado de tiempos por campo de texto | Funciona, pero el reproductor real permite botones "marcar desde el cuadro actual". Mejora natural, no un dato faltante |

**Panel Clip** — `h3` "Clip <span class="r mono">{id}</span>" + reproductor +
`<dl class="kv">` con Material / Desde / Hasta / Duración + `.fld` con "Usar en una corrida"
(`data-screen="compose"`) y "Descargar".

| Dato | Cruce |
|---|---|
| Reproductor | **HAY** — `GET /api/clips/media/clip/{clip_id}` |
| Material | **HAY** — `master` (sin el `raw/`) |
| **Desde / Hasta** | **NO HAY** — mismo hueco que arriba. Degradación: sustituir esas dos filas por Resolución / Cuadros por segundo / Cuadros (`resolution`, `fps`, `n_frames`), que sí existen y describen mejor el clip |
| Duración | **HAY** — `duration_ms` |
| Descargar | **HAY** — el mismo endpoint de media sirve la descarga |
| Usar en una corrida | **HAY** — el clip es fuente `video_file`; el `clip_id` viaja a Nueva corrida |
| Eliminar clip | **NO HAY** — no existe `DELETE /api/clips/{id}`. No agregar el botón |

---

## 6. Tabla resumen — datos NO HAY y degradación propuesta

| # | Pantalla | Dato del prototipo | Por qué no hay | Degradación propuesta |
|---|---|---|---|---|
| 1 | Prompts | Editor de **una sola lista** de frases | El modelo es `phrasings: {backend: [...]}` y **`eind_v1` usa `default`+`gdino`+`yoloe`** | Editor de una lista cuando hay una sola clave; selector de backend por clase cuando hay más. **Guardado con merge, nunca reemplazo del dict** |
| 2 | Prompts | Botón **"Volver a exploración"** | No existe endpoint inverso a `freeze-request` | Quitar el botón; el texto explica que hay que corregir el YAML o derivar. (Backend: `POST .../unfreeze-request`, ~10 líneas) |
| 3 | Prompts | Estado `draft` en el vocabulario | `Status` es un Literal de 3 y el YAML no se valida al leer | Mapa con `default`: chip `c-nt` + valor crudo en mono + nota "estado fuera del ciclo, sin acciones disponibles" |
| 4 | Prompts | "Cambios: 2 clases nuevas, 4 frases" | `changes` es prosa libre, no un diff | Mostrar `changes` tal cual **y** el diff calculado contra `derives_from` (fan-out de 1 llamada) |
| 5 | Prompts | Estrategias del desplegable (3) | `STRATEGY_VALUES` tiene 5, y `edir_v1` usa `direct_absence`, que no está en ninguna | Desplegable con las 5 + opción extra deshabilitada con motivo para valores desconocidos leídos del YAML |
| 6 | Catálogos | **"Por qué" de un origen no disponible** | `available` es booleano pelado (punto 6 del README) | Con `available:true` → `description`. Con `false` → "No disponible en el motor de detección activo" + `id` en mono. **Nunca inventar la causa** |
| 7 | Catálogos | "Por qué" de un dataset sin montar | Solo hay `available` | Mostrar siempre `path` en mono; con `false`, prefijo "No accesible:". Más accionable que la frase genérica |
| 8 | Catálogos | Dispositivo `cuda:0` | `model.device` = `"cuda"`, sin índice | Mostrar `cuda`. No inventar el índice |
| 9 | Catálogos | "Confianza mínima" (un valor) | Hay tres umbrales: `box`, `text`, `confidence` | Mostrar los tres rotulados, no elegir uno |
| 10 | Catálogos | "Clases que define" | El resumen no trae ids de clase | **DERIVABLE**: fan-out de `GET /api/prompt-sets/{id}` (5 llamadas). Alternativa sin fan-out: `n_classes` + `track` |
| 11 | Plataforma | **Tabla de instancias + Activar + Apagar** | `GET /api/platform/instances` → **501** sin `EOVRT_CONSOLE_COMPOSE_DIR` | Estado vacío dentro de la tarjeta: "La orquestación no está habilitada" + `service_url` fijo. Chip `c-nt`, no rojo. Ocultar Apagar. Distinguir 501 (capacidad ausente) de 502/504 (falla) |
| 12 | Plataforma | Nombre de la instancia activa | Sin orquestación no hay fleet | Usar `target.service_url` y retitular "Motor de detección activo" |
| 13 | Plataforma | **"Encendida hace 2 h 14 m"** | No hay uptime en ningún endpoint | Reemplazar la celda por **Adaptador** (`model.adapter`) |
| 14 | Plataforma | **"Memoria de GPU 6 142 MB"** | `runtime` solo trae `half_precision` y `warmup` | Reemplazar por **Dispositivo** + **Precisión** (media/completa) |
| 15 | Plataforma | "Corridas hoy: 14" | No hay agregado | **DERIVABLE** de `GET /api/runs` por `started_at` del día |
| 16 | Cámaras | "Usuario y clave se guardan **ocultos**" | `GET /api/cameras` devuelve `rtsp://admin:PASS@…` en claro | Redactar en el BFF con `redact_rtsp_credentials` (ya existe) **o** cambiar el texto: "la contraseña queda en el preset; `cameras/` está fuera del control de versiones" |
| 17 | Cámaras | Chips de clase fijos (`person`/`vehicle`/`backpack`) | No hay catálogo global de clases; salen del conjunto de prompts | Selector de conjunto de prompts en "Qué mostrar"; los chips se generan de sus clases |
| 18 | Cámaras | "9,8 cuadros/s" en el visor | `PreviewFrameHeader` no trae fps | **DERIVABLE**: media móvil de `Δseq/Δts` |
| 19 | Cámaras | Mínimo de 30 s por toma | El backend solo tiene `max_duration_s` | Regla de producto del frontend; aviso, no bloqueo (como ya hace el prototipo) |
| 20 | Cámaras | Catálogo de escenarios `P1..P8` / variantes `a,b,c` | No hay endpoint | Lista fija en el frontend (coincide con doc 69); el 422 de `InvalidTakeId` es la validación final |
| 21 | Cámaras | Estados `finished` y `error` de la grabación | El prototipo solo modela `idle/starting/rec` | **Agregarlos**: `finished` alimenta la tarjeta "Última toma" desde el backend; `error` es banda roja con el `error` crudo en mono |
| 22 | Cámaras | (falta) `truncated`, `suspected_substream` | Existen y el prototipo los ignora | Chips ámbar en "Última toma": una toma en substream no sirve y hay que saberlo en el momento |
| 23 | Clips | **"desde 41,2 s"** (offset del clip) | `ClipEntry` no expone `onset_ms`/`end_ms`, aunque `list_clips` ya lee ese YAML | Mientras tanto: `{resolution} · {fps} fps`. **Cambio de backend más barato del documento**: dos claves más en el dict de `list_clips` |
| 24 | Clips | "Desde / Hasta" en el detalle del clip | Mismo hueco | Sustituir por Resolución / Cuadros por segundo / Cuadros |
| 25 | Clips | (falta) `regenerated` e `invalidated` del corte | Existen en `GenerateClipResult` y el prototipo no los usa | Confirmación previa si el `clip_id` ya existe; aviso posterior listando lo invalidado. Sin esto se pisa GT en silencio |
| 26 | Clips | Eliminar un clip | No existe `DELETE /api/clips/{id}` | No agregar el botón |

**Recuento del cruce** (unidad = dato o control analizado, 78 en total):
**HAY 48** · **DERIVABLE 8** · **NO HAY 22**.

Por pantalla: Conjuntos de prompts 12/1/5 · Catálogos 9/1/4 · Plataforma 6/2/5 ·
Cámaras 14/2/5 · Clips 7/2/3 (los agregados "existe en la API y el prototipo lo ignora"
cuentan como HAY, y aparecen en la tabla cuando implican trabajo de UI).

### Orden de esfuerzo

1. **Cámaras** — tres bloques acoplados (presets, visor por WebSocket, panel de grabación con
   una máquina de 5 estados y exclusión mutua con la vista previa), más dos estados que el
   prototipo no modela y dos señales de calidad que no muestra.
2. **Conjuntos de prompts** — el editor es el componente más complejo de la consola (listas
   anidadas, validación en vivo, chips de frases) y arrastra la decisión de §0.1, que hay que
   cerrar antes de escribir una línea.
3. **Clips** — dos listas más un panel de tres caras, con reproductores reales y el manejo de
   regeneración/invalidación que el prototipo omite.

Catálogos y Plataforma son mucho más baratas: la primera es solo lectura sobre cuatro
endpoints que ya responden; la segunda, en este entorno, se reduce a la mitad superior más un
estado vacío bien redactado.
