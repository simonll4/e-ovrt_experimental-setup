# Campañas sobre el banco de clips — tabla comparativa

Banco: **34 clips** del rodaje (Bloque A, 2026-07-25), 35 episodios (CR-01 28 /
CR-02 7), P1–P9, `manifest.yaml` sha256 `cef5082e…`. Limitaciones comunes a
todas las campañas: `e-ovrt_datasets/datasets/registry/clip_bench.md` (L1–L5).

**Cómo leer esta tabla.** Cada fila es el rendimiento medido de UNA combinación,
no una nota. La pregunta de la tesis es *qué se consigue hoy con OVD sin
entrenar en construcción civil* — el contraste entre filas **es** el
experimento. Recall/precision son **micro** (por episodio) sobre episodios
evaluables; los clips negativos quedan fuera y se reportan como control de FP.

| # | `campaign_id` | Modelo | Prompts | Gran. | Recall | Prec. | F1 | t_alert | TTFD | SDR | FP neg. | Hallazgo |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| T1 | `t1_gdinotiny560_v2short_scene` | gdino-tiny-560 | `v2_short` | scene | **0,824** | **0,757** | 0,789 | 5.327 ms | 168 ms | 0,698 | **0/4** | Línea de base. P1/P2/P4/P6 recall 1,000 con 1 FP; P7/P8/P9 concentran 6 missed y 8/9 FP |

## Detalle por escenario

| `campaign_id` | P1 | P2 | P3∅ | P4 | P5∅ | P6 | P7 | P8 | P9 |
|---|---|---|---|---|---|---|---|---|---|
| T1 | 1,000 | 1,000 | 0 FP | 1,000 | 0 FP | 1,000 | **0,400** | **0,500** | **0,600** |

(∅ = escenario negativo: se reporta FP, no recall)

## Detalle por condición

| `campaign_id` | CR-01 recall | CR-01 SDR | CR-01 t_alert | CR-02 recall | CR-02 SDR | CR-02 t_alert |
|---|---|---|---|---|---|---|
| T1 | 0,793 (28 eps) | 0,805 | 4.314 ms | **1,000** (7 eps) | **0,281** | 8.572 ms |

## Hallazgos vigentes

- **F-81.1 — la histéresis del motor rescata una percepción intermitente.** CR-02
  llega a recall 1,000 con SDR 0,281 (0,160 en P2 puro): la evidencia de chaleco
  aparece en ~1 de cada 6 frames del episodio (F-G2.1 medido de punta a punta) y
  el patrón temporal la acumula igual, pagando tiempo (t_alert 8.572 vs 4.314 ms
  de CR-01). Argumento pro-plataforma medido — y a la vez el techo: con SDR ~0,16,
  exigir continuidad estricta rompería CR-02.
- **F-81.2 — dónde se rompe la combinación actual.** (a) Granularidad de escena
  vs GT por sujeto en multitud (P7): el GT exige que UN sujeto sostenga 4 s y el
  motor acumula "alguien sin casco"; es el costo de operar sin `track_id`, ahora
  medido → insumo directo del experimento G1 (doc 79). (b) Mis-detección de casco
  en el pre-roll (P7/P9): la alerta cae 0,7–2,4 s antes del episodio porque el
  modelo no ve el casco durante los ~3 s de cumplimiento inicial → candidato a
  prompts de Fase D o a `gdino-base-560` (especialista CR-01, doc 64).
- **F-81.3 — TTFD ~5 frames.** La latencia de la plataforma es la política de
  persistencia, no la percepción: `t_alert ≈ persistencia + TTFD + intermitencia`.

## Campañas candidatas (el contraste que falta)

| Prioridad | Combinación a variar | Qué pregunta responde | Estado |
|---|---|---|---|
| 1 | Prompts `edir_v1` / `eind_v1` (Fase D, congelados doc 76) | ¿La formulación de la condición en lenguaje mueve el rendimiento? Es el eje central de la tesis | desbloqueada |
| 2 | Modelo `gdino-base-560` | ¿El especialista CR-01/`bare_head` (doc 64) arregla el pre-roll de P7/P9? | lista |
| 3 | Granularidad `subject` (G1) sobre los clips P7 | ¿Cuánto del déficit de P7 es la granularidad de escena? | requiere `track_id` (doc 79) |
| 4 | Lote de internet (14 clips) sumado al banco | Material no guionado (L4) + **soak → FAR/hora** (L1) | espera CVAT |

> **Comparabilidad:** T1 se evaluó con los fixes F-EV1/2/3 del evaluador
> (control-plane `c1cbb56`). Cualquier campaña anterior a ese commit **no es
> comparable** sin re-evaluar — se re-evalúa barato desde los artefactos
> guardados (`docs/operacion/datos/81-reevaluar.py`), la inferencia no se repite.
