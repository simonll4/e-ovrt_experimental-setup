# Generación de clips desde la consola — diseño

> **Estado**: diseño aprobado, sin implementar.
> **Fecha**: 2026-07-21
> **Contexto**: `docs/operacion/59-guion-grabacion-bloque-a.md` (guion de rodaje),
> `docs/specs/43-clip-bench-gt-temporal.md` (contrato de GT de video),
> `2026-07-21-grabacion-rodaje-design.md` (la grabación, ya implementada — esto es su
> continuación natural).

## 1. Problema

La grabación desde la consola ya deja el master en
`e-ovrt_datasets/datasets-videos/raw/`. Falta el paso siguiente: convertir ese master
de ~33 s en el clip de ~20 s que el banco necesita, con el evento cayendo en el
segundo 3–4.

Hoy ese paso es una línea de terminal:

```bash
prepare_clip.sh raw/P1-a-take2.mp4 a_p1_c01 --ss 10.5 --to 20
```

Para escribirla hay que mirar el video, anotar en qué segundo ocurre el evento,
restar el pre-roll, y acertarle a la semántica de `--to`. Con ~25 tomas del rodaje,
ahí se pierde el tiempo y se cometen errores que no se ven hasta días después.

## 2. Alcance

**La consola hace exactamente tres cosas** (decisión del usuario, 2026-07-21):

1. **Ubicar las cámaras** — el preview de la ventana Cámaras. Ya existe.
2. **Generar los clips** — grabar (ya existe) + recortar.
3. **Visualizar los clips generados** — para chequear que salieron bien.

**Fuera de alcance, y es deliberado:** la pre-anotación automática con GPU, el
`.clip.yaml` de material ajeno, la corrección en CVAT y la derivación del GT se
siguen haciendo **con scripts**, no desde la web. Se evaluó meter la cola de
pre-anotación en la consola y se descartó: es la parte más cara de construir
(jobs asíncronos, contención de VRAM con el modelo del media-plane, log en vivo) y
la que menos veces por semana se usa.

**Tampoco entra** el manejo elaborado de casos raros. La política es prevenir en el
rodaje —el guion ya lo hace, ver §6— y cuando aparezca un caso raro (sobre todo en
el material de internet) se ajusta con scripts a mano.

## 3. Decisiones

| # | Decisión | Motivo |
|---|---|---|
| D1 | Dos marcas del operador: **evento** y **fin** | Marcar para recortar y anotar el borrador del episodio pasan a ser el mismo gesto, hecho sobre el video real y no sobre el plan |
| D2 | La consola calcula la ventana; el operador no hace cuentas | Es toda la fricción que se quiere sacar |
| D3 | Se pasa **duración** a `prepare_clip.sh`, nunca un instante absoluto | Neutraliza de raíz la trampa de `--to` (§5.1) |
| D4 | `clip_id` = `a_<escenario>_c<NN>` | El id dice bloque y escenario de un vistazo, que es como se razona al mirar resultados |
| D5 | El `.clip.yaml` se genera **sin campos a mano** | Solo `clip_id`/`block`/`scenario` son obligatorios aguas abajo, y los tres se derivan |
| D6 | **No** se piden `distance_band_m` / `lighting` / `occlusion` | Hoy no las consume ningún código (solo tests y fixtures). YAGNI |
| D7 | Si las marcas violan el guion: **avisa fuerte y genera igual** | El material existe y a veces es lo único que hay; bloquearlo no lo mejora. El aviso queda registrado |
| D8 | El master en `raw/` **nunca se toca** | Si marcaste mal, rehacés el clip sin volver a filmar |
| D9 | Regenerar **sobrescribe** el mismo `clip_id` e **invalida la pre-anotación vieja** | Un corte mal hecho es un error, no material. El XML viejo son cajas de un video que ya no existe: dejarlo es material silenciosamente corrupto |

## 4. Arquitectura

```
[Cámaras]  Grabar ─────────────────────► raw/P1-a-take2.mp4     (ya existe)
                                             │
[Clips]    Lista: masters sin recortar  ◄────┘
             │
             ├─ abrir master → player con 2 marcas (evento / fin)
             │     "Generar clip" ──► prepare_clip.sh ──► clips/a_p1_c01.mp4
             │                                        │        + .info.json
             │                                        └──► a_p1_c01.clip.yaml
             │
           Lista: clips generados → player para verificar
                                             │
                              (de acá en adelante, scripts)
```

Todo vive en el webconsole. `e-ovrt_datasets` y `e-ovrt_media-plane` no se modifican:
`prepare_clip.sh` se invoca tal cual está.

### 4.1 Unidades

| Unidad | Responsabilidad | Ubicación |
|---|---|---|
| `clips/window.py` | Marcas → ventana de recorte + advertencias del guion. **Función pura** | backend `clips/` |
| `clips/naming.py` | Próximo `clip_id` libre por escenario | backend `clips/` |
| `clips/inventory.py` | Lee `raw/` y `clips/`, deriva el estado de cada toma | backend `clips/` |
| `clips/trim.py` | Invoca `prepare_clip.sh` y reporta su salida real | backend `clips/` |
| `clips/clip_yaml.py` | Escribe el `.clip.yaml` | backend `clips/` |
| `routers/clips.py` | REST + servido de video con Range | backend |
| `ClipsPage.tsx` | Las dos listas y su estado | frontend |
| `TrimDialog.tsx` | Player con las dos marcas | frontend |

### 4.2 Servido de video con Range

Para marcar el evento hay que arrastrar la línea de tiempo, y eso exige que el
backend responda **HTTP Range**. Sin eso el player descarga los 33 s enteros antes de
permitir saltar a la mitad, y con 25 tomas es insoportable. La consola ya tiene un
proxy con Range para artefactos de corridas: se reusa ese patrón.

## 5. Flujo

1. El operador abre **Clips** y ve los masters de `raw/` que todavía no tienen clip.
2. Abre uno: player con el video y dos botones de marca.
3. Reproduce, marca **el evento** (se saca el casco) y **el fin** (se lo pone).
4. "Generar clip". La consola calcula la ventana, elige el `clip_id`, corre
   `prepare_clip.sh` y escribe el `.clip.yaml`.
5. El clip aparece en la lista de generados; le da play y verifica que el evento cae
   donde debía.
6. De ahí en adelante: pre-anotación, CVAT y GT **con scripts**.

### 5.1 El cálculo

```
inicio    = t_evento - 3,5        (pre-roll)
fin_clip  = t_fin    + 3          (cola)
duración  = fin_clip - inicio

prepare_clip.sh <master> a_p1_c01 --ss <inicio> --to <duración> --fps 30
```

> **Trampa verificada empíricamente (ffmpeg 8.0.1)**: en `prepare_clip.sh` `-ss` va
> antes del input y `-to` después, y con esa combinación **`--to` es relativo al punto
> de corte**: se comporta como una duración. `--ss 5 --to 8` produce 8 s, no 3.
> Por eso D3 pasa siempre duración. Escribirlo mal no falla: produce en silencio un
> clip más largo con el evento descolocado respecto del GT.

Los valores 3,5 s de pre-roll y 3 s de cola salen de las reglas de oro del guion
(doc 59 §1) y de las plantillas de §2.

### 5.2 El `.clip.yaml` generado

```yaml
clip_id: a_p1_c01
block: A                  # rodaje propio guionado
scenario: P1              # heredado del master: se eligió al grabar
source_id: a_p1_c01       # el evaluador matchea alert.source_id == episode.source_id
level: scene

episode_draft:            # borrador, NO es el GT: la verdad sale de CVAT
  onset_ms: 3500
  end_ms: 17500
  marked_by: consola
  warnings: []            # ver §5.3
```

Los tiempos son **relativos al clip**, no al master. `onset_ms` da 3500 siempre que
el pre-roll haya entrado completo; si el evento ocurrió antes de los 3,5 s del master
no se puede retroceder más, así que el corte arranca en 0 y `onset_ms` queda en
`t_evento` — menor a 3500, con su advertencia (§5.3). Esa asimetría es justamente la
señal de que el clip mide el TTFD degradado.

`derive_clip_gt.py` exige solo `clip_id`, `block` y `scenario`; valida el tipo de
`recording`/`annotation` si están, tolera claves extra, y arma el GT con un conjunto
explícito de campos — verificado leyendo el script. Por eso `episode_draft` es seguro
y no se filtra al GT.

### 5.3 Advertencias del guion (D7)

Se calculan al generar y quedan en `episode_draft.warnings`:

| Regla | Se rompe cuando | Mensaje |
|---|---|---|
| Pre-roll ≥ 3,5 s | `t_evento < 3,5` | "solo N s de pre-roll, se necesitan 3,5 — el TTFD va a salir degradado" |
| Cola ≥ 3 s | `t_fin + 3 > duración del master` | "solo N s de cola, se necesitan 3" |
| Duración del escenario | el clip queda bajo el objetivo del escenario | "clip de N s, el guion pide ~M s para este escenario" |

Objetivos de duración, tomados de doc 59 §2–§4: **P1 ≈ 20 s**, **P2 ≈ 30 s**,
**P3 ≈ 15 s**, **P5 15–20 s**, **P9 18–20 s**. Los escenarios que el guion no
cuantifica (P4, P6, P7, P8) **no generan esta advertencia** — no se inventa un
objetivo. Las otras dos reglas (pre-roll y cola) sí aplican a los nueve.

El clip se genera igual. El gate de dimensionamiento de `derive_clip_gt` las volverá a
detectar aguas abajo; el punto de mostrarlas acá es que se vean **el mismo día**, con
el equipo todavía disponible.

## 6. Por qué esto alcanza

El guion de rodaje **ya previene** los tres casos de §5.3. Sus reglas de oro dicen
textual que el onset va en t≈3–4 s, que hay que seguir filmando ≥2–3 s tras corregir
la infracción, y que la toma es de 30–35 s aunque el clip final sea de 20. Lo que no
existía era algo que verificara el cumplimiento **en el momento**; la marca de los
30 s del panel de grabación ya cubre la tercera regla, y §5.3 cubre las otras dos.

Refuerzo pendiente al guion (§8): que el operador **cante en voz alta el momento del
evento**, porque alguien va a tener que encontrarlo después en el video para marcarlo.

## 7. Manejo de errores

| Falla | Respuesta |
|---|---|
| Fin marcado antes que el evento | Se rechaza al generar, con el motivo |
| `prepare_clip.sh` falla | Se muestra su salida real, no un error genérico. El master queda intacto |
| El master no se puede leer | Se marca en la lista; no rompe la vista |
| El `clip_id` ya existe y no es una regeneración | Se toma el siguiente libre |
| Regenerar un clip con pre-anotación previa | Se invalida el XML viejo (D9) |
| `raw/` o `clips/` no existen | Lista vacía, no error |

## 8. Testing

- **`clips/window.py` es una función pura**: se testea sin ffmpeg ni archivos, con los
  casos de las plantillas del guion y los bordes (evento a los 2 s, fin pegado al
  final del master, fin antes que el evento).
- **El `.clip.yaml` se contrasta contra lo que `derive_clip_gt.py` exige de verdad**,
  no contra lo que el spec suponga: un test carga el YAML generado con la misma
  función de validación del script.
- Nombrado: autoincremento por escenario, huecos, material ajeno en el directorio.
- **Criterio de aceptación real**: un clip generado por la consola pasa por
  `prepare_clip.sh` y sale con un `info.json` cuyo `n_frames` es coherente con la
  ventana pedida. Mismo criterio que se usó en la herramienta de grabación.
- Con hardware/material real: generar un clip de una toma de prueba y verificar en el
  player que el evento cae en t≈3,5 s.

## 9. Impacto en los repos

- `e-ovrt_experimental-setup`: **todo el trabajo** (backend `clips/`, router,
  `ClipsPage` + `TrimDialog`).
- `e-ovrt_media-plane`: ninguno.
- `e-ovrt_datasets`: ninguno. `prepare_clip.sh` se invoca sin tocarlo.
- `docs`: refuerzo del guion (§6) — cantar el evento en voz alta.
