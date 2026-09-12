# Videos de la defensa (V1/V2/V3/V-G1)

Material visual para la defensa oral, definido en `docs/nucleo/09` §6.2 y con el
alcance resuelto en `docs/operacion/90` **D-90.7** (2026-08-05, por delegación):
**V1–V3 = una persona, granularidad de escena, sin identidad** (ilustran la
combinación núcleo T1) y **V-G1 = multitud con color por `track_id`** (ilustra G1,
el mejor resultado del banco). Principio doc 81 §1: cada video ilustra una
combinación MEDIDA — los insumos son artefactos reales de las campañas.

| Video | Clip | Combinación ilustrada | Mensaje |
|---|---|---|---|
| `V1_a_p1_c04` | P1, 30,7 s | T1 (tiny-560 + `v2_short` + escena, F1 0,789) | detección no es alerta: candidate → confirmed → ALERTA a t=7,3 s. Bonus A4: el casco detectado EN LA MESA no suprime CR-01 |
| ~~`V2`~~ | — | — | **NO EXISTE. El intento con `gloves` se DESCARTÓ por falso (ver §V2 abajo).** Hay que elegir clase y verificarla antes de renderizar |
| `V3_a_p3_c01` | P3, 18,4 s | T1 | lo que NO alerta: el transitorio queda `candidate` y resuelve en silencio (verificado 2/2 en vivo, doc 71) |
| `VG1_a_p7_c01` | P7 multitud | G1 (sujeto, F1 0,930) | identidad por sujeto: se ve QUIÉN viola. Este clip es el vuelco completo: T1 0 matched/1 missed/1 FP → G1 1/0/0 con las mismas detecciones |
| `VG1e_a_p7_c01` | P7 multitud | T1 (escena) | contraparte para el lado-a-lado (F-89.1: el motor "miraba a otra persona") |
| **`VG1_lado_a_lado`** | P7 multitud | **T1 \| G1 sincronizados** | **la pieza más fuerte del set.** Un solo video 1920×1080 con los dos paneles frame a frame sobre el MISMO clip y el MISMO instante: izquierda escena, derecha sujeto. Cada alerta rotulada con su veredicto contra el GT (`FALSA ALARMA` / `CORRECTA`), el mecanismo F-89.1 al pie y el resultado medido por lado. Como las detecciones son bit a bit idénticas, **la diferencia visible la produce el motor, no el modelo** |

## Cómo se regeneran

```bash
python3 armar_videos.py                # V1, V3, VG1, VG1e (sin GPU: replay + render)
python3 overlay_render.py --selfcheck  # verifica la lógica de timeline

# montaje lado a lado (reusa los replays que dejó armar_videos.py en trabajo/)
MP=/home/simonll4/projects/e-ovrt_media-plane
$MP/.venv/bin/python montaje_lado_a_lado.py --clip a_p7_c01 \
  --video ../../e-ovrt_datasets/datasets-videos/clips/a_p7_c01.mp4 \
  --izq-detections $MP/runs/run_20260803_221102_dbe_grounding_dino_b3e9db/detections.jsonl \
  --der-detections trabajo/a_p7_c01.tracked.jsonl \
  --izq-control trabajo/control_runs/defensa_a_p7_c01_scene_<ts> \
  --der-control trabajo/control_runs/defensa_a_p7_c01_subject_<ts> \
  --out videos/VG1_lado_a_lado.mp4
```

Los rótulos de veredicto (`--izq-alerta-nota` / `--der-alerta-nota`) y el texto del
mecanismo son **parámetros, no inferencias del script**: salen del `eval` de la
campaña (T1 `a_p7_c01`: 0 matched / 1 missed / 1 FP ⇒ su única alerta es la falsa;
G1: 1/0/0 ⇒ su única alerta es la correcta).

- `armar_videos.py` toma las detecciones de la campaña T1 (provenance del banco),
  re-corre el replay del control-plane (determinístico — reproduce T1 campo a campo,
  `datos/96-verificar-comparabilidad-t1.py`) y compone con `overlay_render.py`
  (corre con el venv del media-plane, que tiene OpenCV; salida H.264).
- **V2 está PENDIENTE y necesita GPU** (única pieza que la necesita): una corrida del
  media-plane con la clase nueva agregada al prompt set inline. Ver §V2.
- `videos/` y `trabajo/` están gitignorados (media derivada, se regenera); este
  README + los dos scripts son la fuente de verdad.

## Un segundo intento fallido: el fotograma de CR-02 (2026-09-07)

**Se descartó, y por la misma razón que V2: auditar antes de afirmar.** El informe pedía una
figura que cubriera también la condición de chaleco, y el mejor candidato era `a_p6_c01`, el
escenario donde CR-01 y CR-02 se confirman sobre el mismo sujeto. Se renderizó con este mismo
pipeline y **el fotograma resultó inservible**: sobre la espalda del actor, que viste buzo negro,
el detector dibuja una caja `vest 0,41`, de modo que la imagen muestra una alerta de «persona sin
chaleco» junto a una caja de chaleco sobre esa misma persona.

No es del clip. Medido sobre el episodio de chaleco de los siete clips del rodaje que lo tienen,
el detector propone un chaleco en el **70 % al 96 % de los cuadros**, con el anotador declarando
que no lo hay. Es el falso positivo de `vest` sobre ropa oscura ya documentado en `operacion/70`,
más el sujeto fantasma sobre el cuadro colgado de `operacion/71`.

Lo que sostiene el acierto de CR-02 en el rodaje no es que el detector no vea un chaleco, sino la
geometría de la asociación —el centro de la caja tiene que caer en la franja del torso— y la
ventana de resolución de 3 s, que impide que un falso intermitente apague la condición. En el
cuadro renderizado el centro caía **dentro** de la región por 0,7 px, y el patrón seguía en
`sustained` por la histéresis. Todo correcto, y todo imposible de contar en un epígrafe.

**Conclusión:** ningún clip de CR-02 del rodaje da un fotograma limpio. Si alguna vez se quiere
evidencia visual de esa condición, lo honesto es que ilustre el falso positivo, no el acierto.

## V2 — pendiente, y el intento fallido queda documentado

**El intento con `gloves` se descartó: era falso.** Corrida
`run_20260805_180847_dbe_grounding_dino_9357a7` (a_p1_c04 + `gloves` en el caption):
252 detecciones ≥0,25, conf 0,30–0,67. Auditoría visual de una muestra (las 4 de
mayor confianza + 4 repartidas por el ranking): **las de mayor confianza
(0,63–0,67) caen todas sobre el CASCO AMARILLO**, y las de confianza media sobre la
manga, la cabeza, el chaleco y una zona vacía del piso. **Ninguna sobre un guante.**
Los guantes reales están en la escena (oscuros, dentro del casco sobre la mesa) y el
modelo no los toma.

Lección, y es citable: **es un segundo caso independiente de F-94.1** (doc 94 — la
palabra tiene que alinear con lo que hay y con la taxonomía). Ahí `vehicle` se comía
lo que el GT llamaba `machinery`; acá `gloves` se lo come el objeto amarillo más
prominente del cuadro. Refuerza la versión fuerte de A1: agregar una clase cuesta
minutos **y validar la palabra también** — y el costo de no validarla es exactamente
este, un demo que miente.

**Requisito para cualquier V2 futuro (no negociable):** auditar visualmente las
detecciones de la clase nueva ANTES de renderizar. Un conteo de detecciones
(`252/920 frames`) NO es evidencia de que funcione.

## Estado

- **Listos y verificados frame a frame (4):** `V1`, `V3`, `VG1` + `VG1e`, y el
  montaje `VG1_lado_a_lado`.
- **Pendiente (1):** `V2`, con el requisito de auditoría de arriba y la clase por
  decidir.
- El usuario descartó recortes de duración y subtítulos/narración (2026-08-05).
