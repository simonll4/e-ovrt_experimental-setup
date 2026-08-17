# Configuraciones

Configuraciones congeladas por tier/run. Declaran modelo, datos por manifiesto, vocabulario
ordenado, firma exacta de parámetros entrenables, seed, épocas, batch, workers, resolución y
política de checkpoint. `t1_yoloe26s_lp.yaml` implementa D-FT-01 y D-FT-11: diez épocas sobre
2.946/483, con sólo 12 tensores y 3.096 parámetros de proyección entrenables. ~~D-FT-08 continúa
pendiente hasta aprobar formalmente el contrato de serving de vocabulario fijo.~~
✎ **2026-08-15: D-FT-08 aprobada por el usuario.** El contrato de serving vigente es
vocabulario **fijo y ordenado** — ids `[person, helmet, vest, bare_head]` ligados en ese orden
a `[person, helmet, vest, "bare head"]`, con `set_classes()` prohibido sobre el checkpoint T1.
