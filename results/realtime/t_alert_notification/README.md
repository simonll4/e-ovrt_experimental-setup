# Campaña `t_alert-notification` live

Resultado aceptado de la campaña del 2026-08-13. La cifra citable es
**p95 = 64.534 ms** sobre **n = 460** entregas live confirmadas
por PUBACK MQTT QoS 1.

## Definición y alcance

`t_alert-notification = puback_wall_ms - ts_publish_ms`

Mide exclusivamente el tramo `bus de alertas del control-plane -> PUBACK MQTT`; no mide
sensor -> notificación. Solo entran registros `outcome=delivered`, `mode=live` y
`latency_mode=live`, observados también por el suscriptor testigo.

## Resultado principal

| Muestra | min | media | p50 | p95 | p99 | max |
|---:|---:|---:|---:|---:|---:|---:|
| 460 | 27.766 | 42.577 | 41.434 | 64.534 | 105.926 | 119.443 |

El corpus principal contiene 413 runs y 836 alertas: 460 entregas y
376 supresiones por cooldown. No hubo drops, dead letters,
eventos inválidos, eventos malformados, IDs inesperados ni duplicados MQTT observados.

## Régimen sostenido (steady-state)

| Muestra | n | min | media | p50 | p95 | p99 | max |
|---|---:|---:|---:|---:|---:|---:|---:|
| Primeras entregas de cada corrida | 356 | 27.766 | 39.985 | 40.883 | 49.869 | 65.151 | 76.022 |
| Entregas 2.ª en adelante | 104 | 30.560 | 51.451 | 44.398 | 102.025 | 116.170 | 119.443 |

El p95 principal agrega todas las entregas; el **77.4 %** son primeras entregas de
su corrida (proceso y conexión MQTT recién creados) y resultan las **más rápidas**. La cota
honesta para operación continua es el p95 del régimen sostenido:
**102.025 ms sobre n = 104**.

Ambas particiones salen del mismo `outcomes.csv`, sin re-corrida: la partición es por orden
temporal dentro de cada corrida y usa el mismo percentil nearest-rank que el agregado principal.

## Tamaño de payload

| n | min | media | p50 | p95 | p99 | max |
|---:|---:|---:|---:|---:|---:|---:|
| 460 | 1022 | 1057.9 | 1037 | 1078 | 1374 | 1835 |

Bytes del payload MQTT publicado, observados por el suscriptor testigo.

## Contrastes separados

Las tres repeticiones integradas desde video hasta `report.json` produjeron una entrega cada una,
con `t_alert-notification` de 116.839 ms, 152.901 ms, 91.588 ms. No se mezclan con el agregado principal.

El smoke de cámara figura como `not_executed`: ni OAK-D ni RTSP estaban conectadas. Esto no es un
resultado negativo del sistema y no altera la métrica primaria, cuya fuente es la republicación
live controlada del corpus y cuyo acople completo fue validado con video.

## Artefactos

- `metrics.json`: cifra aceptada, estadísticos, outcomes y gates.
- `outcomes.csv`: los 1.410 registros principales y suplementarios para recomputación.
- `integrated-runs.json`: admisión y tres repeticiones E2E, sin rutas locales.
- `camera-smoke.json`: disposición explícita de la prueba no ejecutada.
- `corpus.json`, `campaign.yaml` y `provenance.json`: universo, configuración y procedencia.
