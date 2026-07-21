# Grabación de rodaje desde la consola (OAK-D / RTSP) — diseño

> **Estado**: diseño aprobado, sin implementar.
> **Fecha**: 2026-07-21
> **Contexto**: `docs/operacion/59-guion-grabacion-bloque-a.md` (guion de rodaje),
> `docs/specs/43-clip-bench-gt-temporal.md` (contrato de GT de video),
> `e-ovrt_experimental-setup/docs/superpowers/specs/2026-07-18-camera-preview-design.md`
> (ventana Cámaras, de la que esto es hermano).

## 1. Problema

El bloque A del banco (episodios de alerta guionados P1–P9) **no existe en material
público**: hay que filmarlo con el equipo según doc 59. Hoy no hay forma de grabar
desde la plataforma. El puente cámara → archivo es manual: se graba con una
herramienta externa, se copia el `.mp4` a `datasets-videos/raw/` y recién ahí
arranca la etapa 0 del video-gt-lab.

Lo que ya existe y **no** se toca:

- Los plugins de ingesta `rtsp` y `oak_d` del media-plane (`sources/`) y su sesión
  de preview, que sirven para verificar encuadre antes de la toma.
- `datasets/scripts/videogt/prepare_clip.sh` — etapa 0: normaliza a CFR 30 fps sin
  audio y emite `<clip_id>.info.json`.

Falta exclusivamente **escribir el stream a disco**, operado desde la consola.

## 2. Alcance

**Entra**: grabar una toma desde una cámara RTSP o una OAK-D Pro PoE, disparada
desde la ventana Cámaras, produciendo un master crudo en
`e-ovrt_datasets/datasets-videos/raw/` con nombre derivado del shot-list de doc 59.

**No entra** (explícito, para que nadie lo asuma):

- Normalización, recorte o generación de `clip_id` — sigue siendo `prepare_clip.sh`.
- La hoja de registro de doc 59 §5 — se llena en papel, como manda el guion.
- Grabar durante una corrida live EBE — ver D3, son mutuamente excluyentes.
- Audio — el pipeline es solo video y `prepare_clip.sh` ya hace `-an`.
- Acelerar `prepare_clip.sh` con NVENC — mejora real y disponible (hay una RTX
  4060 con NVENC en ffmpeg), pero es del repo `e-ovrt_datasets` y va en su propio
  trabajo. Anotado acá para no perderlo.

## 3. Decisiones

| # | Decisión | Motivo |
|---|---|---|
| D1 | Se opera desde la **consola web**, ventana Cámaras | Es donde ya se verifica el encuadre; una sola superficie el día del rodaje |
| D2 | La salida es un **master crudo en `raw/`** | Regla de oro 3 de doc 59: se filma 30–35 s y el recorte fino (onset en t≈3–4 s) se hace después. Normalizar al grabar quemaría ese margen |
| D3 | Grabación y corrida live son **secuenciales**, nunca simultáneas | Doc 59 §7 ya define doble toma |
| D4 | Nombrado por **selector de escenario + take autoincremental** | `P1-a-take2.mp4`. Sin tipeo en obra, sin posibilidad de pisar una toma |
| D5 | **Bitstream nativo por plugin**, no re-encode de frames decodificados | Máxima calidad y máximos fps reales: cero pérdida y CPU del host ~0 en ambas ramas |
| D6 | Capturar a **60 fps** (OAK-D; en RTSP manda el DVR), entregar 30 al banco | Menos motion blur y margen de cámara lenta, sin romper la homogeneidad de los 14 clips existentes ni el GT ya derivado |
| D7 | Durante la toma la consola muestra **solo estado** | El encuadre se verifica antes (doc 59 dry-run). Ningún monitoreo compite con el master |
| D8 | OAK-D en **H.264 a ~25 Mbps** | Compatibilidad total aguas abajo (ffmpeg, OpenCV, CVAT) y el disco no es restricción |
| D9 | Sidecar `<basename>.rec.json` con **procedencia técnica** | Responde "¿con qué cámara y a qué fps salió esto?" en la defensa. No es la hoja de registro |
| D10 | El grabador vive en el **webconsole**, no en el media-plane | Grabar no necesita modelo ni servicio de inferencia. Si el media-plane se cae o ni siquiera está levantado, el rodaje sigue. Ver §3.2 |

### 3.1 Enfoques descartados

- **Grabar pinchando el lector del preview del media-plane.** `_LatestUnitBox`
  (`preview_manager.py:29`) descarta frames por diseño y el preview escala a 960 px
  y recomprime a JPEG q80; habría que pinchar antes, en `_read_source`, y
  re-encodear en CPU. Riesgo real de frames caídos en un master de banco.
  Descartado por D5.
- **Grabar el WS de preview desde el webconsole.** Cero cambios en el media-plane,
  pero graba el stream ya decimado y recomprimido. Inaceptable para el master.
- **Traer frames crudos de la OAK-D y encodear con NVENC.** No entra por el cable:
  1080p60 en NV12 son ~186 MB/s ≈ 1.5 Gbps sobre un enlace PoE Gigabit. Pasar por
  MJPEG on-device y re-encodear es doble pérdida. El encoder de la Myriad X es el
  óptimo disponible.
- **Grabador dentro del media-plane** (versión previa de este diseño). Reusaba el
  `ActivitySlot` y los recorders quedaban al lado de las fuentes, pero ataba el
  rodaje a un servicio que carga un modelo en el arranque y que no aporta nada a
  grabar. Descartado por D10.

### 3.2 Por qué el webconsole y no el media-plane

El media-plane carga el modelo **una sola vez en el startup** (`EOVRT_MODEL_REF`),
independientemente de lo que se haga después. Grabar no usa el modelo, no usa el
pipeline de inferencia y no produce eventos: no tiene por qué depender de que ese
servicio esté sano. Con el grabador en el webconsole, un día de solo-grabar no
necesita el media-plane levantado en absoluto, y una caída del plano de inferencia
en obra no cuesta tomas.

El precio es que el webconsole necesita hablar DepthAI, y ahí hay una restricción
dura: **el backend corre Python 3.14.4 y `depthai` 2.32 no tiene wheels para
3.14** (llega hasta 3.12/3.13). Por eso el recorder de OAK-D es un **script
standalone ejecutado como subproceso con otro intérprete** (§4.2), no un import.
La rama RTSP no tiene este problema: es un subproceso `ffmpeg`, sin dependencias
Python nuevas.

## 4. Arquitectura

```
webconsole (ventana Cámaras)
  │  POST   /api/recordings   {plugin, config, basename, label, capture, max_duration_s}
  │  GET    /api/recordings   estado + duración + bytes
  │  DELETE /api/recordings   corta y cierra el mp4
  ▼
webconsole backend ─ RecordingManager (lock local, singleton)
      ├─ rtsp   → ffmpeg -rtsp_transport tcp -i <url> -c copy
      └─ oak_d  → subproceso: <python-con-depthai> tools/record_oakd.py
                   ColorCamera(1080p60) → VideoEncoder(H.264 25 Mbps) → XLinkOut
                   el script solo escribe bytes a un archivo
  ▼
e-ovrt_datasets/datasets-videos/raw/P1-a-take2.mp4  +  P1-a-take2.rec.json
```

Ambas ramas son **subprocesos que escriben a disco**. El backend no decodifica ni
encodea nada: arranca, vigila, corta y muxea. Por eso la CPU del host queda libre
en las dos.

### 4.1 Unidades

| Unidad | Responsabilidad | Ubicación |
|---|---|---|
| `RecordingManager` | Ciclo de vida start/stop/status; lock; recupera huérfanas al arrancar | webconsole backend `recording/manager.py` |
| `FfmpegCopyRecorder` | Envuelve el subproceso ffmpeg; corte limpio; reporta rc, bytes y duración | webconsole backend `recording/ffmpeg_recorder.py` |
| `OakDSubprocessRecorder` | Lanza y vigila `record_oakd.py` con el intérprete configurado | webconsole backend `recording/oakd_recorder.py` |
| `record_oakd.py` | Script standalone: abre la OAK-D, encodea por hardware, escribe H.264 crudo | webconsole `tools/record_oakd.py` |
| `take_naming.py` | Resuelve `P1` + `a` → próximo `takeN` mirando `raw/` | webconsole backend `recording/` |
| `routers/recordings.py` | REST | webconsole backend |
| `RecordPanel.tsx` | Selector escenario/variante, botón grabar, cronómetro con marca a 30 s | webconsole frontend |

Los dos recorders implementan la misma interfaz mínima (`start()`,
`stop() -> RecordingResult`, `poll() -> RecordingStatus`), así que
`RecordingManager` no sabe de ffmpeg ni de DepthAI.

`record_oakd.py` no importa nada del webconsole ni del media-plane: recibe todo por
argv y escribe a stdout un JSON de cierre. Se puede correr a mano desde una
terminal, que es exactamente lo que querés como plan B si la consola falla en obra.

### 4.2 El intérprete de la rama OAK-D

Setting `oakd_python` del backend, con este orden de resolución:

1. Valor explícito en la config, si está.
2. Default: el venv del media-plane (`../e-ovrt_media-plane/.venv/bin/python`),
   que hoy es Python 3.12.13 con `depthai` 2.32.0.0 ya instalado.
3. Si no resuelve o el import de `depthai` falla, la consola lo reporta **al
   arrancar el backend**, no al apretar grabar en medio del rodaje.

Un venv dedicado solo para grabar es una alternativa válida (desacopla del
media-plane, que según nota conocida se rompe si se mueve de directorio); el
setting lo admite sin cambios de código.

### 4.3 Contrato del request

El `camera_id` de `cameras/*.yaml` lo resuelve el propio backend —los presets viven
en este repo— y viaja al recorder como `{plugin, config}` ya resueltos, más un
`label` opaco que queda asentado en el sidecar.

El bloque `capture` (`fps`, `resolution`, `bitrate_bps`) **solo aplica a `oak_d`**.
En `rtsp` no hay palanca de nuestro lado: se graba lo que emite el DVR. Mandarlo
con `plugin: rtsp` es 422, no un knob que se ignora en silencio.

`max_duration_s` es el corte de seguridad (§7), default 600. Se sube
explícitamente para las tomas soak propias, que por diseño pueden durar más que una
toma de episodio.

### 4.4 Exclusión mutua (D3)

Sin `ActivitySlot` compartido, la exclusión se sostiene en tres capas:

1. **Lock local del backend**: una sola grabación activa por consola.
2. **Chequeo previo contra el media-plane**: si hay preview o run activo, la
   consola responde 409 identificando al ocupante. Como la consola es el único
   cliente que dispara runs y previews (ADR-008/009), alcanza en la práctica.
3. **Exclusividad física de la OAK-D**: un segundo proceso que intente abrir el
   dispositivo falla. Es el backstop real si alguien saltea la consola con `curl`.

Limitación honesta: si alguien dispara un run directo contra el media-plane
mientras se graba con RTSP, ambos conviven (el DVR tolera dos conexiones) y nadie
se entera. No rompe nada — solo deja de valer la separación de doble toma de doc 59.

## 5. Flujo de una toma

1. El operador elige cámara, escenario (`P1`…`P9`) y variante (`a`/`b`/`c`).
2. El backend lista `raw/`, ve `P1-a-take1.mp4` y propone `P1-a-take2`.
3. `POST /api/recordings`. El archivo se crea con `O_EXCL`: si ya existe, 409 y la
   consola reintenta con el siguiente take. **Nunca se pisa una toma.**
4. La UI muestra `● REC`, cronómetro y bytes escritos, con **marca visual a los
   30 s** (regla de oro 3 de doc 59).
5. `DELETE /api/recordings` → corte limpio, `fsync`, muxeo. La respuesta trae
   duración real, fps medido, resolución y tamaño; se escribe el sidecar.
6. Después del rodaje:
   `prepare_clip.sh raw/P1-a-take2.mp4 v20_c01 --ss 12 --to 20`.
   **Ese paso no cambia en nada.**

   > **Trampa verificada empíricamente (ffmpeg 8.0.1)**: en `prepare_clip.sh`,
   > `-ss` va **antes** del input y `-to` después, y con esa combinación **`--to`
   > es relativo al punto de corte, no absoluto**: se comporta como una duración.
   > `--ss 5 --to 8` produce un clip de **8 s** (240 frames a 30 fps), no de 3 s.
   > O sea que para extraer la ventana [12 s, 32 s) del master se escribe
   > `--ss 12 --to 20`, no `--to 32`. Escribirlo mal no falla: produce en silencio
   > un clip más largo, con el onset en el lugar equivocado respecto del GT.

### 5.1 Parámetros por rama

| | RTSP | OAK-D |
|---|---|---|
| Captura | lo que emite el DVR (`-c copy`) | 1080p60, H.264 ~25 Mbps, encoder por hardware |
| CPU del host | ~0 (copia de bitstream) | ~0 (solo escribe bytes de la cola) |
| Palanca de fps | config del DVR, no nuestra | `ColorCamera.setFps` |
| Contenedor | mp4 (remux, sin transcodificar) | H.264 crudo → mp4 al cerrar |
| Keyframes | los del DVR | ~1 s (`setKeyframeFrequency`) |

El intervalo de keyframe corto de la OAK-D no es cosmético: el re-ventaneo de la
etapa 0 con `--ss/--to` es exacto y barato si hay keyframes cerca; con GOP largo
ffmpeg corta mal o re-encodea.

### 5.2 Sidecar `<basename>.rec.json`

```json
{
  "basename": "P1-a-take2",
  "file": "raw/P1-a-take2.mp4",
  "camera_id": "oak_d_lab",
  "plugin": "oak_d",
  "requested": { "fps": 60, "resolution": "1080p", "codec": "h264", "bitrate_bps": 25000000 },
  "measured":  { "fps": 59.94, "resolution": "1920x1080", "duration_ms": 33150, "size_bytes": 103218432 },
  "started_wallclock_ms": 1784646000000,
  "truncated": false,
  "sha256": "…"
}
```

`requested` vs `measured` es deliberado: si el DVR entregó 12 fps cuando se pidieron
60, queda registrado en vez de descubrirse en la defensa. En `rtsp`, `requested`
sale vacío: no se pidió nada.

## 6. Aprovechamiento de recursos del host

Medido en la máquina del rodaje: 16 cores, 7 GB de RAM, disco ext4 nativo con
905 GB libres, RTX 4060 con NVENC disponible en ffmpeg.

- **La GPU no mejora la captura.** Con `-c copy` no se encodea nada, y no se puede
  crear información que el DVR no mandó. En la OAK-D, el camino a NVENC no entra
  por el cable (§3.1). NVENC sí rinde en `prepare_clip.sh`, que hoy usa
  `libx264 -crf 18 -preset medium` en CPU — trabajo aparte (§2).
- **La RAM deja de ser un problema con D10.** El modelo lo cargaba el media-plane
  en su startup, no la grabación; con el grabador en el webconsole, un día de
  solo-grabar no levanta modelo alguno. En un día de doble toma el modelo queda
  residente, pero el grueso de `gdino-tiny` vive en la VRAM de la 4060, no en los
  7 GB de sistema. Se verifica en el dry-run y listo.
- **El disco ya está bien**: ext4 nativo, no `/mnt/c`. A 25 Mbps son ~190 MB/min;
  el rodaje entero entra con margen. El diseño **rechaza rutas bajo `/mnt/c`**: el
  filesystem cruzado de WSL es lo bastante lento como para perder frames por I/O.
- **Bitrate alto en la OAK-D** es la única palanca real de calidad de esa rama, y
  es gratis: el enlace Gigabit está ocioso y el disco sobra.
- **`-rtsp_transport tcp` es obligatorio.** Sobre UDP el DVR pierde paquetes y
  aparecen macrobloques en el master: daño irreversible.
- **Stream principal del DVR, nunca el substream.** Si el preset apunta al
  substream se graba 640×480 sin que nadie se entere; por eso el gate de
  resolución sospechosamente baja de §7.

## 7. Manejo de errores

| Falla | Respuesta |
|---|---|
| El subproceso muere / cámara se desconecta | Sesión a `error`; el mp4 parcial **se conserva** y el sidecar sale `truncated: true`. Nunca se borra material |
| Se corta antes de 30 s | La UI marca la toma en amarillo (regla de oro 3). Advertencia, no bloqueo |
| Disco con menos de 5 GB | 422 al arrancar |
| Ruta destino inválida o bajo `/mnt/c` | 422 al arrancar, no al terminar |
| Resolución medida sospechosamente baja (< 1280 de ancho) | Se graba igual, pero la respuesta y el sidecar lo marcan: probable substream |
| Nadie frena la grabación | Corte automático al llegar a `max_duration_s` (default 600), toma marcada `truncated` |
| Preview o run activos en el media-plane | 409 identificando al ocupante (§4.4) |
| Media-plane caído o apagado | **La grabación funciona igual.** Solo se pierde el chequeo previo, que se degrada a advertencia |
| `oakd_python` no resuelve o no tiene depthai | Se reporta al arrancar el backend, no al apretar grabar |
| El basename ya existe | 409; la consola reintenta con el take siguiente |
| El backend cae con REC activa | Al arrancar, cierra y remuxea la grabación huérfana y la marca `truncated` |

Criterio transversal, consistente con el resto de la plataforma: **nada se
silencia**. Una toma degradada se marca y se conserva; no se descarta ni se
presenta como sana.

## 8. Testing

**Sin hardware (pytest, CI):**

- Autoincremento de takes: huecos en la numeración, colisión, formato inválido.
- Gates de arranque: disco, `/mnt/c`, basename inválido, resolución baja,
  `capture` con `plugin: rtsp` → 422.
- `FfmpegCopyRecorder` apuntado a un `file://` local en vez de RTSP: ejercita
  muxeo, corte, sidecar, sha256 y duración medida sin tocar la red.
- `OakDSubprocessRecorder` contra un script falso que imita el contrato de
  `record_oakd.py` (argv + JSON de cierre): ejercita arranque, corte y error sin
  hardware ni depthai.
- Exclusión mutua: lock local, y media-plane con preview/run activo → 409;
  media-plane caído → se graba con advertencia.
- Corte automático por `max_duration_s` (con reloj inyectado).
- Recuperación de grabación huérfana al arrancar el backend.

**Criterio de aceptación real**: que `prepare_clip.sh` consuma un master grabado y
emita un `info.json` con `n_frames` coherente con la duración. Si eso no cierra, la
herramienta no sirve aunque los tests pasen.

**Con hardware, en el dry-run de doc 59 §7 (el día antes del rodaje):** 60 s con
cada cámara verificando fps medido vs. pedido, tamaño, espaciado de keyframes y el
corte a los 30 s. Se agrega como checklist al guion.

## 9. Impacto en los repos

- `e-ovrt_experimental-setup`: **todo el trabajo**. Backend (`recording/`, router,
  `tools/record_oakd.py`), frontend (`RecordPanel.tsx`), settings `recordings_dir`
  y `oakd_python`.
- `e-ovrt_media-plane`: **ninguno**. Se sigue usando su ventana de preview para
  verificar encuadre y su venv como intérprete con depthai, pero no se le toca
  una línea.
- `e-ovrt_datasets`: **ninguno**. `prepare_clip.sh` y la etapa 0 no se tocan.
- `docs`: agregar al checklist del dry-run de doc 59 §7 la verificación de
  grabación con las dos cámaras.
