# Campañas de Nivel A (estado por persona sobre el bench de imágenes)

Nivel A = **percepción**: se puntúa el estado "sin EPP" de cada persona contra
`has_helmet` / `has_vest`, sin motor de patrones ni tiempo. Es el nivel donde se
decide entre estrategias de prompts (`nucleo/04` §8); el Nivel B (alertas sobre
clips, `results/clip_bench/`) mide la plataforma alrededor del modelo.

**Cómo leer esta tabla.** Cada fila es el rendimiento medido de una combinación, no
una nota (marco del doc 81 §1). Umbrales calibrados en la **mitad A** de cada estrato,
métricas reportadas **solo sobre la mitad B**. Matching persona↔predicción IoU≥0,5
codicioso 1:1; una predicción sin persona del GT es FP.

## D1 — E-DIR vs E-IND (`d1_gdinotiny560_edir_vs_eind`, 2026-08-03)

Modelo `grounding-dino/gdino-tiny-560`. Variable única: el prompt set. E-IND corre en
su forma desplegada (3 clases en un caption); cada variante E-DIR corre **aislada**
en su propio caption. Detalle y caveats: `docs/operacion/83`.

### CR-01 (casco)

| Estrato | Brazo | P | R | F1 | IC95 recall | n+ |
|---|---|---|---|---|---|---|
| `bench_obra` | **E-IND** | 0,476 | 0,357 | **0,408** | [0,179–0,556] | 28 |
| `bench_obra` | `cr01_spec` | 0,200 | 0,179 | 0,189 | [0,043–0,370] | 28 |
| `bench_obra` | `cr01_neg` | 0,160 | 0,143 | 0,151 | [0,028–0,333] | 28 |
| `bench_obra` | `cr01_obs` | 0,097 | 0,250 | 0,140 | [0,100–0,471] | 28 |
| `shel5k` | **E-IND** | 0,464 | 0,662 | **0,546** | [0,628–0,697] | 2487 |
| `shel5k` | `cr01_obs` | 0,119 | 0,445 | 0,188 | [0,420–0,472] | 2487 |
| `shel5k` | `cr01_neg` | 0,083 | 0,232 | 0,123 | [0,211–0,255] | 2487 |
| `shel5k` | `cr01_spec` | 0,061 | 0,234 | 0,097 | [0,215–0,255] | 2487 |

### CR-02 (chaleco) — solo `bench_obra`

| Brazo | P | R | F1 | IC95 recall | n+ |
|---|---|---|---|---|---|
| **E-IND** | 0,567 | 0,415 | **0,479** | [0,243–0,644] | 82 |
| `cr02_obs` | 0,434 | 0,402 | 0,418 | [0,259–0,592] | 82 |
| `cr02_neg` | 0,359 | 0,451 | 0,400 | [0,311–0,646] | 82 |
| `cr02_spec` | 0,298 | 0,341 | 0,318 | [0,220–0,568] | 82 |

`shel5k` y `chv` no aportan CR-02: SHEL5K no anota chaleco y CHV solo permitiría
derivarlo por geometría, que sería circular con E-IND (D10, doc 83 F-83.3).

### Veredicto del gate (`nucleo/04` §8)

| Estrato / condición | ratio F1 E-DIR / E-IND | ¿< 50%? |
|---|---|---|
| `bench_obra` / CR-01 | 0,46 | sí |
| `shel5k` / CR-01 | 0,34 | sí |
| `bench_obra` / CR-02 | 0,87 | **no** |

**El gate no se dispara** — exige estar por debajo del 50% en **ambas** condiciones.
**E-DIR pasa a la Fase 2** (cadena completa sobre clips).

### Complementariedad (predicción pre-registrada: >15% ⇒ margen para E-HYB)

| Estrato / condición | E-IND falla | recupera E-DIR | fracción |
|---|---|---|---|
| `shel5k` / CR-01 | 840 | 155 | **18,5%** |
| `bench_obra` / CR-02 | 48 | 9 | **18,8%** |
| `bench_obra` / CR-01 | 18 | 1 | 5,6% (n insuficiente) |

**Contrastada en las dos condiciones** cuando el n alcanza.

### E-HYB Fase 1 offline (doc 12 §4: dual-run, gating por persona, sin params propios)

| Corte | E-IND F1 | **E-HYB-or F1** | corrobora TPs | corrobora FPs |
|---|---|---|---|---|
| `bench_obra`/CR-01 | 0,408 | 0,293 | 50% | 64% |
| `bench_obra`/CR-02 | 0,479 | **0,473** | 71% | **88%** |
| `shel5k`/CR-01 | 0,546 | 0,333 | **58%** | **24%** |

-or no supera a E-IND en ningún corte de Nivel A (la adopción §8.3 se decide en Fase 2
sobre F1 de alertas). La corroboración (-and) **discrimina 2,4× en CR-01** y se
**invierte en CR-02** (los errores de ambas estrategias caen sobre los mismos chalecos
difíciles) → si -and va a Fase 2, el `corroboration_factor` tiene que ser por condición.

## Hallazgos vigentes

- **F-83.4 — la formulación mueve el rendimiento, y cuánto depende de la condición.**
  E-DIR queda en 0,34–0,46 del F1 de E-IND en casco (dos estratos independientes, IC
  no solapados en `shel5k`) y en 0,87 en chaleco. Coherente con el caveat C1 del acta
  (doc 76): la debilidad del encoder con la negación era la hipótesis del eje.
- **F-83.5 — el eje ganador cambia con la condición, y la negación pura nunca gana.**
  `specificity` y `observable_state` se reparten el primer puesto según estrato y
  condición; `syntactic_negation` es el eje más débil de los tres en todos los cortes.
- **F-83.6 — E-DIR no es un detector, pero es un recuperador.** `cr01_obs` en `shel5k`
  rinde F1 0,188 (precision 0,119, 8.212 FP) y aun así recupera el 18,5% de lo que
  E-IND no ve. El costo de E-DIR es precision, no recall.
- **F-83.7 — la corroboración discrimina en CR-01 y se invierte en CR-02.** Los FP de
  `cr01_obs` son 54% ceguera al atributo + 46% alucinación (el gating filtra solo lo
  segundo). En casco E-DIR corrobora aciertos 2,4× más que errores; en chaleco
  corrobora más a los errores: percepción correlacionada sobre los mismos chalecos
  difíciles (la otra cara de F-G2.1/F-81.1).

## Limitación abierta

**CR-02 no está cerrado.** Vive en un solo estrato con 82 positivos y sus IC se
solapan con los de E-IND: el 0,87 alcanza para que el gate no se dispare (es un
umbral, no una prueba de significancia) pero **no** para afirmar que las estrategias
empatan en chaleco. Haría falta otra fuente con negativos de chaleco explícitos.

## Campañas de Fase 2 que salieron de acá (todas resueltas — ver `results/clip_bench/`)

| Combinación | Resolución |
|---|---|
| ~~Fase 2 (Nivel B): E-DIR sobre el clip bench~~ | **HECHA (D1, doc 85)**: precision 0,146 < 0,5 ⇒ **veto del §8, E-DIR descartada como núcleo**; el ratio F1 cae de 0,34–0,46 (Nivel A) a 0,20 — la brecha se agranda con la plataforma (F-85.4: el ranking de Nivel A no transfiere) |
| ~~Fase 2: fusión `hyb_or`~~ | **HECHA (H1, doc 87)**: predicción refutada — recall 0,824→0,353; F-87.2: la unión de evidencia NO es monótona en un motor temporal |
| ~~Fase 2: fusión `hyb_and`~~ | **No ejecutada CON CAUSA (D-90.4)**: no es medible contra este banco sin romper la comparabilidad de las 6 campañas (el evaluador deriva la ventana de la persistencia nominal del GT); predicción y condición de medición escritas (doc 87 §5) |
| ~~`gdino-base-560` réplica Nivel A + T2 clips~~ | **HECHA (doc 84)**: F-84.1 estructural, F-84.5/F-84.6 en clips |
| ~~`bare_head` como evidencia directa × base-560 (Nivel B)~~ | **HECHA (B1, doc 88)**: F-88.2 — tampoco alcanza (0,480 vs 0,582 sobre las mismas detecciones); de yapa F-88.1 (costo del caption: 0,082 de F1 por una palabra) y F-88.3 (la etiqueta corta gana a la frase negada) |
