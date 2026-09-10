# Tramo 7 — contraste independiente del registro y la API

Los conteos siguientes se calcularon leyendo los cuatro CSV directamente y se compararon con `/api/evidencia`. Se agrupa por prefijo de `result_id`.

| Índice | Resultados | Filas |
| --- | ---: | ---: |
| bench_imagenes | 5 | 41 |
| bench_nivel_a | 4 | 84 |
| clip_bench | 14 | 928 |
| realtime | 12 | 707 |

| Resultado | Corridas únicas dentro del resultado | Filas |
| --- | ---: | ---: |
| `bench_imagenes/clase_nueva` | 5 | 5 |
| `bench_imagenes/confirmacion_b5` | 6 | 6 |
| `bench_imagenes/gdino560` | 2 | 4 |
| `bench_imagenes/modelos_crudos` | 6 | 6 |
| `bench_imagenes/seleccion_s1` | 20 | 20 |
| `bench_nivel_a/d1_gdinotiny560_edir_vs_eind` | 18 | 18 |
| `bench_nivel_a/edir_vs_eind` | 18 | 18 |
| `bench_nivel_a/na1_gdinotiny560_v2short_video` | 17 | 30 |
| `bench_nivel_a/replica_base560` | 18 | 18 |
| `clip_bench/b1_gdinobase560_barehead_scene` | 68 | 68 |
| `clip_bench/d1_gdinotiny560_edirpair_scene` | 68 | 68 |
| `clip_bench/g1_gdinotiny560_v2short_subject` | 68 | 68 |
| `clip_bench/h1_gdinotiny560_hybor_scene` | 102 | 102 |
| `clip_bench/i1_gdinotiny560_v2short_scene_internet` | 26 | 39 |
| `clip_bench/i2_gdinotiny560_v2short_subject_internet` | 26 | 39 |
| `clip_bench/r1_gdinotiny560_v2short_scene_s7` | 68 | 68 |
| `clip_bench/r2_gdinotiny560_v2short_subject_s7` | 68 | 68 |
| `clip_bench/r3_gdinotiny560_v2short_scene_s15` | 68 | 68 |
| `clip_bench/r4_gdinotiny560_v2short_subject_s15` | 68 | 68 |
| `clip_bench/r5_gdinotiny560_v2short_scene_s26` | 68 | 68 |
| `clip_bench/r6_gdinotiny560_v2short_subject_s26` | 68 | 68 |
| `clip_bench/t1_gdinotiny560_v2short_scene` | 68 | 68 |
| `clip_bench/t2_gdinobase560_v2short_scene` | 68 | 68 |
| `realtime/bus_live_paridad` | 3 | 3 |
| `realtime/claqueta_reloj_externo` | 8 | 8 |
| `realtime/decimado_empirico` | 544 | 544 |
| `realtime/descarte_irregular` | 76 | 76 |
| `realtime/frt5_roundtrip_pil` | 23 | 23 |
| `realtime/g2a_single_host` | 1 | 1 |
| `realtime/gdino560` | 2 | 4 |
| `realtime/l0` | 2 | 2 |
| `realtime/matriz_modelo_fuente` | 24 | 24 |
| `realtime/regresion_g1_live` | 4 | 4 |
| `realtime/rodaje_seis_corridas` | 12 | 12 |
| `realtime/t_alert_notification` | 6 | 6 |

Total: 35 resultados; 1760 filas; 1436 corridas únicas globales.
Los conjuntos compartidos se conservan en cada resultado; `shared` no aparece como índice.
`titulos.yaml`: 35 entradas exactas; 35 títulos vacíos.
