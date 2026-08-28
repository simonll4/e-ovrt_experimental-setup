# Fine-tuning E-OVRT

Workspace operativo para preparar, ejecutar y documentar la jornada de fine-tuning E-04.
El gobierno del trabajo vive en:

- [`docs/operacion/116`](../../docs/operacion/116-plan-maestro-finetuning.md): plan maestro;
- [`docs/operacion/117`](../../docs/operacion/117-decisiones-y-tareas-finetuning.md):
  decisiones y backlog vivo;
- [`docs/decisiones/ADR-017`](../../docs/decisiones/adr-017-fine-tuning-jornada-experimental.md):
  autorización y escalera T1→T2→T3.

Estado: ✎ **2026-08-17 — JORNADA T1 CERRADA. Veredicto D-FT-12: NO-GO** (`docs/operacion/123`).
El full corrió en Mendieta (job `1167640`, `COMPLETED`, 10/10 épocas), el checkpoint se promovió
por hash a `media-plane/models/yoloe/finetuned/t1/best.pt` y se evaluó **una sola vez** contra
`bench_v3`: `bare_head` AP50 **0,0000 → 0,0455** y recall CR-01 **0,0002 → 0,2089**, pero el gain
gate exigía +0,05 (faltaron **0,0045**) o recall >0,5, y `person` cayó **−11,62 %** sobre un tope
de 10 %. El checkpoint **no se adopta** como modelo de servicio; catálogo y peso se conservan
sólo para reproducir la evaluación. Negativo **pre-registrado**: es resultado, no fracaso
(ADR-017). Artefactos: `runs/t1_yoloe26s_tuned_bench_v3/eval/` y
`manifests/t1_{promotion,go_no_go}_1167640.json`.

> ✎ **2026-08-28 — la jornada E-04 está COMPLETA: T2 NO-GO (2026-08-21) y T3 cerrado con causa
> técnica** (`docs/operacion/127` y `128`; anotado acá porque este encabezado cerraba en T1 —
> `docs/operacion/130`). **T2** (full fine-tuning YOLOE-26s, job `1167982`, enmienda **D-FT-16**:
> SGD lr0=0,01 explícito tras el submuestreo `1167864` con AdamW auto — no es un reintento)
> **colapsó en entrenamiento**: `EarlyStopping` en la época **16/60** con `best_epoch = 1`. Con
> firma del usuario se consumieron los dos one-shot contra `bench_v3` y COCO val2017:
> **ganancia PASA** (`bare_head` AP50 0,0000 → **0,0909**, sólo en `shel5k`; el rescate de recall
> falla, 0,0055), **retención in-domain FALLA ×4** (`person` **−49,7 %**, `helmet` −40,6 %,
> `vest` −65,6 %, mAP50 −43,4 %, tope 10 %) y **retención OV FALLA** (mAP50 COCO 0,4347 →
> 0,1247, **−71,3 %**). Checkpoint **no adoptado**; constancia en
> `manifests/t2_{promotion,go_no_go}_1167982.json`. **F-127.1: el fallo de T1 no era de
> capacidad, es estructural — 2.946 imágenes de train frente a 10,35 M de parámetros**; la
> curva capacidad/retención queda **completa con 3 puntos** (base · T1 · T2) y es el valor
> declarado de la jornada. T3 quedó cerrado con causa técnica (doc `117` §2). No hay más brazos
> contra `bench_v3` sin pre-registración nueva (acta `128` §5). Trampa de cita: T1 gana por
> recall CR-01 (0,2089) y T2 por AP (0,0909) — no es una métrica única.
>
> ✎ **2026-08-28 — desviación declarada respecto de la Tabla 28 del protocolo (§17.1).** La
> Tabla 28 acotaba el split de entrenamiento a **500–2.000 imágenes**; `finetuning_v1` usa
> **2.946 train / 483 val** (`manifests/finetuning_v1.summary.json`), +47 % sobre el techo.
> Causa: se tomó el **100 % de los linajes elegibles** de `construction_site_safety` (2.203) +
> `ppe_siabar` (743) tras la deduplicación perceptual y la exclusión íntegra de las fuentes del
> banco (`chv` excluido: sus 1.330 imágenes son estrato de `bench_v3`), sin submuestrear al
> techo de 2.000. F-127.1 muestra que aun ese volumen es insuficiente. No estaba
> justificada por escrito en ADR-017 / doc 100 / D-FT-11 hasta esta nota (`docs/operacion/130`,
> R-03).

> **Dos «NO-GO» distintos.** El de arriba es el **veredicto** de D-FT-12. El del histórico que
> sigue era la **puerta de autorización** previa al envío, levantada el 2026-08-15.

*(histórico)* **NO-GO para el full T1**, con el stack técnico verde. D-FT-01/D-FT-09/D-FT-11 están
aprobadas y el split contiene 2.946 train y 483 val, sin usar BENCH para entrenamiento. El smoke
corregido `1166583` terminó `COMPLETED 0:0` en A30 y confirmó exactamente 12 tensores/3.096
parámetros entrenables, optimizador 12/12, checkpoints y gate técnico v2. El servicio real cargó
e infirió el checkpoint con vocabulario fijo; la procedencia T-FT-023 quedó congelada en un
snapshot inmutable de 72 fuentes, verificado localmente y en Mendieta. ✎ **2026-08-15: el
usuario firmó D-FT-08 (contrato de serving), D-FT-12 (márgenes go/no-go, antes de la
baseline) y D-FT-13; no resta ninguna aprobación humana. La misma jornada cerraron
T-FT-031 y T-FT-032**: comando de evaluación congelado (`scripts/evaluate_t1_bench_v3.py`),
enforcement canónico v2 en el config del media-plane, catálogo finetuned
(`yoloe-26s-ft-t1.yaml`), y **baseline YOLOE-26s one-shot** en
`runs/t1_yoloe26s_baseline_bench_v3/` (6.477/6.477; cifras y hashes en
`docs/operacion/120` del repo docs). Las 7 gates del full-authorization están cerradas.
No existe
`full-authorization.json` y se mantienen cero jobs full enviados. ✎ *(superado el 2026-08-15:
la autorización se emitió en el clúster con `gates=7` y se envió un (1) job full — ver el estado
al inicio de esta sección.)*

## Qué pertenece aquí

```text
configs/              configuraciones congeladas de entrenamiento
scripts/              preparación, entrenamiento, export y verificación
containers/           definiciones Apptainer; imágenes locales ignoradas
slurm/                jobs de smoke y corrida completa
manifests/            procedencia y hashes de datos, pesos, entorno y runs
data/payloads/        bundles para el clúster; ignorados por Git
weights/base/         pesos de entrada de trabajo; ignorados por Git
weights/finetuned/    checkpoints nuevos; ignorados por Git
runs/                 logs y artefactos de ejecución; ignorados por Git
tests/                fixtures sintéticas y tests del tooling
```

Los artefactos pesados siguen ignorados. Se versionan el materializador, packager, trainer,
tests, configs, manifiestos, definición Apptainer y scripts Slurm; payload, pesos, imagen y runs
se generan en sus directorios de trabajo y se verifican por SHA-256.

El trabajo histórico de `e-ovrt_datasets/main` es material de referencia: pueden recuperarse
esquemas de manifiesto, trazabilidad y funciones de exportación, pero no sus vistas
`canonical_cr01_cr02`/`finetuning_cr01_cr02`, sus clases v1 ni sus splits. Toda pieza adoptada
debe ajustarse a `canonical_v2`, al contrato de anotación vigente y a `bench_v3` congelado.

## Fronteras con los repos hermanos

- `e-ovrt_datasets` conserva datos canónicos, splits, labels y licencias.
- Este directorio declara el split derivado `finetuning_v1`, materializa payloads
  transportables y registra su procedencia, sin reescribir el repositorio de datasets.
- Los pesos se almacenan aquí durante el proceso de entrenamiento.
- `e-ovrt_media-plane` conserva el adapter, el catálogo y la copia promovida de un peso que
  ya pasó el gate de serving.
- `docs/operacion` conserva las decisiones y la evidencia citable.

## Reglas

1. No versionar pesos, payloads, imágenes de contenedor, runs ni credenciales.
2. Todo recurso pesado debe tener un manifiesto versionado con SHA-256, tamaño y origen.
3. Ningún script portable puede depender de una ruta `/home/<usuario>/...`.
4. Un smoke remoto precede a cada tier completo.
5. Los jobs remotos usan Slurm y registran su entorno efectivo.
6. `bench_v3` se usa sólo para evaluación final, nunca para tuning o selección.
7. No promover un peso al media-plane sin integridad, binding de clases y serving smoke.
8. No repartir variantes de un mismo linaje ni duplicados perceptuales entre `train`, `val` y
   bench.
9. No copiar una implementación histórica sin comprobar compatibilidad con los contratos y
   consumidores actuales de la plataforma.

## Lanzamiento manual de T1

La corrida completa requiere dos puertas independientes. `smoke-ready.json` y
`technical-smoke-ready.txt` vinculan el smoke CUDA con configuración, trainer, payload, pesos e
imagen. `full-authorization.json` aprueba D-FT-08 y enlaza por hash la procedencia, serving,
evaluación local, baseline BENCH v3 y el smoke técnico. Sólo cuando ambas puertas verifican, el
operador ejecuta en Mendieta:

```bash
EOVRT_T1_ROOT="$PWD" bash bundle/scripts/submit_t1_full_mendieta.sh RUN_T1_10_EPOCHS
```

El wrapper comprueba inventario exacto, hashes, autorización, duplicados activos y cluster `ivb`
antes de enviar las 10 épocas. No se debe invocar `sbatch` directamente. El usuario conserva la
ejecución manual del full; los watchers sólo observan y finalizan un job ya enviado.
