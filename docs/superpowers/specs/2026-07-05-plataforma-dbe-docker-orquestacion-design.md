# Plataforma DBE containerizada + orquestación desde la consola — Diseño

- **Fecha:** 2026-07-05 · **Estado:** implementado y verificado — plan ejecutado (10/10 tareas), smoke integral de aceptación (Task 10) completo el 2026-07-05 (ver `docs/superpowers/plans/2026-07-05-plataforma-dbe-docker-orquestacion.md` y `.superpowers/sdd/progress-plataforma-docker.md`). Próxima fase: EBE dos nodos en contenedores.
- **Repos:** `e-ovrt_experimental-setup` (compose de plataforma, BFF orquestador, UI) + `e-ovrt_media-plane` (ajustes a la imagen del servicio). Ramas actuales (`feature/webconsole` / `feature/inference-service`), **sin merge a main**.
- **Depende de:** servicio media-plane Fase 1 + Feature C (evaluación BENCH por HTTP) + webconsole MVP — todo implementado y verificado.

## 0. Decisiones de alcance (cerradas con el usuario)

1. **Topología: DBE primero.** Esta fase containeriza y orquesta el pipeline single-host completo (consola + N instancias del servicio, un host GPU). EBE dos nodos es la fase siguiente, sobre esta base. Los artefactos two-node deprecados en `e-ovrt_media-plane/deploy/` NO se tocan.
2. **Ciclo de vida por consola.** El compose declara una instancia del servicio por modelo, apagadas; la consola las lista y las enciende/apaga desde la web. Cambiar de modelo no requiere terminal.
3. **Todo en compose + socket montado.** `docker compose up -d console` levanta la plataforma; el BFF corre containerizado con `/var/run/docker.sock` montado (riesgo root-equivalente documentado en §8, aceptado para host de laboratorio single-user).
4. **Una instancia activa a la vez, switch atómico.** A lo sumo una instancia del fleet running (incluye mock, para que "el target" sea siempre único). Activar otra = stop de las running → up de la nueva → esperar `/readyz`.
5. **Mecanismo: `docker compose` CLI por subprocess.** El compose es la única fuente de verdad del fleet (volúmenes, GPU, red); el BFF ejecuta 3 verbos: `up -d <svc>`, `stop <svc>`, `ps --format json`. Sin SDK de Docker.

## 1. Arquitectura

**Convención de infra (dos niveles):**
1. **Cada repo de servicio tiene su `/infra`** con lo necesario para construir su imagen y desplegar **solo ese servicio** standalone (Dockerfile + compose propio + README). El repo de servicio es el único dueño de su imagen.
2. **El repo `e-ovrt_experimental-setup` es dueño de la infra de plataforma**: compone los servicios (reutilizando las imágenes definidas en el `/infra` de cada repo, vía build context hermano) y agrega la orquestación.

```
e-ovrt_media-plane/infra/                      # deploy standalone del servicio de inferencia
├── docker/Dockerfile                          # imagen del servicio (se MUEVE el Dockerfile raíz acá)
├── docker-compose.yml                         # UNA instancia standalone: EOVRT_MODEL_REF por env,
│                                              #   volúmenes (models/, runs/, datasets, mobileclip), GPU
└── README.md

e-ovrt_experimental-setup/infra/
├── console/
│   ├── Dockerfile                             # imagen de la consola (multi-stage node→python+docker CLI)
│   └── docker-compose.yml                     # consola standalone (target externo por
│                                              #   EOVRT_CONSOLE_SERVICE_URL, modo static, sin socket)
├── platform/
│   ├── docker-compose.yml                     # PLATAFORMA completa (console + fleet de modelos)
│   └── README.md                              # bootstrap, smoke, troubleshooting, riesgo del socket
```

- El compose de plataforma construye las imágenes desde los `/infra` de cada repo: las instancias `mp-*` con `context: ../../../e-ovrt_media-plane` + `dockerfile: infra/docker/Dockerfile`; la consola con el `infra/console/Dockerfile` propio. **Una sola definición de imagen por servicio**, dueño el repo del servicio.
- El compose standalone del media-plane sirve para operar el servicio sin consola (dev/debug/CI del repo); el de plataforma es el despliegue integral.

Servicios del compose de plataforma:
  console          (sin profile: arranca con `up -d console`)   :8090 publicado
  mp-mock          profiles:[models]  EOVRT_MODEL_REF=mock                  (CPU)
  mp-gdino-tiny    profiles:[models]  EOVRT_MODEL_REF=grounding-dino/gdino-tiny  (GPU)
  mp-gdino-base    profiles:[models]  EOVRT_MODEL_REF=grounding-dino/gdino-base  (GPU)
  mp-yoloe-26s     profiles:[models]  EOVRT_MODEL_REF=yoloe/yoloe-26s            (GPU)
  mp-yoloe-26m     profiles:[models]  EOVRT_MODEL_REF=yoloe/yoloe-26m            (GPU)
  mp-yoloe-26l     profiles:[models]  EOVRT_MODEL_REF=yoloe/yoloe-26l            (GPU)
  mp-yoloe-26x     profiles:[models]  EOVRT_MODEL_REF=yoloe/yoloe-26x            (GPU)
```

(Criterio del fleet: una instancia por modelo con pesos presentes en `models/` del host. MM-GDINO queda fuera: la variante tiny fue descartada en Sprint 2 por bboxes rotas y las demás no están validadas.)

- Los build contexts referencian repos hermanos, igual que el acoplamiento sibling de todo el workspace.
- Todas las instancias `mp-*` usan **la misma imagen** (la definida en `e-ovrt_media-plane/infra/docker/Dockerfile` — es el `Dockerfile` raíz existente del Spec A §3.3, movido y ajustado en §2); solo difieren `EOVRT_MODEL_REF` y la reservation de GPU (mock sin GPU).
- `profiles: [models]` evita que las instancias arranquen con el `up` por default; solo la consola las enciende.
- Labels por instancia: `eovrt.instance=true`, `eovrt.model_ref=<ref>` — el BFF los usa para descubrir el fleet y validar nombres.
- Red bridge compartida `eovrt`: la consola resuelve `http://mp-gdino-tiny:8080` por nombre de service.
- Healthcheck de instancia: el ya definido en la imagen (`curl /readyz`, `start_period` 180s).

## 2. Imagen del servicio media-plane (ajustes, no rehacer)

El `Dockerfile` raíz existente **se mueve a `infra/docker/Dockerfile`** (build context = raíz del repo) y queda como base; `infra/docker-compose.yml` nuevo lo usa para el deploy standalone de UNA instancia (modelo por env). Ajustes a la imagen:

- **Pesos por volumen, no en imagen**: el host monta `models/` (ro) en `/app/models`. Los catálogos ya usan paths relativos al CWD (`local_dir: models/grounding-dino/...`, `weights: models/yoloe/...`) y `WORKDIR /app`, así que resuelven sin cambios. `HF_HOME=/data/weights` (volumen compartido) queda como cache de fallback si un `local_dir` falta.
- **Cache MobileCLIP (YOLOE)**: `mobileclip2_b.ts` (253 MB, ya descargado en el root del host) se monta ro en `/app/mobileclip2_b.ts`. (Alternativa si molesta el bind: materializarlo en la imagen al build, como hacía el Dockerfile.node-b deprecado.)
- **Datasets cross-repo**: el repo `e-ovrt_datasets` completo montado ro en `/e-ovrt_datasets`. Con `WORKDIR /app`, el auto-discovery del GT (`../e-ovrt_datasets/...` relativo al CWD) resuelve idéntico al host → la evaluación BENCH funciona en contenedor sin tocar código. Los catálogos de datasets (`configs/datasets/*.yaml`, paths `../e-ovrt_datasets/...`) resuelven por la misma razón.
- **`runs/` compartido**: bind del `runs/` del host en `/data/runs` (`EOVRT_RUNS_DIR`) en TODAS las instancias. Clave: el historial y el compare cross-model funcionan desde cualquier instancia activa (`list_runs` lee disco). La política una-activa-a-la-vez elimina escrituras concurrentes; los `run_id` llevan sufijo uuid igual.
- **Device**: `device: auto` (ya implementado) resuelve `cuda` con la reservation NVIDIA y `cpu` en mock. Sin `EOVRT_MODEL_DEVICE` en el compose.
- Verificado existente: `constraints.txt` (el COPY del Dockerfile), `.dockerignore`.

## 3. BFF — orquestador y target dinámico

Módulo nuevo `src/eovrt_webconsole/orchestrator.py` con dos unidades:

### 3.1 `ComposeOrchestrator`
- Ejecuta `docker compose` por `asyncio.create_subprocess_exec` (timeout por comando, cwd=`EOVRT_CONSOLE_COMPOSE_DIR`).
- `fleet()` → lista declarada: parsea `docker compose config --format json` una vez al startup (cacheada) y filtra services con label `eovrt.instance` → `{name, model_ref}`. **Allowlist**: todo nombre de instancia que entre por API se valida contra este set (404 si no está) — nunca input libre hacia el socket.
- `ps()` → estado actual: `docker compose ps -a --format json` → `{name: {state, health}}`.
- `up(name)` / `stop(name)` → los verbos correspondientes. Errores de subprocess (exit≠0) → excepción con stderr capturado.

### 3.2 `TargetManager`
- Reemplaza el target fijo: mantiene `active: str | None` (nombre de instancia) y el `httpx.AsyncClient` apuntando a `http://<name>:8080`. Swap = cerrar cliente viejo, crear nuevo, actualizar `app.state.http/backend` (la costura `RunBackend` no cambia: recibe el cliente).
- **Bootstrap del BFF**: `ps()` → si hay exactamente una instancia running → target; si ninguna → target `None` (la UI ofrece activar); si varias (estado anómalo, p.ej. crash previo del BFF a mitad de switch) → target `None` y warning en log (el próximo activate normaliza: apaga todas y enciende una).
- **`switch(name)` (atómico):**
  1. `name` ∉ fleet → `UnknownInstance` (404).
  2. Run activo en el target actual (`GET /api/runs` del target: alguno `running`) → `PlatformBusy` (409, con el `run_id`).
  3. `name` ya es el target y está ready → no-op (200).
  4. `stop` de toda instancia del fleet en estado running.
  5. `up -d name`.
  6. Poll `http://<name>:8080/readyz` cada 2s hasta ready o timeout (`EOVRT_CONSOLE_SWITCH_TIMEOUT`, default 300s — la carga desde volumen tarda 30s–3min).
  7. Ready → swap del cliente, target=`name`. Timeout/error → `SwitchFailed` (504/502 con el paso que falló); **sin rollback automático**: el estado queda honesto (target `None`, instancia según docker) y el retry es manual.
- `stop_active()` → apagar el target sin activar otro (target pasa a `None`). Misma guarda de run activo (409).

### 3.3 Compatibilidad (crítico para no romper lo existente)
- La orquestación se habilita **solo si `EOVRT_CONSOLE_COMPOSE_DIR` está seteado**. Sin esa var: modo `static` — target fijo `EOVRT_CONSOLE_SERVICE_URL`, endpoints de plataforma responden 501 ("orquestación no habilitada"), y TODO lo demás opera exactamente como hoy. `make dev-backend`, el flujo actual y los 116 tests existentes no se tocan.
- En modo orquestado, `EOVRT_CONSOLE_SERVICE_URL` se ignora (el target es dinámico).

## 4. API del BFF

```
GET  /api/platform/instances
  → 200 [{"name":"mp-gdino-tiny","model_ref":"grounding-dino/gdino-tiny",
           "state":"running|exited|created|absent","ready":true|false,
           "is_target":true|false}]
     (merge de fleet() + ps() + readyz del target; `ready` solo se sondea para la running)
  → 501 si modo static

POST /api/platform/instances/{name}/activate
  → 200 {"target":"mp-gdino-tiny","model_ref":"..."}     (switch completo)
  → 404 instancia fuera del fleet
  → 409 {"detail","run_id"} run activo en el target actual
  → 502/504 {"detail","step"} docker falló / readyz timeout
  → 501 modo static

POST /api/platform/stop
  → 200 {"target":null}      (apaga el target actual; 409 si run activo; no-op si no hay target)
```

Sin WS/SSE de progreso: la UI pollea `GET /api/platform/instances` durante el switch (el POST es síncrono con timeout largo; el `fetch` del SPA no impone timeout propio, así que la llamada espera al BFF). `GET /api/target` (existente) sigue siendo la verdad del target: en modo orquestado reporta la instancia activa o `healthy:false` si no hay.

## 5. Frontend

- **Página nueva "Plataforma"** (`/platform`, link en el nav): tabla del fleet (nombre, modelo, estado docker, ready, badge TARGET), botón **Activar** por fila (confirm si implica apagar otra; durante el switch: fila en "activando…", botones deshabilitados, poll de instances hasta resolverse) y **Apagar** en el target. Errores del switch visibles con el paso que falló.
- `types.ts`: `PlatformInstance`; `api.ts`: `getInstances()`, `activateInstance(name)`, `stopPlatform()`.
- Modo static (501): la página muestra "orquestación no habilitada" con hint de configuración.
- El resto de las páginas no cambia: componen/corren/evalúan contra el target activo vía los endpoints existentes. `TargetBadge` ya pollea `/api/target` y refleja el switch solo.

## 6. Imagen de la consola

`e-ovrt_experimental-setup/infra/console/Dockerfile`, multi-stage:
1. `node:20-slim`: `npm ci && npm run build` del frontend → `dist/`.
2. `python:3.11-slim`: BFF instalado + `dist/` (el `create_app` ya sirve la SPA si existe `frontend/dist`) + **docker CLI + compose plugin** (paquete `docker-ce-cli` + `docker-compose-plugin` del repo apt de Docker).

`infra/console/docker-compose.yml` (standalone) levanta solo la consola en modo static contra un `EOVRT_CONSOLE_SERVICE_URL` externo, sin socket — el deploy "solo este servicio" del repo.

Montajes del service `console` en el compose de **plataforma**: `/var/run/docker.sock`, el dir `infra/platform/` (ro, para `compose config/ps/up/stop` con `-f`), `prompts/` (ro), `experiments/` (rw — saveManifest escribe). Env: `EOVRT_CONSOLE_COMPOSE_DIR=/infra/platform`, `EOVRT_CONSOLE_REPO_ROOT=/repo` (montando la raíz del repo experimental-setup ro salvo experiments). Puerto 8090 publicado.

Nota: los comandos compose del BFF usan `--project-name eovrt` fijo, para que el proyecto sea el mismo lo lance quien lo lance.

## 7. Manejo de errores (end-to-end)

| Situación | Servicio/docker | BFF | UI |
|---|---|---|---|
| Activar con run corriendo | — | 409 + run_id | "Hay un run activo; esperá o detenelo" |
| Instancia desconocida | — | 404 | — (la UI solo ofrece el fleet) |
| Docker/compose falla | exit≠0 | 502 + stderr + step | error visible con causa |
| readyz nunca llega | instancia unhealthy | 504 + step="readyz" | "la instancia no levantó" + retry |
| Sin target (nada running) | — | /api/target healthy:false | badge rojo + link a Plataforma |
| BFF reinicia a mitad de switch | — | bootstrap re-descubre (§3.2) | estado consistente al recargar |
| Modo static | — | 501 en /api/platform/* | página con hint de config |

## 8. Seguridad

El socket de Docker montado en la consola es **root-equivalente en el host**. Aceptado explícitamente para este despliegue (host de laboratorio, single-user, sin exposición de red externa). Mitigaciones: (a) la superficie del BFF hacia docker son 3 verbos compose con nombres validados contra la allowlist del fleet declarado; (b) sin endpoint de creación paramétrica de contenedores; (c) riesgo documentado en `infra/platform/README.md`. Revisitar si la consola alguna vez se expone fuera del host. El compose standalone de la consola (`infra/console/`) NO monta el socket.

## 9. Testing

- **Orchestrator (pytest, sin docker):** subprocess fakeado (monkeypatch de `create_subprocess_exec`) — parseo de `config`/`ps` JSON, allowlist (404), secuencia del switch (stop→up→poll→swap) con readyz fakeado por httpx MockTransport, guarda de run activo (409), timeout (504 sin rollback), bootstrap con 0/1/N running, no-op si ya es target.
- **Router platform (pytest):** endpoints contra orchestrator fake; 501 en modo static; mapeos de error.
- **Frontend (vitest):** página Plataforma con api mockeada — render del fleet, flujo activar (spinner→target), error visible, modo 501.
- **Smoke real (manual, documentado en `infra/platform/README.md`, no en pytest):** `docker compose build` → `up -d console` → abrir :8090 → activar `mp-mock` desde la web → correr un run mock e2e → activar `mp-gdino-tiny` → run BENCH corto + evaluar. Este smoke es el criterio de aceptación de la fase. Smoke del standalone del media-plane (en su `infra/README.md`): `docker compose up` con `EOVRT_MODEL_REF=mock` → `curl /readyz` + un run por API.

## 10. Alcance y no-objetivos

- **Tasks estimadas:** ~11–14 (media-plane: mover Dockerfile a `infra/` + ajustes + compose standalone ~2; experimental-setup `infra/`: Dockerfile.console + compose console standalone + compose plataforma + READMEs ~3; BFF: orchestrator, TargetManager+settings, endpoints ~3–4; frontend: types/api, página Plataforma ~2; smokes E2E ~1–2).
- **NO (YAGNI):** EBE/two-node (fase siguiente; el fleet declarativo es el hook — agregar services no cambia el mecanismo), redeploy paramétrico (contenedores al vuelo), build de imágenes desde la web, multi-host, autenticación/multi-usuario, HTTPS, streaming de logs de contenedores en la UI, OAK-D, recarga de modelo in-process (sigue prohibida por Spec A).
