# Vista de outcomes de distribución de alertas — diseño

Fecha: 2026-08-11
Repo: `e-ovrt_experimental-setup` · alcance: `webconsole/backend/` + `webconsole/frontend/`
Normativa: [ADR-016](../../../../docs/decisiones/adr-016-reapertura-acotada-distribucion.md)
§2a ("vista en la webconsole existente") · spec 45 §8 / `informe/92b` §10
("webconsole muestra los outcomes de entrega — no hay dashboard propio").

## 1. Contexto

`docs/operacion/114-relevamiento-distribucion-alertas.md` releva el módulo
`e-ovrt_alert-distribution` (spec 45, reabierto por ADR-016) y encuentra que su
6º criterio de terminado —integrar `distribution_summary.json` al reporte— ya
está resuelto (`report.py`, mismo día): la métrica `t_alert-notification` figura
sola en la tabla genérica "Resultados del experimento", y el summary completo
pasa verbatim en `report["distribucion"]`. Esta pieza es la que falta: **una
vista de outcomes por alerta**, que es lo que ADR-016 §2a nombra explícitamente
como parte del recorte comprometido.

**Hallazgo que fija la arquitectura:** `GET /api/experiments/{id}/alerts` no lee
el directorio consolidado — es un proxy en vivo al control-plane
(`control_backend.alerts(control_run_id)`, resuelto desde el estado en memoria
del `experiment_manager`). El módulo de distribución, en cambio, escribe en
`runs/exp_<id>/distribution/`, el mismo directorio consolidado que ya lee
`GET /api/experiments/{id}/report`. Por eso el join por-alerta no puede vivir en
el endpoint de alertas sin mezclar dos fuentes con ciclos de vida distintos: vive
en `report.json`, aditivo, igual que `censored_episodes`.

## 2. Backend: `report["distribucion_por_alerta"]`

Nueva función en `report.py`, mismo patrón que `_censored_episodes_detail` /
`_distribution_detail` (lectura tolerante, `{}` si no existe):

```python
def _distribution_outcomes_by_alert(consolidated_dir: Path) -> dict[str, dict]:
    """Ultimo DeliveryRecord por alert_id en notifications.jsonl. 'Ultimo' es
    el desenlace real: los intentos 'failed' de reintento quedan contiguos al
    mismo alert_id (Distributor.run() no intercala alertas), asi que la ultima
    linea escrita para ese alert_id es su outcome terminal -- delivered,
    dead_letter, suppressed_cooldown o skipped_duplicate."""
    path = consolidated_dir / "distribution" / "notifications.jsonl"
    if not path.is_file():
        return {}
    by_alert: dict[str, dict] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        alert_id = row.get("alert_id")
        if alert_id:
            by_alert[alert_id] = row
    return by_alert
```

Se llama en `generate_report()` junto a `_distribution_detail`, y el resultado se
agrega al dict devuelto como `"distribucion_por_alerta": ...`. Ningún campo
existente cambia; `{}` para toda corrida que no tenga `distribution/` (el 100%
de las corridas históricas hoy, porque el runner todavía no orquesta el
distribuidor — brecha B4 del doc 114, sin cambios en este diseño).

Cada valor del dict es el `DeliveryRecord` completo (outcome, notification_id,
`talert_notification_ms`, `latency_mode`, `attempted_at`); el frontend solo usa
`outcome`, el resto queda disponible sin trabajo adicional si hiciera falta
después.

## 3. Frontend: columna "Notificada" + tarjeta de conteos

**Tipo** (`types.ts`): agregar a `ExperimentReport` (tolerante, como el resto):
```ts
distribucion?: Record<string, unknown>
distribucion_por_alerta?: Record<string, { outcome: string }>
```

**Columna en "Alertas emitidas"** (`ExperimentDetailPage.tsx`): quinta columna
"Notificada". Para cada `alert.alert_id`, busca en
`report?.distribucion_por_alerta`. Tres estados, ninguno inventado:
- **hay entrada** → `Badge` con el outcome (tono `ok` si `delivered`, `neutral`
  si `suppressed_cooldown`/`skipped_duplicate`, `error` si `failed`/`dead_letter`)
  y su label vía `applicabilityLabel`-style lookup en un diccionario nuevo de
  `labels.ts` (`DISTRIBUTION_OUTCOME`), mismo mecanismo que `APPLICABILITY_CAUSE`
  (fallback al código crudo, nunca en blanco).
- **`report.distribucion_por_alerta` es `{}`** (módulo no corrió) → `—` con
  título/tooltip "el módulo de distribución no corrió para este experimento" (no
  es un error, es un artefacto que no existe todavía — mismo criterio que
  `alertsPending`).
- **hay dict pero sin esa alert_id** (no debería pasar si el módulo procesó
  todas las alertas del run, pero el código no lo asume) → `—` liso, sin
  tooltip especial.

**Tarjeta nueva "Distribución de alertas"**, después de la tarjeta "Alertas
emitidas": usa `report.distribucion` (ya expuesto). Contenido:
- si `{}` → `EmptyState` neutral, mismo texto que el caso `—` de arriba.
- si tiene datos → `Meter` con segmentos por outcome (mismo patrón que el
  desglose de severidad en `ExperimentSummary.tsx`) + una línea con la latencia
  p95 y su estado, leída de `report.resultados` (la fila `t_alert-notification`
  que ya existe — no se duplica el cálculo, se reusa `readMetricRow`) + su causa
  vía `applicabilityLabel(m.cause, APPLICABILITY_CAUSE)` cuando no es `computed`.
- si `skipped_invalid_alerts > 0` en `report.distribucion` → línea de aviso
  adicional (no es un outcome, es una anomalía de entrada — mismo espíritu que
  "no se inventa un valor, se cuenta y se muestra").

**Labels nuevos** (`labels.ts`):
```ts
export const DISTRIBUTION_OUTCOME: Record<string, string> = {
  delivered: 'entregada',
  suppressed_cooldown: 'suprimida (cooldown)',
  skipped_duplicate: 'duplicada (ya entregada)',
  failed: 'falló, reintentando',
  dead_letter: 'agotada (dead letter)',
}
```
Y agregar a `APPLICABILITY_CAUSE` las dos causas nuevas de `report.py`
(`no_notifications_delivered`, `distribution_wall_clock_dbe_only`) — ya
existen en el backend desde A1 pero no tenían label en el frontend todavía
(hoy caen al código crudo, que es un fallback válido pero no el mejor).

## 4. Fuera de alcance (ADR-016 §2a: sin dashboard propio)

Sin filtros, sin paginación propia, sin historial entre corridas, sin gráfico de
latencia — la tabla y la tarjeta muestran la corrida actual, nada más. Sin nuevo
endpoint HTTP: todo viaja en el `report.json` que el frontend ya pide. Sin tocar
`GET /alerts` (el proxy en vivo queda como está).

## 5. Testing

**Backend** (`test_report_generator.py`, TDD): `_distribution_outcomes_by_alert`
con notifications.jsonl de 2+ líneas para el mismo `alert_id` (una `failed`, una
`delivered`) → el dict debe quedarse con la `delivered`. Caso sin
`distribution/` → `{}`. Caso con múltiples alert_ids → cada uno resuelve al
suyo.

**Frontend** (`ExperimentDetailPage.test.tsx`, sigue el patrón existente de
mockear `getExperimentReport`): columna "Notificada" con `distribucion_por_alerta`
poblado (verifica el outcome correcto por fila) y vacío (verifica `—` + no
rompe). Tarjeta "Distribución de alertas": con datos (conteos correctos en el
`Meter`) y sin datos (`EmptyState`).
