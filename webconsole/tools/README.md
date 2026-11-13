# Herramientas standalone del webconsole

## `record_oakd.py`

Graba la OAK-D a H.264 crudo con el encoder por hardware del dispositivo. Lo
invoca la consola (`POST /api/recordings` con una cámara `oak_d`), pero es
**standalone a propósito**: corre a mano desde una terminal y es el plan B si la
consola falla en obra.

Requiere un intérprete con el SDK DepthAI. El backend de la consola corre Python
3.14 y `depthai` no publica wheels para 3.14, así que se usa otro intérprete —
por default el venv del media-plane:

```bash
../../e-ovrt_media-plane/.venv/bin/python tools/record_oakd.py \
    --device 192.168.1.50 \
    --out /tmp/toma.h264 \
    --fps 60 --resolution 1080p --bitrate 25000000
# cortar con Ctrl-C; despues muxear a mp4:
ffmpeg -f h264 -r 60 -i /tmp/toma.h264 -c copy /tmp/toma.mp4
```

Se puede apuntar a otro intérprete con `EOVRT_CONSOLE_OAKD_PYTHON`.

Códigos de salida: `0` ok, `2` argumentos inválidos, `3` SDK ausente, `4` fallo
del dispositivo. En stdout emite una línea JSON por evento (`{"event":
"started"}`, `{"event": "finished", "bytes_written": N}` o `{"event": "error",
"reason": "..."}`); corta limpio con SIGTERM/SIGINT.

## `mirar_pantallas.mjs`

Captura pantallas contra una consola que ya está corriendo y dice, para cada una, qué encabezados mostró y qué
errores dejó en el navegador. Es para mirar un cambio con datos reales antes de darlo por bueno; no inventa datos
ni intercepta nada (para eso está `capture_console.mjs`).

```bash
node webconsole/tools/mirar_pantallas.mjs --out /tmp/mirar /resultados /resultados/ALR-13
node webconsole/tools/mirar_pantallas.mjs --out /tmp/mirar --tarjeta "Las tomas" /resultados/RT-06
node webconsole/tools/mirar_pantallas.mjs --out /tmp/mirar --tecla e --dialogo /demo/resultado/<sesión>
```

Necesita Playwright, que no es dependencia del proyecto: se instala en `webconsole/tools/.capture-runtime`
(ignorada por git) o se indica con `--playwright-module`. El navegador, con `--chromium <ruta>` si no hay uno
instalado por Playwright. Las opciones están en el encabezado del archivo.
