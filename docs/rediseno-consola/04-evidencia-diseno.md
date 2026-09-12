# La consola como vitrina de evidencia

**Fecha:** 2026-09-10
**Objetivo:** que el día de la defensa la consola muestre **lo que el informe
reporta**, y nada más. Todo lo que fue prueba de plataforma se archiva: deja de
verse, no se borra.

Este documento es el **por qué**. El **qué hacer** está en `tramo-6.md` y
`tramo-7.md`.

---

## 1. El criterio ya existe — no se inventa

`results/evidence-runs.yaml` (`schema_version: evidence_runs.v1`, 438 líneas) es
el registro canónico de qué corrida es evidencia y por qué. Se genera de forma
determinista y ya declara:

- **1.436 corridas** de evidencia: 440 del media-plane, 996 del control-plane.
- **35 `result_id`** distintos. Su prefijo coincide **uno a uno con los cuatro
  índices de `results/`**, que es la estructura con la que ya se citan las cifras:

  | Prefijo = índice | Resultados | Filas |
  |---|---|---|
  | `bench_imagenes` | 5 | 41 |
  | `bench_nivel_a` | 4 | 84 |
  | `clip_bench` | 14 | 928 |
  | `realtime` | 12 | 707 |
  | | **35** | **1.760** |

- ⚠ La columna `collection` tiene un cuarto valor, **`shared`**, que **no es una
  colección**: marca las 43 filas de corridas que pertenecen a más de un
  resultado (una misma corrida bajo `bench_imagenes/gdino560` y
  `realtime/gdino560`). Por eso se agrupa **por el prefijo del `result_id`**, no
  por esa columna: agrupar por ella dibuja un grupo fantasma y saca esas corridas
  de donde corresponden.
- **16 campañas** con artefacto.
- Por cada corrida: su `role` (21 distintos), su `source_ref` (el eval o dato que
  la cita) y su documento de procedencia.
- `archived_only` (44 corridas cuyo directorio ya no existe pero cuyo dato
  sobrevive versionado), `source_dispositions` con exclusiones **razonadas** —
  por ejemplo dos corridas del doc 73 excluidas por ser telemetría previa y un
  bloque parcial de 25 s.

**La consola simplemente no sabe que este archivo existe.** Ese es todo el hueco.

La forma consumible ya está resuelta: `results/evidence-runs/collections/*.csv`,
cuatro archivos planos con una fila por corrida y las columnas
`collection, result_id, role, plane, run_id, status, source_ref, artifact_path`.
No hay que parsear el YAML.

---

## 2. Lo medido: son dos problemas distintos

| Superficie | Hoy | Evidencia | Ruido |
|---|---|---|---|
| Corridas (media-plane) | 472 | 420 | **52 — 11 %** |
| Ejecuciones de experimento (`runs/`) | 398 | ~13 | **385 — 97 %** |
| Manifiestos de experimento | 19 | a definir | `mock`, `gdino`, `yoloe`, `bench_v2`… |

Las 385 ejecuciones de ruido son smokes del orquestador, y se ven de un vistazo:

```
orq_2a 78 · orq_1 78 · orq_alerts_502 77 · orq_alerts 77 · gate_orq 75
```

**La conclusión que ordena el trabajo:** archivar limpia **Experimentos** y casi
no toca **Corridas**. En Corridas el problema no es la basura sino la
**granularidad** — 420 filas planas donde lo presentable son 35 resultados.

Por eso son dos remedios:

- **Archivar** (`tramo-6.md`) → resuelve Experimentos.
- **Vista Evidencia** (`tramo-7.md`) → resuelve Corridas, colapsando 1.436
  corridas en los 35 resultados que efectivamente se reportan.

---

## 3. Decisiones

| # | Decisión |
|---|---|
| **E-1** | **Archivar + vista Evidencia**, las dos cosas. Sólo archivar dejaría 420 filas planas en Corridas el día de la defensa. |
| **E-2** | **La vista Evidencia lee el archivo curado** (`results/evidence-runs/artifacts/`, 120 MB, las 1.436 corridas con `summary.json`, `metrics`, `detections`, `alerts`, `pattern_events`). No depende de que el media-plane, el control o la GPU estén arriba. Cuando la corrida todavía existe en disco, la vista **ofrece abrir su detalle vivo**. |
| **E-3** | **Archivar es ocultar, nunca borrar ni mover.** El flag vive en la consola, alimentado por el registro. Nada se mueve de `runs/` ni de los repos hermanos: es reversible y no toca a los planos. |
| **E-4** | **El default de la API no cambia.** El filtro de evidencia es un parámetro explícito; `GET /api/runs` sin parámetros sigue devolviendo todo. Es el **frontend** el que pide la vista. Ver §4. |
| **E-5** | **Los 35 títulos los escribe el usuario, no Codex.** Los `result_id` son legibles para nosotros (`clip_bench/t1_gdinotiny560_v2short_scene`) pero no son un rótulo de defensa. Codex genera el esqueleto con los 35 y una etiqueta derivada; el texto final lo pone el usuario. |
| **E-6** | **La clasificación de experimentos se deriva y se revisa.** Regla automática + lista de excepciones + reporte de en qué cae cada slug, para que el usuario lo revise antes de darlo por bueno. Ver §5. |

---

## 4. La trampa: no cambiar el default del endpoint

El contrato congelado (`__tests__/contrato/`) afirma el comportamiento de
`GET /api/runs` con fixtures sintéticas. **Esas fixtures no son evidencia** — no
están en el registro.

Si el filtro de evidencia se vuelve el valor por defecto del endpoint, el
listado deja de devolverlas y **el contrato se pone rojo**, en los cuatro
flujos. Y el arreglo tentador —tocar el contrato— es justo lo prohibido.

**Regla:** el parámetro nuevo (`vista=evidencia|archivadas|todas`) tiene
`todas` como valor por defecto. Quien elige la vista es la pantalla, pasándolo
explícitamente. Un `GET /api/runs` pelado se comporta hoy igual que ayer.

Lo mismo vale para las 454 pruebas de frontend y las 784 de backend: son la línea
de base y tienen que seguir verdes.

---

## 5. Cómo se clasifica un experimento

El registro cubre corridas de media-plane y control-plane. **No cubre las
ejecuciones de experimento** de `runs/`, así que necesitan regla propia.

**Regla derivada:** una ejecución es evidencia si al menos una de las corridas
que consolidó aparece en el registro. Un manifiesto es evidencia si tiene al
menos una ejecución de evidencia.

**Excepciones explícitas:** un archivo chico y versionado —`results/evidence-vista/consola.yaml`—
con dos listas, `forzar_evidencia` y `forzar_archivado`, por slug o por id de
ejecución. La regla derivada es el default; la lista manda cuando aparece.

**Y se revisa antes de cerrar:** el tramo tiene que imprimir en qué cae cada uno
de los 19 manifiestos y cada grupo de ejecuciones, con el motivo. Que la regla
sea automática no la vuelve correcta: `diag_riesgo_activo` o `video16_clip10_gt`
pueden caer del lado equivocado, y eso lo decide el usuario mirando la lista.

---

## 6. Lo que no entra

- **Borrar nada.** Ni corridas, ni ejecuciones, ni artefactos.
- **Mover directorios** entre repos o dentro de `runs/`.
- **Tocar el contrato congelado** ni ningún test existente.
- **Modo defensa** (esconder Cámaras, Clips, Plataforma). Se evaluó y quedó
  afuera de este tramo; si hace falta, es un cambio chico y posterior.
- **Imágenes en la vista Evidencia.** La `archive_policy` del registro excluye
  `previews`, `frames`, `images` y `annotated`, así que el archivo curado no las
  tiene. Los cuadros anotados se ven abriendo el detalle vivo (E-2).

---

## 7. Dependencia a tener presente

`results/evidence-runs/` está **gitignorado**: son 120 MB que viven en la capa de
evidencia del backup (`docs/operacion/126`), no en git.

Consecuencia práctica: **la máquina de la defensa tiene que tenerlo en disco.**
La vista Evidencia debe degradar con dignidad si el directorio no está — un
estado vacío que lo diga con todas las letras, nunca una pantalla en blanco ni un
error crudo.
