# Tramo 6 — clasificación A.4 regenerada

Decisión del usuario del 2026-09-10: conservar sólo los paraguas con evidencia abrible; resultado esperado `talert_integrated_video`, 4 ejecuciones, 3 de evidencia. Las dos listas de `consola.yaml` siguen vacías.

El clasificador descubre recursivamente cada `manifest.effective.yaml` y busca identidades en todo su subárbol JSON/JSONL/YAML. `_ejecuciones_por_slug` permanece intacto; sus conteos no se sustituyen.

Registro disponible: **True**. Resultados: **35**.

## Los 11 paraguas del listado

| Slug | Ejecuciones recursivas | Con evidencia | Veredicto | Motivo / resultado |
| --- | ---: | ---: | --- | --- |
| `diag_riesgo_activo` | 5 | 0 | Archivado | 0 de 5 ejecuciones son evidencia |
| `ebe_oakd_live` | 0 | 0 | Archivado | Sin ejecuciones consolidadas asociadas al slug |
| `ebe_p1_live` | 0 | 0 | Archivado | Sin ejecuciones consolidadas asociadas al slug |
| `ebe_p2_live` | 0 | 0 | Archivado | Sin ejecuciones consolidadas asociadas al slug |
| `ebe_p3_live` | 0 | 0 | Archivado | Sin ejecuciones consolidadas asociadas al slug |
| `rt-01` | 0 | 0 | Archivado | Sin ejecuciones consolidadas asociadas al slug |
| `talert_camera_smoke` | 0 | 0 | Archivado | Sin ejecuciones consolidadas asociadas al slug |
| `talert_integrated_video` | 4 | 3 | Evidencia | 3 de 4 ejecuciones son evidencia; `realtime/t_alert_notification` |
| `yoloe_p1_live` | 0 | 0 | Archivado | Sin ejecuciones consolidadas asociadas al slug |
| `yoloe_p2_live` | 0 | 0 | Archivado | Sin ejecuciones consolidadas asociadas al slug |
| `yoloe_p3_live` | 0 | 0 | Archivado | Sin ejecuciones consolidadas asociadas al slug |

## Contraste con archivos persistidos y el registro

Los cuatro directorios siguientes contienen manifiesto y reporte. Se contrastan los ids persistidos, no el nombre de la campaña. Admisión no figura en los CSV; las tres repeticiones sí.

| Ejecución | Manifiesto y artefactos dentro de runs/ | Corridas | Veredicto / resultados |
| --- | --- | --- | --- |
| `exp_20260813T051644827375Z_talert_admission-1` | `runs/t-alert-notification/official-20260813-03/integrated-video-02/admission-1/consolidated/exp_20260813T051644827375Z_talert_admission-1`: `manifest.effective.yaml`, `media/summary.json`, `control/summary.json`, `report/report.json` | `control_talert_integrated_a_p1_c08_20260813T051644Z_275fb5`<br>`run_20260813_051644_dbe_grounding_dino_3399b8` | Archivado:  |
| `exp_20260813T051703399915Z_talert_repetition-1` | `runs/t-alert-notification/official-20260813-03/integrated-video-02/repetition-1/consolidated/exp_20260813T051703399915Z_talert_repetition-1`: `manifest.effective.yaml`, `media/summary.json`, `control/summary.json`, `report/report.json` | `control_talert_integrated_a_p1_c08_20260813T051703Z_21e369`<br>`run_20260813_051703_dbe_grounding_dino_1d5e83` | Evidencia: realtime/t_alert_notification |
| `exp_20260813T051718284240Z_talert_repetition-2` | `runs/t-alert-notification/official-20260813-03/integrated-video-02/repetition-2/consolidated/exp_20260813T051718284240Z_talert_repetition-2`: `manifest.effective.yaml`, `media/summary.json`, `control/summary.json`, `report/report.json` | `control_talert_integrated_a_p1_c08_20260813T051718Z_362334`<br>`run_20260813_051718_dbe_grounding_dino_5135ac` | Evidencia: realtime/t_alert_notification |
| `exp_20260813T051736306649Z_talert_repetition-3` | `runs/t-alert-notification/official-20260813-03/integrated-video-02/repetition-3/consolidated/exp_20260813T051736306649Z_talert_repetition-3`: `manifest.effective.yaml`, `media/summary.json`, `control/summary.json`, `report/report.json` | `control_talert_integrated_a_p1_c08_20260813T051736Z_200a27`<br>`run_20260813_051736_dbe_grounding_dino_6fac85` | Evidencia: realtime/t_alert_notification |

## Grupos huérfanos: slugs ausentes del catálogo de paraguas

No cuelgan de ninguno de los 11 manifiestos listados. Se incluyen en el inventario y en el contador de ejecuciones archivadas; no se agregan recetas a la pantalla ni se infiere un slug por similitud.

| Slug huérfano | Ejecuciones | Con evidencia | Archivadas | Motivo |
| --- | ---: | ---: | ---: | --- |
| `d1` | 1 | 0 | 1 | Slug fuera del catálogo; ninguna corrida figura en los CSV. |
| `gate` | 1 | 0 | 1 | Slug fuera del catálogo; ninguna corrida figura en los CSV. |
| `gate_orq` | 81 | 0 | 81 | Slug fuera del catálogo; ninguna corrida figura en los CSV. |
| `orq_1` | 84 | 0 | 84 | Slug fuera del catálogo; ninguna corrida figura en los CSV. |
| `orq_2a` | 84 | 0 | 84 | Slug fuera del catálogo; ninguna corrida figura en los CSV. |
| `orq_alerts` | 83 | 0 | 83 | Slug fuera del catálogo; ninguna corrida figura en los CSV. |
| `orq_alerts_502` | 83 | 0 | 83 | Slug fuera del catálogo; ninguna corrida figura en los CSV. |
| `video16_clip10_gt` | 3 | 0 | 3 | Slug fuera del catálogo; ninguna corrida figura en los CSV. |

Total descubierto: **429**; evidencia: **3**; archivadas: **426**.

Los conteos son la foto del disco al ejecutar el script. Las suites anteriores generan smokes del orquestador en runs/; por eso el número de huérfanas puede crecer sin cambiar los 4/3 de talert ni los 5/0 de diag.

## Los 19 individuales: documentados aparte, fuera del filtro

| Manifiesto individual | Alcance |
| --- | --- |
| `experiments/bench_v2/b2_g_e1_gdino_t_test.yaml` | No listado; no se clasifica ni filtra. |
| `experiments/bench_v2/b2_g_e1_gdino_t_val.yaml` | No listado; no se clasifica ni filtra. |
| `experiments/bench_v2/b2_g_e2_gdino_b_test.yaml` | No listado; no se clasifica ni filtra. |
| `experiments/bench_v2/b2_g_e2_gdino_b_val.yaml` | No listado; no se clasifica ni filtra. |
| `experiments/bench_v2/b2_g_e5_mmgdino_t_test.yaml` | No listado; no se clasifica ni filtra. |
| `experiments/bench_v2/b2_g_e5_mmgdino_t_val.yaml` | No listado; no se clasifica ni filtra. |
| `experiments/bench_v2/b2_g_e6_mmgdino_b_test.yaml` | No listado; no se clasifica ni filtra. |
| `experiments/bench_v2/b2_g_e6_mmgdino_b_val.yaml` | No listado; no se clasifica ni filtra. |
| `experiments/bench_v2/b2_y_e3_yoloe_26l_test.yaml` | No listado; no se clasifica ni filtra. |
| `experiments/bench_v2/b2_y_e3_yoloe_26l_val.yaml` | No listado; no se clasifica ni filtra. |
| `experiments/bench_v2/b2_y_e4_yoloe_26s_test.yaml` | No listado; no se clasifica ni filtra. |
| `experiments/bench_v2/b2_y_e4_yoloe_26s_val.yaml` | No listado; no se clasifica ni filtra. |
| `experiments/gdino.yaml` | No listado; no se clasifica ni filtra. |
| `experiments/mock.yaml` | No listado; no se clasifica ni filtra. |
| `experiments/mock_chv.yaml` | No listado; no se clasifica ni filtra. |
| `experiments/video_annotated.yaml` | No listado; no se clasifica ni filtra. |
| `experiments/video_annotated_gdino.yaml` | No listado; no se clasifica ni filtra. |
| `experiments/yoloe.yaml` | No listado; no se clasifica ni filtra. |
| `experiments/yoloe_video.yaml` | No listado; no se clasifica ni filtra. |

## Cada ejecución: pertenencia, ruta, ids y motivo

| Slug | Pertenece al catálogo | Directorio | Corridas | Veredicto y motivo |
| --- | --- | --- | --- | --- |
| `d1` | No: huérfana | `runs/exp_20260712T140000Z_d1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate` | No: huérfana | `runs/exp_20260712T140000Z_gate` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `video16_clip10_gt` | No: huérfana | `runs/exp_20260718T175011Z_video16_clip10_gt` | `control_video16_clip10_gt_20260718T175238Z_cee43b`<br>`run_20260718_175011_dbe_grounding_dino_536018` | Archivado: Ninguna corrida consolidada figura en el registro |
| `video16_clip10_gt` | No: huérfana | `runs/exp_20260718T185006Z_video16_clip10_gt` | `control_video16_clip10_gt_20260718T185032Z_45f542`<br>`run_20260718_185007_dbe_grounding_dino_8e9b82` | Archivado: Ninguna corrida consolidada figura en el registro |
| `video16_clip10_gt` | No: huérfana | `runs/exp_20260718T185429Z_video16_clip10_gt` | `control_video16_clip10_gt_20260718T185818Z_00e118`<br>`run_20260718_185429_dbe_grounding_dino_1da6d3` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260725T130802Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260725T130802Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260725T130802Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260725T130802Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260725T130846Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260725T135246Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260725T135246Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260725T135246Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260725T135246Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260725T135329Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260725T135455Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260725T135456Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260725T161459Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260725T161459Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260725T161459Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260725T161459Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260725T161541Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260725T161836Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260725T161836Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260725T161836Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260725T161837Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260725T161918Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260725T162343Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260725T162343Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260725T162343Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260725T162344Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260725T162425Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260725T162857Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260725T162857Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260725T162857Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260725T162857Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260725T162939Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260725T165319Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260725T165319Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260725T165320Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260725T165320Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260725T165402Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260725T165754Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260725T165754Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260725T165755Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260725T165755Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260725T165836Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260725T170312Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260725T170313Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260725T170313Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260725T170313Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260725T170355Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260725T171305Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260725T171306Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260725T171306Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260725T171306Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260725T171348Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260725T184936Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260725T184936Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260725T184936Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260725T184936Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260725T185019Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `diag_riesgo_activo` | Sí | `runs/exp_20260725T185627Z_diag_riesgo_activo` | `control_diag_riesgo_activo_20260725T185627Z_6049ad`<br>`run_20260725_185627_dbe_grounding_dino_57b4eb` | Archivado: Ninguna corrida consolidada figura en el registro |
| `diag_riesgo_activo` | Sí | `runs/exp_20260725T185857Z_diag_riesgo_activo` | `control_diag_riesgo_activo_20260725T185857Z_0f933e`<br>`run_20260725_185857_dbe_grounding_dino_0b7e5a` | Archivado: Ninguna corrida consolidada figura en el registro |
| `diag_riesgo_activo` | Sí | `runs/exp_20260725T191134Z_diag_riesgo_activo` | `control_diag_riesgo_activo_20260725T191134Z_450c36`<br>`run_20260725_191134_dbe_grounding_dino_6c1dbf` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260725T193333Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260725T193333Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260725T193333Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260725T193333Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260725T193416Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260725T195031Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260725T195031Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260725T195031Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260725T195031Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260725T195114Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `diag_riesgo_activo` | Sí | `runs/exp_20260725T195209Z_diag_riesgo_activo` | `control_diag_riesgo_activo_20260725T195209Z_375719`<br>`run_20260725_195209_dbe_grounding_dino_66ff3a` | Archivado: Ninguna corrida consolidada figura en el registro |
| `diag_riesgo_activo` | Sí | `runs/exp_20260725T195701Z_diag_riesgo_activo` | `control_diag_riesgo_activo_20260725T195701Z_7fd13f`<br>`run_20260725_195701_dbe_grounding_dino_036df2` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260726T023210Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260726T023211Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260726T023211Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260726T023211Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260726T023255Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260726T023319Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260726T023320Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260726T023320Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260726T023320Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260726T023404Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260726T230631Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260726T230631Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260726T230631Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260726T230631Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260726T230714Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260726T230903Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260726T230903Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260726T230903Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260726T230903Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260726T230946Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260726T232309Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260726T232309Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260726T232309Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260726T232309Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260726T232352Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260726T232927Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260726T232927Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260726T232927Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260726T232928Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260726T233011Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260726T233239Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260726T233239Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260726T233239Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260726T233240Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260726T233323Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260726T233618Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260726T233618Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260726T233619Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260726T233619Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260726T233703Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260728T040647Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260728T040647Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260728T040648Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260728T040648Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260728T040732Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260728T131541Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260728T131542Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260728T131542Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260728T131542Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260728T131627Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260728T163105Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260728T163106Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260728T163106Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260728T163106Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260728T163149Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260729T014456Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260729T014457Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260729T014457Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260729T014457Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260729T014541Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260729T020236Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260729T020236Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260729T020236Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260729T020236Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260729T020320Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260729T022854Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260729T022854Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260729T022854Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260729T022854Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260729T022941Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260729T023645Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260729T023646Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260729T023646Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260729T023646Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260729T023732Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260729T034433Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260729T034433Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260729T034433Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260729T034433Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260729T034519Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260729T040506Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260729T040506Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260729T040506Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260729T040507Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260729T040550Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260805T043431Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260805T043431Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260805T043432Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260805T043432Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260805T043516Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260810T235443Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260810T235443Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260810T235444Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260810T235444Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260810T235529Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260811T044804Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260811T044804Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260811T044805Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260811T044805Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260811T044849Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260811T045053Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260811T045053Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260811T045054Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260811T045054Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260811T045138Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260812T034809Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260812T034810Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260812T034810Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260812T034810Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260812T034855Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260813T002959Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260813T002959Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260813T003000Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260813T003000Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260813T003044Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260813T005017Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260813T005017Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260813T005018Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260813T005018Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260813T005103Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260813T045717Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260813T045717Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260813T045717Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260813T045718Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260813T045809Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260813T045839Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260813T045840Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260813T045840Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260813T045840Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260813T045928Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260814T010749Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260814T010749Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260814T010750Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260814T010750Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260814T010855Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260814T172239Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260814T172240Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260814T172240Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260814T172240Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260814T172326Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260814T181059Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260814T181100Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260814T181100Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260814T181101Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260814T181153Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260814T202705Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260814T202705Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260814T202706Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260814T202706Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260814T202752Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260814T203341Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260814T203341Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260814T203341Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260814T203341Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260814T203426Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260815T214324Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260815T214324Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260815T214325Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260815T214325Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260815T214410Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260817T233532Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260817T233533Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260817T233533Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260817T233533Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260817T233619Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260817T233653Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260817T233653Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260817T233654Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260817T233654Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260817T233739Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260817T233812Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260817T233812Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260817T233812Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260817T233813Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260817T233858Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260817T233931Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260817T233931Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260817T233931Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260817T233932Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260817T234017Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260817T234051Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260817T234051Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260817T234051Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260817T234052Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260817T234136Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260817T234541Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260817T234541Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260817T234541Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260817T234541Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260817T234626Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260817T234700Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260817T234701Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260817T234701Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260817T234701Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260817T234749Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260817T234749Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260817T234750Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260817T234750Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260817T234835Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260818T000059Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260818T000059Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260818T000059Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260818T000059Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260818T000142Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260818T000436Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260818T000436Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260818T000437Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260818T000437Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260818T000523Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260818T003912Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260818T003912Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260818T003912Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260818T003913Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260818T003958Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260818T004514Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260818T004514Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260818T004515Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260818T004515Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260818T004559Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260818T005027Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260818T005027Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260818T005028Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260818T005028Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260818T005113Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260818T005159Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260818T005159Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260818T005200Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260818T005200Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260818T005244Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260818T020743Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260818T020744Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260818T020744Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260818T020744Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260818T020829Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260818T021352Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260818T021352Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260818T021353Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260818T021353Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260818T021437Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260819T214625Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260819T214625Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260819T214626Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260819T214626Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260819T214712Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260819T220724Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260819T220724Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260819T220724Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260819T220725Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260819T220812Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260819T221136Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260819T221137Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260819T221137Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260819T221137Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260819T221224Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260825T030210Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260825T030210Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260825T030211Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260825T030211Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260825T030253Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260909T021042Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260909T021042Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260909T021042Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260909T021042Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260909T021137Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260909T030857Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260909T030857Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260909T030858Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260909T030858Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260909T030954Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260909T031203Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260909T031203Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260909T031204Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260909T031204Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260909T031302Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260909T032257Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260909T032257Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260909T032258Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260909T032258Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260909T032407Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260909T122348Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260909T122348Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260909T122349Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260909T122349Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260909T122510Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260909T123657Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260909T123658Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260909T123659Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260909T123659Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260909T123800Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260909T125447Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260909T125452Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260909T125454Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260909T125505Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260909T125633Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260909T131150Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260909T131154Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260909T131157Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260909T131208Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260909T131335Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260909T133137Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260909T133141Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260909T133144Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260909T133155Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260909T133328Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260910T012516Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260910T012517Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260910T012517Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260910T012518Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260910T012608Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260910T012608Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260910T012610Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260910T012610Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260910T012701Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260910T013247Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260910T013247Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260910T013248Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260910T013248Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260910T013338Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260910T022209Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260910T022209Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260910T022211Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260910T022211Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260910T022318Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260910T023355Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260910T023355Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260910T023356Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260910T023357Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260910T023446Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260910T031919Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260910T031919Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260910T031921Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260910T031921Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260910T032011Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260910T034602Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260910T034602Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260910T034603Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260910T034604Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260910T034656Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260910T034926Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260910T034926Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260910T034928Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260910T034928Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260910T035016Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts` | No: huérfana | `runs/exp_20260910T035136Z_orq_alerts` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_alerts_502` | No: huérfana | `runs/exp_20260910T035136Z_orq_alerts_502` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_1` | No: huérfana | `runs/exp_20260910T035137Z_orq_1` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `orq_2a` | No: huérfana | `runs/exp_20260910T035137Z_orq_2a` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `gate_orq` | No: huérfana | `runs/exp_20260910T035225Z_gate_orq` | `run_active_1` | Archivado: Ninguna corrida consolidada figura en el registro |
| `talert_integrated_video` | Sí | `runs/t-alert-notification/official-20260813-03/integrated-video-02/admission-1/consolidated/exp_20260813T051644827375Z_talert_admission-1` | `control_talert_integrated_a_p1_c08_20260813T051644Z_275fb5`<br>`run_20260813_051644_dbe_grounding_dino_3399b8` | Archivado: Ninguna corrida consolidada figura en el registro |
| `talert_integrated_video` | Sí | `runs/t-alert-notification/official-20260813-03/integrated-video-02/repetition-1/consolidated/exp_20260813T051703399915Z_talert_repetition-1` | `control_talert_integrated_a_p1_c08_20260813T051703Z_21e369`<br>`run_20260813_051703_dbe_grounding_dino_1d5e83` | Evidencia: Corridas en el registro: control_talert_integrated_a_p1_c08_20260813T051703Z_21e369, run_20260813_051703_dbe_grounding_dino_1d5e83 |
| `talert_integrated_video` | Sí | `runs/t-alert-notification/official-20260813-03/integrated-video-02/repetition-2/consolidated/exp_20260813T051718284240Z_talert_repetition-2` | `control_talert_integrated_a_p1_c08_20260813T051718Z_362334`<br>`run_20260813_051718_dbe_grounding_dino_5135ac` | Evidencia: Corridas en el registro: control_talert_integrated_a_p1_c08_20260813T051718Z_362334, run_20260813_051718_dbe_grounding_dino_5135ac |
| `talert_integrated_video` | Sí | `runs/t-alert-notification/official-20260813-03/integrated-video-02/repetition-3/consolidated/exp_20260813T051736306649Z_talert_repetition-3` | `control_talert_integrated_a_p1_c08_20260813T051736Z_200a27`<br>`run_20260813_051736_dbe_grounding_dino_6fac85` | Evidencia: Corridas en el registro: control_talert_integrated_a_p1_c08_20260813T051736Z_200a27, run_20260813_051736_dbe_grounding_dino_6fac85 |
