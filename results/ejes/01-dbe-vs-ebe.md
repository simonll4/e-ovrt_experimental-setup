# Eje 1 — Escenario de despliegue: DBE y EBE

Vista de lectura. Las cifras son las de los cuatro índices; acá sólo se dice **en
qué escenario se midió cada cosa**.

---

## Los dos escenarios

| | **DBE** — despliegue básico | **EBE** — despliegue extendido |
|---|---|---|
| Acople medios↔control | **por archivo**: el media-plane escribe `runs/<id>/detections.jsonl` y el control lo relee (`eovrt-control replay`) | **por bus ZeroMQ PUB/SUB + msgpack** (ADR-003), envelope `bus.envelope.v1` |
| Tiempo | offline, sin restricción | en vivo, 1:1, cierra con `run.lifecycle.v1/run_finished` |
| Fuente típica | carpeta de imágenes, archivo de video | cámara (OAK-D PoE, RTSP) |
| Qué permite medir | percepción y reglas sin el costo del tiempo real | el costo del tiempo real y la integridad del transporte |

El repositorio es la fuente de verdad en los dos casos: **toda corrida live es
re-evaluable offline y produce artefactos idénticos** (verificado — doc 37).

---

## Reparto de la evidencia

| Escenario | Índices | Resultados | Filas |
|---|---|---:|---:|
| **DBE** | `bench_imagenes` · `bench_nivel_a` · `clip_bench` | **23** | 1.053 |
| **EBE** | `realtime` | **12** | 707 |

### DBE — 23 resultados

**`bench_imagenes` (5)** — percepción espacial sobre `bench_v3` (6.477 imgs, 3
estratos: `bench_obra` 147 · `chv` 1.330 · `shel5k` 5.000).

| `result_id` | Filas |
|---|---:|
| `bench_imagenes/seleccion_s1` | 20 |
| `bench_imagenes/modelos_crudos` | 6 |
| `bench_imagenes/confirmacion_b5` | 6 |
| `bench_imagenes/clase_nueva` | 5 |
| `bench_imagenes/gdino560` ⇄ | 4 |

**`bench_nivel_a` (4)** — estado «sin EPP» por persona. Ojo: **dos materiales
distintos en el mismo índice** y sus agregados no se mezclan.

| `result_id` | Material | Filas |
|---|---|---:|
| `bench_nivel_a/na1_gdinotiny560_v2short_video` ⇄ | **video** (17 clips, GT humano CVAT) | 30 |
| `bench_nivel_a/d1_gdinotiny560_edir_vs_eind` | imágenes | 18 |
| `bench_nivel_a/edir_vs_eind` | imágenes | 18 |
| `bench_nivel_a/replica_base560` | imágenes | 18 |

**`clip_bench` (14)** — alertas contra GT temporal humano. 12 sobre el banco del
rodaje y **2 sobre el estrato B** (lote de internet), que no se comparan entre sí
sin control.

| Grupo | `result_id` | Filas |
|---|---|---:|
| Combinación (6) | `t1_gdinotiny560_v2short_scene` · `t2_gdinobase560_v2short_scene` · `b1_gdinobase560_barehead_scene` · `d1_gdinotiny560_edirpair_scene` · `g1_gdinotiny560_v2short_subject` · `h1_gdinotiny560_hybor_scene` | 68 c/u (H1: 102) |
| Densidad R1–R6 (6) | `r1`…`r6_gdinotiny560_v2short_{scene,subject}_s{7,15,26}` | 68 c/u |
| Estrato B (2) ⇄ | `i1_…_scene_internet` · `i2_…_subject_internet` | 39 c/u |

### EBE — 12 resultados (`realtime`)

| `result_id` | Filas | Qué mide |
|---|---:|---|
| `realtime/decimado_empirico` | 544 | Contraste de decimado con controles propios |
| `realtime/descarte_irregular` | 76 | Irregularidad del descarte en vivo |
| `realtime/matriz_modelo_fuente` | 24 | Modelo × fuente |
| `realtime/frt5_roundtrip_pil` | 23 | Los 23 bloques de F-RT5 |
| `realtime/rodaje_seis_corridas` | 12 | **Las 6 corridas del rodaje** |
| `realtime/claqueta_reloj_externo` | 8 | Claqueta con reloj externo |
| `realtime/t_alert_notification` | 6 | Bus de alertas → PUBACK MQTT QoS 1 |
| `realtime/regresion_g1_live` | 4 | Regresión G1 en vivo |
| `realtime/gdino560` ⇄ | 4 | Contraste de resolución |
| `realtime/bus_live_paridad` | 3 | Paridad live ↔ replay |
| `realtime/l0` | 2 | Línea de base L0 |
| `realtime/g2a_single_host` | 1 | G2A en un solo host |

⇄ = pertenece a **dos** resultados (marcado `shared`): `gdino560` se cita desde
`bench_imagenes` y desde `realtime`; `na1` y los dos de estrato B cruzan también.

---

## Trampas de lectura de este eje

**No se suman percentiles entre tramos.** La cadena está entera instrumentada pero
cada tramo tiene su reloj y su dueño: `capture_to_host` (202–217 ms en las 6
corridas del rodaje) · **G2A** (31,8 ms p95 single-host video; 630–890 ms GDINO
live; 225–249 ms YOLOE live) · `t_alert-system` (dominado por la persistencia del
patrón, 4–7 s, no por el transporte) · `t_alert-notification` (p95 64,534 ms,
n=460). Se citan **por separado**.

**El G2A arranca en el dequeue, no en el fotón** (F-101.8). Vidrio→alerta es
`capture_to_host` + G2A, y hay que decirlo así.

**`bare_head` y el orden de arranque.** En vivo el orden real es **control →
distribución → medios**; la no-pérdida en el bus la garantiza el handshake XPUB
del publicador, no el orden.
