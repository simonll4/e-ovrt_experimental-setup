# Integración completa de distribución de alertas — diseño

Fecha: 2026-08-12
Repo: `e-ovrt_experimental-setup`
Normativa: [ADR-016](../../../../docs/decisiones/adr-016-reapertura-acotada-distribucion.md)
§2a, spec 44, spec 45 y ADR-014.

## 1. Objetivo y fronteras

Cerrar A2 y B4 del relevamiento 114: mostrar outcomes de entrega en la webconsole y hacer que el
runner orqueste `eovrt-distribute` tanto en DBE-replay como en live. También se termina la
declaración operacional del broker ya incorporada al compose. No se crea endpoint nuevo, dashboard
dedicado, canal adicional ni historial global entre corridas.

El distribuidor sigue siendo un proceso por corrida. Convertirlo en daemon HTTP o hacer que el BFF
reimplemente su pipeline mezclaría responsabilidades y queda fuera de alcance.

## 2. Declaración en el manifiesto

`runs.distribution` es opcional y usa el mismo `PlaneRun` con estos campos:

```yaml
runs:
  distribution:
    service: eovrt-alert-distribution
    config: ../e-ovrt_alert-distribution/configs/example.yaml
    mode: replay
    endpoint: null
    idle_timeout_ms: null
```

`PlaneRun` incorpora `endpoint: str | None` e `idle_timeout_ms: float | None`. Solo el bloque
`distribution` los consume. Su `mode` debe coincidir con `runs.control.mode`; una contradicción se
rechaza antes de llamar a cualquier backend. Si el bloque falta, las corridas históricas conservan
su comportamiento y el reporte expone `distribucion: {}` / `distribucion_por_alerta: {}`.

## 3. Ejecución testeable

El runner recibe un callable asíncrono inyectable `run_distribution`; el default administra
`eovrt-distribute` con `asyncio.create_subprocess_exec`, captura stdout/stderr, aplica timeout y
devuelve el summary JSON. Los tests usan un fake y no requieren broker ni binario instalado.

El ejecutable se resuelve en este orden: `EOVRT_DISTRIBUTION_EXECUTABLE`, `PATH`, y el venv del repo
hermano. La ruta de config declarada se pasa sin reinterpretar, igual que las configs de los otros
planos.

### DBE-replay

1. media termina con éxito;
2. control replay termina con éxito;
3. se consolida media/control en `runs/<experiment_id>/`;
4. se ejecuta `replay --alerts <consolidado>/control/alerts.jsonl --out-dir
   <consolidado>/distribution --config <config>`;
5. se ejecutan la evaluación temporal y `write_report`.

La distribución corre después de consolidar para consumir una ruta estable y para que el reporte
incluya sus artefactos en el mismo intento.

### Live

1. el runner fuerza `control_config.alert_bus.enabled=true` y un
   `wait_for_subscriber_ms` mínimo de 10000 cuando hay bloque de distribución;
2. lanza control y confirma su suscripción al bus de media como hoy;
3. arranca `eovrt-distribute live` antes de lanzar media;
4. deriva el endpoint de conexión del endpoint de bind del control (`0.0.0.0` o `*` se traduce a
   `127.0.0.1`), salvo que `runs.distribution.endpoint` lo declare explícitamente;
5. lanza media y espera media, control y distribución;
6. consolida y genera el reporte.

El `wait_for_subscriber_ms` del XPUB es la barrera de readiness: el publicador no procesa alertas
antes de observar la suscripción del distribuidor. El sentinel `run_finished` termina el proceso
distribuidor. `idle_timeout_ms` es solo una salvaguarda configurable si el sentinel no llega.

## 4. Semántica de fallo y resultado

`ExperimentResult` agrega `distribution_status: str | None`. Si el manifiesto pidió distribución,
un exit code no cero, timeout, summary ausente o summary inválido deja
`distribution_status="failed"`, `ok=false` y no genera un reporte final que aparente una cadena
completa. Si el bloque no existe, el campo queda `None` y no modifica la compatibilidad.

En live, si media/control fallan, el runner termina el proceso distribuidor de manera cooperativa
primero y forzada solo después del timeout. Nunca deja un hijo huérfano. Los mensajes de error no
incluyen credenciales del broker ni el contenido de la config.

## 5. Reporte y webconsole

El backend implementa `distribucion_por_alerta` según la spec específica del 2026-08-11: lee
`distribution/notifications.jsonl` y conserva el último `DeliveryRecord` por `alert_id`.

El frontend agrega:

- tipo tolerante para `distribucion` y `distribucion_por_alerta`;
- diccionario `DISTRIBUTION_OUTCOME` y labels de las dos causas nuevas;
- columna “Notificada” en “Alertas emitidas”, con tonos y fallback crudo;
- tarjeta “Distribución de alertas” con `Meter`, conteos, p95/estado reutilizado desde
  `report.resultados` y aviso por `skipped_invalid_alerts`;
- estado vacío neutral cuando el módulo no corrió.

No se toca `GET /api/experiments/{id}/alerts`: las alertas siguen viniendo del control-plane y los
outcomes persistidos siguen viniendo del reporte consolidado.

## 6. Empaquetado y operación

Mosquitto permanece en `infra/platform/docker-compose.yml`. El control-plane y el distribuidor se
ejecutan como procesos del host en la topología actual y no mantienen imágenes propias. La
documentación incluye comandos de arranque,
configuración del bloque `runs.distribution` y el orden live.

No se agrega un servicio persistente `distribution` al compose: no existe un daemon que deba quedar
escuchando entre corridas.

## 7. Pruebas y criterio de terminado

- Backend: último outcome por alerta, múltiples alertas y ausencia de artefacto.
- Runner replay: orden media-control-consolidación-distribución-reporte y propagación del fallo.
- Runner live: barrera XPUB, distribución antes de media, espera del hijo y limpieza ante error.
- Manifiesto: compatibilidad sin distribución y rechazo de modos contradictorios.
- Frontend: columna poblada/vacía, labels, tonos, tarjeta con conteos/latencia/anomalías y EmptyState.
- Suites completas de backend/frontend, Ruff y build de TypeScript.
- Smoke DBE real que produzca `runs/<experiment_id>/distribution/` y un `report.json` con outcomes.
- Smoke live real contra broker MQTT cuando los servicios locales estén disponibles.

## 8. Commits

Los cambios se commitean por responsabilidad y sin arrastrar los archivos de campañas/resultados ya
modificados en el árbol: reporte/backend, runner/manifiesto, frontend, infraestructura/documentación.
