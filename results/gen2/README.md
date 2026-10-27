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

Siete pruebas de contraste (`ALR-03…06`, `IMG-02`, `IMG-03`, `PER-02`) no tienen carpeta acá: no
se regeneran y su cifra vigente es la de la generación 1, escrita en su pre-registro
(`gen1.cifras`, con el motivo en `no_se_regenera`).

## Tres veredictos posibles

- **idéntico**: mismos números, campo a campo, que la generación 1;
- **equivalente con diferencia declarada**: mismo insumo, otra máquina o pila; la diferencia se explica;
- **otra combinación**: cambió el insumo o la configuración; se muestra al lado, nunca en reemplazo.

Para el banco temporal la referencia es la generación 1 **re-evaluada con el GT corregido**
(revisión dirigida del 2026-10-26): así la comparación aísla el cambio de máquina del cambio
de referencia.
