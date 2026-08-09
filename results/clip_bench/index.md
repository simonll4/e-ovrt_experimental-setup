# Campañas sobre el banco de clips — tabla comparativa

Banco: **34 clips** del rodaje (Bloque A, 2026-07-25), 35 episodios (CR-01 28 /
CR-02 7), P1–P9, `manifest.yaml` sha256 `cef5082e…` — **ese sha es el freeze de 34
que usaron todas las campañas de esta tabla**, recuperable en el commit `f7a27fe6` de
`e-ovrt_datasets`. El banco **vigente** tiene **38 clips** (34 del rodaje + 4 del
estrato B, manifest `4437eb6d…`): las filas del rodaje nunca cambiaron, el manifest
solo creció. El estrato B tiene su propia sección al final. **Denominador citable: 34
episodios evaluables sobre 35** — 1 censurado con causa
(`clip_too_short_for_t_alert_window`, un CR-01 de P1; enmienda A2): todos los
recall de esta página son sobre 34 (T1 28/34 = 0,824; G1 33/34 = 0,971 — quien
recomponga 28/35 no reproduce la tabla). Limitaciones comunes a todas las
campañas: `e-ovrt_datasets/datasets/registry/clip_bench.md` (L1–L5).

**Cómo leer esta tabla.** Cada fila es el rendimiento medido de UNA combinación,
no una nota. La pregunta de la tesis es *qué se consigue hoy con OVD sin
entrenar en construcción civil* — el contraste entre filas **es** el
experimento. Recall/precision son **micro** (por episodio) sobre episodios
evaluables; los clips negativos quedan fuera y se reportan como control de FP.

| # | `campaign_id` | Modelo | Prompts | Gran. | Recall | Prec. | F1 | t_alert | TTFD | SDR | FP neg. | Hallazgo |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| T1 | `t1_gdinotiny560_v2short_scene` | gdino-tiny-560 | `v2_short` | scene | **0,824** | **0,757** | **0,789** | 5.327 ms | 168 ms | 0,698 | **0/4** | Línea de base. P1/P2/P4/P6 recall 1,000 con 1 FP; P7/P8/P9 concentran 6 missed y 8/9 FP |
| T2 | `t2_gdinobase560_v2short_scene` | **gdino-base-560** | `v2_short` | scene | 0,735 | 0,676 | 0,704 | **4.899 ms** | 221 ms | **0,819** | **0/4** | Contraste de modelo. **F-81.2b REFUTADA**: el especialista no recupera P7 (0,400=) ni P8 (0,500=) y empeora P9 (0,600→0,400). **Pero CR-02 SDR 0,281→0,920** y su t_alert −2,2 s |
| D1 | `d1_gdinotiny560_edirpair_scene` | gdino-tiny-560 | **`edir_v1` (par)** | scene | **0,176** | **0,146** | **0,160** | 6.611 ms | 847 ms | 0,210 | **2/4** | **Fase 2 del eje: E-DIR de punta a punta.** Precision 0,146 < 0,5 → **veto del §8: E-DIR descartada como núcleo, E-IND confirmada.** Ratio F1 0,20 (vs 0,34–0,46 en Nivel A: la brecha se AGRANDA con la plataforma). CR-02 recall **0,000**. Único escenario donde gana: **P9 0,800 vs 0,600** |
| H1 | `h1_gdinotiny560_hybor_scene` | gdino-tiny-560 | **fusión dual-run T1+D1** | scene | 0,353 | 0,255 | 0,296 | 6.956 ms | **113 ms** | **0,738** | 2/4 | **E-HYB-or. Predicción pre-registrada REFUTADA**: el recall no sube, se derrumba (0,824→0,353). **F-87.2: la unión de evidencia NO es monótona en un motor temporal** — evidencia más temprana no agrega alertas, *corre* las que ya había fuera de su ventana. P1 pasa de 1,000/0 FP a **0,000/12 FP** con la percepción MEJORADA (SDR 0,738, TTFD 113 ms). **Sin GPU** |
| **G1** | `g1_gdinotiny560_v2short_subject` | gdino-tiny-560 | `v2_short` | **subject** | **0,971** | **0,892** | **0,930** | 5.236 ms | 168 ms | 0,698 | **0/4** | **La mejor combinación del banco.** Única variable vs T1: la granularidad — **SDR y TTFD idénticos** (las detecciones son bit a bit las de T1), así que los **+0,141 de F1 vienen enteros del motor**. **P7 de 0,400 a 1,000** (F-89.1 cierra F-81.2a); prematuras de pre-roll 5→1 (F-89.2). **Sin GPU**, 0,4 min. La identidad es capacidad de plataforma (`input.track_persons`, DBE+live): el camino config-driven reproduce esta campaña **exacto** |
| B1 | `b1_gdinobase560_barehead_scene` | gdino-base-560 | **`bench_v2` (4cl), `bare_head` directo** | scene | 0,382 | 0,371 | 0,377 | **3.919 ms** | **41 ms** | **0,940** | **3/4** | **F-88.2**: la vía que T2 no probó tampoco alcanza — 0,480 vs 0,582 de la ausencia espacial **sobre las mismas detecciones** (CR-01 puro). **F-88.1**: su control interno mide el **costo del caption** — una clase más cuesta **0,082 de F1** (T2 0,704 → 0,622). Mejor percepción del banco (SDR 0,940) y peores negativos |

## Detalle por escenario

| `campaign_id` | P1 | P2 | P3∅ | P4 | P5∅ | P6 | P7 | P8 | P9 |
|---|---|---|---|---|---|---|---|---|---|
| **G1** | 1,000 | 1,000 | 0 FP | 1,000 | 0 FP | 1,000 | **1,000** | **1,000** | **0,800** |
| T1 | 1,000 | 1,000 | 0 FP | 1,000 | 0 FP | 1,000 | **0,400** | **0,500** | **0,600** |
| T2 | 0,818 | 1,000 | 0 FP | 1,000 | 0 FP | 1,000 | **0,400** | **0,500** | **0,400** |
| D1 | 0,091 | 0,000 | 2 FP | 0,500 | 0 FP | 0,000 | 0,000 | 0,000 | **0,800** |
| H1 | **0,000** | 1,000 | 2 FP | 0,000 | 0 FP | 0,500 | 0,400 | 0,000 | 0,600 |
| B1 | 0,273 | 0,000 | 2 FP | 1,000 | 1 FP | 0,250 | 0,200 | 1,000 | 0,800 |

(∅ = escenario negativo: se reporta FP, no recall. Fila B1 agregada 2026-08-06 —
regla L5: ninguna campaña sin su desglose. Ojo con los `n` chicos: P2 = 5
episodios, P6 = 2 clips / 4 episodios, P8 = 1 clip.)

## Detalle por condición

| `campaign_id` | CR-01 SDR | CR-01 t_alert | CR-01 FP | CR-02 SDR | CR-02 t_alert | CR-02 FP |
|---|---|---|---|---|---|---|
| T1 | 0,805 | 4.314 ms | 8 | **0,281** | 8.572 ms | 1 |
| T2 | 0,804 | 4.364 ms | 11 | **0,920** | **6.417 ms** | 1 |
| D1 | 0,252 | 6.611 ms | **27** | **0,020** | — (recall 0) | **14** |
| H1 | 0,854 | 5.081 ms | 24 | 0,282 | 9.167 ms | 13 |
| G1 | 0,805 | 4.331 ms | **3** | **0,281** | 8.572 ms | 1 |
| B1 | 0,940 | 3.919 ms | 14 | 0,966 | 3.867 ms | 9 |

(CR-01 = 28 episodios / 25 clips; CR-02 = 7 episodios / 7 clips, en todas. Filas
H1/G1/B1 agregadas 2026-08-06 desde sus `metrics.json` — regla L5. **Dos
advertencias de lectura:** (1) los FP se imputan a las condiciones *presentes* en
el clip, con solapamiento — la suma por condición puede superar el total de la
campaña (D1: 27+14 = 41 vs 35 totales); (2) `by_condition` no trae recall — el
recall por condición vive en los docs de campaña: en T1 **CR-02 confirma 7/7 =
1,000 pese a SDR 0,281** (F-81.1, doc 81), la cifra que sostiene el argumento de
la histéresis.)

## Mecanismo de las alertas inesperadas (`datos/85-mecanismo-de-fallas.py`)

| Tipo | T1 | T2 | D1 | H1 | I1 † | I2 † |
|---|---|---|---|---|---|---|
| `prematura_pre_roll` | 5 | 6 | 14 | **20** | 2 | **117** |
| `cruzada_de_condicion` | 4 | 4 | 8 | **14** | 3 | 79 |
| `sin_episodio_activo` | 0 | 2 | **12** | 3 | 2 | 20 |
| `tardia` | 0 | 0 | 3 | 0 | 0 | 0 |
| adelanto mediano de prematuras | 0,5 s | 1,8 s | 2,5 s | **2,6 s** | 341,9 s | **221,2 s** |

† Columnas del estrato B agregadas 2026-08-06 — **NO comparar con las del rodaje sin
la nota F-107.4** (doc `operacion/107`): en clips largos la taxonomía satura — el
adelanto mediano de las "prematuras" de I2 es **221 s**, no medio segundo: la etiqueta
técnica aplica pero el mecanismo es *otra persona fabricando la misma condición
minutos antes del episodio*, la firma de la evidencia fabricada del doc 103.

## Hallazgos vigentes

- **F-81.1 — la histéresis del motor rescata una percepción intermitente.** CR-02
  llega a recall 1,000 con SDR 0,281 (0,160 en P2 puro): la evidencia de chaleco
  aparece en ~1 de cada 6 frames del episodio (F-G2.1 medido de punta a punta) y
  el patrón temporal la acumula igual, pagando tiempo (t_alert 8.572 vs 4.314 ms
  de CR-01). Argumento pro-plataforma medido — y a la vez el techo: con SDR ~0,16,
  exigir continuidad estricta rompería CR-02.
- **F-81.2 — dónde se rompe la combinación actual.** (a) Granularidad de escena
  vs GT por sujeto en multitud (P7): el GT exige que UN sujeto sostenga 4 s y el
  motor acumula "alguien sin casco"; es el costo de operar sin `track_id`, ahora
  medido → insumo directo del experimento G1 (doc 79). (b) Mis-detección de casco
  en el pre-roll (P7/P9): la alerta cae 0,7–2,4 s antes del episodio porque el
  modelo no ve el casco durante los ~3 s de cumplimiento inicial → candidato a
  prompts de Fase D o a `gdino-base-560` (especialista CR-01, doc 64).
- **F-81.3 — TTFD ~5 frames.** La latencia de la plataforma es la política de
  persistencia, no la percepción: `t_alert ≈ persistencia + TTFD + intermitencia`.
- **F-84.5 — F-81.2b refutada para la palanca "cambiar de modelo bajo `v2_short`".**
  El especialista no recupera el pre-roll: P7 0,400=, P8 0,500=, **P9 empeora**
  (0,600→0,400); mecanismo clasificado contra el GT (`datos/85-mecanismo-de-fallas.py`):
  las prematuras de pre-roll pasan de 5 a 6, pero **su adelanto mediano se triplica**
  (0,5 s → 1,8 s) — con tiny caían al filo del borde, con base caen adentro del tramo
  que el GT marca "cumple"; los FP cruzados de condición quedan idénticos en 4 (la
  granularidad no depende del modelo). **Alcance**: la "especialidad CR-01" del doc 64 se midió
  detectando **`bare_head`**, clase que `v2_short` no incluye — T2 nunca la ejercitó.
  La vía `bare_head`-como-evidencia-positiva (base: recall 0,599 vs 0,308 de tiny)
  sigue sin probar a Nivel B y requiere el evaluador `direct_evidence` — la misma
  pieza que la Fase 2 de E-DIR. Palancas restantes para P7–P9: `track_id`/G1 y
  evidencia directa.
- **F-84.6 — el modelo sí compra percepción de chaleco, y la plataforma cobra menos
  tiempo.** CR-02 pasa de SDR **0,281 → 0,920** (la evidencia intermitente de F-81.1,
  ~1 de cada 6 frames, se vuelve continua) y su `t_alert` baja **8.572 → 6.417 ms**.
  El recall de CR-02 ya era 1,000 en T1 gracias a la histéresis, así que la mejora no
  puede verse ahí: se ve en calidad de evidencia y en latencia. **Son dos palancas
  independientes** — la histéresis rescata la percepción pobre (F-81.1) y el modelo
  la elimina como problema. El precio es CR-01: recall global 0,824→0,735.

- **F-85.3 — la histéresis es una palanca de doble filo, medida en los dos sentidos.**
  F-81.1: el motor **rescata** percepción intermitente pero correcta (CR-02 con SDR
  0,16 llegaba a recall 1,000). D1: el motor **amplifica** percepción persistente pero
  equivocada — E-DIR dispara sobre gente que cumple, la evidencia errónea es sostenida
  y la persistencia la confirma: 35 FP contra 9, y **2 FP en negativos** (T1/T2 tenían
  0/4). La histéresis solo mide persistencia; no distingue "débil pero correcta" de
  "fuerte pero equivocada".
- **F-85.4 — el ranking de Nivel A no transfiere a Nivel B.** CR-02 era el punto
  **fuerte** de E-DIR en imágenes (ratio 0,87) y es donde **colapsa** en video (recall
  0,000, SDR 0,020); CR-01 al revés. Por eso el pre-registro exige las dos fases y
  decide en la segunda.
- **F-85.5 — P9 es la única victoria de E-DIR y está donde E-IND es más débil**
  (0,800 vs 0,600, con menos FP). Coherente con la complementariedad de Nivel A
  (18,5%): ubica a E-HYB en el pre-roll, no "en general".

- **F-87.2 — la unión de evidencia NO es monótona en un motor temporal.** En una
  clasificación por frame un OR solo puede agregar positivos. Acá no se clasifican
  frames: se **confirman episodios**, con ventana de persistencia y de matching.
  Evidencia más temprana no agrega una alerta — **corre la que ya existía**, y una
  alerta adelantada fuera de la ventana cuenta doble mal (missed + unexpected). Firma
  inequívoca: los 11 clips de P1 confirman en H1 a **~4,0 s exactos** = `confirm_after_ms`
  contado desde el frame 0, porque la evidencia directa está desde el primer frame; con
  E-IND sola confirmaban a `onset + 4,0 s` ≈ 7,6 s, dentro de la ventana. P1 pasa de
  1,000/0 FP a 0,000/12 FP **con la percepción mejorada** (SDR 0,698→0,738, TTFD
  168→113 ms). Es el tercer filo de F-85.3: la evidencia equivocada *temprana* no solo
  agrega falsas alarmas, **canibaliza las alertas correctas**.

- **F-88.1 — el caption tiene un costo medido, y responde una pregunta abierta del
  pre-registro.** T2 y el control interno de B1 comparten modelo, evaluador, pattern
  set, GT y timings; **difieren en una palabra del caption** (`bare head`) y eso cuesta
  **0,082 de F1** (0,704 → 0,622). El doc 12 §4.1 dejaba el pase único de vocabulario
  unión como "variante operativa condicionada si la interacción es despreciable":
  **no lo es**. La regla dual-run queda validada empíricamente y el atajo de un solo
  pase no es gratis.
- **F-88.3 — la etiqueta corta gana a la frase negada, y eso ordena el eje.** Sobre los
  23 clips de CR-01 puro: ausencia espacial con `helmet` **0,582–0,731**, `bare head`
  (evidencia directa pero **etiqueta corta**) **0,480**, frases negadas de E-DIR
  **0,231**. La ventaja de E-IND no es "inferir es mejor que detectar": es que su
  vocabulario está hecho de etiquetas cortas que el modelo entiende. `bare_head` cae en
  el medio exacto, y esa posición intermedia es la evidencia más limpia de que **lo que
  manda es cómo se expresa la condición, no si se infiere o se detecta**.

- **F-89.1 / F-89.2 — el margen que quedaba no estaba en el modelo ni en los prompts,
  estaba en la identidad del motor.** Cuatro palancas de percepción y formulación (D1
  0,160 / H1 0,296 / T2 0,704 / B1 0,377) no superaron a T1 (0,789); **la granularidad
  por sujeto sí: 0,930**, con **SDR y TTFD idénticos** a T1 porque las detecciones son
  bit a bit las mismas. P7 pasa de 0,400 a 1,000 (cierra F-81.2a) y las prematuras de
  pre-roll caen de 5 a 1 — lo que **refina F-81.2b**: bajo escena basta que CUALQUIER
  persona esté sin casco para que la escena entre en evidencia durante el pre-roll en
  que el sujeto objetivo sí cumple. No era que el modelo no viera el casco: **era que
  el motor miraba a otra persona**. Verificado que no es artefacto: en P7 ambas
  campañas emiten **las mismas 7 alertas**, pero G1 acierta 5 en vez de 2 y baja FP de
  5 a 1.

## Comparación restringida a CR-01 puro (23 clips, 25 episodios)

El agregado penalizaría a `bare_head` por episodios CR-02 que su pattern set no puede
detectar por diseño. Comparación justa:

| Campaña | recall | precision | F1 |
|---|---|---|---|
| **T1** (tiny, 3cl, E-IND) | **0,760** | **0,704** | **0,731** |
| T2 (base, 3cl, E-IND) | 0,640 | 0,593 | 0,615 |
| B1-eind (base, 4cl, E-IND) | 0,640 | 0,533 | 0,582 |
| B1 `bare_head` (base, 4cl, directo) | 0,480 | 0,480 | 0,480 |
| D1 (E-DIR frases) | 0,240 | 0,222 | 0,231 |
| H1 (hyb_or) | 0,200 | 0,185 | 0,192 |

## Veredicto del eje (nucleo/04 §8, criterios fijados antes de correr)

Las tres estrategias del pre-registro, corridas de punta a punta sobre el mismo banco,
GT, motor y timings:

| Estrategia | F1 de alertas | Veredicto |
|---|---|---|
| **E-IND** | **0,789** | **Núcleo** (ADR-001, confirmado por medición) |
| E-DIR | 0,160 | Descartada — **veto de precisión** del §8 (0,146 < 0,5) |
| E-HYB-or | 0,296 | No supera a la mejor individual (§8.3 exige ≥0,05 por encima) |

No hacen falta desempates: la brecha con E-IND es de 0,63 y 0,49 en F1. Las estrategias
no elegidas quedan documentadas con sus números (§8 criterio 4). **La brecha se agranda
al pasar por la plataforma**: E-DIR tiene ratio F1 0,20 a Nivel B contra 0,34–0,46 a
Nivel A. Y las tres fallas están **explicadas por mecanismo**, no solo cuantificadas:
ceguera al atributo (Nivel A), su amplificación por la histéresis (D1) y la no-monotonía
de la unión (H1).

`hyb_and` **no se implementó, con causa y predicción registrada**. La causa vigente es
**D-90.4** (2026-08-05, doc 90 §hyb_and): **no es medible contra este banco sin romper
la comparabilidad de las 6 campañas** — el evaluador deriva la ventana de la
persistencia nominal del GT, y `-and` la altera. El planteo original (doc 87 §5: su
único efecto declarado es *acelerar* la confirmación, y F-87.2 muestra que adelantar
es justamente el mecanismo de falla) queda archivado como predicción conservada.
Salida legítima del pre-registro (§6.2: "lo no corrido se reporta *no ejecutada con
causa*").

## Eje de densidad de evidencia — el costo del tiempo real (R1–R6, doc 96)

**Estas filas NO van en la tabla de arriba a propósito.** Aquélla compara combinaciones
a `stride: 1`; ésta varía la *cadencia*, y el SDR **no es comparable entre cadencias**
(F-96.6: la subida del SDR al bajar la densidad es ~100% artefacto del instrumento —
`_sdr_for_episode` funde huecos ≤ paso nominal, y el paso nominal crece con el stride).
Mezclarlas invitaría justo a esa lectura equivocada.

Las seis campañas del banco corrieron todas a 30 fps de evidencia; el camino live
entrega 1,16–4,42 fps (docs 71/73). Estas seis miden qué sobrevive a esa restricción.
Variable única contra T1/G1: el `stride`.

| # | `campaign_id` | Gran. | fps ev. | Ancla del live | Recall | Prec. | F1 | t_alert | TTFD | FP neg. |
|---|---|---|---|---|---|---|---|---|---|---|
| T1 | `t1_…_scene` | escena | 30,00 | (referencia DBE) | 0,824 | 0,757 | **0,789** | 5.327 ms | 168 ms | 0/4 |
| R1 | `r1_…_scene_s7` | escena | **4,29** | ancla del techo live (stride 7) | 0,794 | 0,794 | **0,794** | 5.623 ms | 572 ms | 0/4 |
| R3 | `r3_…_scene_s15` | escena | **2,00** | lo que corrió en el rodaje | 0,706 | 0,774 | **0,738** | 4.846 ms | 870 ms | 0/4 |
| R5 | `r5_…_scene_s26` | escena | **1,15** | ancla del peor caso (stride 26) | 0,618 | 0,677 | **0,646** | 5.360 ms | 1.463 ms | 0/4 |
| G1 | `g1_…_subject` | sujeto | 30,00 | (referencia DBE) | 0,971 | 0,892 | **0,930** | 5.236 ms | 168 ms | 0/4 |
| R2 | `r2_…_subject_s7` | sujeto | **4,29** | ancla del techo live (stride 7) | 0,853 | 0,879 | **0,866** | 5.635 ms | 572 ms | 0/4 |
| R4 | `r4_…_subject_s15` | sujeto | **2,00** | lo que corrió en el rodaje | 0,824 | 0,933 | **0,875** | 4.981 ms | 870 ms | 0/4 |
| R6 | `r6_…_subject_s26` | sujeto | **1,15** | ancla del peor caso (stride 26) | 0,676 | 0,821 | **0,742** | 5.577 ms | 1.463 ms | 0/4 |

Anclas: los strides son 30/7 ≈ 4,29 y 30/26 ≈ 1,15 fps **nominales** — el techo
medido fue 4,42 fps con F-RT5 (4,12 hoy, doc 101) y el peor caso medido 1,16 fps
(20:10). **R4 (0,875) > R2 (0,866) pese a tener la mitad de densidad: es ruido, no
una inversión — se declara, no se explica (doc 96 §7).**

**Lo que dicen estas filas (verificadas con bootstrap pareado por clip, doc 96 §4.1):**

- **F-96.4 (el central): la ganancia de la identidad sobrevive al tiempo real y
  excluye el cero en las CUATRO densidades** — sujeto−escena: +0,141 [+0,032,+0,258]
  a 30 fps, +0,072 [+0,013,+0,145] a 4,29, +0,137 [+0,032,+0,258] a 2,00, +0,096
  [+0,011,+0,202] a 1,15. Es la única palanca del banco significativa a la densidad
  del live de hoy. El tracker NO se fragmenta (tracks 154→103/91/105). La comparación
  cruzada "R2 (0,866) > T1 con 30 fps (0,789)" es **estimación puntual** (IC
  [−0,071,+0,229]), se reporta como consistente, no como hallazgo.
- **F-96.1: a ~4 fps el agregado no se degrada de forma detectable** (+0,005
  [−0,120,+0,132]), pero esconde una redistribución: P2 cae 1,00→0,60 y P6 1,00→0,50,
  mientras **P9 sube 0,60→1,00 con 2 FP menos**. Los deltas de densidad del agregado
  **de escena** NO excluyen el cero (ni R5−T1 −0,143); bajo **sujeto** el peor caso
  **sí**: R6−G1 = −0,188 [−0,334, −0,040] es el único costo de densidad
  individualmente significativo (doc 96 §4.1). Para escena, el costo queda como
  tendencia monótona con mecanismo identificado, no como efecto establecido.
- **F-96.2: lo primero que se rompe es el rescate de F-81.1.** CR-02 vive de que la
  histéresis acumule percepción intermitente (SDR 0,281); P2 pasa a 0,600 y luego a
  0,200. Límite declarado de F-81.1: la histéresis rescata mientras la cadencia
  alcance para muestrear. La identidad no lo arregla — es percepción, no atribución.
- **F-96.5 (✎ corregido en revisión adversarial): el `t_alert` agregado quieto era
  un artefacto de supervivencia** — los episodios lentos mueren como `missed` y su
  salida baja el promedio. Entre supervivientes comunes, t_alert crece **+0,7 a
  +1,3 s**. El costo real es acotado (~1 s sobre políticas de 4–7 s) y `t_alert` no
  se compara entre densidades sin control de supervivencia.
- **F-96.7: 0 FP en negativos en las ocho campañas.** Con 4 clips es control
  comparativo, no cota — el tiempo real no introduce falsas alarmas en cumplimiento.

> **Guards de esta campaña.** (a) `run_descriptor.rate_control.stride` + conteo de
> unidades contra `ceil(n/stride)`, por clip: 34/34 en las seis. (b) Comparabilidad
> con las referencias verificada, no supuesta: re-correr replay + `evaluate-alerts`
> con el código de hoy sobre las detecciones de T1 reprodujo sus **34 evals idénticos
> campo a campo** (`datos/96-verificar-comparabilidad-t1.py`).

> **Qué NO miden.** No son corridas por el bus: miden densidad de evidencia sobre el
> camino DBE. Integridad del acople y latencia operativa siguen viniendo de los humos
> EBE (docs 37/65/67/91). El decimado es regular; el descarte live es irregular —
> **límite cerrado por el doc 101**: la irregularidad real se midió (CV 0,22 hoy /
> 0,36 rodaje) y el eje se re-corrió con decimado empírico (3 semillas, equivalencia
> decimado≡re-inferencia verificada 34/34 contra R1): ningún contraste
> jitter−regular detectable y la ganancia de la identidad conserva el signo en 6/6
> realizaciones (F-101.3/4, con matiz declarado a 2,5 fps).

## Campañas candidatas (el contraste que falta)

| Prioridad | Combinación a variar | Qué pregunta responde | Estado |
|---|---|---|---|
| ~~1~~ | ~~Prompts `edir_v1` / `eind_v1`~~ | **RESUELTO**: Nivel A (doc 83) + Nivel B (D1, doc 85) → veto de precisión, E-IND es el núcleo | **cerrado** |
| ~~2~~ | ~~Modelo `gdino-base-560`~~ | **HECHO** (T2, doc 84): F-81.2b refutada bajo `v2_short`; CR-02 SDR 0,281→0,920 | **cerrado** |
| ~~1~~ | ~~E-HYB `hyb_or`~~ | **HECHO (H1, doc 87)**: predicción refutada, F-87.2 | **cerrado** |
| ~~2~~ | ~~E-HYB `hyb_and`~~ | **No ejecutada CON CAUSA** — la vigente es D-90.4: no medible contra este banco sin romper la comparabilidad de las 6 campañas (el planteo original de doc 87 §5 queda archivado como predicción) | trabajo futuro con predicción escrita |
| ~~1~~ | ~~`bare_head` × `gdino-base-560`~~ | **HECHO (B1, doc 88)**: F-88.2 tampoco alcanza (0,480 vs 0,582); de yapa F-88.1 (costo del caption) y F-88.3 | **cerrado** |
| ~~1~~ | ~~Granularidad `subject` (G1)~~ | **HECHO (G1, doc 89)**: F1 0,930, la mejor del banco. `track_id` post-hoc, sin GPU | **cerrado** |
| ~~1~~ | ~~Densidad de evidencia del camino live~~ | **HECHO (R1–R6, doc 96)**: F-96.4 — la ganancia de la identidad excluye el cero en las 4 densidades; los deltas de densidad del agregado no | **cerrado** |
| 1 | Lote de internet sumado al banco | Material no guionado (L4) + soak → **análisis de sensibilidad del control de FP** (D-90.1 punto 4 — NO habilita FAR/hora: la limitación L1 permanece, ver caveat abajo) | **GT LISTO (3 clips, doc 102); campañas I1/I2 armadas, sin correr** |
| 2 | Campaña EBE de punta a punta por el bus sobre los 34 clips | Integridad del acople y latencia operativa CONTRA GT, no en humos. Hoy el eje se cubre por densidad (R1–R6) + humos verdes (37/65/67/91) | trabajo ubicado, no ejecutado |
| 2 | Port de `track_id` al pipeline online (spec 42 §3) | Solo si se decide llevar G1 a producción: hoy el `track_id` es post-hoc. Decisión de ADR-002, ver doc 89 §7 | decisión del usuario |

**Todas las palancas del banco están agotadas.** Formulación (D1), fusión (H1), modelo
(T2), vocabulario nativo (B1), granularidad (G1) y **densidad de evidencia (R1–R6)**.
Lo único que falta para cerrar el banco es material: video no guionado (L4) y el soak
como **control de negativos ampliado** — que no convierte a FAR/hora en métrica (L1
permanece: el techo del banco con soak es 0,263 h y hacen falta 3 h).

### Estrato B — lote de internet (4 clips, obra real NO guionada)

### Estrato B — lote de internet (13 clips, obra real NO guionada) · gen. 3, 2026-08-09

**El lote cerrado y medido de punta a punta.** 13 de los 14 clips con GT humano
(`v08_c01` excluido con causa, doc `operacion/111`); inferencia fresca de los 13 en
**una sola sesión** de 72 min de GPU. Procedencia única. Las gen. 1 y 2 (3 y 4 clips)
quedan supersedidas — `metrics.gen2.json` preservado al lado.

**El material:** 4 clips positivos (5 episodios, **1 censurado** por A1 ⇒ 4 evaluables)
y **9 negativos** (13,1 min), de los cuales **1 es soak** (`v06_c01`, 6:09,6 = 0,1027 h,
el único denominador temporal del banco). Dos nocturnos positivos (`v04_c01`,
`v04_c02`) y un nocturno negativo (`v04_c03`, el único del banco).

| | I1 `scene` | I2 `subject` |
|---|---|---|
| recall (4 eps evaluables) | 0,750 | **1,000** |
| precision | **0,375** | 0,111 |
| **F1** | **0,500** | 0,200 |
| matched / missed / FP | 3 / 1 / 5 | 4 / 0 / 32 |
| t_alert | **4.767 ms** | 5.800 ms |
| SDR · TTFD | 0,890 · 16,5 ms | idénticos (mismas detecciones) |
| FP sobre los 9 negativos | **21** | **304** |
| **FAR/hora** (soak, 0,1027 h) | **29,2** | **1.850,8** |

**Por escenario:**

| | P1 (3 clips, 2 eps) | P6 (1 clip, 2 eps) | P5∅ (9 clips) |
|---|---|---|---|
| `scene` | recall 0,500 · 5 FP | **recall 1,000 · 0 FP** | 21 FP |
| `subject` | recall 1,000 · 32 FP | **recall 1,000 · 0 FP** | 304 FP |

### Cómo se lee — y confirma lo que la gen. 2 insinuaba

1. **`scene` le gana a `subject` en F1 (0,500 vs 0,200), y la brecha se agrandó** al
   pasar de 4 a 13 clips. `subject` compra el episodio que falta (recall 0,750→1,000)
   pagando **6× más FP en positivos y 14× más en negativos**. En el rodaje G1 dominaba;
   en obra real no guionada, no. **No hay una granularidad mejor: hay una correcta para
   cada régimen de densidad** (F-108.1).
2. **`v04_c02` (P6) es el único caso limpio de todo el estrato**: recall 1,000 y **0 FP**
   en ambas granularidades. Es nocturno, disperso y con un solo violador sosteniendo las
   dos condiciones — el régimen donde el sistema funciona.
3. **El episodio que `scene` pierde** es el CR-01 de `v04_c01`, por alerta prematura
   (confirma a los 4,0 s; la ventana abre a los 7,97 s).
4. **FAR/hora: 29,2 FA/hora en el mejor caso**, sobre 6 minutos de obra real donde nadie
   infringe. Ver el bloque de L1 abajo.
5. **n = 4 episodios evaluables en 13 clips.** Describe un régimen; no establece un
   ranking con poder estadístico.

**Determinismo re-confirmado (F-109.1).** Los 4 clips que ya se habían inferido en la
gen. 2 dieron detecciones **idénticas** al re-inferirlos (572 / 840 / 11.087 / 1.771
frames, mismas cajas). El pipeline DBE es reproducible entre sesiones.

**⚠️ Corrección de métrica que afecta cifras publicadas antes (doc 111 §6).** El
agregador calculaba `far_per_hour` con el numerador de **todos** los negativos y el
denominador de **solo los soak** — dos bases distintas. Con 1 soak y 1 negativo corto
(gen. 2) la distorsión era 1,2×; con 9 negativos infla **7×**. Corregido con test de
regresión: ahora numerador y denominador salen del mismo conjunto. **Las cifras de FAR
de la gen. 2 que circularon (48,7 y 2.045,6) eran incorrectas; las correctas son 29,2 y
1.850,8** — y son las mismas en gen. 2 y gen. 3, porque dependen solo del clip soak,
que es determinista. El `metrics.json` expone además `far_per_hour_all_negatives`
(96,1 / 1.390,5) como base informativa.

**Advertencias de lectura que salieron de este estrato** (valen para toda la página):

- **F-104.2** — en `scene`, subir el gate de área **empeora** los FP porque el conteo
  bajo era el latch de la escena capturada. **El conteo de FP no compara `scene` contra
  `subject` cuando la escena está capturada.**
- **F-104.4** — en `v10_c01` (fachada en altura: arnés, **no** chalecos) el GT humano
  dice `unknown` en ~85% de los frames-sujeto y el motor alerta igual. **El conteo de FP
  se mueve por alucinación de la clase ausente, no por acertar.**
- **F-108.2** — la mejor palanca de configuración medida in-sample
  (`min_subject_confidence` 0,50) **costó un episodio real** fuera de muestra. Ninguna
  configuración sale recomendada de este estrato.

**Nivel A del mismo material** (estado por persona, sin motor temporal), consolidado con
los 4 clips piloto: `results/bench_nivel_a/na1_gdinotiny560_v2short_video/`.

**✎ 2026-08-07 — L1 cambió de naturaleza: FAR/hora pasó a ser MEDIBLE, y el dato la
refuta.** Con la corrección del GT, `v06_c01` es negativo de 6:09,6 ⇒ **el primer clip
soak del banco** ⇒ denominador **0,1027 h** (era 0,0 h). El agregador ya no devuelve
`None`: devuelve **29,2 FA/hora en escena y 1.850,8 FA/hora por sujeto** (cifras
corregidas el 08-09 — las que circularon antes, 48,7 y 2.045,6, salían de un cálculo
que mezclaba bases; ver la sección del estrato B).

**D-90.1 no queda derogada, queda precisada.** Su argumento era que ningún denominador
alcanzable permite afirmar *"≤1 FA/hora"* — y sigue siendo cierto: con 0,1027 h y la
regla de 3 harían falta 3,0 h. Lo que cambió es que **ya no hace falta ese argumento**:
no se declara "no medible" una métrica cuando el dato medido la refuta de frente. El
banco pasó de 0,0358 h a **0,1548 h de tiempo negativo total** (`clip_bench_manifest.json`),
de los cuales 0,1027 h son soak citable.

> **~~FAR/hora no es una métrica de este trabajo~~ — DEROGADO el 2026-08-07 por el
> bloque de arriba.** Se conserva el texto original por trazabilidad: *"(D-90.1,
> 2026-08-04) Para afirmar 'FAR ≤ 1 FA/hora' con 0 FP harían falta 3 h de video en
> cumplimiento anotado; el banco alcanza 0,101 h con el clip soak previsto y 0,263 h
> como techo. Una cota de 11–30 FA/h no sostiene ninguna afirmación operativa."*
> **Lo que cambió:** el clip soak existe y FAR/hora se mide (**29,2** y **1.850,8** FA/hora).
> El argumento del denominador sigue en pie —no alcanza para afirmar una cota— pero ya
> no se declara la métrica no medible. **La evidencia de falsas alarmas del rodaje
> sigue siendo la columna "FP neg." de la tabla de arriba**: T1/T2/G1 dan 0 FP de 4;
> D1, H1 y B1 dan 2–3.

> **Comparabilidad:** T1 se evaluó con los fixes F-EV1/2/3 del evaluador
> (control-plane `c1cbb56`). Cualquier campaña anterior a ese commit **no es
> comparable** sin re-evaluar — se re-evalúa barato desde los artefactos
> guardados (`docs/operacion/datos/81-reevaluar.py`), la inferencia no se repite.
>
> Después vino `5327080` (08-04), que cambió el despacho de evaluadores y toca
> `_positive_flags_for_source` (el que deriva SDR/TTFD). **Verificado que NO afecta a
> las campañas `eind`**: el código de hoy reproduce los 34 evals de T1 idénticos campo
> a campo (`datos/96-verificar-comparabilidad-t1.py`, 2026-08-05). Las filas de arriba
> son comparables entre sí sin re-evaluar.

> **El SDR no se compara entre cadencias (F-96.6).** Vale dentro de un mismo `stride`.
> Las seis campañas de la tabla principal comparten `stride: 1`, así que ninguna
> conclusión previa se ve afectada; para el eje de densidad, ver la sección R1–R6.
