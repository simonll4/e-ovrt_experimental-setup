# Derivar experimentos con configuración propia — diseño

**Fecha**: 2026-07-25
**Repo**: `e-ovrt_experimental-setup` (webconsole: backend BFF + frontend)
**Estado**: aprobado, pendiente de plan de implementación

## Problema

La pantalla de Experimentos manda un único campo al lanzar: el `slug` del manifiesto
(`ExperimentsPage.tsx:74`). No hay forma de ajustar nada desde la UI. Para cambiar
`warmup_frames`, el prompt set o los umbrales del motor hay que editar los YAML del
manifiesto a mano.

Esto se volvió un problema operativo durante el rodaje: `warmup_frames` es por-run,
su default es `0` (`schemas.py:218` del media-plane) y **no** se hereda del preset de
cámara, así que la única forma de fijarlo era editar
`experiments/ebe_oakd_live/media.yaml` entre tomas.

La pantalla de Composición (`/compose`) sí expone esos campos, pero lanza **solo el
media-plane**: su payload no lleva `bus`, así que el control-plane nunca entra en el
circuito y no hay alertas CR-01/CR-02. Componer un run y derivarlo a experimento
tampoco sirve: el botón `Guardar como manifiesto` de esa pantalla escribe un YAML
suelto con el payload del media (como `mock.yaml`, `yoloe.yaml`), **no** un manifiesto
paraguas con `runs` + `sequencing`, así que no aparece en el desplegable de
Experimentos.

## Decisión de fondo

Los parámetros no se sobrescriben al lanzar: **se deriva un manifiesto nuevo**. El
`slug` sigue siendo la unidad reproducible y congelada — dos corridas del mismo slug
corrieron siempre con la misma configuración. Cada combinación de parámetros es un
slug propio, con registro de cuál lo originó.

Se descartó el override efímero en el formulario de lanzamiento: hace que el slug deje
de identificar una configuración, y obliga a reconstruir a posteriori con qué corrió
cada toma.

## Patrón que se reusa

El repo ya tiene derivación para prompt sets: `POST /api/prompt-sets/{set_id}/derive`
(`routers/prompts.py:89`) → `prompt_store.derive_set` (`prompt_store.py:225`), que
copia el original, le asigna id nuevo y guarda `derives_from` + `changes` como
procedencia (`prompt_store.py:232`).

Este diseño es el espejo de ese patrón para manifiestos paraguas. Mismos nombres de
campo, misma semántica, para que el vocabulario del repo sea uno solo.

## Alcance

### Endpoint

`POST /api/experiments/manifests/{slug}/derive` → `201`

```json
{
  "new_slug": "ebe_oakd_live_w30",
  "changes": "warmup_frames 20 -> 30 por sobreexposición inicial",
  "overrides": {
    "warmup_frames": 30,
    "fps": 30,
    "camera_id": "oak_d_lab",
    "prompt_set_id": "cr01_cr02_v2_short",
    "max_units": 600,
    "pattern_set_file": "/home/simonll4/projects/e-ovrt_control-plane/configs/patterns/cr01_cr02_v2.yaml",
    "pattern_active_ids": ["CR-01", "CR-02"]
  }
}
```

Escribe `experiments/<new_slug>/` con los tres YAML (`manifest.yaml`, `media.yaml`,
`control.yaml`), copiados del manifiesto fuente y con los overrides aplicados.

**Semántica de cada clave de `overrides`** — sin ambigüedad:

- **clave ausente** → conserva el valor del manifiesto fuente
- **clave con valor** → lo reemplaza
- **clave con `null` explícito** → **borra** el campo del YAML derivado, dejándolo en
  el default del plano correspondiente (p. ej. `"stride": null` quita `run.stride`,
  y el media-plane usa su default)

La distinción importa: sin ella no habría forma de volver un campo a su default una
vez que el manifiesto fuente lo declara.

### Mapa de overrides

Cada campo de la UI aterriza en una ruta YAML explícita. No hay overrides genéricos
por path — la lista es cerrada y validada.

| Grupo | Campo | Destino |
|---|---|---|
| Captura | `warmup_frames` | `media.yaml` → `ingest.config.warmup_frames` |
| Captura | `fps` | `media.yaml` → `ingest.config.fps` |
| Captura | `camera_id` | `media.yaml` → `ingest.plugin` + `ingest.config.url` |
| Prompts | `prompt_set_id` | `media.yaml` → `prompts.set_inline` (expandido) |
| Límites | `stride`, `max_units` | `media.yaml` → `run.stride`, `run.max_units` |
| Patrones | `pattern_set_file` | `control.yaml` → `patterns.file` (ruta absoluta) |
| Patrones | `pattern_active_ids` | `control.yaml` → `patterns.active_ids` |

`camera_id` se resuelve contra el catálogo de `/api/cameras`, que devuelve
`{id, name, plugin, config}` — de ahí salen `plugin` y `config.url`.

### Reescritura de identidad y rutas

Copiar el directorio no alcanza: hay cuatro campos que referencian al manifiesto
fuente por nombre o por ruta absoluta, y quedan mal si se copian tal cual.

| Archivo | Campo | Acción |
|---|---|---|
| `manifest.yaml` | `slug` | pasa a `new_slug` |
| `manifest.yaml` | `runs.media.config`, `runs.control.config` | reapuntar a `experiments/<new_slug>/{media,control}.yaml` |
| `media.yaml` | `run.name` | pasa a `new_slug` |
| `control.yaml` | `run.name` | pasa a `control_<new_slug>` |

El caso de `runs.*.config` es el peligroso: son **rutas absolutas** (ADR-009) que hoy
apuntan a `/home/.../experiments/ebe_oakd_live/media.yaml`. Si se copian sin
reescribir, el manifiesto derivado carga los payloads del **original** — corre con la
configuración vieja sin fallar ni avisar, y los overrides que escribiste en el
directorio nuevo no los lee nadie. Es un fallo silencioso, del peor tipo: el
experimento anda, produce artefactos, y son de la config equivocada.

Test obligatorio: derivar con un override, cargar el manifiesto derivado con
`load_manifest` y verificar que los paths resuelven **dentro del directorio nuevo** y
que el valor leído es el override, no el del fuente.

### Prompts: expansión inline obligatoria

El media-plane **solo acepta `set_inline`**: `PromptsSpec` declara
`model_config = ConfigDict(extra="forbid")` con los campos `set_inline` y `active_ids`
únicamente (`run_request.py:24-27`). No existe `set_id`, y el media-plane no tiene
catálogo de prompt sets — viven en `experimental-setup/prompts/`.

Por eso el selector de prompts del formulario **expande** el set elegido dentro del
`media.yaml` derivado, leyéndolo del catálogo del BFF. El `id` del set se preserva en
`prompts.set_inline.id` para que el manifiesto derivado siga declarando de cuál salió.

### Procedencia

`ExperimentManifest` declara `model_config = ConfigDict(extra="forbid")`
(`experiment/manifest.py`), así que los campos nuevos requieren agregarse al modelo:

- `derives_from: str | None = None` — slug del manifiesto fuente
- `changes: str | None = None` — texto libre, por qué se derivó

Ambos opcionales: los manifiestos existentes (`ebe_oakd_live`, `video16_clip10_gt`)
siguen validando sin tocarlos.

### Validación

Antes de escribir nada:

1. **Slug**: regex `^[a-z0-9][a-z0-9_-]*$`, la misma de `manifest_writer._NAME_RE`.
2. **Colisión**: si `experiments/<new_slug>/` existe, `409`. Nunca se pisa un slug.
3. **`ingest.config`**: las claves resultantes se chequean contra
   `SourceSection.model_fields`, que es la misma regla que aplica el media-plane en
   `run_request.py:87`. Un campo mal tipeado falla al derivar, no en medio de una toma.
4. **`camera_id`**: tiene que existir en el catálogo de `/api/cameras`.
5. **`prompt_set_id`**: tiene que existir en el catálogo de `/api/catalog/prompt-sets`
   (`routers/catalog.py:12`).
6. **`pattern_set_file`**: tiene que existir en disco y ser ruta absoluta (ADR-009).
7. **`warmup_frames` vs tipo de fuente**: `warmup_frames > 0` solo vale con fuentes
   vivas — `LIVE_SOURCE_TYPES = ("rtsp", "oak_d")` (`schemas.py:145`), y el media-plane
   lo rechaza explícitamente en otro caso (`schemas.py:239-246`). Derivar un
   experimento sobre `video_file` con `warmup_frames` heredado del original tiene que
   fallar al derivar, no con un 422 al lanzar.

### Escritura

`manifest_writer.write_manifest` (`manifest_writer.py`) escribe **un** YAML de forma
atómica (`tmp` + `os.replace` en el mismo filesystem). Acá hacen falta tres archivos,
y tres escrituras atómicas **no** son atómicas como conjunto: si la segunda falla,
queda un directorio a medio construir que `_iter_umbrella_manifests` puede llegar a
listar, o peor, un `manifest.yaml` válido apuntando a un `media.yaml` que no existe.

Por eso la unidad atómica es el **directorio**, no el archivo: se arma completo en un
temporal hermano (`experiments/.<new_slug>.tmp/`) y recién con los tres archivos
escritos se hace `os.replace` del directorio. `os.replace` sobre un directorio destino
inexistente es atómico en el mismo filesystem, que es justamente el caso — el paso 2
de validación ya garantiza que el destino no existe. Si algo falla antes, se borra el
temporal y no queda rastro.

Se conserva la validación de nombre de `write_manifest` (`_NAME_RE`) y la noción de
grupos protegidos, aplicada al directorio destino.

### Frontend

Botón **Derivar** en cada fila de la tabla de manifiestos de `ExperimentsPage`. Abre
un formulario precargado con los valores del manifiesto fuente, más dos campos
propios: nombre nuevo y `changes`.

Al guardar con éxito, la lista de manifiestos se recarga, el slug nuevo queda
seleccionado en el desplegable, y se lanza con el botón `Lanzar experimento` que ya
existe. Derivar **no** lanza nada.

## Fuera de alcance

Deliberadamente, para no inflar la superficie:

- Editar un manifiesto existente desde la UI. Si hay que cambiar algo, se deriva otro.
- Borrar manifiestos desde la UI.
- Editor de YAML libre.
- Crear un manifiesto desde cero. Siempre se parte de uno que ya funciona.
- Override efímero en el lanzamiento (descartado arriba, con razón).

## Tests

TDD, test primero en cada caso.

**Backend** (`webconsole/backend/tests/`):

- cada override aterriza en la ruta YAML correcta (uno por fila del mapa)
- campos omitidos conservan el valor del original
- `derives_from` y `changes` quedan registrados en el manifiesto derivado
- los manifiestos existentes siguen validando con los campos nuevos ausentes
- slug repetido → `409`, y el directorio original queda intacto
- fallo a mitad de la escritura → no queda ni el directorio destino ni el temporal
  (simular con un error al escribir el segundo archivo)
- slug inválido (mayúsculas, `..`, vacío) → `400`
- campo desconocido en `ingest.config` → `400`, sin escribir nada
- `camera_id` / `prompt_set_id` / `pattern_set_file` inexistentes → `400`
- el prompt set se expande inline y preserva el `id`
- `warmup_frames > 0` sobre una fuente no viva → `400` al derivar
- el manifiesto derivado se puede cargar con `load_manifest` y aparece en
  `_iter_umbrella_manifests`
- **`slug`, `runs.*.config` y los dos `run.name` quedan reescritos al nuevo slug**, y
  los paths resuelven dentro del directorio derivado
- **guard anti-fallo-silencioso**: derivar con un override, cargar el manifiesto
  derivado y verificar que el valor leído es el override — no el del manifiesto
  fuente. Sin este test, un bug en la reescritura de `runs.*.config` pasa toda la
  suite en verde y corre con la configuración equivocada.

**Frontend** (`webconsole/frontend/src/`, vitest):

- el formulario precarga los valores del manifiesto fuente
- el submit arma el body esperado
- el error del backend se muestra sin romper la pantalla

## Riesgo conocido

`_iter_umbrella_manifests` hace `rglob("*.yaml")` sobre `experiments_dir`
(`routers/experiments.py:67`) y se queda con los que parsean como
`ExperimentManifest`. Un directorio derivado con un `manifest.yaml` inválido no
rompe el listado — simplemente no aparece. La validación previa a la escritura es lo
que evita que se generen manifiestos fantasma.
