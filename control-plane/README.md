# Control Plane Experimental Setup

Este directorio centraliza configuraciones para evaluar el plano de control con salidas JSONL del plano de medios.

## Dataset de prueba inicial

La matriz `detections_3` usa como entrada:

```text
../../../../e-ovrt_control-plane/tests/generator/detections_3.jsonl
```

Ese archivo corresponde al clip `video6bis`, con detecciones `person`, `helmet` y `vest`, y fue elegido como primer input estable para comparar parametros del plano de control.

## Directorios

- `patterns/cr01_cr02/`: variantes de patrones CR-01 y CR-02.
- `replay/detections_3/`: configs de replay que apuntan al mismo input y a cada variante de patrones.
- `experiments/detections_3/matrix.yaml`: matriz declarativa de experimentos.
- `results/detections_3/`: resumen versionable de resultados. Los artefactos completos de replay quedan ignorados en `runs/`.

## Ejecucion

Desde la raiz del workspace:

```bash
e-ovrt_control-plane/.venv/bin/eovrt-control replay \
  e-ovrt_experimental-setup/control-plane/replay/detections_3/baseline.yaml
```

Para ejecutar toda la matriz, correr cada YAML dentro de `control-plane/replay/detections_3/`.

