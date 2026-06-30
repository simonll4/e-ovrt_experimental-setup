# e-ovrt_experimental-setup

Declaración de **experimentos** de la plataforma E-OVRT-VDP: los *prompt sets* y los
*manifiestos de corrida* que antes vivían dentro de `e-ovrt_media-plane/configs/`.

Este repo es la fuente canónica de "qué se estudia"; el media-plane conserva el **contrato**
(schemas, `PromptPlan`, adaptadores) y las **capacidades** (catálogos `configs/models/`,
`configs/datasets/`), referenciadas por id desde los manifiestos.

Ver el diseño: `e-ovrt_media-plane/docs/superpowers/specs/2026-06-27-experimental-setup-config-design.md`.

## Layout

```
prompts/        # prompt sets (formato classes + phrasings por backend)
  cr01_cr02_v2_short.yaml      # congelado (3 clases)
  cr01_cr02_bench_v2.yaml      # congelado BENCH v2 (4 clases, incl. bare_head)
  ppe_v2_descriptive.yaml      # set descriptivo NO congelado (A/B)
experiments/    # manifiestos de corrida
  mock.yaml, gdino.yaml, yoloe.yaml, yoloe_video.yaml, mock_chv.yaml
  bench_v2/     # matriz de experimentos BENCH v2
```

## Cómo correr (desde la raíz del media-plane)

**Importante:** ejecutar `eovrt-media` **desde la raíz de `e-ovrt_media-plane`** (los catálogos
de datasets usan rutas relativas `../e-ovrt_datasets/...` que resuelven contra el CWD), pasando el
manifiesto externo con `--config`:

```bash
cd ../e-ovrt_media-plane
source .venv/bin/activate
eovrt-media run --config ../e-ovrt_experimental-setup/experiments/mock.yaml
eovrt-media run --config ../e-ovrt_experimental-setup/experiments/bench_v2/<exp>.yaml
```

### Resolución de referencias (dos raíces)

- `prompts.ref` → `e-ovrt_experimental-setup/prompts/<ref>.yaml` (raíz del experimento, se descubre
  subiendo desde el manifiesto hasta el dir que contiene `prompts/`).
- `model.ref` / `source.ref` → catálogo del media-plane (`configs/models/`, `configs/datasets/`),
  autodescubierto repo-relative. Override: `--catalog-root <path>` o `EOVRT_MEDIA_CATALOG_ROOT`.

Asume que `e-ovrt_media-plane`, `e-ovrt_experimental-setup` y `e-ovrt_datasets` viven como
**repos hermanos** en el mismo directorio.

## Convención de versionado

Se commitean prompt sets y manifiestos (texto). No se commitean salidas de corridas.
Los prompt sets congelados (`cr01_cr02_*`) **no se modifican** — reproducibilidad del BENCH.
