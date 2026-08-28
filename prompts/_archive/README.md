# Prompt sets archivados

Sets exploratorios del **Carril 2 (E-DIR)** que no ejecuta ningún manifiesto de
`experiments/` todavía. Se archivaron el 2026-07-18 para dejar el catálogo activo
(`prompts/*.yaml`) solo con lo que está en uso o a punto de usarse:

- `cr01_cr02_bench_v2` — **frozen**, protocolo BENCH v2 (12 manifiestos).
  ✎ 2026-08-28: el YAML dice `status: exploratory` — **no está congelado**
  (`docs/operacion/130`).
- `cr01_cr02_v2_short` — **frozen**, demos/smoke (7 manifiestos).
- `eind_v1` — **frozen_pending_review**, núcleo E-IND, espera acta para congelarse.
  ✎ 2026-08-28: **`frozen`** desde el 2026-07-29 por acta (`docs/operacion/76`); el YAML
  ya lo dice (`docs/operacion/130`).

`prompt_store` (BFF) y la resolución de `prompts.ref` del media-plane leen solo el
top-level de `prompts/`, así que estos archivados **no aparecen en el catálogo ni son
referenciables por `ref`**. Para reactivar uno, moverlo de vuelta a `prompts/`.

## Contenido

| Archivo | derives_from | Motivo del archivo |
|---|---|---|
| `edir_exp_cr01_candidates.yaml` | — | candidatas CR-01 para derivar `edir_v1`; línea E-DIR sin manifiesto aún |
| `edir_exp_cr02_candidates.yaml` | — | candidatas CR-02 para derivar `edir_v1` |
| `edir_exp_weak_classes.yaml` | cr01_cr02_bench_v2 | rescate de clases débiles (bare_head/vest) |
| `ppe_v2_descriptive.yaml` | cr01_cr02_bench_v2 | variante descriptiva para A/B contra el frozen del BENCH |
