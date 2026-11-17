# Las curvas del ajuste fino

Los `results.csv` de Ultralytics de los dos tramos del ajuste fino, tal como salieron de Mendieta. Los originales
viven en `finetuning/weights/finetuned/full-<job>/`, que git ignora junto con los pesos: se copian acá, byte a byte,
para que la figura 9 del informe se dibuje desde el repositorio público. El ajuste fino no se vuelve a entrenar.

| Archivo | Job | Tramo | sha256 (el mismo que el original) |
|---|---|---|---|
| `t1_full-1167640.results.csv` | `1167640` | T1: proyección de clases de YOLOE-26s, 10 épocas | `f70fd0b5217aa73dadf1795232ac2b47656edd38e564a7d25d24d20a3d2284c8` |
| `t2_full-1167982.results.csv` | `1167982` | T2: ajuste completo, SGD explícito, detención temprana en la época 16 | `046e1e0012ede727c5d0d00ee673b483b199f83a51f328d7e0df8fb96815bfe9` |

- El job intermedio `1167864` no está: no es un resultado (se corrigió antes de evaluar).
- Las métricas de validación de estos archivos son las de la partición de validación del ajuste, no las del banco
  congelado. Las cifras de la Tabla 55 del informe salen de las evaluaciones de `finetuning/runs/`, no de acá.
- La consola dibuja la figura con `results/evidence-vista/figuras.yaml` (figura 9, `grafico: curvas`), y
  `webconsole/tools/sacar_figuras.mjs` la guarda en esta carpeta como `figura-09-curvas-del-ajuste-fino.png`.
