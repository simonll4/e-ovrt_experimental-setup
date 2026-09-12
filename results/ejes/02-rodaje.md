# Eje 2 — El día de rodaje

**Rodaje: 2026-07-25, Bloque A.** La única jornada de captura propia con actores y
hardware real. Todo lo que sigue sale de ese día; lo que no, está listado al final
para que no se confunda.

---

## Qué se grabó

**34 clips, 35 episodios** (CR-01 28 / CR-02 7), escenarios P1–P9, con GT temporal
anotado a mano en CVAT.

`manifest.yaml` sha256 **`cef5082e…`** — ese sha es el **freeze de 34** que usaron
todas las campañas del banco, recuperable en el commit `f7a27fe6` de
`e-ovrt_datasets`.

**Denominador citable: 34 episodios evaluables sobre 35** — uno censurado con
causa declarada.

> El banco **vigente** tiene 47 clips (34 del rodaje + 13 del estrato B) y 37
> episodios, manifest `3f14f50a…`. Pero **las filas del rodaje nunca cambiaron**:
> tanto las altas del estrato B como la revisión ciega del GT del 08-09 ocurrieron
> enteramente en el Bloque B.

---

## Qué salió del rodaje

### A · Las 6 corridas en vivo — `realtime/rodaje_seis_corridas` (12 filas)

Lo que efectivamente corrió ese día, sobre OAK-D PoE, en EBE:

| Corrida | proc/drop | fps_eff | inf p50 | G2A p95 | ¿tiempo real? |
|---|---|---|---|---|---|
| GDINO P1 | 47/767 (**94 % drop**) | **1,16** | 567 ms | 890 ms | ✗ |
| GDINO P2 | 93/1115 (92 %) | 1,76 | 439 ms | 665 ms | ✗ |
| GDINO P3 | 55/629 (92 %) | 1,51 | 432 ms | 630 ms | ✗ |
| YOLOE P1 | 254/615 (71 %) | **5,55** | 116 ms | 232 ms | ✓ |
| YOLOE P2 | 295/710 (71 %) | 5,98 | 118 ms | 225 ms | ✓ |
| YOLOE P3 | 152/322 (68 %) | 5,12 | 112 ms | 249 ms | ✓ |

Dos hechos del día que se citan siempre juntos:

- **Integridad del transporte perfecta**: `bus_dropped_events = 0` y
  `degraded = false` en las seis, y también en las de la tarde.
- **La jornada no fue estacionaria**: la misma configuración rindió **2,62 fps a
  las 13:33 y 1,16 fps a las 20:10 — 2,26×**. Lo que separa las poblaciones es
  **la fuente** (`video_file` 306 ms vs `oak_d`), no la hora en sí.

`capture_to_host` en las seis: **202–217 ms**, estable. Es el término que hay que
sumarle al G2A para hablar de vidrio→alerta (F-101.8: el G2A arranca en el
dequeue, no en el fotón).

### B · Las 12 campañas sobre el banco del rodaje — `clip_bench` (DBE)

Los clips del rodaje se re-evalúan offline. Son 12 de las 14 campañas del índice:

| Grupo | Campañas |
|---|---|
| **Combinación (6)** | `t1_gdinotiny560_v2short_scene` · `t2_gdinobase560_v2short_scene` · `b1_gdinobase560_barehead_scene` · `d1_gdinotiny560_edirpair_scene` · `g1_gdinotiny560_v2short_subject` · `h1_gdinotiny560_hybor_scene` |
| **Densidad R1–R6 (6)** | `r1`…`r6_gdinotiny560_v2short_{scene,subject}_s{7,15,26}` |

Recall de episodios sobre los 34: **T1 28/34 = 0,824** · **G1 33/34 = 0,971**.

---

## Qué NO es rodaje

Esto es lo que más se confunde, y por eso está acá:

| No es rodaje | Qué es en realidad |
|---|---|
| `clip_bench/i1_…_internet` y `i2_…_internet` | **Estrato B**: 13 clips del lote de internet (Bloque B). Columnas agregadas el 08-06 — **no comparar con las del rodaje sin control** |
| `bench_nivel_a/na1_gdinotiny560_v2short_video` | 17 clips = **los 13 del estrato B + 4 del piloto del 2026-07-18**. Es video, pero no del rodaje |
| `bench_nivel_a/d1_…`, `edir_vs_eind`, `replica_base560` | Nivel A sobre **imágenes** |
| Todo `bench_imagenes` | `bench_v3`: 6.477 imágenes de tres datasets — `bench_obra` (147, curado de `construction_site_safety`), `chv` (1.330), `shel5k` (5.000). Ninguna es del rodaje |

**Regla corta:** del rodaje son las **12 campañas de `clip_bench` sobre el freeze
de 34** y las **6 corridas de `realtime`**. Nada más.

---

## Trampa de anotación conocida

El export de CVAT a nivel **proyecto** sin `split_cvat_project.py` produce **GT
negativo en silencio**. La cadena correcta es `split → derive → validate →
promote → aggregate`. Y «person N» de la interfaz de CVAT **no es** el `track_id`
del XML.
