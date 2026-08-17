# Real-time / EBE — resultados consolidados

Índice de lo medido sobre el **camino en vivo** (EBE: cámara → bus ZeroMQ →
control-plane) y sobre el comportamiento temporal de la plataforma. Complementa a
`results/bench_imagenes/` (percepción espacial) y `results/clip_bench/` (alertas
contra GT temporal).

**Cómo leer esto.** El eje real-time se cubre en **cuatro planos distintos**, y
conviene no confundirlos porque miden cosas diferentes:

| Plano | Qué responde | Estado |
|---|---|---|
| **Integridad del acople** | ¿el bus pierde eventos? ¿la corrida cierra 1:1? | ✅ cerrado |
| **Latencia operativa** | ¿cuánto tarda de captura a alerta? ¿entra en presupuesto? | ✅ medido (GDINO fuera de budget, con causa) |
| **Techo de throughput** | ¿cuántos fps sostiene esta máquina y por qué? | ✅ diagnosticado + una palanca aplicada |
| **Calidad bajo restricción de tiempo real** | ¿qué rendimiento sobrevive a ver menos frames? | ✅ **medido 2026-08-05 (doc 96)** |
| **Distribución de alertas** | ¿cuánto tarda el bus de alertas en obtener PUBACK MQTT QoS 1? | ✅ **p95 64,534 ms (n = 460)** |

La campaña [`t_alert_notification`](t_alert_notification/README.md) mide exclusivamente
`bus de alertas → PUBACK MQTT QoS 1`. El agregado principal da **p95 = 64,534 ms
(n = 460)**. En régimen sostenido (entregas 2.ª+ de cada corrida), el p95 es
**102,025 ms (n = 104)**; las primeras entregas dan **49,869 ms (n = 356)**.
Ambas lecturas proceden del mismo `outcomes.csv`, sin re-corrida.

---

## 1. Integridad del acople EBE

| Evidencia | Resultado |
|---|---|
| Gate de paridad replay↔stream (`test_bus_parity.py`) | **Artefactos idénticos**; un bbox corrido 1 px hace fallar el gate (compara contenido, no contadores) |
| Corrida live E2E (doc 37) | Replay del `detections.jsonl` de una corrida live produce artefactos **byte-idénticos** (15 `pattern_events`, 6 alertas, iguales módulo `control_run_id`/`alert_id`) |
| Rodaje completo, 6 corridas (doc 71) | **`bus_dropped_events = 0`** y `degraded = false` en las 6, y también en las de la tarde |
| L0 ensayo 1:1 (doc 65) | Verde, 30/30 unidades, `bus_dropped_events = 0` |
| Regresión post-cambios (doc 91) | **0 eventos perdidos** en ambas fases, `units_failed = 0` |

**Este subsistema está cerrado.** El JSONL sigue siendo la verdad en los dos caminos:
toda corrida live es re-evaluable offline y produce artefactos idénticos (verificado).

> **Trampa no negociable (docs 37/68):** nunca cerrar un socket ZeroMQ desde un hilo
> distinto del que lo creó mientras otro está en `recv_multipart` — libzmq aborta el
> proceso con `SIGABRT`. Por eso las fuentes de red exponen `request_stop()`.
>
> **Orden de arranque EBE:** control-plane **primero** (`POST :8081/api/runs`,
> `mode: live`, cuyo 201 implica suscripción activa) y media-plane **después** con
> `bus.enabled: true`. PUB/SUB pierde lo publicado antes de la suscripción.
>
> **Tres trampas más, medidas el 2026-08-05 (doc 101 §5.2):** **F-101.5** la fuente
> OAK-D no cierra cooperativamente y depthai tira `std::system_error` desde un hilo
> no-Python → **SIGABRT del media-plane** (misma familia que la de ZeroMQ, otro
> culpable) ⇒ **una sola corrida OAK-D por vida del servicio**; los artefactos se
> salvan porque se escriben incrementalmente. **F-101.6** el device crashea y
> reconecta **mientras el ping ICMP da 0% de pérdida** (la pila de red del PoE
> responde con la aplicación caída) ⇒ el ping no descarta nada, el remedio es
> power-cycle. **F-101.7** el status en vivo del media-plane **no trae
> `units_processed`** (aparece recién en el `summary`): esperar frames leyéndolo de
> ahí reporta "la cámara no entregó frames" con la cámara funcionando.

## 2. Latencia operativa (G2A: captura → alerta)

| Contexto | G2A p50 | G2A p95 | Presupuesto 50–250 ms |
|---|---|---|---|
| Single-host, video (doc 39) | **14,7 ms** | **31,8 ms** | ✅ dentro |
| GDINO (`tiny-560`) live sobre OAK-D (doc 71) | — | **630–890 ms** | ❌ fuera |
| YOLOE live sobre OAK-D (doc 71) | — | **225–249 ms** | ✅ dentro |

**El resultado incómodo, y es un resultado, no una falla:** el único modelo que entra
en presupuesto temporal (YOLOE) es el que **no sirve para la condición** (recall
`bare_head` 0,000 en el bench de imágenes, y en vivo produjo una CR-02 falsa al 100% y
dos alertas con tiempo corrompido). El que detecta (GDINO) no entra en presupuesto.
Esa tensión calidad↔latencia es un hallazgo de primera línea del trabajo.

> **F-101.8 — el G2A se mide desde el DEQUEUE, no desde el fotón, y el informe debe
> decirlo.** `capture_wallclock_ms` se estampa cuando el host saca el frame de la
> cola; el wallclock del fotón es `capture_wallclock_ms − capture_to_host_ms`. O sea
> que **la latencia vidrio→alerta es `capture_to_host` + G2A**, y ese término varía
> un orden de magnitud con el estado de la fuente (medianas por corrida):
> **202–217 ms en las 6 corridas del rodaje**, **169 ms** en el humo del doc 91 y
> **1.600 ms** en las tomas del 08-05 (cola estacionaria, huecos regulares de
> 275 ms — consistente con el doc 61 hallazgo 5: el cuello es la fuente, no el
> modelo). Está instrumentado por frame, así que es **declarable, no un hueco**, y
> quedó **validado contra el mundo físico** por la toma anclada del doc 101 §5.4
> (tono → fotón = +1.066 ms). **Los números de la tabla de arriba son G2A y su
> lectura no cambia**: en el rodaje el término era ~0,21 s estable.

## 3. Techo de throughput y su diagnóstico

### Lo que efectivamente corrió en el rodaje (doc 71 §2.1)

| Corrida | proc/drop | fps_eff | inf p50 | G2A p95 |
|---|---|---|---|---|
| GDINO P1 | 47/767 (**94% drop**) | **1,16** | 567 ms | 890 ms ✗ |
| GDINO P2 | 93/1115 (92%) | 1,76 | 439 ms | 665 ms ✗ |
| GDINO P3 | 55/629 (92%) | 1,51 | 432 ms | 630 ms ✗ |
| YOLOE P1 | 254/615 (71%) | **5,55** | 116 ms | 232 ms ✓ |
| YOLOE P2 | 295/710 (71%) | 5,98 | 118 ms | 225 ms ✓ |
| YOLOE P3 | 152/322 (68%) | 5,12 | 112 ms | 249 ms ✓ |

**Variación a lo largo de la jornada**: la misma configuración rindió **2,62 fps a
las 13:33 y 1,16 fps a las 20:10 (2,26×)**. ✎ 2026-08-06: *la lectura original
("degradación monótona, correlato térmico 41 °C vs 55–61 °C", doc 71) fue refutada
por doc 73 §0.3 con los datos del propio rodaje*: 17:50 rindió 201 ms y 17:58
445 ms (2,2× en 8 min), y la corrida de las 13:33 es más lenta que la de las 17:50
— lo que separa las poblaciones es **la fuente** (`video_file` 306 ms vs `oak_d`
426 ms, intercaladas en el tiempo), no el calor. Coherente con F-RT3 (abajo): el
techo es contención de GIL, no térmico.

### Causa raíz y palanca aplicada (docs 73/74)

- **F-RT3 — el techo es contención de GIL**, no térmico ni la rama de texto.
  Verificado que la GPU sí se usa (triple chequeo: `torch.cuda`, 1,6 GB VRAM del
  proceso, `dmon` con SM 6–41%); el perfil "bursty" es la firma de un transformer a
  batch=1, no ociosidad.
- **F-RT5 — palanca aplicada y significativa**: sacar el round-trip PIL del productor
  da **+18% de fps (3,75 → 4,42) y −14,4% de latencia**, p = 0,0195 con 11 pares
  pareados. Commit `3deb64c` en `perf/producer-pil-roundtrip` (merge = decisión del
  usuario). Salida byte a byte idéntica: no requiere re-validar mAP.
- **Las tres palancas que sí estaban planificadas** (cachear texto, 480 px, térmica)
  sumaban <15% y **quedaron descartadas con números**.

> **Higiene de medición (doc 74), aprendida a los golpes:** `py-spy` en WSL infla la
> medición 2×; cualquier palanca de menos del 20% necesita **~10 pares pareados
> intra-campaña** para separarse del ruido del host (F-RT4, deriva ±150 ms). Protocolo:
> reinicio de WSL + verificación de p50 < 300 ms antes de medir.

### Prefilter EN-2 on-device (doc 10 E-07)

Gate de personas **en la cámara** (OAK-D, blob `person-detection-retail-0013`),
fail-open estructural: A/B real con GDINO da **87% de drop on-device**. Solo aplica a
`source.type = oak_d`.

## 4. Calidad bajo restricción de tiempo real (doc 96 — el plano que faltaba)

Hasta 2026-08-05 los tres planos anteriores estaban medidos pero **ninguna métrica de
calidad contra GT** existía para el camino live: las 6 campañas del banco corrieron
todas a `stride: 1` = **30 fps de evidencia**, mientras el live entrega **1,16–4,42
fps**. Las campañas R1–R6 cierran ese hueco.

**Tabla completa y hallazgos: `results/clip_bench/index.md` § "Eje de densidad de
evidencia".** Lo esencial:

- **F-96.4 (verificado con bootstrap pareado por clip):** la ganancia de la
  granularidad por sujeto **excluye el cero en las cuatro densidades** (+0,141 a 30
  fps, +0,072 a 4,29, +0,137 a 2,00, +0,096 a 1,15). Es la única palanca del banco
  significativa a la densidad que el live entrega hoy — y el tracker **no se
  fragmenta** (154 → 103/91/105 tracks).
- **F-96.2:** lo primero que se rompe bajo tiempo real es el rescate de la histéresis
  (F-81.1): CR-02/P2 cae 1,00 → 0,60 → 0,20. Límite de cadencia declarado.
- **F-96.5:** el costo real en tiempo de alerta es **+0,7 a +1,3 s** entre
  supervivientes comunes, sobre políticas de 4–7 s. Acotado y declarable.
- **Ningún delta de densidad del agregado de escena excluye el cero** — ahí el costo
  del tiempo real es tendencia monótona con mecanismo identificado, no efecto
  establecido. Bajo **sujeto**, el peor caso **sí es individualmente significativo**:
  R6−G1 = −0,188 [−0,334, −0,040] (doc 96 §4.1).

> **Dos reglas de lectura que salieron de acá y el informe debe llevar:** el **SDR no
> se compara entre cadencias** (F-96.6: la subida es ~100% artefacto del instrumento) y
> el **`t_alert` agregado no se compara entre densidades sin control de
> supervivencia** (F-96.5).

**Verificación posterior (doc 101, 2026-08-05).** El límite declarado del doc 96
("el decimado es regular; el descarte live es irregular") quedó **medido y
verificado**: la irregularidad real es CV 0,22 (estado actual, media 7,28 frames@30
= 4,12 fps — que además **valida empíricamente el ancla stride 7** de R1/R2) y CV
0,36 (rodaje); re-corriendo el eje con decimado **empírico** (huecos muestreados de
esas distribuciones, 3 semillas, guard de equivalencia decimado≡re-inferencia verde
en 34/34 contra R1), **ningún contraste jitter−regular es detectable** (12/12 IC
cruzan el cero, t_alert +11 ms entre supervivientes comunes, 0 FP en negativos en
las 16 variantes) y **la ganancia de la identidad conserva el signo en 6/6
realizaciones** (F-101.3/4; matiz declarado a 2,5 fps en doc 101 §3).

## 5. Confirmaciones de patrones en vivo (evidencia contra reloj real)

| Condición | Confirmaciones live legítimas | Deltas medidos | Umbral |
|---|---|---|---|
| CR-01 | **7** (rodaje: 18:30, 19:21, 19:43, 20:10 + humos) | 4,1–4,6 s | 4,0 s |
| CR-02 | **3** (rodaje 15:47 + humo fase A + humo fase B) | 7,1 s y superiores | 7,0 s |

**Verificación con reloj EXTERNO (doc 101 §5.4, toma anclada del 2026-08-05).** Lo
anterior compara los relojes del sistema contra sí mismos; esta toma ancla la cadena
a un instante físico conocido (tono generado por el host, cuyo wallclock real se
mide, y el sujeto entra a cuadro en ese instante). Las cuatro patas cierran:
**ancla física→estampa +1.066 ms**; **onset observado = 1ª evidencia del motor**
(mismo frame, con confirmación visual del hombro entrando al cuadro); **política
4.142 ms** contra 4.000; **relojes de los dos procesos con 4 ms de residuo**; y la
**cadena completa tono→alerta = 7.045 ms = 2.716 + 4.329**. Cierra el stretch que el
doc 58 había declarado diferible. Cadencia de esa corrida: 3,60 fps, CV **0,016**.

La aritmética cierra contra la política, que es lo que había que demostrar del motor
temporal en vivo. El caso de las 19:21 además demostró la resolución con histéresis:
17 s de `sustained` con 17 "brillos de pelada" (helmet 0,25–0,46 intermitente) que
**no** resolvieron el episodio.

### G1 (identidad) verificado en vivo (doc 91)

| | Fase A (escena) | Fase B (sujeto) |
|---|---|---|
| Unidades | 150 | 160 |
| `bus_dropped_events` | **0** | **0** |
| Alertas | 2 (CR-01 + CR-02) | 2 (CR-01 + CR-02) |
| **`subject_key`** | `CR-01:smoke_ebe` | **`CR-01:smoke_ebe:subject_001`** |

El contraste de la última fila es toda la evidencia: bajo sujeto la clave incorpora el
`track_id` que el decorador de fuente produce **sobre el bus**, sin que el media-plane
emita nada nuevo. Y `no_track_id` **no** aparece en las causas de degradación — si
apareciera, el motor habría degradado a escena y la fase B habría medido G0 creyendo
medir G1.

## 6. Hallazgos negativos que son resultados, no fallas

- **F-RT1 — la sobre-marca de `vest` suprime CR-02.** Es dependiente de la vestimenta,
  documentado con su caso positivo y su caso negativo: campera a franjas conf 0,54 /
  torso liso 0,31 (ambos ≥ umbral 0,25) suprimen o retrasan; con remera negra lisa
  hubo **0 detecciones de `vest` en 309 frames** y CR-02 confirmó limpia.
- **F-RT2 — la ventana temporal exige estabilidad perceptual** con huecos <
  `resolve_after_ms`. GDINO la cumple; YOLOE no. Es una **condición de validez
  descubierta**, exactamente el tipo de aporte que el trabajo argumenta.

## 7. Qué NO está medido

- **Campaña EBE de punta a punta por el bus sobre los 34 clips.** El eje de calidad se
  cubre hoy por proxy de densidad sobre DBE (doc 96) + integridad verificada en humos,
  y el proxy quedó verificado también contra el descarte irregular (doc 101) — la
  prioridad de esta campaña baja aún más. Bloqueo técnico: el ancla wallclock↔media
  (ingeniería, no material). ~~Trabajo ubicado, no ejecutado.~~ ✎ **2026-08-15 —
  DECLARADA CON CAUSA, no pendiente (F-121.1, `operacion/121` §2.2).** Se evaluó
  ejecutarla y **no produciría ningún resultado nuevo**: el pipeline DBE es determinista
  (F-109.1) y el bus publica el evento **byte-idéntico** al del JSONL (gate de paridad
  verificado por mutación, doc 37 §3) ⇒ **el resultado sería idéntico a T1 por
  construcción**. La única divergencia posible es pérdida en el bus, que se cuenta
  (`bus_dropped_events`) y degrada la corrida — y en DBE la presión sobre el bus es
  **menor** que en vivo, o sea un test más flojo que los humos que ya dieron 0. No es un
  experimento: es un guard de un modo de falla que ya tiene detector.
- ~~La irregularidad del descarte live~~ → **MEDIDA Y VERIFICADA (doc 101)**: CV
  0,22–0,36 según estado del host, sin efecto detectable sobre el eje de densidad.
  Residuo de segundo orden declarado: el jitter muestreado es i.i.d.; el real puede
  correlacionar con el contenido de la escena.
- **El tracker en obra real con multitud.** G1 se verificó en vivo con pocos sujetos.
- **`gdino-base-560` no tiene latencia live medida** (doc 101 §1): lo medido en vivo
  fue `gdino-base` a **800 px** (G2A p50 311–388 / p95 446–614 ms); el −24% de la
  resolución 560 es inferencia batch sobre el BENCH (D-61.4), no una medición live.
  T2 y B1 quedan sin costo operativo live declarado.
- **Ancla de sincronización para EBE-desde-clip**, lo que impediría hoy alimentar el
  banco por el bus con correspondencia exacta al GT temporal.
- **FAR/hora**: limitación declarada (D-90.1), no métrica. La evidencia de falsas
  alarmas es el control de negativos del clip bench.

## 8. Dónde está cada número

| Qué | Dónde |
|---|---|
| Bus, runtime live y paridad | `docs/operacion/37` + `datos/37-*` |
| Servicio del control-plane | `docs/operacion/38` |
| G2A single-host | `docs/operacion/39` + `datos/39-2026-07-10-g2a-video-summary.json` |
| Benchmark realtime por modelo/fuente | `docs/operacion/61` |
| L0 ensayo EBE 1:1 | `docs/operacion/65` |
| **Rodaje: las 6 corridas live** | `docs/operacion/71` |
| Diagnóstico del techo de fps (GIL) | `docs/operacion/73` |
| Protocolo de higiene de medición | `docs/operacion/74` |
| Regresión live post-cambios + G1 en vivo | `docs/operacion/91` |
| **Calidad bajo densidad del live** | `docs/operacion/96` + `results/clip_bench/` |
| **Irregularidad del descarte live + verificación por decimado empírico** | `docs/operacion/101` + `datos/101-*` |
| Manual de arranque y trampas operativas | `docs/operacion/68` |
