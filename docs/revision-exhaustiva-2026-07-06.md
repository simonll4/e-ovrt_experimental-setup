# Revisión exhaustiva del workspace — 2026-07-06

> ⚠️ **DOCUMENTO HISTÓRICO (2026-07-06)** — describe el mundo de dos repos/dos servicios
> previo a ADR-016…020 (hoy son tres servicios HTTP config-driven: media `:8080`,
> control `:8081`, distribución `:8082`); los conteos de tests y composes ya no son
> actuales. **Manda esta nota, no el cuerpo.**

Auditoría de pies a cabeza de los dos repos activos del proyecto (`e-ovrt_media-plane`,
rama `feature/inference-service`, y `e-ovrt_experimental-setup`, rama `feature/webconsole`),
ejecutada con 4 auditores independientes en paralelo (legacy/configs por repo, alineación
cross-repo, verificación funcional) más 2 agentes de corrección. Objetivo: confirmar estado
actual, alineación entre repos, funcionalidad completa, y ausencia de código/configs legacy.

**Veredicto global: FUNCIONAL COMPLETO, sin legacy de código real.** La deuda encontrada
fue casi toda documental y quedó corregida el mismo día (ver §4).

---

## 1. Verificación funcional (evidencia de ejecución real, no supuestos)

| Verificación | media-plane | webconsole (experimental-setup) |
|---|---|---|
| Tests | **435 passed** (pytest, 1 warning de librería) | backend **141 passed** + frontend **38 passed** (8 archivos vitest) |
| Lint (ruff) | limpio | limpio |
| Type-check / build | `create_app()` arranca con mock | `tsc --noEmit` limpio; build prod 189.49 kB (61.48 kB gzip) |
| Docker composes (`config --quiet`) | los 4 parsean (`infra/`, `infra/twonode/` ×3) | `infra/platform/` + `infra/console/` parsean |
| Imágenes Docker | `eovrt/media-plane:latest` (13.2GB) y `eovrt/media-plane-edge:latest` (970MB) presentes, rebuild del día | — |
| Makefiles (dry-run) | todos los targets coherentes | ídem (7 targets) |

Los únicos warnings son de librerías de terceros (httpx/starlette testclient,
websockets legacy, React Router future-flags) — ninguno del código propio.

## 2. Legacy de código: erradicado

Las tres grandes transiciones del proyecto se verificaron limpias:

- **CLI `eovrt-media` → servicio HTTP**: sin `[project.scripts]` colgantes, sin
  referencias vivas al binario (solo menciones históricas legítimas que explican
  la eliminación).
- **`deploy/` → `infra/twonode/`**: cero referencias a `deploy/` fuera de
  specs/planes fechados y `docs/_archive`.
- **Consola subprocess/tailing → cliente HTTP**: cero restos de spawn/tailing en
  `webconsole/`; el único `subprocess` es el de `ComposeOrchestrator` (legítimo,
  para `docker compose`).

Sin imports/deps/settings/componentes huérfanos en ninguno de los dos repos.
Los `.gitignore` cubren lo que deben (pesos, runs, venvs, node_modules, dist).

**Caso especial — `two_node_local.py`**: el auditor lo marcó como código muerto
(helpers inalcanzables en producción tras el guard `RuntimeError`), pero esos
helpers fueron **preservados deliberadamente** por decisión de la spec de Fase 2
(2026-07-05: "remover `run_two_node_local` y helpers de subprocess, preservar
generación de config"). Fix aplicado: nota en el docstring del módulo
documentando la decisión, en vez de borrar.

## 3. Alineación cross-repo: verificada OK

- **Contrato servicio↔BFF↔frontend**: consistente campo por campo, incluidos los
  campos nuevos `live` y `summary.run_descriptor.topology` (feature de
  visibilidad two-node, spec `2026-07-06-webconsole-twonode-visibility-design.md`).
- **Paths cross-repo**: `configs/datasets/*.yaml` del media-plane resuelven a
  carpetas hoja reales de `e-ovrt_datasets` (coherente con `ImageFolderSource`
  no-recursivo); todos los mounts de los composes existen en disco; el two-root
  loader encuentra `prompts/` correctamente.
- **Vocabulario canónico v2**: los 3 prompt sets usan exactamente
  `person/helmet/vest/bare_head`; sin referencias al view deprecado
  `canonical_cr01_cr02` (el prefijo `cr01_cr02` de los archivos refiere a las
  condiciones de riesgo, no al view legacy).
- **Docs de topología**: fieles a la implementación real (ZeroMQ REQ/REP +
  heartbeat PUSH/PULL + `request_timeout_ms=10000`).
- **Nombres de imagen Docker**: idénticos en los 8 puntos de uso (Dockerfiles,
  composes de ambos repos, test de contrato, orquestador).

## 4. Hallazgos y correcciones aplicadas (mismo día, en working tree)

### media-plane (7 archivos)
| Hallazgo | Fix |
|---|---|
| 4 docs decían "Fase 2 pendiente de decisión" (README, CLAUDE.md, docs/usage.md, docstring de `tools/debug_run.py`) cuando Fase 2 ya se completó y verificó | Reformulados: el reemplazo es `infra/twonode/` (ya existente); la ruta local `run_two_node_local` queda deshabilitada permanentemente |
| Docstrings de `config/loader.py` y CLAUDE.md mencionaban el flag CLI `--catalog-root` (murió con el CLI) | Solo queda `EOVRT_MEDIA_CATALOG_ROOT` / parámetro programático |
| Helpers de `two_node_local.py` sin explicación de por qué se conservan | Nota en docstring del módulo (decisión spec Fase 2) |
| CLAUDE.md del **workspace** apuntaba a rutas muertas de los scripts deprecados de datasets | Actualizadas a `e-ovrt_datasets/legacy/scripts/...` |

Verificación post-fix: 435 passed, ruff limpio.

### experimental-setup (6 archivos)
| Hallazgo | Fix |
|---|---|
| Spec B original (`2026-07-01-webconsole-design.md` §4) describía una arquitectura EBE con servicio HTTP en Nodo B que nunca se construyó, sin señalización | Nota "**superseded**" apuntando a la spec vigente (2026-07-06); texto original intacto como historia |
| 4 referencias a comandos `eovrt-media` inexistentes (`docs/experiments.md` ×2, `docs/prompt-sets.md` ×2) | Reemplazadas por los flujos reales (webconsole / `POST /api/runs` / `python -m eovrt_media.tools.inspect_runs compare`; la validación ocurre al lanzar, 422) |
| Tabla de experimentos desactualizada: faltaban `video_annotated.yaml` y `video_annotated_gdino.yaml`; fila `yoloe_video` con dataset incorrecto | Filas agregadas; corregido a `demo_v2 (stride 5)` |
| README raíz no mencionaba `infra/` (subsistema completo invisible) | `infra/platform/` e `infra/console/` agregados al layout con descripción |
| `infra/platform/.env` commiteado con path absoluto local del autor | `.gitignore` de raíz creado; `.env` destrackeado (`git rm --cached`, sigue en disco; `.env.example` sigue versionado) |
| Warning de `websockets.legacy` ensuciaba la salida de pytest | `filterwarnings` agregado en `webconsole/backend/pyproject.toml` |

Verificación post-fix: 141 passed.

### Clasificados OK-INTENCIONAL (no tocar)
- `mm-gdino-tiny.yaml` en el catálogo de modelos pese al descarte de Sprint 2:
  es catálogo de capacidades declarativo, no de modelos "activos".
- 4 manifiestos MM-GDINO en `experiments/bench_v2/`: provenance de corridas ya
  ejecutadas (naming `e5`/`e6` estable), historia legítima.
- `infra/console/` vs `infra/platform/`: dos modos de despliegue deliberados
  (consola standalone vs plataforma completa), no duplicación.
- El caveat de `debug_run` en CLAUDE.md del media-plane sigue siendo válido
  (describe la ruta local, distinta del mecanismo dockerizado).

### Cosmético conocido, no corregido (deuda menor aceptada)
- `fake_service.py` no replica `bench_split`/`evaluated` en el branch del run
  activo, y duplica mensajes de error como strings literales.
- `E501` (line-length) no está en el select de ruff del backend de la consola.
- `infra/console/Dockerfile` copia `src` antes del `pip install` → invalida la
  capa de deps en cada cambio de código (mismo patrón que costó ~11 min de
  rebuild en `infra/twonode`). Optimización de build, no bug.
- `scripts/datasets/steelbench.py` (media-plane): script standalone sin
  documentar en Makefile/README.
- Deuda Fase 2 ya trackeada en `.superpowers/sdd/progress.md` de este repo
  (round-trip source.type video, quiet-stream WS, `manifest_to_composition` /
  `validateComposition` sin consumir, etc.).

## 5. Estado de los working trees (al cierre de esta revisión)

Ambos repos tienen trabajo **sin commitear** (regla del workspace: commits solo
a pedido explícito):

- **media-plane**: implementación de la spec de visibilidad two-node (Tasks 1-3:
  finalización garantizada de `run_node_b`, `running`+`live` en el disk-scan,
  ownership two-node en `reconcile_orphan_runs`) + fixes documentales de esta
  revisión. El campo `live` ya es consumido por la consola: **es el punto de
  mayor riesgo si este working tree se pierde**.
- **experimental-setup**: BFF+frontend de la visibilidad two-node (Tasks 4-5:
  propagación `live`/`topology`, badge, guarda del WS anti reconnect-loop) +
  spec y plan (untracked) + fixes documentales + destracking de `.env`.

La feature completa fue revisada con gates independientes por task, un Critical
real corregido en el camino (AttributeError en `reconcile` ante config mal
formada), smoke E2E con Docker real (3 escenarios: mock, kill de Nodo A,
reconciliación durante run en vuelo), y whole-branch review final cross-repo:
**"Ready to merge"** sin Critical/Important.

## 6. Referencias

- Spec de la feature: `docs/_archive/superpowers/specs/2026-07-06-webconsole-twonode-visibility-design.md`
- Plan ejecutado: `docs/_archive/superpowers/plans/2026-07-06-webconsole-twonode-visibility.md`
- Ledgers de ejecución: `.superpowers/sdd/progress.md` (este repo) y
  `e-ovrt_media-plane/.superpowers/sdd/progress.md`
- Smoke E2E documentado: `e-ovrt_media-plane/infra/twonode/README.md`,
  sección "Visibilidad en la consola web (2026-07-06)"
