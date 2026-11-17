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
node webconsole/tools/mirar_pantallas.mjs --out /tmp/mirar-oscuro --tema oscuro /resultados /resultados/ALR-13
```

Por defecto mira el tema claro, que es el de la consola y el de las capturas; `--tema oscuro` deja elegido el otro,
como lo haría el selector de la barra lateral. Cada cambio se mira en los dos.

Necesita Playwright, que no es dependencia del proyecto: se instala en `webconsole/tools/.capture-runtime`
(ignorada por git) o se indica con `--playwright-module`. El navegador, con `--chromium <ruta>` si no hay uno
instalado por Playwright. Las opciones están en el encabezado del archivo.

## `sacar_figuras.mjs`

Saca las diez figuras del informe de una consola que ya está corriendo. La lista es
`results/evidence-vista/figuras.yaml` y la herramienta la lee de la consola (`GET /api/figuras`): un gráfico se
captura de la página de su pregunta, una pantalla se captura del elemento que dice el archivo y un archivo se copia.

```bash
node webconsole/tools/sacar_figuras.mjs                        # contra la consola en contenedor (8090)
node webconsole/tools/sacar_figuras.mjs --base http://localhost:5173 --solo falsas-alarmas-por-causa
```

Cada figura va a su carpeta y a ninguna otra: la pública `results/gen2/<prueba>/capturas/` solo recibe gráficos y
pantallas de texto (si el elemento tiene una imagen o un video, no se guarda) y lo que tiene personas o cuadros de
terceros va a `defensa/capturas/figuras/`, que no va a git. Se sacan en el tema claro y al doble de resolución
(`--escala`). Un archivo con `recorte_arriba` se copia sin esa franja de arriba (la banda de códigos internos que
graba VIS-01). Las figuras pendientes se listan con su motivo. Sale con 1 si alguna falló.

La figura 9 (las curvas del ajuste fino) no tiene prueba de la campaña: es un gráfico y va con sus datos a
`finetuning/curvas/`.

## `armar_figuras_privadas.py`

Arma, desde la evidencia, los dos archivos que copian las figuras 5 y 10, y los deja en `defensa/figuras/<prueba>/`
(git los ignora), cada uno con un `.json` al lado que dice de qué corridas y cuadros salió:

- **Figura 5 (RT-09):** el mismo instante de dos tomas P2 del perfil operativo, con remera negra y con blanca,
  dibujado con las funciones del Resultado de la demo (`eovrt_webconsole.demo.render`).
- **Figura 10 (EXT-01):** una imagen de `construction_site_safety` con las cajas de `machinery` de la corrida de
  obra.

Corre donde estén las corridas y va **antes** de `sacar_figuras.mjs`:

```bash
# En la Victus, adentro de la consola (monta el workspace en la misma ruta):
docker compose exec console sh -c 'python "$EOVRT_CONSOLE_REPO_ROOT/webconsole/tools/armar_figuras_privadas.py"'
# En la PC de desarrollo, con los paquetes privados que traen las corridas:
.venv/bin/python webconsole/tools/armar_figuras_privadas.py --raiz <paquete 11-07> --raiz <ws de la Victus>
```
