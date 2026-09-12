# Eje 3 — Modelo: zero-shot y fine-tuning

---

## La afirmación central, y hay que decirla primero

**Todas las cifras de los cuatro índices de `results/` son zero-shot.** Ningún
modelo ajustado produjo un número en `results/`. El fine-tuning es una **línea
aparte, cerrada, que no aportó un modelo de servicio** — su valor declarado es una
curva de tres puntos, no un checkpoint adoptado.

Esto es coherente con el norte del trabajo: la pregunta no es «¿se puede mejorar
entrenando?» sino *qué rendimiento se obtiene hoy en construcción civil con
detección open-vocabulary **sin entrenar**, expresando las condiciones de riesgo
en lenguaje, y qué aporta la plataforma alrededor del modelo*.

---

## Baseline — lo que produce todo `results/`

**Modelo campeón: `grounding-dino/gdino-tiny-560`.** Mejor mAP50 del banco de
imágenes tanto en el núcleo curado (147 imgs) como en `bench_v3` completo (6.477):
robusto a la fuente.

Par de operación que hay que citar **siempre junto**: `image_size` **560** ·
`box_threshold` **0,30** · `text_threshold` 0,25 · NMS IoU 0,50 · fp16.

> ⚠ **Trampa de comparación.** `gdino-tiny` (800) corrió a `box_threshold` 0,35 y
> `gdino-tiny-560` a 0,30: en el par *tiny*, resolución y umbral están
> **confundidos**. El par *base* sí está a 0,30 en ambos (0,453 vs 0,401). Nunca
> presentar el par tiny como evidencia limpia del efecto de la resolución.

Especialista secundario: `gdino-base-560` para CR-02 / `bare_head` — recall CR-01
**0,599 vs 0,308** del campeón.

---

## Fine-tuning — la jornada E-04, cerrada

Vive en **`finetuning/`**, no en `results/`, y **no está en el inventario de
evidencia** (`evidence-runs.yaml` cubre corridas de media-plane y control-plane).

### Lo primero que hay que entender: es otro modelo

**La escalera de fine-tuning corrió sobre `YOLOE-26s`, no sobre el campeón.**
`gdino-tiny-560` es GroundingDINO y **nunca se ajustó**. Por lo tanto esta curva
**no dice nada sobre el campeón**: es un experimento de capacidad/retención dentro
de la familia YOLOE.

### La curva de tres puntos — cifras leídas de disco

Percepción sobre `bench_v3` (AP50 por clase, IoU 0,5):

| Brazo | mAP50 | person | helmet | vest | bare_head |
|---|---:|---:|---:|---:|---:|
| **base** — YOLOE-26s sin tocar | **0,4193** | 0,7843 | 0,6286 | 0,2642 | 0,0000 |
| **T1** — linear probe | 0,4171 | 0,6932 | 0,6004 | 0,3292 | 0,0455 |
| **T2** — full fine-tuning | 0,2374 | 0,3943 | 0,3734 | 0,0909 | **0,0909** |

Recall CR-01 (persona sin casco), por fuente:

| Brazo | `bench_obra` | `shel5k` | Agregado |
|---|---|---|---|
| base | 0,0167 (1/60) | 0,0000 (0/5248) | **0,0002** (1/5308) |
| **T1** | 0,1667 (10/60) | 0,2094 (1099/5248) | **0,2089** (1109/5308) |
| T2 | 0,0000 (0/60) | 0,0055 (29/5248) | **0,0055** (29/5308) |

Retención open-vocabulary, COCO val2017, 80 clases:

| Brazo | mAP50 | Δ |
|---|---:|---:|
| base | 0,4347 | — |
| T2 tuned | 0,1247 | **−71,3 %** |

### Los veredictos

| Tier | Veredicto | Constancia |
|---|---|---|
| **T1** (linear probe) | **NO-GO** — D-FT-12 | `operacion/123`, `manifests/t1_{promotion,go_no_go}_1167640.json` |
| **T2** (full FT, job `1167982`, enmienda D-FT-16 SGD lr0=0,01) | **NO-GO** | `operacion/127`, `manifests/t2_{promotion,go_no_go}_1167982.json` |
| **T3** | cerrado con **causa técnica** | `operacion/117` §2, `128` |

**Ningún checkpoint se adoptó** como modelo de servicio (ADR-017). Catálogo y
pesos se conservan sólo como constancia.

T2 colapsó en entrenamiento: early stop 16/60 con `best_epoch=1`. Su lectura es la
de las tres condiciones pre-registradas: **la ganancia PASA** (`bare_head` 0 →
0,0909, pero sólo en `shel5k`), la **retención in-domain FALLA** (`person`
−49,7 %) y la **retención OV FALLA** (COCO −71,3 %).

**F-127.1: el fallo de T1 no era de capacidad — es estructural**: 2.946 imágenes
de entrenamiento contra 10,35 M de parámetros. Con eso, la curva
capacidad/retención queda **completa con tres puntos** y ése es el valor declarado
de la jornada.

**No hay más brazos contra `bench_v3`** sin una pre-registración nueva (acta
`128` §5).

---

## Trampas de cita de este eje

**No hay una métrica única.** **T1 gana por recall CR-01** (0,2089 vs 0,0055) y
**T2 gana por AP de `bare_head`** (0,0909 vs 0,0455). Presentar «el fine-tuning
mejoró» o «empeoró» sin decir en qué métrica es falso en las dos direcciones.

**La ganancia de `bare_head` de T2 es sólo en `shel5k`.** En `bench_obra` —el
material de obra— el recall CR-01 de T2 es **0,0000**.

**El denominador de CR-01.** Estas evaluaciones usan **5.308** violadores (GT
vigente). Un `n=5.313` que aparezca en documentos previos es el GT del 23-jul; la
medición no se repitió.

**El entrenamiento fue en el clúster, nunca local.** La restricción es Slurm, no
la disponibilidad de CUDA.

**El encuadre nunca es «faltó tiempo».** El fine-tuning se hizo, se midió con
protocolo pre-registrado y dio NO-GO por razones técnicas medidas.

---

## Dónde está cada artefacto

```
finetuning/runs/t1_yoloe26s_baseline_bench_v3/eval/   ← brazo base
finetuning/runs/t1_yoloe26s_tuned_bench_v3/eval/      ← T1
finetuning/runs/t2_yoloe26s_tuned_bench_v3/eval/      ← T2 sobre bench_v3
finetuning/runs/t2_coco_retention_{base,tuned}/eval/  ← retención OV
finetuning/manifests/t{1,2}_{promotion,go_no_go}_*.json
```

Cada `eval/` trae `eval_perception.aggregate.json`, `eval_perception.by_stratum.json`,
`eval_cr01.by_source.json` y `protocol_snapshot.json`.
