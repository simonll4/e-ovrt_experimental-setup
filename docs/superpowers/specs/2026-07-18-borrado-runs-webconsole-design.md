# Borrado de runs completos desde la web console

Fecha: 2026-07-18

## Problema

La web console no ofrece ninguna forma de borrar runs terminados. El media-plane
ya tiene un endpoint de borrado (`DELETE /api/runs/{id}`), pero el control-plane
no tiene ninguno (gap documentado en ADR-008 y `docs/operacion/38`/`51` — "sin
retención de `runs/`"), y la web console no expone borrado de ningún tipo hoy.
Sin esta capacidad, los directorios `runs/` de ambos planos crecen sin límite y
no hay forma de limpiar corridas de prueba/descartadas desde la UI.

## Alcance

- Borrado **físico** (hard delete): elimina el directorio `runs/<id>/` completo
  en disco, en ambos planos (media-plane y control-plane).
- Solo permitido sobre runs en **estado terminal** (`succeeded`, `failed`,
  `stopped`, `interrupted` en media-plane; equivalente en control-plane). Un run
  `running` no se puede borrar — hay que detenerlo primero.
- Disponible desde la web console en dos lugares: la lista de runs (`RunsPage`)
  y el detalle de un run (`RunDetailPage`), con un modal de confirmación previo
  al borrado (irreversible).
- Fuera de alcance: soft-delete/archivado, retención automática (GC) —
  ya existe `retention.py` en media-plane pero es un mecanismo aparte y no se
  toca en este trabajo — y borrado en batch/múltiple.

## Arquitectura

```
Frontend (RunsPage / RunDetailPage)
  → modal de confirmación → DELETE /api/runs/{id}  (webconsole backend, orquestador)
      → DELETE {media_plane}/api/runs/{media_run_id}    (ya existe)
      → DELETE {control_plane}/api/runs/{control_run_id} (nuevo, este spec)
```

El webconsole backend no persiste runs — resuelve el run correlacionado
(media_run_id + control_run_id, mismo mecanismo que ya usa `GET /api/runs`
para hidratar la lista) y llama a borrar en cada plano donde el run exista.

## Componente 1 — Control-plane: `DELETE /api/runs/{id}`

Nuevo endpoint en `src/eovrt_control/service/routers/runs.py`, espejando el
existente en media-plane (`src/eovrt_media/service/routers/runs.py:66-78`):

- 404 si el run no existe.
- 409 si el run no está en un estado terminal (no se borra nada).
- Si es terminal: `shutil.rmtree(run_dir)` + remoción del registro en memoria
  del `RunManager` → 204 sin contenido.

## Componente 2 — Webconsole backend: endpoint orquestador

Nuevo `DELETE /api/runs/{id}` en
`webconsole/backend/src/eovrt_webconsole/routers/runs.py`:

1. Resuelve el run correlacionado (media_run_id / control_run_id).
2. Si cualquiera de los dos lados presentes no está en estado terminal →
   409, no se borra nada en ningún lado.
3. Si ambos (o el único presente) están en estado terminal: llama DELETE a
   media-plane y, si existe `control_run_id`, a control-plane.
4. Si alguna llamada falla después de haber empezado a borrar (red, error
   inesperado): se responde con detalle de qué lado(s) fallaron y cuáles se
   borraron con éxito. El run queda parcialmente borrado — no se hace rollback.
5. El endpoint es **idempotente**: reintentar el DELETE sobre un run
   parcialmente borrado solo repite el/los lado(s) que faltan (un 404 de un
   plano ya borrado se trata como éxito en el reintento, no como error).

## Componente 3 — Frontend

- `api.ts`: nueva función `deleteRun(id)` → `DELETE /api/runs/{id}` (mismo
  patrón que `deletePromptSet`, líneas 123-124).
- `RunsPage.tsx`: botón "Borrar" por fila de la tabla, visible solo si el run
  está en estado terminal. Abre un modal de confirmación (id/nombre del run,
  aviso de que es irreversible). Al confirmar, llama `deleteRun` y refresca la
  lista.
- `RunDetailPage.tsx`: mismo botón/modal en la vista de detalle. Al confirmar y
  borrar con éxito, redirige a `RunsPage`.
- Si la respuesta indica fallo parcial, se muestra el error explícito (qué
  plano falló) y el run permanece visible en la lista para poder reintentar el
  borrado.

## Testing

- Control-plane: test del nuevo endpoint — 404 sin run, 409 con run `running`,
  204 + directorio removido con run terminal.
- Webconsole backend: test del orquestador — ambos planos ok, solo un lado
  presente, 409 si un lado no es terminal, fallo parcial reportado
  correctamente, reintento idempotente tras fallo parcial.
- Frontend: test de que el botón no aparece para runs `running`, que el modal
  bloquea el borrado sin confirmar, y que un fallo parcial se muestra sin sacar
  el run de la lista.
