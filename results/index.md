# Resultados del proyecto — punto de entrada

Todo lo medido, organizado por **material** (imágenes / video / tiempo real). Es el
insumo directo del capítulo de resultados del informe: cada tabla de acá tiene su
artefacto en disco y su doc de procedencia.

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
| **[`clip_bench/`](clip_bench/index.md)** | Alertas contra GT temporal humano: 34 clips, 35 episodios. **6 campañas de combinación + 6 de densidad** | plataforma (Nivel B) |
| **[`realtime/`](realtime/index.md)** | Camino en vivo: integridad del bus, latencia operativa, techo de fps y su causa, y calidad bajo restricción de tiempo real | operación (EBE) |

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
- **FAR/hora no es una métrica de este trabajo** (D-90.1): ninguna cota alcanzable
  sostiene una afirmación. La evidencia de falsas alarmas es el **control de
  negativos**.
- **Las métricas que no aplican usan los estados del ADR-006/013**
  (`not_applicable:<causa>`), nunca frases vagas.

## Limitaciones declaradas

**Lista canónica cerrada el 2026-08-05 (L1–L8).** Antes había cinco etiquetadas y tres
sueltas sin etiqueta; ahora las ocho tienen código, porque se citan cruzado entre
documentos y en el informe.

| | Limitación |
|---|---|
| **L1** | **FAR/hora no reportable** (D-90.1): harían falta 3 h de cumplimiento anotado y el banco llega a 0,27 h de tiempo negativo total (0,1027 h de soak). Se reemplaza por el **control de negativos**, que discrimina (T1/T2/G1: 0 FP de 4; D1/H1/B1: 2–3). ✎ **2026-08-09 — se precisa, NO se deroga** (doc `operacion/111` §6.3): con el clip soak `v06_c01` (0,1027 h) el FAR/hora **pasó a ser computable y se reporta**: **29,2** (escena) y **1.850,8** (sujeto) — sobre **3 y 190 FP** en 6:09,6 de un único clip. Lo que no cambia es la limitación: 0,1027 h siguen a dos órdenes de magnitud de las 3,0 h de la regla de 3, así que el valor **no sostiene ninguna cota** ("≤1 FA/hora") — sí refuta la operabilidad. **Al citar: "3 FP en 6:09,6 del único clip soak", con la tasa horaria como derivada** (AF-11 sin cambios) |
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
enlaces markdown relativos resuelvan, (b) los **8 F1 del índice de clips** (T1, G1,
R1–R6) coincidan con el `metrics.json` en disco, (c) los 3 deltas del bootstrap donde
se afirma exclusión del cero coincidan con su artefacto, y (d) todo doc referenciado
exista. **Última corrida: todo verde.** Alcance declarado (no sobreestimar): **no
cubre** D1/H1/T2/B1 ni las cifras de `bench_imagenes`/`bench_nivel_a`/`realtime`
(verificadas a mano — hueco registrado en `docs/informe/99` §2.2); si se agrega una
campaña al índice, extender el script. Correrlo antes de volcar cifras al informe — la auditoría del informe
(`docs/informe/95-auditoria-y-plan-de-cierre.md` §2.1, serie distinta de
`operacion/95`) ya encontró una vez que *"el número estrella del TFG no tenía
respaldo en el repo"*.

## Procedencia

Cada campaña trae `campaign.yaml` con la combinación declarada y los sha256 del prompt
set congelado y del manifest del banco; `metrics.json` con la **misma forma** para todas
(`clip_campaign_metrics.v1`), para que comparar sea leer dos archivos y no rehacer
aritmética; `evals/` por unidad; y `provenance.json` apuntando a las corridas del
media-plane, que son la fuente de verdad de las detecciones (DA-03) y **no se copian**.
