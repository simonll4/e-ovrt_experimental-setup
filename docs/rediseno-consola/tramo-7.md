# Tramo 7 — La vista Evidencia

Leé antes `01-reglas-codex.md`, `04-evidencia-diseno.md` y `tramo-6.md`
(este tramo usa el lector del registro que aquél construyó).

Objetivo: una sección que muestre **los 35 resultados que reporta el informe**,
navegables, en vez de 420 corridas planas. Es la pantalla que se usa el día de la
defensa.

---

## De qué se compone

Tres niveles, y ninguno inventado — los tres salen del registro:

```
Índice     (4)   bench_imagenes · bench_nivel_a · clip_bench · realtime
   └─ Resultado (35)   clip_bench/t1_gdinotiny560_v2short_scene …
        └─ Corridas    con su rol: campaign_media, campaign_control, …
```

**El primer nivel es el prefijo del `result_id`, y coincide exactamente con los
cuatro directorios de `results/`:**

| Prefijo | Resultados | Filas |
|---|---|---|
| `bench_imagenes` | 5 | 41 |
| `bench_nivel_a` | 4 | 84 |
| `clip_bench` | 14 | 928 |
| `realtime` | 12 | 707 |
| | **35** | **1.760** |

Se agrupa así, y **no por la columna `collection`**, por dos razones: es la
estructura que el usuario ya usa para citar cifras (los cuatro índices de
`results/`), y evita la trampa de abajo.

⚠ **`shared` no es una colección.** Los cuatro CSV suman 1.760 filas para 1.436
corridas únicas: las 43 filas de `shared.csv` son corridas que pertenecen a **dos**
resultados — por ejemplo la misma corrida bajo `bench_imagenes/gdino560` y bajo
`realtime/gdino560`. Si agrupás por la columna `collection` vas a dibujar un grupo
«shared» que no existe y a sacar esas corridas de los resultados donde tienen que
estar. Agrupando por prefijo la corrida compartida aparece **en los dos**, que es
lo correcto.

Volumen por resultado, para que dimensiones la pantalla: va de **1 corrida**
(`realtime/g2a_single_host`) a **544** (`realtime/decimado_empirico`). La mayoría
de las campañas de `clip_bench` tienen 68. **Paginá el nivel de corridas.**

---

## Backend

### Fuente

`results/evidence-runs/artifacts/<plane>/<run_id>/`, que ya tiene las 1.436
corridas con `summary.json`, `effective_config.yaml` y los `.jsonl.gz`
(`detections`, `metrics`, `errors`; en control además `alerts`, `pattern_events`,
`pattern_progress`, y `alerts.csv`).

**No se consultan los servicios.** Toda esta sección funciona con el media-plane,
el control y la GPU apagados: es el punto de E-2.

### Endpoints

```
GET /api/evidencia                      → colecciones + los 35 resultados con conteos
GET /api/evidencia/resultado?id=<rid>   → las corridas de un resultado (paginado)
GET /api/evidencia/run?plane=&run_id=   → el summary congelado de una corrida
```

**`result_id` lleva una barra** (`clip_bench/t1_…`). Va como **parámetro de
consulta**, no como segmento de ruta: meterlo en el path obliga a codificar y
después alguien lo va a romper. Por eso la forma de arriba.

Cada corrida devuelta trae:

- `run_id`, `plane`, `role`, `status` (`copied` | `archived_only`)
- `source_ref` — el eval o dato que la cita
- `tiene_detalle_vivo`: si el directorio original todavía existe en el plano
  correspondiente. Es lo que habilita el enlace de E-2.

### Degradación

Si `results/evidence-runs/` no está en disco —está **gitignorado**, así que en
otra máquina puede faltar— la sección responde vacía y **lo dice**: qué directorio
falta y de dónde sale (capa de evidencia del backup, `docs/operacion/126`).
Nunca una pantalla en blanco ni un error crudo.

### Tests

- Los 35 resultados y sus conteos salen del registro, no hardcodeados.
- Un `result_id` con barra se resuelve bien.
- `archived_only` se distingue de `copied` y no se ofrece como detalle vivo.
- Repositorio ausente → respuesta vacía explicativa, sin excepción.
- Una corrida de `shared.csv` aparece bajo sus dos resultados.

---

## Frontend

Ruta nueva `/evidencia` (y el detalle por resultado). Va en `nav.ts`, **primera
del grupo «Trabajo»** — el día de la defensa es la pantalla de entrada.

Tres vistas encadenadas, con las migas que ya existen:

1. **Índice.** Las 3 colecciones, cada una con sus resultados y el conteo de
   corridas. Es el mapa del capítulo de resultados.
2. **Resultado.** Sus corridas agrupadas por `role`, paginadas. Arriba: a qué
   índice de `results/` pertenece y su documento de procedencia.
3. **Corrida.** El summary congelado. Si `tiene_detalle_vivo`, un enlace a
   `/runs/:id`; si no, se dice que el artefacto vive sólo en el archivo.

Reglas de la pantalla:

- **Nada de imágenes.** La `archive_policy` excluye `previews`, `frames`,
  `images` y `annotated`: el archivo no las tiene. Los cuadros anotados se ven
  abriendo el detalle vivo. No inventes marcadores de posición.
- Reusá `ui/`, `charts/` y `palette.ts`. **Cero componentes nuevos** si uno
  existente sirve.
- `archived_only` se muestra con su motivo, no como un error. Son 44 corridas
  cuyo directorio ya no existe y cuyo dato sobrevive versionado: eso es una
  decisión registrada, no una falla.

---

## Los títulos los pone el usuario

`clip_bench/t1_gdinotiny560_v2short_scene` nos sirve a nosotros; **no es un
rótulo de defensa**.

Generá `results/evidence-vista/titulos.yaml` con las **35** entradas, cada una con
el `result_id`, una etiqueta derivada mecánicamente y un campo `titulo:` **vacío**.
La vista usa `titulo` cuando está y cae a la etiqueta derivada cuando no.

**No escribas los 35 títulos.** Son texto que va a proyectarse en una defensa: los
redacta el usuario. Tu trabajo es dejarle el esqueleto y que la pantalla funcione
con y sin él.

---

## Cierre

```bash
cd webconsole/backend && ./.venv/bin/python -m pytest -q
cd webconsole/frontend && npm test && npm run build
```

- Backend y frontend verdes, con los tests nuevos.
- **Contrato 10/10.**
- Capturas de los tres niveles.
- **Una captura con los tres servicios apagados**, que es la prueba de E-2: si la
  sección necesita el media-plane arriba, el tramo no está cerrado.
- Una captura del estado vacío, renombrando `results/evidence-runs/` a mano.
- En el reporte: los 35 resultados con su conteo, para contrastar contra
  `04-evidencia-diseno.md` §1.

Commit: `feat(webconsole): tramo 7 — vista de evidencia`
