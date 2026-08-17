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
    provenance.json    clip_id → media_run_id (referencia al original)
```

Las **detecciones** (`detections.jsonl`, ~1 GB por campaña) quedan en `runs/` del
media-plane, que es su fuente de verdad (DA-03 / ADR-014 híbrido selectivo). Acá se
referencian por `media_run_id`. Además, el archivo común
[`../evidence-runs/`](../evidence-runs/README.md) conserva una copia versionable del subconjunto
textual de cada run citado, con los JSONL comprimidos y sin imágenes, video, previews, presets ni
secretos. El listado exhaustivo y regenerable está en [`../evidence-runs.md`](../evidence-runs.md).

## Convención de `campaign_id`

`<fase><n>_<modelo>_<promptset>_<granularidad>` — p.ej.
`t1_gdinotiny560_v2short_scene`, `d1_gdinotiny560_edirpair_scene`,
`g1_gdinotiny560_v2short_subject`. La fase remite al plan maestro (doc 62).

## Cómo agregar una campaña

1. **Correr la cadena** sobre el banco (hoy **47 clips**: 34 del rodaje + 13 del
   estrato B; runners de referencia `docs/operacion/datos/81-ciclo-rodaje-runner.py` y
   `102-ciclo-internet-runner.py`) → un directorio con `eval_<clip>.json` por clip.
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
5. **Extender `docs/operacion/datos/96-verificar-indices.py`** con una fila en `CIFRAS`.
   No es opcional: el script tiene un **guard de cobertura** que falla si una campaña
   con `metrics.json` no tiene cifra verificada — justamente para que "todo verde" no
   signifique "verde sobre lo que mirábamos hace tres meses".

> ⚠️ **Trampa: re-evaluar NO regenera `metrics.json`** (encontrada el 2026-08-09 en
> I1/I2). El agregador **copia `campaign.yaml` adentro de `metrics.json`**, así que
> tocar el GT o el yaml sin volver a correr el paso 3 deja el archivo con las cifras
> nuevas y **la procedencia vieja** — I1/I2 llegaron a declarar el freeze del banco
> pre-corrección, con lo cual quien reprodujera desde ese sha obtenía F1 0,500 en vez
> de 0,333. **Después de cualquier cambio de GT o de `campaign.yaml`: re-correr el paso
> 3 y diffear.** Con los `evals/` archivados cuesta segundos y no usa GPU.

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

> ⚠️ **Este README es el manual de proceso** (cómo se agrega y se agrega una campaña).
> **La lista canónica de limitaciones es L1–L8 en `results/index.md`**, no la de acá:
> si las dos discrepan, manda `index.md`. Lo de abajo quedó como resumen y se actualizó
> el 2026-08-09.

Vienen del banco, no de la combinación — están en
`e-ovrt_datasets/datasets/registry/clip_bench.md` y se declaran una vez en el informe,
no por campaña: **FAR/hora se reporta pero no sostiene una cota** (D-90.1 **precisada**
el 08-07/09 — limitación **L1**: con el clip soak del estrato B la métrica pasó a ser
computable, 29,2 y 1.850,8 FA/hora = 3 y 190 FP en 6:09,6, pero 0,1027 h están a dos
órdenes de magnitud de las 3 h que exigiría afirmar una cota; la evidencia principal
sigue siendo el control de negativos), sin doble anotación (sin kappa, decisión
declarada — **L2**), bordes adjudicados en 6 clips (**L3**), **obra real medida pero
acotada** (**L4 precisada**, D-113.1: el estrato B aportó 13 clips no guionados, y su
contenido nuevo es la frontera de juzgabilidad), escenarios desbalanceados (**L5**).
