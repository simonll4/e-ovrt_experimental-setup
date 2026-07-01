# detections_3 Results

Resumen comparativo de la matriz `cp_detections_3_cr01_cr02_matrix`.

Los artefactos completos de replay se generan en `runs/` y no se versionan.

## Resultado inicial

| Variante | Alertas | CR-01 | CR-02 | Eventos patron | Errores |
|---|---:|---:|---:|---:|---:|
| `baseline` | 1 | 0 | 1 | 19 | 0 |
| `conservative` | 1 | 0 | 1 | 17 | 0 |
| `epp_lenient` | 1 | 0 | 1 | 19 | 0 |
| `fast_confirm` | 3 | 0 | 3 | 22 | 0 |
| `strict_association` | 1 | 0 | 1 | 19 | 0 |
| `wide_association` | 1 | 0 | 1 | 17 | 0 |

Todas las variantes procesaron `161` unidades sin errores. La alerta persistente dominante es CR-02 para `subject_001`.

`fast_confirm` confirma eventos mas cortos y por eso abre tres alertas CR-02. Para este clip, las variantes `baseline`, `epp_lenient` y `wide_association` conservaron el mismo punto de alerta principal en `3.8s`.

## Archivos

- `summary.csv`: resumen por corrida.
- `alerts.csv`: detalle de alerta, segundo y bbox asociada.
