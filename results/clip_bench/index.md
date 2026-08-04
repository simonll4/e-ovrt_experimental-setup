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
| T1 | `t1_gdinotiny560_v2short_scene` | gdino-tiny-560 | `v2_short` | scene | **0,824** | **0,757** | **0,789** | 5.327 ms | 168 ms | 0,698 | **0/4** | Línea de base. P1/P2/P4/P6 recall 1,000 con 1 FP; P7/P8/P9 concentran 6 missed y 8/9 FP |
| T2 | `t2_gdinobase560_v2short_scene` | **gdino-base-560** | `v2_short` | scene | 0,735 | 0,676 | 0,704 | **4.899 ms** | 221 ms | **0,819** | **0/4** | Contraste de modelo. **F-81.2b REFUTADA**: el especialista no recupera P7 (0,400=) ni P8 (0,500=) y empeora P9 (0,600→0,400). **Pero CR-02 SDR 0,281→0,920** y su t_alert −2,2 s |
| D1 | `d1_gdinotiny560_edirpair_scene` | gdino-tiny-560 | **`edir_v1` (par)** | scene | **0,176** | **0,146** | **0,160** | 6.611 ms | 847 ms | 0,210 | **2/4** | **Fase 2 del eje: E-DIR de punta a punta.** Precision 0,146 < 0,5 → **veto del §8: E-DIR descartada como núcleo, E-IND confirmada.** Ratio F1 0,20 (vs 0,34–0,46 en Nivel A: la brecha se AGRANDA con la plataforma). CR-02 recall **0,000**. Único escenario donde gana: **P9 0,800 vs 0,600** |

## Detalle por escenario

| `campaign_id` | P1 | P2 | P3∅ | P4 | P5∅ | P6 | P7 | P8 | P9 |
|---|---|---|---|---|---|---|---|---|---|
| T1 | 1,000 | 1,000 | 0 FP | 1,000 | 0 FP | 1,000 | **0,400** | **0,500** | **0,600** |
| T2 | 0,818 | 1,000 | 0 FP | 1,000 | 0 FP | 1,000 | **0,400** | **0,500** | **0,400** |
| D1 | 0,091 | 0,000 | 2 FP | 0,500 | 0 FP | 0,000 | 0,000 | 0,000 | **0,800** |

(∅ = escenario negativo: se reporta FP, no recall)

## Detalle por condición

| `campaign_id` | CR-01 SDR | CR-01 t_alert | CR-01 FP | CR-02 SDR | CR-02 t_alert | CR-02 FP |
|---|---|---|---|---|---|---|
| T1 | 0,805 | 4.314 ms | 8 | **0,281** | 8.572 ms | 1 |
| T2 | 0,804 | 4.364 ms | 11 | **0,920** | **6.417 ms** | 1 |
| D1 | 0,252 | 6.611 ms | **27** | **0,020** | — (recall 0) | **14** |

(CR-01 = 28 episodios / 25 clips; CR-02 = 7 episodios / 7 clips, en las tres campañas)

## Mecanismo de las alertas inesperadas (`datos/85-mecanismo-de-fallas.py`)

| Tipo | T1 | T2 | D1 |
|---|---|---|---|
| `prematura_pre_roll` | 5 | 6 | **14** |
| `cruzada_de_condicion` | 4 | 4 | 8 |
| `sin_episodio_activo` | 0 | 2 | **12** |
| `tardia` | 0 | 0 | 3 |
| adelanto mediano de prematuras | 0,5 s | 1,8 s | **2,5 s** |

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
- **F-84.5 — F-81.2b refutada para la palanca "cambiar de modelo bajo `v2_short`".**
  El especialista no recupera el pre-roll: P7 0,400=, P8 0,500=, **P9 empeora**
  (0,600→0,400); mecanismo clasificado contra el GT (`datos/85-mecanismo-de-fallas.py`):
  las prematuras de pre-roll pasan de 5 a 6, pero **su adelanto mediano se triplica**
  (0,5 s → 1,8 s) — con tiny caían al filo del borde, con base caen adentro del tramo
  que el GT marca "cumple"; los FP cruzados de condición quedan idénticos en 4 (la
  granularidad no depende del modelo). **Alcance**: la "especialidad CR-01" del doc 64 se midió
  detectando **`bare_head`**, clase que `v2_short` no incluye — T2 nunca la ejercitó.
  La vía `bare_head`-como-evidencia-positiva (base: recall 0,599 vs 0,308 de tiny)
  sigue sin probar a Nivel B y requiere el evaluador `direct_evidence` — la misma
  pieza que la Fase 2 de E-DIR. Palancas restantes para P7–P9: `track_id`/G1 y
  evidencia directa.
- **F-84.6 — el modelo sí compra percepción de chaleco, y la plataforma cobra menos
  tiempo.** CR-02 pasa de SDR **0,281 → 0,920** (la evidencia intermitente de F-81.1,
  ~1 de cada 6 frames, se vuelve continua) y su `t_alert` baja **8.572 → 6.417 ms**.
  El recall de CR-02 ya era 1,000 en T1 gracias a la histéresis, así que la mejora no
  puede verse ahí: se ve en calidad de evidencia y en latencia. **Son dos palancas
  independientes** — la histéresis rescata la percepción pobre (F-81.1) y el modelo
  la elimina como problema. El precio es CR-01: recall global 0,824→0,735.

- **F-85.3 — la histéresis es una palanca de doble filo, medida en los dos sentidos.**
  F-81.1: el motor **rescata** percepción intermitente pero correcta (CR-02 con SDR
  0,16 llegaba a recall 1,000). D1: el motor **amplifica** percepción persistente pero
  equivocada — E-DIR dispara sobre gente que cumple, la evidencia errónea es sostenida
  y la persistencia la confirma: 35 FP contra 9, y **2 FP en negativos** (T1/T2 tenían
  0/4). La histéresis solo mide persistencia; no distingue "débil pero correcta" de
  "fuerte pero equivocada".
- **F-85.4 — el ranking de Nivel A no transfiere a Nivel B.** CR-02 era el punto
  **fuerte** de E-DIR en imágenes (ratio 0,87) y es donde **colapsa** en video (recall
  0,000, SDR 0,020); CR-01 al revés. Por eso el pre-registro exige las dos fases y
  decide en la segunda.
- **F-85.5 — P9 es la única victoria de E-DIR y está donde E-IND es más débil**
  (0,800 vs 0,600, con menos FP). Coherente con la complementariedad de Nivel A
  (18,5%): ubica a E-HYB en el pre-roll, no "en general".

## Veredicto del eje (nucleo/04 §8, criterios fijados antes de correr)

**Veto de precisión** (criterio 1): una estrategia con precision de alertas < 0,5 no
puede ser núcleo aunque gane en F1. **D1 tiene 0,146 → E-DIR descartada como núcleo;
E-IND confirmada** (ADR-001), por medición y no por prior. No hacen falta desempates:
la brecha es de 0,63 en F1. La estrategia no elegida queda documentada con sus números
(§8 criterio 4). **La brecha se agranda al pasar por la plataforma**: ratio F1 0,20 a
Nivel B contra 0,34–0,46 a Nivel A.

## Campañas candidatas (el contraste que falta)

| Prioridad | Combinación a variar | Qué pregunta responde | Estado |
|---|---|---|---|
| ~~1~~ | ~~Prompts `edir_v1` / `eind_v1`~~ | **RESUELTO**: Nivel A (doc 83) + Nivel B (D1, doc 85) → veto de precisión, E-IND es el núcleo | **cerrado** |
| ~~2~~ | ~~Modelo `gdino-base-560`~~ | **HECHO** (T2, doc 84): F-81.2b refutada bajo `v2_short`; CR-02 SDR 0,281→0,920 | **cerrado** |
| 1 | **E-HYB `hyb_or` sobre el banco** | La fusión ya corre por config (`strategy: hyb_or`). F-85.5 dice dónde esperar ganancia: pre-roll/P9, no en general | lista (sin código) |
| 2 | E-HYB `hyb_and` (factor de ventana) | §8.3: adopción solo si supera a la mejor individual por ≥0,05 en F1 de alertas. Corroboración validada en CR-01, indeterminada en CR-02 | requiere motor (spec 41 §6.2) |
| 3 | `bare_head` como evidencia directa × `gdino-base-560` | La vía que T2 no probó (F-84.5): mayor separación medida entre modelos (0,599 vs 0,308), vía `direct_evidence` con `match: region_center` | lista (sin código) |
| 4 | Granularidad `subject` (G1) sobre los clips P7 | ¿Cuánto del déficit de P7 es la granularidad de escena? | requiere `track_id` (doc 79) |
| 5 | Lote de internet (14 clips) sumado al banco | Material no guionado (L4) + **soak → FAR/hora** (L1) | espera CVAT |

> **Comparabilidad:** T1 se evaluó con los fixes F-EV1/2/3 del evaluador
> (control-plane `c1cbb56`). Cualquier campaña anterior a ese commit **no es
> comparable** sin re-evaluar — se re-evalúa barato desde los artefactos
> guardados (`docs/operacion/datos/81-reevaluar.py`), la inferencia no se repite.
