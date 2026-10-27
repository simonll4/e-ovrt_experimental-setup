"""Driver de la evidencia de la generación 2 (docs/operacion/134 del repo `docs`).

Cada prueba del catálogo (`experiments/evidencia/<ID>/prueba.yaml`) se pre-registra antes de
correr, se ejecuta por un único camino —el runner de experimentos de la consola
(`POST /api/experiments/run`)— y deja su carpeta en `results/gen2/<ID>/`.

Corre donde corre la consola: en el deploy Docker, dentro del contenedor `console` (ver
`infra/platform/evidencia.sh` / `.ps1`); en una PC con los servicios nativos, con el venv del
repo. Solo usa la biblioteca estándar, PyYAML y los scripts de medición de los repos hermanos.
"""
