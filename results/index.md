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
   gana a los prompts directos de ausencia (E-DIR) por el criterio pre-registrado, en
   los dos niveles; a Nivel B el **veto de precisión (0,146 < 0,5)** la descarta como
   núcleo. Lo que manda es la formulación, no el mecanismo (F-88.3). →
   `bench_nivel_a/` + `clip_bench/`
3. **Qué agrega la plataforma sobre la detección cruda** — la histéresis rescata
   percepción intermitente (CR-02 llega a recall 1,000 con SDR 0,281), pero es palanca
   de doble filo; y **la capa que más agrega es la identidad**: F1 0,789 → **0,930**
   con las detecciones bit a bit idénticas. El margen no estaba en el modelo. →
   `clip_bench/`
4. **Qué sobrevive al tiempo real** — la ganancia de la identidad **excluye el cero en
   las cuatro densidades medidas**, incluida la que el camino live entrega hoy
   (4,29 fps). Es la única palanca del banco significativa bajo esa restricción. →
   `realtime/` + `clip_bench/` § densidad

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

`L1` FAR (determinación D-90.1) · `L2` sin doble anotación, sin kappa (decisión) ·
`L3` seis bordes adjudicados · **`L4` un solo bloque guionado, sin obra real en
video** (la más citable; la levanta el lote de internet cuando tenga GT) · `L5`
escenarios desbalanceados · CR-02 a Nivel A en un solo estrato con IC solapados · el
`track_id` de G1 es post-hoc/decorador (verificado en vivo, pero el tracker no está
medido en obra real) · licencia de `chv` parcial (20,5% del bench de imágenes).

## Verificación de estos índices

`docs/operacion/datos/96-verificar-indices.py` chequea mecánicamente que (a) todos los
enlaces relativos resuelvan, (b) cada cifra citada coincida con el `metrics.json` en
disco, (c) los deltas del bootstrap coincidan con su artefacto y sus IC excluyan el
cero donde se afirma, y (d) todo doc referenciado exista. **Última corrida: todo
verde.** Correrlo antes de volcar cifras al informe — la auditoría del informe
(`docs/informe/95-auditoria-y-plan-de-cierre.md` §2.1, serie distinta de
`operacion/95`) ya encontró una vez que *"el número estrella del TFG no tenía
respaldo en el repo"*.

## Procedencia

Cada campaña trae `campaign.yaml` con la combinación declarada y los sha256 del prompt
set congelado y del manifest del banco; `metrics.json` con la **misma forma** para todas
(`clip_campaign_metrics.v1`), para que comparar sea leer dos archivos y no rehacer
aritmética; `evals/` por unidad; y `provenance.json` apuntando a las corridas del
media-plane, que son la fuente de verdad de las detecciones (DA-03) y **no se copian**.
