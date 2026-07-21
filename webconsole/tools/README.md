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
