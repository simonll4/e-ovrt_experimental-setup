# Demo en vivo de la defensa — operación en la Victus

Pantalla `/demo` de la consola (spec `docs/superpowers/specs/2026-10-23-demo-defensa-design.md`,
con su bloque ✎ 2026-10-26): la cadena completa cámara → detección → reglas temporales →
distribución → broker, en vivo, con la configuración congelada que evaluó el informe. Durante
la corrida solo se ve el estado (dos tarjetas: Casco y Chaleco); el video anotado, los cuadros
clave y la línea de tiempo se arman **después**, en el Resultado.

**Dos modos** (✎ 2026-10-31): por defecto `/demo` vive **dentro de la consola** (barra lateral,
migas y botones Iniciar · Finalizar · Evidencia · Proyectar), para preparar, ensayar y revisar sin
salir de ella. Con **`P`** (o el botón Proyectar) pasa a la **proyección**:
`http://localhost:8090/#/demo?proyectar=1`, oscura, letra grande, sin el armazón y sin consultas
globales, que es lo que se proyecta el día de la defensa (con el navegador en F11). `P` vuelve a
la consola. Al ir y volver del Resultado se conservan el modo y la variante.

**Cámara de la demo** (✎ 2026-11-01): en la consola, antes de iniciar, la tarjeta **Cámara** deja:
- **Ver el estado de cada cámara, siempre** (se actualiza sola cada 5 s mientras la pantalla está en Listo):
  *Activa*, *Sin respuesta*, *Con problemas* o *Sin comprobar*. Una RTSP se sondea por el puerto (liviano). La
  OAK-D **no se sondea sola** (abrirla ocupa su única conexión, F-101.5): su estado es el de la última
  comprobación explícita, con su antigüedad (vale 15 min).
- **Elegir** entre los presets de `cameras/` (OAK-D y RTSP). Se recuerda en el navegador y la proyección usa la
  misma. Con la OAK-D la plantilla manda (960×540 a 5 fps, lo medido): del preset solo se toma la dirección;
  un RTSP usa lo que dice su preset.
- **Comprobar** que se ve, con la causa y cómo arreglarlo. RTSP: puerto + `ffprobe` (resolución y cuadros por
  segundo). OAK-D: la prueba de `oakd_probe.py` en un proceso aparte dentro del motor activo (con una sesión o
  un experimento en curso no se abre: admite una sola conexión). Si falla ofrece acciones (volver a comprobar;
  reiniciar el motor cuando la causa es una cámara ocupada) y los pasos físicos del inyector PoE.
- **Ver la cámara**: vista previa en vivo para encuadrar, sin modelo (imagen directa). Al iniciar se corta sola y
  **durante la corrida la consola no recibe video, solo telemetría** (medido: ~7 KiB/s de JSON, 0 imágenes, 0
  WebSockets). Los cuadros se guardan en el motor y el **video con las detecciones se arma al terminar**
  (Resultado). Cortar la vista de la OAK-D reinicia el motor (F-101.5: queda «usado»).
- Las credenciales de un RTSP no viajan al navegador ni se guardan: al cerrar la sesión se redactan en `config/`.

**Teclas** (en proyección, todo por teclado): `I` iniciar · `F` `F` finalizar (dos veces
en menos de 2 s) · `E` / `Esc` capa de evidencia · `R` respaldo nivel 1 · `L` (en el
Resultado) volver a Listo, solo con el motor fresco · `P` proyectar / volver a la consola.

Scripts: `demo.ps1` (PowerShell, el camino principal en la Victus) y `demo.sh` (los mismos
comandos desde WSL; el chequeo del host que mira WSL —ruta a la cámara sin `via`, ARP, memoria
de la VM— solo se ve desde ahí). **La Victus no tiene entorno nativo**: el respaldo nativo de la
spec (D-3) no aplica; los comandos `native-up/down` solo lo dicen.

---

> ✎ 2026-11-01: para dejar **toda la plataforma** lista (núcleo, modelo activo, motor fresco y los dos
> chequeos previos) hay un solo comando: `infra/platform/plataforma.sh` (`plataforma.ps1` en PowerShell). `demo.ps1 up`
> sigue siendo el de la demo, y lo suyo es un subconjunto: ver `infra/platform/README.md`, «Levantar y verificar».

## 1. Preparación (una vez, después del `git pull`) — NO el día de la demo

Cambiaron dos imágenes: la **consola** (ffmpeg, Pillow, paho-mqtt y el núcleo del
control-plane) y el **control-plane** (`episodes[]` en `GET /api/runs/current`). El media-plane
y la distribución no cambiaron.

```powershell
cd <workspace>\e-ovrt_experimental-setup
.\infra\platform\compose.ps1 build console control-plane
.\infra\platform\compose.ps1 up -d --no-build console control-plane
```

Ese `up -d` **recrea** la consola y el control-plane (hay que hacerlo una vez para que tomen la
imagen y los montajes nuevos: `results/` y `defensa/sesiones/` en escritura). Es la operación
que en el doc 133 §5.5 tiró el adaptador de red de WSL: si después **ningún** puerto responde,
Inicio → Reiniciar Windows. Por eso se hace en la preparación y nunca el día de la demo.

Después:

```powershell
.\infra\demo\demo.ps1 up       # núcleo + mp-gdino-tiny-560 + motor fresco (no recrea nada)
.\infra\demo\demo.ps1 check    # chequeo del host -> defensa\sesiones\preflight_host.json
```

y abrir `http://localhost:8090/#/demo` (F11). Todo en verde = la tecla `I` funciona.

## 2. G1 — la cadena sin hardware (cámara de ensayo)

```powershell
.\infra\demo\demo.ps1 smoke
```

Levanta `mediamtx` + un `ffmpeg` que retransmite `a_p1_c04.mp4` (el clip de V1, un CR-01 a los
~7 s) como `rtsp://mediamtx:8554/ensayo`, corre una sesión con la variante de ensayo, espera un
CR-01 confirmado **y** su mensaje en el testigo MQTT, la finaliza, revisa que el Resultado tenga
video y apaga la cámara. Termina en `SMOKE G1 EN VERDE` o `EN ROJO`. Es también el build + smoke
del compose.

Para verlo en pantalla: `demo.ps1 camara-ensayo on` y `http://localhost:8090/#/demo?variante=ensayo`
(la pantalla anuncia «la entrada es una grabación; todo lo demás corre en vivo»).

Requisito: el clip en `e-ovrt_datasets/datasets/raw/clip_bench/clips/` (doc 134 §2).

## 3. G3 — ensayos con la OAK-D (en casa)

Escenario (spec §4): pared o fondo liso, una sola persona en cuadro, **remera lisa y oscura**,
cámara a 960×540 a 5 fps (ya en la plantilla), cable directo a la Victus. Guion: entrar con casco
y chaleco → sacarse el casco (CR-01 confirma a los ~4 s) → ponérselo (resuelve a los 2 s) →
sacarse el chaleco (CR-02 a los ~7 s) → ponérselo → `F` `F`.

**Un ensayo se aprueba** (spec §9) si CR-01 confirma dentro de los 6 s desde que se saca el casco,
el testigo recibe el mensaje, la alerta se resuelve al ponerse el casco, `bus_dropped_events = 0`
(lo muestra el indicador de cámara si no es cero), nada se cae y el Resultado está listo menos de
60 s después de `F` `F`. **5 seguidos.** CR-02 queda en vivo solo si pasa 4 de 5.

Después de cada `F` `F` la consola reinicia sola el motor (F-101.5: una corrida con la OAK-D por
vida del proceso); `L` vuelve a Listo cuando quedó fresco (~20–30 s).

**G3 se puede hacer dentro del rodaje en vivo de la generación 2** (RT-04,
`experiments/evidencia/README.md`): `infra\platform\rodaje.ps1 -Escena DEMO` corre exactamente este
guion por `/demo`, lo dice por voz con la hora real de cada acción y cierra con el equivalente de
`F` `F`; después `evidencia.ps1 correr RT-04` aplica este mismo criterio a cada toma `DEMO`
(«ensayos de la demo aprobados» y la mejor racha) y cuenta en cuántas CR-02 confirmó en vivo. Las
demás escenas del rodaje (P1…P9) también corren por `/demo`: son ensayos de la pantalla con otros
guiones.

## 4. G4 — ensayo general en la sala

- Al terminar, marcar esa sesión como **respaldo nivel 1** (tecla `R`):
  `.\infra\demo\demo.ps1 respaldo demo_AAAAMMDDTHHMMSSZ` (el id está en la URL del Resultado).
- **Nivel 2:** grabación de pantalla del ensayo general, un mp4 en `C:`, en una pestaña abierta de
  antemano (no depende de WSL ni de Docker).
- **Plan B de cámara:** la grabación del operario hecha en el ensayo, retransmitida por la cámara de
  ensayo: `$env:EOVRT_ENSAYO_DIR=<carpeta>; $env:EOVRT_ENSAYO_CLIP=<archivo.mp4>` y
  `demo.ps1 camara-ensayo on`, `/demo?variante=ensayo`.
- Las capturas para el informe salen de esta sesión.

## 5. El día (spec §7.2, adaptado a la Victus)

| Cuándo | Qué |
|---|---|
| T−60 | Inicio → **Reiniciar** (no Apagar). Trípode, cinta, PoE, cargador. `demo.ps1 up`, `demo.ps1 check` (y `demo.sh check` desde WSL para la ruta y el ARP de la cámara). Wi-Fi de la sede sin `172.20.x.x` |
| T−30 | Corrida de verificación completa: un ciclo de CR-01, `F` `F`, revisar el Resultado. El motor se reinicia solo |
| T−10 | `/demo` en Listo y todo en verde, **en proyección (`P`)**, F11, notificaciones y suspensión desactivadas, la pestaña del nivel 2 abierta |
| T0 | Se proyecta. Dos intentos fallidos → respaldo, sin depurar delante del tribunal |

Si una corrida queda colgada: `demo.ps1 reset` (reinicia control y distribución sin recrearlos, y el
motor). **Nunca** `docker compose up -d` el día de la demo.

---

## Decisiones de implementación (donde la spec dejaba lugar)

- **Granularidad escena** (`cr01_cr02_v2`), no el `_subject` de `oakd_docker_live`: lo que dice la spec.
- **Sin límite práctico de tiempo**: la sesión pasa un tope de 6 h al ejecutor (no infinito: el mismo
  valor viaja al cliente HTTP de la distribución). Cada espera del cierre en cascada tiene 30 s y el
  cierre entero 120 s; si se vencen, la sesión queda `failed` y el Resultado se arma igual.
- **Cierre por el operador** (`RunHooks.ended_by = "operator"`): el `stopped` del media es el fin
  normal; el experimento queda `succeeded` con `ended_by: operator` (no se agregó un estado nuevo al
  vocabulario de experimentos). El «Detener» de la consola no cambia.
- **La distribución no lleva `idle_timeout_ms`**: cierra con el `run_finished` que el control
  republica en el bus de alertas (verificado en el código: `zmq_source.py`). Un idle timeout cortaba
  la distribución en medio de una demo larga sin alertas.
- **`bus.wait_for_subscriber_ms: 10000`** en las dos plantillas de medios (slow joiner).
- **Lo amarillo no frena la tecla `I`**; solo lo rojo. Un chequeo del host de más de 15 min es lo
  normal en plena defensa (la demo puede llegar 30 min después de T−10).
- **Motor fresco** = lo reinició esta consola y el media-plane no tiene corridas nuevas desde
  entonces. Sin reinicio registrado (p.ej. si se reinició la consola) cuenta como rojo en compose:
  `demo.ps1 restart-motor` lo resuelve. El reinicio usa `docker compose restart`, que no recrea.
- **Cifras en pantalla**: se leen en el momento de `results/gen2/<ID>/resultado.json`
  (ALR-01 `f1`, ALR-07/ALR-08 `falsas_alarmas`, RT-03); si no existen, «cifra pendiente
  (generación 2)». Ningún número del informe v0.1 está escrito en la demo.
- **Principio 1 (no se toca lo medido)**: `comparar_corridas_control.py` compara dos corridas del
  control. Prueba hecha el 2026-10-26 con el clip `a_p1_c04` (escena y sujeto): los campos que
  difieren antes/después del cambio son exactamente los 27 que difieren entre dos corridas del mismo
  código (id de corrida y relojes); todo lo demás, idéntico.

## Archivos de una sesión (`defensa/sesiones/<id>/`, fuera de git: tiene caras)

`session.json` (ids, horarios, stack, huellas de lo congelado, `ended_by`) · `config/` (lo que se
mandó a cada servicio) · `preflight.json` · `state_log.jsonl` (cada estado mostrado, para que la
pantalla sea reproducible) · `witness.jsonl` (el testigo MQTT) · `resultado/` (`video.mp4`,
`cuadros/`, `linea_de_tiempo.json`, `resumen.json`, `log/`). **Nunca a la carpeta compartida.**
