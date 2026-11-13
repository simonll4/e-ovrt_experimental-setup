# Generación 2 — los resultados finales del informe

Esta carpeta tiene **los resultados que van al informe final**. Se generaron en la PC de la
demo (HP Victus, plataforma completa en contenedores Docker) con el driver
`tools/evidencia/`, prueba por prueba, a partir de los pre-registros de
`experiments/evidencia/<ID>/prueba.yaml`, escritos **antes** de correr.

Todo lo corrido antes (julio–septiembre de 2026), en la PC de desarrollo que se usó hasta contar
con la PC de la demo, es la **generación 1**: la validación inicial que eligió modelo,
granularidad y umbrales. Se conserva intacta en
`results/clip_bench/`, `results/bench_imagenes/`, `results/bench_nivel_a/` y `results/realtime/`,
y cada prueba de acá se compara contra ella.

## Cómo leer una prueba (`<ID>/`)

| Archivo | Qué tiene |
|---|---|
| `prueba.yaml` | el pre-registro, tal como estaba al correr |
| `resultado.json` | las métricas, un `resumen` legible y el veredicto contra la generación 1 (propuesto por el driver, confirmado por una persona) |
| `corridas.json` | cada experimento disparado por la consola: `experiment_id`, ids de las corridas de cada plano, estado, tiempos y huellas de las configs |
| `entorno.json` | dónde corrió: host, GPU, versiones, imágenes Docker, commit de cada repo |
| `comandos.txt` | lo que se ejecutó, en orden y con su hora |
| `evals/`, `logs/` | evaluaciones por clip o por estrato, salida de los scorers y un ejemplo de la configuración expandida que se envió |

`indice.json` resume todas las pruebas (lo lee la consola).

Las 45 pruebas que corrieron hasta las jornadas en vivo tienen carpeta acá, todas con su veredicto confirmado. Desde
la enmienda del 2026-10-30 (doc 134 §13.10), las siete de contraste (`ALR-03…06`, `IMG-02`, `IMG-03`, `PER-02`)
también se regeneran. Las pruebas en vivo (`RT-03…RT-09`) corrieron en dos jornadas, el 2026-11-01 y el 2026-11-07.
Tres quedaron parciales, firmadas con el motivo de lo que falta (`RT-03`, `RT-05` y `RT-09`; ver
`veredicto.confirmado.faltante` en su `resultado.json`).

El catálogo tiene 49, y las 49 tienen carpeta acá con su veredicto confirmado. `ALR-11…ALR-14` se pre-registraron el
2026-11-12, después de las jornadas (YOLOE-26s en los bancos de clips y la sensibilidad de la regla a sus umbrales),
corrieron ese mismo día y se firmaron el 2026-11-13. El 2026-11-12 también se corrigió la cifra de cuadros por segundo
de las pruebas en vivo: ahora se mide entre el primer y el último cuadro, y la anterior (sobre la duración entera de la
corrida, que incluye abrir y cerrar la cámara) queda al lado como `fps_sobre_duracion`.

## Carpetas que no son una prueba

| Carpeta | Qué es |
|---|---|
| `PLAT-01.hasta-F6`, `PLAT-01.cierre-F6`, `PLAT-01.F7-jornada-1` | versiones anteriores de `PLAT-01`, guardadas antes de volver a correrla (la consola se reconstruyó entre fases). La vigente es `PLAT-01/` |
| `INT-03.descartada-<fecha>` | la carpeta que el driver archiva cuando una prueba se vuelve a correr con `--forzar` porque su pre-registro cambió (acá, la huella de GDINO base pasó a la de la fuente). Queda como constancia y no cuenta en el índice |
| `_calibraciones/` | las calibraciones de encuadre de las pruebas en vivo, una por sesión de calibración |
| `_registro/` | los logs de las campañas y la constancia de `limpiar-rutas` |

## Tres veredictos posibles

- **idéntico**: mismos números, campo a campo, que la generación 1;
- **equivalente con diferencia declarada**: mismo insumo, otra máquina o pila; la diferencia se explica;
- **otra combinación**: cambió el insumo o la configuración; se muestra al lado, nunca en reemplazo.

Para el banco temporal la referencia es la generación 1 **re-evaluada con el GT corregido**
(revisión dirigida del 2026-10-26): así la comparación aísla el cambio de máquina del cambio
de referencia.
