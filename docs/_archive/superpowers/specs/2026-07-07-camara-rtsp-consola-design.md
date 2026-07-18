# Cámara RTSP desde la consola web — Diseño

**Fecha:** 2026-07-07
**Repo:** `e-ovrt_experimental-setup/webconsole/` (BFF FastAPI + SPA React)
**Estado:** aprobado, pendiente de plan de implementación

## Objetivo

Permitir que, desde "Nueva corrida" en la consola, el usuario elija el plugin de
ingesta `rtsp`, pegue una URL `rtsp://usuario:clave@host:554/stream` y lance un run
en vivo contra una cámara IP. El media-plane ya soporta RTSP de punta a punta
(`RtspSource`: reconexión con backoff, timestamps wall-clock, redacción de credenciales
en logs, plugin marcado `available: true`). El trabajo es **de la consola**: hoy bloquea
rtsp por una política heredada del MVP.

## Contexto y decisión de encuadre

La consola nació con una política "MVP" (`2026-07-01-webconsole-design.md` §6) que
restringía las fuentes lanzables a las **acotadas** (`image_folder`, `video_file`),
dejando fuera las fuentes vivas (`rtsp`, `oak_d`) aunque el servicio las expusiera como
disponibles. Ese encuadre MVP se retira: el objetivo pasa a ser la plataforma
experimental completa. **RTSP queda habilitado de forma permanente** (sin flag,
siempre disponible). `oak_d` sigue fuera hasta tener el hardware (ver memoria
`project_oak_d_pending`).

Este documento **supersede la política de restricción de fuentes de
`2026-07-01-webconsole-design.md` §6**. Los comentarios de código que referencian
"policy MVP (Spec B §6)" se actualizan para apuntar a esta decisión.

## Decisiones de diseño (cerradas)

1. **Forma del formulario:** URL RTSP única (un solo campo de texto), no campos
   separados host/puerto/usuario/clave. Calza directo con el `url` que espera el
   servicio y soporta cualquier path/query del fabricante.
2. **Credenciales al persistir:** al guardar una composición como manifiesto, la URL se
   escribe **redactada** (`rtsp://***:***@host:554/stream`). El password nunca se
   escribe a disco. Al re-lanzar desde un manifiesto guardado, el usuario recompleta las
   credenciales. El run activo **sí** usa la URL real (no se redacta en el camino al
   servicio).
3. **Habilitación:** rtsp se suma al set de plugins soportados de forma permanente. Se
   retira el nombre "MVP" del código: `MVP_PLUGINS → SUPPORTED_PLUGINS`,
   campo de API `mvp_enabled → enabled`, textos de UI actualizados.

## Fuera de alcance

- **Media-plane:** ningún cambio. Ya soporta rtsp con reconexión y redacción de logs.
- **OAK-D:** sigue fuera (hardware no disponible).
- **Campos separados** host/puerto/clave: descartado a favor de URL única.
- **Stop del run:** ya existe (`POST /api/runs/{id}/stop` en el BFF, botón "■ Detener"
  en `RunDetailPage.tsx`). Un run RTSP es infinito y se corta desde ahí; no requiere
  trabajo nuevo. (Sólo se aclara en la doc que las fuentes vivas se detienen manualmente.)

## Arquitectura y flujo

El contrato interno no cambia de forma: `Composition` (form/BFF) → `run request`
(servicio). Para rtsp el `config` de la composición lleva `{ "url": "rtsp://..." }`.

```
Form (ComposePage)
  plugin = "rtsp", rtspUrl = "rtsp://user:pass@host:554/stream"
        │
        ▼  Composition { ingest: { plugin: "rtsp", config: { url } } }
  POST /api/runs (BFF)
        │  validate_composition:  rtsp ⇒ exige config.url y prefijo rtsp://
        │  composition_to_run_request:  reenvía plugin+config VERBATIM (url real)
        ▼
  media-plane POST /api/runs → RtspSource(url) → run en vivo
```

Camino de guardado (separado, con redacción):

```
POST /api/manifests (BFF)
        │  composition_to_manifest:  source.type == "rtsp"
        │        ⇒ url = _redact_rtsp_credentials(url)   →  rtsp://***:***@host:554/stream
        ▼
  write_manifest → experiments/<name>.yaml  (nunca escribe el password)
```

Puntos clave de la separación:
- `composition_to_run_request` **no** redacta (el run necesita credenciales reales).
- `composition_to_manifest` **sí** redacta (persistencia a disco/git).

## Cambios detallados

### Backend BFF

**`settings.py`**
- `MVP_PLUGINS` → `SUPPORTED_PLUGINS = frozenset({"image_folder", "video_file", "rtsp"})`.
- Campo del dataclass `mvp_plugins` → `supported_plugins` (default `SUPPORTED_PLUGINS`).
- Actualizar el comentario de política: rtsp soportado permanentemente; `oak_d` fuera
  hasta tener hardware.

**`routers/compose.py` — `validate_composition`**
- `settings.mvp_plugins` → `settings.supported_plugins`; mensaje "fuera del MVP" →
  "no soportado por la consola".
- Nueva rama de validación de fuente según plugin:
  - `plugin == "rtsp"`: exigir `config.url` no vacío; error en `ingest.config.url` si
    falta. Exigir prefijo `rtsp://`; error en `ingest.config.url` si no cumple.
  - resto (`image_folder`/`video_file`): la validación dataset/path actual queda igual,
    pero sólo se aplica a esos plugins (no a rtsp).

**`routers/catalog.py` — `ingest_plugins`**
- Campo de salida `mvp_enabled` → `enabled` (misma semántica: `p["id"] in
  settings.supported_plugins and p.get("available", False)`).
- Actualizar el comentario que referencia "policy MVP (Spec B §6)".

**`translation.py`**
- `_SOURCE_TYPE_TO_PLUGIN`: agregar `"rtsp": "rtsp"` (round-trip manifiesto→composición).
- `_PLUGIN_TO_SOURCE_TYPE`: agregar `"rtsp": "rtsp"` (composición→manifiesto).
- Mensaje de error `source.type fuera del MVP` → `source.type no soportado`.
- Nuevo helper `_redact_rtsp_credentials(url: str) -> str`: regex local que reemplaza
  `rtsp://<credenciales>@` por `rtsp://***:***@`. No se importa del media-plane (evita
  acoplar los repos).
- En `composition_to_manifest`, cuando el `source["type"] == "rtsp"` y hay `url`,
  redactar la url antes de escribir el `source`.
- `composition_to_run_request`: **sin cambios** (ya reenvía plugin+config verbatim).

**`__init__.py`**
- Docstring: quitar "(Spec B, MVP)" → describir como cliente del servicio media-plane.

### Frontend

**`types.ts`**
- `IngestPlugin.mvp_enabled` → `enabled`.

**`pages/ComposePage.tsx`**
- Nuevo estado `const [rtspUrl, setRtspUrl] = useState('')`.
- Dropdown de plugin: `disabled={!p.enabled}` y texto `'(no soportado)'` en vez de
  `'(no disponible en MVP)'`.
- Render condicional de la fuente:
  - `plugin === 'rtsp'`: ocultar la fila dataset/path; mostrar un input de URL con
    placeholder `rtsp://usuario:clave@192.168.1.50:554/stream1` ligado a `rtspUrl`, con
    `<FieldMsg field="ingest.config.url" />`. Si `rtspUrl` contiene `***`, mostrar un
    hint inline: "recompletá las credenciales antes de lanzar".
  - resto: comportamiento actual (dataset del catálogo o path manual).
- `composition()`: para rtsp, `config = rtspUrl ? { url: rtspUrl } : {}`;
  `source_type` puede quedar `null` (el BFF lo deriva vía `_PLUGIN_TO_SOURCE_TYPE`).
- Prefill (`?from=`): si `source.type === 'rtsp'`, `setPlugin('rtsp')` y
  `setRtspUrl(source.url ?? '')`. (La url viene redactada; el hint de `***` avisa.)

**`pages/CatalogPage.tsx`**
- `!p.mvp_enabled` → `!p.enabled`; texto `[fuera del MVP]` → `[no soportado]`.

## Tests

**Backend**
- `test_settings.py`: `supported_plugins == {image_folder, video_file, rtsp}`.
- `test_catalog_proxy.py`: renombrar campo a `enabled`; `rtsp` ahora `enabled is True`;
  `oak_d` sigue `enabled is False`.
- `test_compose.py`: repurpose `test_plugin_fuera_del_mvp` → usar `oak_d` (sigue no
  soportado). Nuevos casos rtsp: sin `url` → error en `ingest.config.url`; url sin
  prefijo `rtsp://` → error; url válida → sin errores de fuente.
- `test_translation.py`: `composition_to_run_request` de una composición rtsp lleva la
  `url` **real** (con credenciales); `composition_to_manifest` de la misma composición
  produce `source.url` **redactada**; round-trip manifiesto rtsp preserva `type: rtsp`.
- `test_manifest_writer.py`: revisar el test de "plugin no soportado al guardar" (línea
  ~139) — debe seguir usando un plugin realmente fuera de `_PLUGIN_TO_SOURCE_TYPE`
  (p.ej. `oak_d`), no rtsp (que ahora sí mapea). Actualizar comentario.

**Frontend**
- `ComposePage.test.tsx`: renombrar `mvp_enabled` → `enabled` en los fixtures; nuevo
  caso: elegir plugin `rtsp` muestra el campo URL, oculta dataset/path y la composición
  arma `config: { url }`.

## Docs

- Actualizar `webconsole/README.md` si menciona fuentes soportadas / MVP.
- Nota en la doc de uso: las fuentes vivas (rtsp) generan runs infinitos que se detienen
  manualmente desde la vista de run.
- Los comentarios de código que citaban "policy MVP (Spec B §6)" pasan a citar esta
  decisión (fuentes vivas habilitadas, 2026-07-07).

## Riesgos y notas operativas

- **Credenciales redactadas en re-lanzamiento:** si el usuario carga un manifiesto
  guardado y lanza sin recompletar, el media-plane intentará conectar con `***:***` y
  fallará la autenticación (comportamiento esperado; el hint de UI lo previene).
- **Prerequisito operativo (no de esta feature):** para detección real el media-plane
  debe estar levantado con un modelo real (`EOVRT_MODEL_REF`) y `/readyz` en verde;
  con `mock` se puede validar el pipeline RTSP end-to-end sin GPU.
- **Alcance del rename:** `mvp_enabled` es un campo de contrato API consumido por el
  frontend; el rename a `enabled` debe aplicarse coordinado backend+frontend+tests en el
  mismo cambio para no romper el dropdown.
