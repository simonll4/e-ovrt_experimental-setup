# Plataforma E-OVRT — deploy integral (single-host)

Stack completo de la plataforma en Docker Compose (✎ 2026-08-19; antes solo consola +
fleet media-plane): **consola web (:8090) + control-plane (:8081) + distribución de
alertas (:8082) + broker MQTT mosquitto (:1883, loopback) + fleet de instancias del
servicio media-plane** (una por modelo, mismo image, distinto `EOVRT_MODEL_REF`).
Las instancias media arrancan **apagadas** (profile `models`); se encienden/apagan
desde la página **Plataforma** de la consola, con la política *una activa a la vez*
(switch atómico). Los servicios core (mosquitto, control-plane, distribution, console)
son persistentes (`restart: unless-stopped`).

## Paridad de rutas (la regla que hace esto reproducible)

Consola, control-plane y distribución montan el workspace de repos hermanos **en la
misma ruta absoluta del host**: `${EOVRT_WORKSPACE}:${EOVRT_WORKSPACE}`. Motivo: los
contratos de la plataforma intercambian rutas absolutas por filesystem compartido —
los manifiestos usan rutas absolutas (ADR-009), y el `out_dir` del distribuidor es
una ruta que el BFF elige y ambos procesos deben ver (ADR-019 §3). Con paridad de
rutas, un path significa lo mismo en el host y en cualquier contenedor. Para
desplegar en otro host alcanza con clonar los repos hermanos y ajustar
`EOVRT_WORKSPACE` en `.env` — ninguna otra ruta está hardcodeada.

La consola monta el workspace `:ro` con remounts `rw` solo donde escribe
(`experiments/`, `prompts/`, `cameras/`, `runs/` del repo). Control y distribución
montan `rw` (escriben artefactos en rutas arbitrarias del workspace por diseño).

## Bootstrap (una vez)

```bash
cd e-ovrt_experimental-setup/infra/platform
cp .env.example .env                 # ajustar EOVRT_WORKSPACE (raíz absoluta del workspace)
mkdir -p ../../cameras               # gitignorado; evitar que el bind lo cree root
docker compose build                 # 4 imágenes: media-plane, control-plane, distribution, console
docker compose up -d                 # core: mosquitto + control-plane + distribution + console
```

Abrir http://localhost:8090 → página **Plataforma** → Activar `mp-mock` (o un modelo).

Requisitos en el host:
- Repos hermanos clonados bajo `EOVRT_WORKSPACE` (media-plane, control-plane,
  alert-distribution, experimental-setup, datasets).
- Pesos en `e-ovrt_media-plane/models/` (`make download-models`), y el text-encoder
  `models/yoloe/original/mobileclip2_b.ts` para YOLOE (ver `models/README.md` del
  media-plane).
- `nvidia-container-toolkit` para instancias GPU (`mp-mock` corre sin GPU).

## Endpoints y buses

| Componente | En la red `eovrt` | Publicado al host |
|---|---|---|
| consola (BFF + SPA) | `console:8090` | `:8090` |
| media-plane (instancia activa) | `mp-<modelo>:8080` | no (la consola orquesta y proxea) |
| control-plane | `control-plane:8081` | `:8081` |
| distribución | `distribution:8082` | `:8082` |
| mosquitto | `mosquitto:1883` | `127.0.0.1:1883` |
| bus detecciones (media XPUB) | `tcp://mp-<modelo>:5557` | no |
| bus alertas (control XPUB) | `tcp://control-plane:5558` | `127.0.0.1:5558` |

En configs/manifiestos escritos para ESTE deploy, los endpoints internos usan los
nombres de servicio de la red (`tcp://mp-gdino-tiny-560:5557`,
`tcp://control-plane:5558`, canal MQTT `host: mosquitto`). Los manifiestos históricos
con `tcp://127.0.0.1:...` son del despliegue como procesos del host y no son
portables a contenedores — no reescribirlos: son registro de sus corridas.

Hay dos buses y no son intercambiables: `control.input.bus` (`:5557`) lleva
detecciones media→control; `control.alert_bus` (`:5558`) lleva alertas
control→distribución. `alert_bus.enabled` es **false por default**: sin habilitarlo
en la config del control, la distribución lee 0 alertas aunque el control produzca.
El orden de suscripción se conserva (distribución antes que control, control antes
que media — PUB/SUB pierde lo anterior a la suscripción).

> ✎ **2026-08-28 — corrección del orden (`docs/operacion/130`, R-01).** El orden literal
> del párrafo anterior **no es el que ejecuta el runner**
> (`webconsole/backend/src/eovrt_webconsole/experiment/runner.py:1095-1149`): lanza
> **primero el control** (con `alert_bus.enabled: true` y `wait_for_subscriber_ms ≥ 10 s`),
> **después la distribución** (`POST :8082/api/runs`, que necesita el `control_run_id`) y
> **al final el media**. La no-pérdida en `:5558` no la garantiza la secuencia sino el
> handshake XPUB del publicador (`wait_for_subscriber` en el control-plane: no publica
> hasta ver al suscriptor o agotar la espera). Lo que sigue siendo obligatorio es que el
> consumidor del bus de detecciones (`:5557`, el control) esté suscripto **antes** de
> disparar el media.

## Operación

- La consola ejecuta `docker compose --project-name eovrt up -d --no-build <instancia>`
  / `stop` contra este directorio (visible por paridad de rutas en
  `${EOVRT_WORKSPACE}/e-ovrt_experimental-setup/infra/platform`). El `.env` con
  `EOVRT_WORKSPACE` viaja con el directorio: **paths absolutos de host**, necesarios
  porque compose corre dentro del contenedor de la consola pero los binds los
  resuelve el daemon en el host.
- El BFF alcanza control y distribución por la red interna
  (`EOVRT_CONSOLE_CONTROL_SERVICE_URL=http://control-plane:8081`,
  `EOVRT_CONSOLE_DISTRIBUTION_SERVICE_URL=http://distribution:8082`, seteadas en el
  compose). El transporte hacia la distribución es **HTTP por default (ADR-020,
  deroga ADR-018)**; el fallback `subprocess` NO está disponible dentro del
  contenedor (la imagen de la consola no instala `eovrt-distribute`) — es solo para
  el despliegue como procesos del host.
- `runs/` del media-plane es compartido entre TODAS las instancias: historial y
  compare cross-model completos desde cualquier target.
- Cambiar de modelo NO recarga in-process (Spec A): siempre es stop + up + carga.
- Artefactos del control quedan en `e-ovrt_control-plane/runs/` del host
  (`EOVRT_CONTROL_RUNS_DIR` con paridad de rutas); los del distribuidor en el
  `out_dir` que el BFF eligió para la corrida.

## Broker MQTT (distribución de alertas, spec 45 / ADR-016)

`mosquitto` es el broker canónico de este deploy (✎ 2026-08-19; el bloque dejó de
ser "declarado sin verificar" al containerizar el resto). Para el camino sin Docker
(procesos del host) sigue valiendo la alternativa liviana:

```bash
pip install amqtt          # broker MQTT 3.1.1 puro Python, sin apt/sudo
amqtt -c infra/platform/mosquitto/amqtt.yaml   # o el binario mosquitto si está instalado
```

`amqtt` respeta el mismo `mosquitto.conf` en espíritu (puerto 1883, anónimo, sin
persistencia) y es lo que se usó para verificar el camino `live` real del canal MQTT
del distribuidor (`docs/operacion/114`; PUBACK QoS 1 revalidado el 2026-08-13).
Tanto el puerto publicado por Docker como el broker aMQTT del host quedan ligados a
`127.0.0.1`: el acceso anónimo es solo para el laboratorio single-host. Credenciales,
si se usan, solo por env (`EOVRT_MQTT_USERNAME`/`EOVRT_MQTT_PASSWORD` en `.env`).

### Manifiesto del runner

La distribución es opt-in. Su `mode` debe coincidir con el del control-plane:

```yaml
runs:
  media:
    service: media-plane          # etiqueta; el target real lo resuelve la consola
    config: experiments/mi_corrida/media.yaml
    mode: run
  control:
    service: control-plane
    config: experiments/mi_corrida/control.yaml
    mode: live
  distribution:
    service: alert-distribution
    config: experiments/mi_corrida/distribution.yaml   # canal MQTT: host: mosquitto
    mode: live
    # Opcional: si falta, se deriva de control.alert_bus.endpoint.
    endpoint: tcp://control-plane:5558
    idle_timeout_ms: 300000
```

En live el runner habilita `alert_bus`, inicia control, lanza el distribuidor
suscripto a `:5558` y recién después dispara media. En replay espera media y
control, consolida, ejecuta el distribuidor sobre `control/alerts.jsonl` y
finalmente genera el reporte.

## Smoke de aceptación

1. `docker compose up -d` → `curl -sf localhost:8081/healthz && curl -sf localhost:8082/healthz`
   responden ok; http://localhost:8090 responde y `/platform` lista el fleet.
2. Activar `mp-mock` → pasa a TARGET ready; lanzar una corrida `demo_v2` corta → succeeded.
3. Activar `mp-gdino-tiny-560` (apaga mock solo) → correr un BENCH corto
   (`max_units` 10) → Evaluar → métricas visibles.
4. Corrida live con distribución: habilitar `alert_bus` en la config del control,
   `POST :8082/api/runs` (mode live) → control → media; verificar
   `distribution_summary.json` en el `out_dir` y los PUBACK contra mosquitto.
5. `docker compose stop` para bajar todo.

**Historial de verificación:**
- 2026-07-05: consola + fleet media verificados end-to-end (imágenes 13.2GB/399MB;
  mp-mock demo_v2 succeeded; switch a gdino-tiny; BENCH corto mAP50=0.6762 sobre
  10 imgs). Detalle en `.superpowers/sdd/progress-plataforma-docker.md` (Task 10).
- 2026-08-19/20: se agregan control-plane, distribution, mosquitto como camino canónico
  y paridad de rutas. **Los builds y el smoke integral 1–5 quedan pendientes por
  decisión** — se ejecutan cuando se cierren los repos, no ahora.

  **Verificado estáticamente** (sin daemon, todo client-side) para que el build futuro
  no falle por algo evitable:
  - `docker compose config` valida los **13 servicios**.
  - Los tres Dockerfiles (`media-plane`, `control-plane`, `alert-distribution`):
    `[build-system]` declarado, `packages.find where=["src"]` (o sea que copiar `src/`
    alcanza), y los entrypoints existen como console scripts —
    `eovrt-control`, `eovrt-distribute`— o son `uvicorn --factory` en el media-plane.
  - Ningún `pyproject.toml` declara `readme`, así que excluir `docs/` en el
    `.dockerignore` **no** rompe el build (es el footgun clásico de este patrón).
  - Todo lo que los Dockerfiles hacen `COPY` existe en su contexto de build.
  - Los `HEALTHCHECK` en forma exec son JSON válido y los snippets de Python parsean;
    el del media-plane usa `curl`, que su imagen sí instala (línea 8 de su Dockerfile).
    Los tres servicios que otros esperan con `condition: service_healthy` tienen
    healthcheck propio — sin eso, compose aborta el arranque de la consola.
  - **Todos los bind mounts resuelven y con el tipo correcto**: `mobileclip2_b.ts` y
    `mosquitto.conf` como ARCHIVO (si faltaran, Docker crearía un directorio en su
    lugar y el fallo sería silencioso), el resto como directorios.

  Lo único no verificable sin daemon: que las imágenes efectivamente compilen (resolución
  de dependencias, ruedas de CUDA) y el comportamiento en runtime.

## Seguridad

El socket de Docker montado en la consola es **root-equivalente en el host**. Aceptado
para este despliegue de laboratorio (single-user, sin exposición externa). Mitigación:
el BFF solo ejecuta 3 verbos compose con nombres validados contra el fleet declarado.
No exponer los puertos 8090/8081/8082 fuera del host sin revisar esto.
