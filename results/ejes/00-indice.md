# Ejes de lectura de la evidencia

**Fecha:** 2026-09-10

`results/` está organizado por **material** (imágenes / video / tiempo real) y ésa
sigue siendo la organización canónica: los cuatro índices son la fuente de las
cifras. Esta carpeta no agrega ni una medición — **son vistas de lectura** que
cortan la misma evidencia por otros ejes, los que hacen falta para explicar el
trabajo en la defensa.

| Eje | Documento | Pregunta que responde |
|---|---|---|
| Escenario de despliegue | [`01-dbe-vs-ebe.md`](01-dbe-vs-ebe.md) | ¿Qué se midió offline (acople por archivo) y qué en vivo (bus ZeroMQ)? |
| Día de rodaje | [`02-rodaje.md`](02-rodaje.md) | ¿Qué salió del rodaje del 25-jul y qué no es rodaje aunque lo parezca? |
| Modelo | [`03-baseline-vs-finetuning.md`](03-baseline-vs-finetuning.md) | ¿Qué es zero-shot y qué produjo el fine-tuning? |

---

## Lo que hay que saber antes de leer cualquiera de los tres

**Todas las cifras de los cuatro índices son zero-shot.** Ningún modelo ajustado
produjo un número en `results/`. El fine-tuning es una línea aparte, cerrada, que
vive en `finetuning/` y cuyo valor declarado es una curva de tres puntos, no un
modelo adoptado. Detalle en [`03-baseline-vs-finetuning.md`](03-baseline-vs-finetuning.md).

**El marco de lectura no cambia** (doc 81 §1): cada número es el rendimiento
medido de **una combinación concreta**, no una nota. El contraste entre filas es
el experimento.

---

## Estado de la organización — verificado el 2026-09-10

Los dos verificadores mecánicos que gobiernan `results/` se corrieron y dan verde:

| Verificador | Qué comprueba | Resultado |
|---|---|---|
| `docs/operacion/datos/96-verificar-indices.py` | Que cada cifra citada exista en disco; cobertura campaña↔cifra; deltas del bootstrap; docs de procedencia | **17/17 campañas cubiertas**, 37 docs referenciados sin faltantes — ✅ |
| `docs/operacion/datos/109-verificar-organizacion.py` | Integridad lab↔banco, correcciones firmadas, exclusiones declaradas, freeze del banco | **freeze de 189 archivos**, exclusiones declaradas — ✅ |

Y el inventario canónico de corridas ([`../evidence-runs.md`](../evidence-runs.md)):
**1.436 corridas únicas** — 440 del media-plane, 996 del control-plane — resueltas
en **35 resultados**, con `status` `copied` = 1.392 y `archived_only` = 44,
**cero `missing` y cero `conflict`**.

## Cómo se reparten los 35 resultados

El prefijo del `result_id` es el índice de `results/` al que pertenece:

| Índice | Resultados | Filas del inventario |
|---|---:|---:|
| `bench_imagenes` | 5 | 41 |
| `bench_nivel_a` | 4 | 84 |
| `clip_bench` | 14 | 928 |
| `realtime` | 12 | 707 |
| **Total** | **35** | **1.760** |

Las filas suman más que las corridas porque **43 corridas pertenecen a dos
resultados** a la vez (marcadas `shared` en el inventario): la misma corrida
citada desde dos lugares, no una duplicación.
