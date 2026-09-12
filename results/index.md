# Resultados del proyecto — punto de entrada

Todo lo medido, organizado por **material** (imágenes / video / tiempo real). Es el
insumo directo del capítulo de resultados del informe: cada tabla de acá tiene su
artefacto en disco y su doc de procedencia.

> **Estado: 2026-08-14.** El tramo experimental está **completo** — 17 campañas con
> artefacto (16 de video y la campaña de distribución), más el bench de imágenes.
> La última corrección de fondo fue la **revisión ciega del GT del estrato B**
> (doc `operacion/113` §B), ya propagada a los cuatro índices y a las limitaciones
> **L1 / L4 / L6**. Verificación mecánica al día: `96-verificar-indices.py` (26 cifras,
> cobertura 17/17) y `109-verificar-organizacion.py`, ambos verdes.
> **Lectura de una sola pasada:** `docs/sintesis/resultados-y-conclusiones.md`.

> **Marco de lectura, común a todo (doc 81 §1).** Cada número es el rendimiento medido
> de **una combinación concreta**, no una nota de aprobación. La pregunta del trabajo
> no es *"¿OVD detecta bien?"* sino *¿qué rendimiento se obtiene HOY en construcción
> civil con detección open-vocabulary **sin entrenar**, expresando las condiciones de
> riesgo en lenguaje, y qué aporta la plataforma alrededor del modelo?* **El contraste
> entre filas ES el experimento.** Un recall de 0,40 en multitud no es un fallo del
> proyecto: es el dato.

## Los cuatro índices

| Índice | Qué mide | Nivel |
|---|---|---|
| **[`bench_imagenes/`](bench_imagenes/index.md)** | Selección de modelos, AP por clase y estrato sobre `bench_v3` (6.477 imgs, 3 fuentes), y el costo de agregar una clase nueva | percepción espacial |
| **[`bench_nivel_a/`](bench_nivel_a/index.md)** | Estado "sin EPP" por persona: el nivel donde se decide entre estrategias de prompts (E-DIR vs E-IND) | percepción, por sujeto |
| **[`clip_bench/`](clip_bench/index.md)** | Alertas contra GT temporal humano. Banco vigente **47 clips** (34 del rodaje + 13 del estrato B), 32 pos / 15 neg, **37 episodios**. **14 campañas: 6 de combinación + 6 de densidad + 2 de estrato B** | plataforma (Nivel B) |
| **[`realtime/`](realtime/index.md)** | Camino en vivo: integridad del bus, latencia operativa, techo de fps y su causa, y calidad bajo restricción de tiempo real | operación (EBE) |

La campaña específica de distribución bajo [`realtime/t_alert_notification/`](realtime/t_alert_notification/README.md)
cerró el tramo `bus de alertas -> PUBACK MQTT QoS 1`: **p95 64,534 ms (n=460)**. Esta cifra no
representa sensor -> notificación y se mantiene separada de las latencias de percepción y control.
Para operación continua se informa además el régimen sostenido: entregas 2.ª+ por corrida,
**p95 102,025 ms (n=104)**; las primeras entregas dan **49,869 ms (n=356)**.

### La cadena temporal completa se cita POR TRAMOS (✎ 2026-08-15)

Con la distribución medida, la plataforma tiene **toda la cadena instrumentada** — pero cada
tramo tiene su propio origen de reloj, su propio dueño y su propia cifra, y **no se suman
percentiles entre tramos** (los p95 no son aditivos). La formulación correcta para el informe:

| Tramo | Qué mide | Cifra citable | Fuente |
|---|---|---|---|
| `capture_to_host` | fotón → dequeue en el host (F-101.8: el G2A arranca en el dequeue, no en el fotón) | **202–217 ms** en las 6 corridas del rodaje; hasta ~1,6 s degradado | [`realtime/`](realtime/index.md) §2 |
| **G2A** | captura (dequeue) → alerta, por frame | por contexto: 31,8 ms p95 single-host video · **630–890 ms** GDINO live · 225–249 ms YOLOE live | [`realtime/`](realtime/index.md) §2 |
| **`t_alert-system`** | inicio anotado del episodio (GT) → alerta. **Otra referencia temporal**: está dominada por la persistencia del patrón (`confirm_after_ms` 4.000/7.000), no por el transporte — no se encadena aritméticamente con los tramos físicos | por campaña/condición, p. ej. T1 5.327 ms · G1 5.236 ms | [`clip_bench/`](clip_bench/index.md), equivalencia de nombres allí |
| **`t_alert-notification`** | bus de alertas → PUBACK MQTT QoS 1 | **p95 64,534 ms (n=460)**; sostenido 102,025 ms (n=104) | [`realtime/t_alert_notification/`](realtime/t_alert_notification/README.md) |

Lectura honesta de conjunto: **la distribución no es el cuello** — su p95 (≈65 ms) es un
orden de magnitud menor que el G2A live del modelo que detecta (630–890 ms) y dos órdenes
menor que la persistencia deliberada del patrón (4–7 s). La cadena vidrio→notificación de
un evento se describe cualitativamente con los cuatro tramos citados por separado.

## Ejes de lectura (✎ 2026-09-10)

Esta página organiza por **material**. Para leer la misma evidencia por otros ejes
—los que hacen falta para explicar el trabajo— está [`ejes/`](ejes/00-indice.md),
que **no agrega ni una medición**: son vistas sobre estas mismas cifras.

| Eje | Documento |
|---|---|
| Escenario de despliegue: qué se midió offline y qué en vivo | [`ejes/01-dbe-vs-ebe.md`](ejes/01-dbe-vs-ebe.md) |
| El día de rodaje: qué salió de él y qué no lo es aunque lo parezca | [`ejes/02-rodaje.md`](ejes/02-rodaje.md) |
| Modelo: zero-shot y la jornada de fine-tuning | [`ejes/03-baseline-vs-finetuning.md`](ejes/03-baseline-vs-finetuning.md) |

**Todas las cifras de estos cuatro índices son zero-shot.** El fine-tuning es una
línea aparte, cerrada, que vive en `finetuning/` y **no aportó un modelo de
servicio**; su valor declarado es una curva de tres puntos.

## Runs de evidencia

El [`inventario canónico generado`](evidence-runs.md) enumera, sin globs ni IDs abreviados,
todos los runs citados por estos resultados DBE y EBE. La copia versionable correspondiente vive
en [`evidence-runs/`](evidence-runs/README.md): conserva únicamente artefactos textuales curados,
comprime los JSONL y excluye imágenes, video, previews, presets de cámara y secretos. Un run que
no figure en el inventario no pasa a ser evidencia canónica por el solo hecho de existir.

Desde la raíz de este repositorio, `python3 tools/evidence_runs.py sync` regenera ambos artefactos;
`python3 tools/evidence_runs.py --check` comprueba el catálogo contra los originales y
`python3 tools/evidence_runs.py --check --archive-only` valida la copia sin depender de ellos.

## El recorrido del argumento, en cuatro números

1. **Qué ve el detector sin entrenar** — `gdino-tiny-560`, campeón robusto a la fuente:
   **mAP50 0,551** sobre 6.477 imágenes de 3 fuentes independientes. La asimetría es
   estructural: `person`/`helmet` sólidas, `vest` débil, `bare_head` fuerte solo en el
   especialista. → `bench_imagenes/`
2. **Cómo conviene expresar la condición** — evidencia positiva + inferencia (E-IND)
   gana a los prompts directos de ausencia (E-DIR) en los dos niveles: a Nivel A por
   F1 con IC no solapados en `shel5k` (el gate pre-registrado **no se disparó** y
   E-DIR pasó a Fase 2), y a Nivel B decide el criterio pre-registrado — el **veto de
   precisión (0,146 < 0,5)** la descarta como núcleo. Lo que manda es la formulación,
   no el mecanismo (F-88.3). → `bench_nivel_a/` + `clip_bench/`
3. **Qué agrega la plataforma sobre la detección cruda** — la histéresis rescata
   percepción intermitente (CR-02 llega a recall 1,000 con SDR 0,281), pero es palanca
   de doble filo; y **la capa que más agrega es la identidad**: F1 0,789 → **0,930**
   con las detecciones bit a bit idénticas. El margen no estaba en el modelo. →
   `clip_bench/`
4. **Qué sobrevive al tiempo real** — la ganancia de la identidad **excluye el cero en
   las cuatro densidades medidas** (bajo decimado regular; conserva la dirección bajo
   el descarte irregular medido del live, 6/6 — doc 101), incluida el ancla del techo
   live de hoy (stride 7 ≈ 4,29 fps nominal; el live entrega 1,16–4,42 fps). Es la
   única palanca del banco significativa bajo esa restricción. → `realtime/` +
   `clip_bench/` § densidad

## Reglas de lectura que NO son negociables

Salieron de artefactos de medición cazados **antes** de reportar (familia F-EV1/2/3,
doc 81 §3). Ignorarlas produce conclusiones falsas con números correctos:

- **Reportar siempre por estrato y por escenario, nunca solo el agregado** (L5). El
  agregado de `bench_v3` está dominado por `shel5k` (77%); el del clip bench, por
  P1/P2. Y en el eje de densidad, un agregado plano escondía una redistribución
  completa (F-96.1).
- **Los clips negativos no entran a precision/recall/F1** — su métrica son los FP
  (F-EV1). Promediar su F1 hunde el agregado contando aciertos como catástrofes.
- **`re_alerts` no son falsos positivos** (ADR-011).
- **El SDR no se compara entre cadencias** (F-96.6): sube al bajar la densidad y es
  ~100% artefacto del instrumento, verificado por decimación de las mismas
  detecciones.
- **El `t_alert` agregado no se compara entre densidades sin control de
  supervivencia** (F-96.5): los episodios lentos mueren como `missed` y su salida baja
  el promedio justo cuando el costo sube.
- **FAR/hora se reporta, pero no sostiene ninguna cota** (D-90.1 **precisada**, no
  derogada — ver L1). Desde que existe el clip soak (`v06_c01`, 0,1027 h) la métrica es
  computable y se publica (**29,2** escena / **1.850,8** sujeto), pero el denominador
  está a dos órdenes de magnitud de las 3 h que exige la regla de 3: **citar siempre
  como "3 y 190 FP en 6:09,6 del único clip soak", con la tasa horaria como derivada**,
  nunca como "≤N FA/hora". La evidencia principal de falsas alarmas sigue siendo el
  **control de negativos**.
- **Las métricas que no aplican usan los estados del ADR-006/013**
  (`not_applicable:<causa>`), nunca frases vagas.

## Limitaciones declaradas

**Lista canónica cerrada el 2026-08-05 (L1–L8).** Antes había cinco etiquetadas y tres
sueltas sin etiqueta; ahora las ocho tienen código, porque se citan cruzado entre
documentos y en el informe.

| | Limitación |
|---|---|
| **L1** | **FAR/hora: se reporta como conteo crudo y no sostiene cota** (enmienda a D-90.1; formulación original: “no reportable”). ✎ **2026-08-09 — se precisa, NO se deroga** (doc `operacion/111` §6.3): con el clip soak `v06_c01` (0,1027 h) el FAR/hora **pasó a ser computable y se publica** — **29,2** (escena) y **1.850,8** (sujeto), derivados de **3 y 190 FP en 6:09,6**. Lo que no cambia es la limitación: harían falta **3 h de cumplimiento anotado** y el banco llega a **0,27 h de tiempo negativo total** (0,1027 h de soak), dos órdenes de magnitud por debajo de lo que exige la regla de 3, así que el valor **no sostiene ninguna cota** (“≤1 FA/hora”) — **sí refuta la operabilidad**. La evidencia principal sigue siendo el **control de negativos**, que discrimina (**T1/T2/G1: 0 FP de 4; D1/H1/B1: 2–3**). **Al citar: “3 FP en 6:09,6 del único clip soak”, con la tasa horaria como derivada** (AF-11 sin cambios). |
| **L2** | Sin doble anotación ni kappa — **decisión declarada, no omisión** |
| **L3** | **Bordes del GT adjudicados en 6 clips** por oclusión (no cambio de estado), con firma en `clip.yaml` |
| **L4** | **Un solo bloque guionado, sin obra real en video.** ✎ **2026-08-09 — PRECISADA con el cierre del estrato B (DECISIÓN FIRMADA, D-113.1: se precisa esta etiqueta, NO se crea `L9`; el set L1–L8 de `informe/99` §6 sigue cerrado).** El lote de internet aportó obra real no guionada, 13 clips (banco **47**, docs `operacion/109`/`111`/`112`), y la limitación queda así: **hay medición en obra real, pero acotada** — tras la **revisión ciega del GT** (doc 113 §B, 2026-08-09: **5 de las 7 declaraciones de episodio del lote resultaron errores de anotación**, todas sobre-declarando donde el estado no era observable — la calidad del GT es un resultado en sí y la re-revisión a ciegas lo auditó), quedan **2 episodios evaluables**: Nivel B `scene` F1 **0,333** / `subject` **0,190** (n insuficiente para CUALQUIER ranking entre granularidades — F-111.1 enmendado; lo robusto es la asimetría de FP: 26 vs 323 en los 11 negativos, **12×**); Nivel A sobre 17 clips de video: CR-01 **0,031** / CR-02 **0,018** contra 0,408/0,479 en imágenes (derrumbe de **precision**; el recall sube a 0,47/0,32 al salir del denominador los no-observables). **Contenido nuevo de la limitación: la frontera de juzgabilidad**, con tres ejes medidos (escala × iluminación × oclusión) y una propiedad negativa verificada — **el `unknown` del anotador no la predice** (F-105.2/3/4): no hay un índice escalar barato para saber de antemano si el material es juzgable. **Citar como:** *"L4 se precisó: existe medición en obra real no guionada, y esa medición caracteriza por mecanismo dónde el sistema deja de ser evaluable — no la valida sobre obra real"* (doc `operacion/112` §6) |
| **L5** | **Escenarios desbalanceados** ⇒ obliga a reportar siempre por escenario y por estrato |
| **L6** | **El tracker no está medido en obra real con multitud** — G1 se verificó en vivo con pocos sujetos; el `track_id` es post-hoc/decorador. ✎ **2026-08-09 — la parte descriptiva quedó levantada** (doc `operacion/103`, F-103.2): `v06_c01`, con **127 personas en el GT**, sí puso al tracker en multitud real y **el resultado es un dato, no un hueco**: **182 identidades con FP contra 127 personas reales** — fragmenta identidades, y esa fragmentación es el mecanismo que explica la precision **0,111** de `subject` en el estrato B. Sigue en pie el resto: no hay métricas MOT (E-10, excluida por ADR-015) y el `track_id` sigue siendo post-hoc |
| **L7** | **Licencia de `chv` parcial** (20,5% del bench de imágenes): uso permitido con cita, sin redistribución |
| **L8** | **CR-02 a Nivel A no cerrada** — un solo estrato, IC solapados |

> **Ojo al citar `L1`:** la **Fase L** del plan maestro (doc 62) usa `L0`/`L1` para sus
> hitos (`L0` = ensayo pre-rodaje, `L1` = el rodaje). Son cosas distintas: escribir
> **"limitación L1"** cuando se habla de esta lista, y "hito L1" / "el rodaje" cuando se
> habla de la fase.

## Verificación de estos índices

`docs/operacion/datos/96-verificar-indices.py` chequea mecánicamente que (a) los
enlaces markdown relativos resuelvan, (b) **26 cifras citadas** coincidan con el
`metrics.json` en disco, (c) **toda campaña con artefacto tenga al menos una cifra
verificada**, (d) los 3 deltas del bootstrap donde se afirma exclusión del cero
coincidan con su artefacto, y (e) todo doc referenciado exista. **Última corrida:
todo verde.**

✎ **2026-08-14 — alcance ampliado.** Antes cubría 8 F1 (T1, G1, R1–R6) y luego las
16 campañas de video. Hoy cubre **las 17 campañas con artefacto**: las 14 de
`clip_bench`, las 2 de `bench_nivel_a` y `realtime/t_alert_notification`, incluida
su cifra citable y el desglose first-delivery/steady-state. El chequeo **(c) es el
que impide que el script vuelva a envejecer en silencio**: si aparece una campaña
nueva sin fila en `CIFRAS`, falla en vez de reportar "todo verde" sobre un
subconjunto. El chequeo **(b) además cuenta ocurrencias con límites numéricos**: una
cifra puede declarar cuántas veces la cita su índice (p. ej. `64,534` y `n = 460` salen
**2 veces** en `realtime/index.md`), de modo que romper **una sola** de las dos ya falla,
y un entero desnudo como `104` no se da por citado por aparecer dentro de `1.104`.
Alcance que sigue **sin cubrir**: las cifras de `bench_imagenes/`, que
no tienen `metrics.json` en este repo y se verifican contra el doc 64.

Correrlo antes de volcar cifras al informe — la auditoría del informe
(`docs/informe/ajustes/gobierno/95-auditoria-y-plan-de-cierre.md` §2.1, serie distinta de
`operacion/95`) ya encontró una vez que *"el número estrella del TFG no tenía
respaldo en el repo"*.

## Licencias de los pesos de modelo (✎ 2026-08-10)

Los **11 catálogos** de `e-ovrt_media-plane/configs/models/**/*.yaml` declaran `license:` y
`source:` por variante, y el registro con la evidencia de verificación vive en
**`e-ovrt_datasets/datasets/registry/license_registry.md` §PESOS DE MODELO**:
**Grounding DINO** y **MM-Grounding-DINO** son **Apache-2.0** (verificado contra el
frontmatter de los model cards descargados), **YOLOE** es **AGPL-3.0** (verificado contra la
cadena embebida en el propio `.pt` y contra el paquete `ultralytics`). Al citar los modelos
en el informe hay que decir la licencia de las tres familias, y para YOLOE que se usó como
**contraste medido y descartado con causa**. No se redistribuyen pesos: `models/**` está
gitignoreado en el media-plane.

## Procedencia

Cada campaña trae `campaign.yaml` con la combinación declarada y los sha256 del prompt
set congelado y del manifest del banco; `metrics.json`; y **procedencia por corrida**
apuntando a los runs del media-plane, que son la fuente de verdad de las detecciones
(DA-03). Los originales permanecen fuera de este repo; el archivo común
[`evidence-runs/`](evidence-runs/README.md) conserva la copia textual curada de los runs citados,
sin imágenes ni video procesados.

Alcance exacto, para no prometer de más (✎ 2026-08-09):

- **`clip_bench` (14 campañas)** — el caso completo: `metrics.json` con la **misma forma**
  para todas (`clip_campaign_metrics.v1`), `evals/` por clip, y `provenance.json`.
- **`bench_nivel_a` (2 campañas)** — otro esquema de métricas (es otro nivel) y
  procedencia con nombre propio en D1 (`provenance_runs.json`, indexado por corrida en
  vez de por clip). **Sin `evals/` por diseño**: a Nivel A no interviene el motor
  temporal, así que no existe la noción de "eval por clip".
- **`bench_imagenes`** — consolida mediciones cuyos artefactos viven en los repos
  hermanos y sus cifras se contrastan con el doc 64.
- **`realtime/t_alert_notification`** — tiene campaña propia, `metrics.json` y
  cobertura obligatoria en `96-verificar-indices.py`; los demás resultados live
  conservan la procedencia declarada en sus documentos operativos.

**Las 17 campañas con artefacto tienen hoy procedencia por corrida completa.** En las
**16 de video** eso no era cierto hasta el 08-09: I1/I2 declaraban 4 corridas para 13
clips y NA1 no tenía ninguna; hoy es regenerable y verificable con
`docs/operacion/datos/113-regenerar-provenance-estrato-b.py --check`. La 17.ª,
`realtime/t_alert_notification`, la declara en su propio `provenance.json` (intento
aceptado, fases y hashes) más `integrated-runs.json`, que enumera `media_run_id` y
`control_run_id` por corrida integrada.
