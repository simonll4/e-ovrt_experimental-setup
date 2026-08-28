# Bench de imágenes — resultados consolidados

Índice de los resultados del **material de imágenes**: selección de modelos (Fase S),
caracterización del banco `bench_v3` y extensibilidad a clases nuevas. El estado por
persona (Nivel A, el nivel donde se decide entre estrategias de prompts) vive en
`results/bench_nivel_a/`; las alertas sobre video (Nivel B) en `results/clip_bench/`.

**Cómo leer estas tablas.** Cada fila es el rendimiento medido de una combinación
concreta, no una nota (marco del doc 81 §1). La pregunta del trabajo es *qué se
consigue hoy con OVD sin entrenar en construcción civil*; el contraste entre filas
**es** el experimento. Todo es **zero-shot**: ningún modelo vio una imagen de este
dominio en entrenamiento.

**Regla de reporte (`registry/bench_v3.md`):** las métricas se dan **por estrato y
agregadas, nunca solo el agregado.** El agregado de `bench_v3` está dominado por
`shel5k` (77% de las imágenes).

---

## 1. El banco: `bench_v3` (congelado 2026-07-23)

**6.477 imágenes, 3 fuentes independientes.** Manifest con sha256 por fuente
(`bench_v3_manifest.json`); procedencia y salvedades completas en
`e-ovrt_datasets/datasets/registry/bench_v3.md`.

| Estrato | Origen | Imágenes | Qué aporta |
|---|---|---|---|
| `bench_obra` | `construction_site_safety` curado (doc 63) | 147 | Núcleo con pasada visual muestral; todas las clases con negativos explícitos |
| `chv` | CHV (académico, cita obligatoria `wang2021ppe`) | 1.330 | 2ª fuente person/helmet/vest; **mejor AP de vest del proyecto** |
| `shel5k` | SHEL5K (Mendeley, CC BY 4.0) | 5.000 | 3ª fuente; **`bare_head` nativo** (6.120 instancias vs 61 del núcleo) + `person_gt_shel5k.json` (5.248 violadores CR-01) |
| **Total** | | **6.477** | |

> **Por qué existe `bench_v3` y no el BENCH original.** El split de 196 imgs de
> `construction_site_safety` resultó ~20–25% fuera de dominio (selfies COVID, PASCAL
> VOC, aeropuerto/casino — auditado en doc 63). Se conserva sin modificar como
> artefacto histórico; todo resultado reportable usa `bench_v3`.

## 2. Fase S — selección de modelos (docs 61/64/66)

### S1/S2 sobre el núcleo curado `bench_obra` (147 imgs)

| Configuración | mAP50 obra | recall CR-01 obra | vest AP obra |
|---|---|---|---|
| **`gdino-tiny-560`** | **0,503** | 0,369 | 0,520 |
| `gdino-tiny` (800) | 0,502 | 0,323 | 0,456 |
| `gdino-base-560` | 0,474 | **0,400** | **0,582** |
| `yoloe-26x` | 0,405 | 0,000 | 0,182 |

### Las 6 configuraciones que NO llegaron a `bench_obra` (✎ agregado 2026-08-10)

La tabla de arriba re-puntúa **4** configuraciones sobre el núcleo curado. La matriz S1
original (doc 64) midió **10**, y las 6 restantes se descartaron antes de esa re-puntuación.
Hasta hoy este índice nombraba solo a `mm-gdino-tiny` y `mm-gdino-large` en la prosa de
descartes, y **omitía a `mm-gdino-base` y a `gdino-base` (800)** — que sí se midieron. Van
acá con sus números, para que la exclusión no sea una afirmación sin dato:

> ⚠️ **Marco distinto: estas filas son BENCH v2 (196 imgs), no `bench_obra` (147).** No se
> comparan celda a celda con la tabla de arriba; se leen entre sí. Es la única escala en la
> que existen: nunca se re-puntuaron, precisamente porque quedaron fuera.

| Configuración (BENCH v2, 196 imgs) | mAP50 | recall CR-01 | vest AP | `bare_head` AP | inf p50 | Por qué no siguió |
|---|---|---|---|---|---|---|
| `gdino-base` (800) | 0,401 | 0,514 | 0,43 | 0,01–0,03 | 213 ms | **Dominada por su propia variante 560** (0,453 mAP, 146 ms): peor mAP y **+46% de latencia**. Misma regla que descartó `gdino-tiny` (800) |
| `mm-gdino-base` | 0,360 | 0,029 | 0,39 | **0,00** | 213 ms | **Mediocre sin ventaja en nada** (hallazgo 5 del doc 64): recall CR-01 0,029 y `bare_head` 0,00 |
| `mm-gdino-large` | 0,017 | — | — | — | 723 ms | **Roto**: reproduce el bug de bboxes degeneradas (sanity-check pre-planificado: 2–3 degeneradas) |
| `mm-gdino-tiny` | — | — | — | — | — | **Excluido a priori** en Sprint 2 por bboxes degeneradas; no se re-midió |
| `yoloe-26l` / `26m` / `26s` | 0,407 (26x, campeón de la familia) | 0,049 (`26s`) | — | **0,000 en las 4** | 43 ms (`26x`) | **La familia entera es ciega a la condición.** `26x` es el campeón YOLOE y **el único tabulado arriba** por eso: representa a la familia en su mejor talla, no en la más rápida |

Fuente: doc 64 (BENCH v2, 196 imgs — sin `metrics.json` mecánico; verificado a mano
2026-08-14).

**Lectura de esta tabla, en una línea:** de los 6 descartes, **3 son por dominancia
medida** dentro de su propia familia (las dos variantes 800 y las tallas menores de YOLOE),
**2 por defecto técnico verificado** (MM-GDINO large y tiny, bboxes degeneradas) y **1 por
mediocridad sin eje propio** (`mm-gdino-base`). Ninguno quedó afuera por no haberse
probado.

### Confirmación B5 sobre `bench_v3` completo (6.477 imgs)

| Modelo | mAP50 (n=6.477) | recall CR-01 (n=5.313) | inf p50 † |
|---|---|---|---|
| **`gdino-tiny-560`** | **0,551** (1º) | 0,308 | **129 ms** |
| `gdino-base-560` | 0,525 | **0,599** (1º) | 146 ms |
| `yoloe-26x` | 0,442 | 0,000 | 43 ms |

† Las latencias p50 provienen de la matriz sobre el BENCH v2 (196 imgs, doc 64), no
se re-midieron sobre `bench_v3`.

> ✎ **2026-08-28 — dos precisiones sobre esta tabla (`docs/operacion/130`, R-04 y R-11).**
> (a) **El `n=5.313` del recall CR-01 es el del GT del 2026-07-23**; con el GT vigente
> `person_gt_bench_obra.json` (fix del 2026-07-29: 60 violadores en `bench_obra` en vez de
> 65) el denominador sería 5.308. La medición **no se repitió**: la cifra se cita fechada.
> (b) **La comparación de resolución S1/S2 en `tiny` no está a umbral igual**: `gdino-tiny`
> (800 px) corrió a `box_threshold` 0,35 y `gdino-tiny-560` a 0,30 (catálogos
> `configs/models/grounding-dino/gdino-tiny.yaml` y `gdino-tiny-560.yaml` del media-plane;
> así en todas las corridas). El par `gdino-base`/`gdino-base-560` sí está a 0,30 en ambos.
> Por eso "560 px iguala o mejora el mAP de 800 px" en `tiny` está **confundido con el
> umbral** (léase "560 @0,30 ≥ 800 @0,35"); el mAP50 0,551 del campeón sigue siendo el dato
> de la combinación (560 · 0,30 · text 0,25), y el **−24 % de latencia no depende del
> umbral**.

**El campeón se sostiene en las dos escalas** — `gdino-tiny-560` gana mAP50 tanto en
el núcleo curado (147) como en el bench completo (6.477): **es robusto a la fuente**,
no un artefacto del denominador chico.

### Por clase y por estrato (la asimetría es estructural)

| Modelo | Estrato | person | helmet | vest | bare_head | recall CR-01 |
|---|---|---|---|---|---|---|
| `gdino-tiny-560` | `shel5k` (n=5.000) | 0,770 | 0,707 | — | **0,133** | 0,308 |
| `gdino-tiny-560` | `chv` (n=1.330) | 0,862 | 0,886 | **0,553** | — | — |
| `gdino-base-560` | `shel5k` (n=5.000) | 0,693 | 0,415 | — | **0,399** | **0,602** |
| `gdino-base-560` | `chv` (n=1.330) | 0,783 | 0,453 | **0,576** | — | — |
| `yoloe-26x` | `shel5k` (n=5.000) | 0,785 | 0,715 | — | 0,000 | 0,000 |
| `yoloe-26x` | `chv` (n=1.330) | 0,785 | 0,888 | 0,243 | — | — |

### Decisiones S2 que salieron de acá

1. **Campeón: `gdino-tiny-560`.** La resolución 560 da **−24% de latencia con igual o
   mejor mAP que 800** (doc 61; el −24% es inferencia batch sobre el BENCH — D-61.4 —
   no una medición live: `base-560` quedó **sin latencia live medida**, doc 101 §1).
   La variante 800 quedó descartada por dominancia. ✎ **2026-08-10 — el corolario, que
   hasta hoy era inferencia del lector: por eso NINGUNA variante 800 px se llevó al banco
   temporal** (decisión declarada en doc 64 §Decisiones S2). No es un hueco de cobertura:
   correr 800 en los clips habría medido una configuración **dominada** y roto la variable
   única de las campañas. Sigue siendo **trabajo futuro con causa**: doc 103 §7.4 lista
   "800 px" entre las mitigaciones **no medidas** para el colapso de `vest` a distancia.
2. **`gdino-base-560` es el especialista, con rol acotado, en dos ejes:**
   **`bare_head` (evidencia de CR-01)** — casi empate en `bench_obra` (0,400 vs
   0,369, n=65) que **se separa con claridad al sumar `shel5k`** (0,599 vs 0,308,
   n=5.313 — ✎ 2026-08-28: GT del 2026-07-23; con el GT vigente `person_gt_bench_obra.json`
   del 07-29 el denominador es 5.308; la medición no se repitió, `docs/operacion/130`): no
   era ruido de denominador chico, es un efecto real — **y `vest`
   (CR-02)** (0,582 vs 0,520 en `bench_obra`; en video, SDR CR-02 0,281→0,920 — T2).
   (✎ 2026-08-06: *la etiqueta anterior "especialista CR-02/`bare_head`" mezclaba
   los dos ejes* — `bare_head` es evidencia de CR-01, no de CR-02.)
3. **La familia YOLOE no sirve para CR-01**: AP 0,000 en `bare_head` en las cuatro
   variantes medidas (26x/26l/26s/26m); recall CR-01 0,000 en `26x` (0,049 en `26s`).
   Es rápida (43 ms) pero ciega a la condición que importa.
4. **MM-Grounding-DINO descartado — la familia COMPLETA, sus tres variantes** (✎ 2026-08-10:
   *antes esta línea decía "en dos pasos" y nombraba solo `tiny` y `large`, omitiendo a
   `mm-gdino-base`, que sí se midió*): `tiny` excluido en Sprint 2 por bboxes degeneradas;
   `large` **roto** (mAP 0,017 en S1, con el sanity-check de bboxes que estaba
   pre-planificado "por si la familia reincide"); **`base` medido y mediocre** (mAP 0,360,
   recall CR-01 0,029, `bare_head` 0,00 — "sin ventaja en nada", hallazgo 5 del doc 64).
   Números en la tabla de descartes de §2.

> **Salvedad de lectura.** `vest` no tiene AP en `shel5k` y `bare_head` no lo tiene en
> `chv`: ninguna de las dos fuentes anota esa clase. Las celdas `—` son ausencia de
> GT, no rendimiento nulo.

## 3. Nivel A — estado por persona

Vive en **`results/bench_nivel_a/index.md`** (campaña D1, E-DIR vs E-IND). Resumen del
veredicto: el gate pre-registrado de `nucleo/04` §8 **no se dispara** (CR-01 ratio
0,34–0,46 sí cumple, CR-02 0,87 no, y el gate exige ambas) ⇒ E-DIR pasó a Fase 2, donde
el veto de precisión de Nivel B la descartó como núcleo (D1, doc 85).

**CR-02 a Nivel A no está cerrado**: se mide en un solo estrato (`bench_obra`, **n=82
violadores en la mitad B de test** — el estrato completo trae 142, pero la mitad A se
consume en calibración) y con IC solapados. Declarado, no disimulado.

## 4. Extensibilidad — el costo de una clase nueva (A1, doc 94)

El argumento que `nucleo/09` llama *"el más cuantificable"* y que exige medir, medido
sobre material con clases que la plataforma **jamás configuró**:

| Costo de agregar clases nuevas | Medido |
|---|---|
| Entrenamientos | **0** |
| Artefacto de configuración | **1 archivo, 48 líneas** (`prompts/clase_nueva_v1.yaml`, 5 clases) |
| Tiempo de pared del piloto completo | **9 minutos** |
| GT nuevo anotado | **0** (se reutilizó GT que `canonical_v2` nunca usó) |

| Medición | Valor | n |
|---|---|---|
| **`machinery` AP@0.5, zero-shot, jamás configurada** | **0,662** | 99 cajas GT |
| `person` vs `Worker` en MOCS (ancla cross-dataset) | 0,610 | 507 cajas GT |
| `excavator` con det ≥0,5 en MOCS | 62/151 imgs | sin GT (visual) |

**`machinery` zero-shot (0,662) supera el mAP50 agregado del campeón con las clases
configuradas** — tanto el rango sobre el mismo núcleo curado (0,447–0,503, doc 64,
que es la comparación que hace la fuente, doc 94) como el agregado de `bench_v3`
(0,551).

> **F-94.1, el hallazgo honesto que acompaña al número:** la palabra tiene que alinear
> con la taxonomía del despliegue. `vehicle` junto a `machinery` en el mismo caption da
> **0 detecciones** (inanición por solapamiento semántico, caso extremo de F-88.1);
> aislada da 118 cajas pero AP 0,026 porque **el 67% cae sobre lo que ese GT llama
> `machinery`** — no es que no vea, es que la palabra significa otra cosa en esa
> taxonomía. Versión más fuerte de A1: agregar la clase cuesta minutos **y validar la
> palabra también** — el bench lo expone en ~3 min, mientras que con un detector
> cerrado ese error se descubre después de anotar y entrenar.

## 5. Qué NO cubre este material

- **Nada temporal.** Estas métricas son espaciales por imagen; el aporte de la
  plataforma (histéresis, identidad, política de alerta) solo se mide sobre video —
  `results/clip_bench/`.
- **CR-02 a Nivel A en un solo estrato**, con IC solapados (§3).
- **Licencia de `chv` parcial**: cita obligatoria, imágenes no redistribuibles. Es el
  20,5% del bench.
- **`bench_obra` con n<30 por condición** en varios cortes: los contrastes de ese
  estrato son direccionales, no cuantitativos.

## 6. Dónde está cada número

| Qué | Dónde |
|---|---|
| Banco, composición y salvedades | `e-ovrt_datasets/datasets/registry/bench_v3.md` |
| Benchmark de modelos (crudo) | `docs/operacion/datos/31-benchmark-modelos-host-local.*` |
| Selección S1/S2 + confirmación B5 | `docs/operacion/64` (+ doc 61 para latencia/resolución) |
| Ampliación del bench y por-estrato | `docs/operacion/66` |
| Auditoría del BENCH original | `docs/operacion/63` |
| Nivel A (estado por persona) | `results/bench_nivel_a/` + `docs/operacion/83`, `84` |
| Piloto de clase nueva | `docs/operacion/94` + `datos/94-piloto-clase-nueva/` |
