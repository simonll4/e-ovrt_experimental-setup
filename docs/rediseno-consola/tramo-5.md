# Tramo 5 — Salud del distribuidor y repaso de punta a punta

Leé antes `01-reglas-codex.md`.

Único tramo que escribe código que **no** está en el árbol de referencia. Acá no
se copia: se implementa, chico y acotado.

---

## Parte A — `:8082` en la barra lateral (decisión D-5)

Hoy la barra lateral muestra la salud de **dos** servicios: `:8080` motor de
detección y `:8081` motor de reglas. Desde ADR-019/020 son **tres**: la consola
exige el servicio de distribución arriba cuando la distribución está habilitada,
y no dice si lo está.

### Backend

Dos archivos.

**1. `src/eovrt_webconsole/app.py`** — hoy crea dos clientes httpx en el arranque:
`app.state.http` (línea 59) y `app.state.control_http` (línea 65). **No hay
cliente para distribución.** Agregá `app.state.distribution_http` siguiendo el
mismo patrón, con `settings.distribution_service_url` como base — que **ya
existe**, con default `http://localhost:8082`. Sin esto, `_probe` no se puede
reusar y la parte 2 termina en una llamada httpx suelta.

**2. `src/eovrt_webconsole/preflight.py`** — la firma es:

```python
async def platform_preflight(app: FastAPI, manifest: ExperimentManifest | None = None) -> dict
```

En la línea 134 sondea media y control con `asyncio.gather` sobre `_probe`, y al
final devuelve:

```python
{"ready": not blockers, "blockers": blockers, "media": media, "control": control}
```

Sumar `"distribution"` con la misma forma que las otras dos (`service_url`,
`healthy`, `ready`), sondeando el cliente nuevo con `_probe`.

Ojo con dos cosas:

- En el archivo ya hay un sondeo al distribuidor,
  `_distribution_http_transport_checks`, pero es **otra cosa**: sólo corre bajo
  `if manifest is not None`, o sea en el preflight de un manifiesto de
  experimento, y produce *blockers*. La barra lateral llama a `/api/preflight`
  **sin** manifiesto, así que hoy no recibe nada de distribución. Lo que se
  agrega acá es el estado de salud permanente. No los mezcles.
- El distribuidor caído **no** debe volver `ready: false` ni agregar un blocker
  por sí solo. Sólo se informa. Convertirlo en bloqueo cambiaría el gateo del
  botón Lanzar, y eso es comportamiento troncal: el contrato se pondría rojo, con
  razón.

Test nuevo, al lado de los que ya existen para el preflight.

### Frontend

`webconsole/frontend/src/components/Shell.tsx`: tercer punto en el bloque
`.eo-sidebar__services`, junto a `:8080` y `:8081`, con el mismo tratamiento
visual y el mismo `title` descriptivo. Rótulo: **«Distribución de alertas»**,
puerto `:8082`.

---

## Parte B — Repaso de punta a punta

Los *outcomes de distribución* (ADR-019/020) son la única feature que **no
existe** en el árbol de referencia. Sobrevivieron al merge y sus tests están
verdes, pero **nadie los miró todavía con el aspecto nuevo**.

- Levantá la plataforma y recorré el flujo troncal completo con los tres
  servicios arriba.
- Mirá `ExperimentDetailPage` con un experimento que tenga outcomes de
  distribución: que se vean, que se entiendan y que no hayan quedado con estilos
  del armazón viejo.
- Recorré los cuatro flujos del contrato a mano, no sólo por tests.

---

## Cierre

```bash
cd webconsole/frontend && npm test && npm run build
cd webconsole/backend && ./.venv/bin/python -m pytest -q
```

- Contrato verde.
- Suites completas verdes, con el test nuevo del preflight.
- Capturas de la barra lateral con los tres servicios: los tres arriba, y con el
  distribuidor caído.
- Capturas de `ExperimentDetailPage` con outcomes de distribución.
- En el reporte: el recorrido manual de los cuatro flujos, dicho paso por paso,
  con lo que viste. Si algo quedó feo o raro y no lo arreglaste, decilo — no lo
  omitas.

Commit: `feat(webconsole): tramo 5 — salud del distribuidor y repaso integral`
