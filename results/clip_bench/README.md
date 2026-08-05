# Resultados de campañas sobre el banco de clips (Nivel B)

Cada **campaña** es una corrida del banco de clips completo con **UNA
combinación declarada** de modelo × prompt set × pattern set × granularidad ×
camino. Este directorio existe para que comparar dos combinaciones sea *leer dos
archivos con la misma forma*, y no rehacer aritmética a mano — que es
exactamente donde se colaron los tres errores de medición del doc 81 §3.

> **Marco de lectura (doc 81 §1).** Los números de una campaña son el
> rendimiento medido de esa combinación, no una nota. Un recall bajo no es un
> fallo del proyecto: es el dato de qué se consigue hoy con OVD sin entrenar en
> construcción civil. **El contraste entre campañas ES el experimento.**

## Estructura

```
results/clip_bench/
  README.md            este archivo
  index.md             tabla comparativa de todas las campañas  ← va al informe
  <campaign_id>/
    campaign.yaml      la COMBINACIÓN declarada + procedencia (shas)
    metrics.json       agregado normalizado (clip_campaign_metrics.v1)
    evals/             eval_<clip>.json por clip (livianos, versionados)
    provenance.json    clip_id → media_run_id (las detecciones NO se copian)
```

Las **detecciones** (`detections.jsonl`, ~1 GB por campaña) quedan en `runs/` del
media-plane, que es su fuente de verdad (DA-03 / ADR-014 híbrido selectivo). Acá
se referencian por `media_run_id`. Si hay que re-evaluar, `provenance.json` dice
dónde está cada una.

## Convención de `campaign_id`

`<fase><n>_<modelo>_<promptset>_<granularidad>` — p.ej.
`t1_gdinotiny560_v2short_scene`, `d1_gdinotiny560_edirv1_scene`,
`g1_gdinotiny560_v2short_subject`. La fase remite al plan maestro (doc 62).

## Cómo agregar una campaña

1. **Correr la cadena** sobre los 34 clips (runner de referencia:
   `docs/operacion/datos/81-ciclo-rodaje-runner.py`) → un directorio con
   `eval_<clip>.json` por clip.
2. **Declarar la combinación** en `<campaign_id>/campaign.yaml`. No es opcional:
   sin eso el número no significa nada dentro de seis meses. Incluir los sha256
   del prompt set congelado y del `manifest.yaml` del banco.
3. **Agregar**:
   ```bash
   cd e-ovrt_datasets
   python3 datasets/scripts/bench/aggregate_clip_campaign.py \
       --evals-dir  <dir de evals> \
       --gt-dir     datasets-videos/gt \
       --campaign   <.../campaign.yaml> \
       --out        <.../metrics.json>
   ```
4. **Agregar la fila a `index.md`** con el hallazgo en una línea.

## Reglas de agregación (todas con test)

Están implementadas en `aggregate_clip_campaign.py` y cubiertas por
`datasets/tests/test_aggregate_clip_campaign.py`:

| Regla | Por qué |
|---|---|
| Los clips **negativos no entran** a precision/recall/F1 | Su `applicability_state` es `not_applicable` (F-EV1): promediarlos hunde el agregado contando aciertos como catástrofes. Entran al **control de FP**, que es su métrica. |
| Los episodios **censurados** salen del denominador de recall | A2, doc 57 §6.7 |
| Las **`re_alerts` no son FP** | ADR-011 |
| **Siempre** el desglose por escenario | L5 de `registry/clip_bench.md`: el agregado está dominado por P1/P2 |
| **micro ≠ macro**, se emiten los dos | Escenarios desbalanceados (P1=11 clips, P8=1). Micro = por episodio (default del informe); macro = media por clip. Declarar cuál se usa. |
| **FAR/hora solo con clips soak** (≥5 min) | doc 57 §3.2 G1. Sin soak queda `null` con la base declarada, nunca un 0.0 que parezca medido. |

## Limitaciones que arrastran TODAS las campañas

Vienen del banco, no de la combinación — están en
`e-ovrt_datasets/datasets/registry/clip_bench.md` (L1–L5) y se declaran una vez
en el informe, no por campaña: **FAR/hora no reportable como rendimiento**
(determinación doc 90 D-90.1: ninguna cota alcanzable sostiene una afirmación; la
evidencia de FP es el control de negativos, comparativo pareado), sin doble anotación
(sin kappa, decisión del equipo), 6 episodios con bordes adjudicados, un solo
bloque guionado sin obra real, escenarios desbalanceados.
