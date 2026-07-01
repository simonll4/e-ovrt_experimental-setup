# detections_3 Control-Plane Matrix

## Input

- Archivo: `../../../../e-ovrt_control-plane/tests/generator/detections_3.jsonl`
- Fuente: `video6bis`
- Duracion cubierta: `0.0s` a `10.67s`
- Eventos: `161`
- Detecciones totales: `683`
- Labels:
  - `person`: `211`
  - `helmet`: `293`
  - `vest`: `179`

## Objetivo

Comparar configuraciones CR-01/CR-02 manteniendo fijo el input del plano de medios. Esto permite aislar el efecto de parametros del plano de control:

- persistencia temporal,
- umbrales de confianza,
- area minima de persona,
- regiones espaciales usadas para asociar EPP a una persona.

## Variantes iniciales

| Variante | Intencion |
|---|---|
| `baseline` | Referencia equivalente a la configuracion usada en las pruebas previas. |
| `fast_confirm` | Confirma mas rapido para medir sensibilidad a eventos cortos. |
| `conservative` | Exige mas persistencia, confianza y area minima. |
| `wide_association` | Amplia regiones para tolerar desalineacion de bboxes. |
| `strict_association` | Reduce regiones y sube confianza de EPP. |
| `epp_lenient` | Acepta EPP con menor confianza para evaluar reduccion de falsas ausencias. |

## Ejecucion

Desde la raiz del workspace:

```bash
for cfg in e-ovrt_experimental-setup/control-plane/replay/detections_3/*.yaml; do
  e-ovrt_control-plane/.venv/bin/eovrt-control replay "$cfg"
done
```
