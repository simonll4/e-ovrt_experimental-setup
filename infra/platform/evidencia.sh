#!/usr/bin/env bash
# Driver de evidencia de la generación 2 (doc 134): lo corre DENTRO del contenedor de la
# consola, que ve el workspace con paridad de rutas, habla con los servicios por la red del
# compose y tiene el docker CLI. Sirve en Git Bash (Windows) y en WSL.
#
#   infra/platform/evidencia.sh lista
#   infra/platform/evidencia.sh verificar F1 F3
#   infra/platform/evidencia.sh correr INT-01 INT-02 INT-03 PLAT-01 GT-01
#   infra/platform/evidencia.sh --fondo correr F3      # sigue aunque se cierre la terminal
#   infra/platform/evidencia.sh estado
#   infra/platform/evidencia.sh vivo RT-03 --toma t1 --config 960x540@5   (el rodaje RT-04: rodaje.ps1)
#   infra/platform/evidencia.sh veredicto ALR-01 identico --motivo "..." --quien "Nombre"
#
# Con --fondo la salida va a e-ovrt_experimental-setup/results/gen2/_registro/<hora>.log.
# El driver se retoma donde quedó: si se corta, se vuelve a lanzar el mismo comando.
set -euo pipefail

CONTENEDOR="${EOVRT_CONSOLE_CONTAINER:-eovrt-console-1}"
FONDO=0
if [ "${1:-}" = "--fondo" ]; then
  FONDO=1
  shift
fi
if [ $# -eq 0 ]; then
  sed -n '2,15p' "$0"
  exit 2
fi
if ! docker ps --format '{{.Names}}' | grep -qx "$CONTENEDOR"; then
  echo "el contenedor $CONTENEDOR no está corriendo: levantá la plataforma (infra/platform/README.md)" >&2
  exit 2
fi

# MSYS (Git Bash) convierte argumentos que parecen rutas; el driver no recibe rutas, pero por
# las dudas se desactiva para esta llamada.
export MSYS_NO_PATHCONV=1

if [ "$FONDO" = 1 ]; then
  HORA=$(date -u +%Y%m%dT%H%M%SZ)
  docker exec -d -e PYTHONDONTWRITEBYTECODE=1 "$CONTENEDOR" sh -c \
    'cd "$EOVRT_CONSOLE_REPO_ROOT" && mkdir -p results/gen2/_registro && exec python -m tools.evidencia "$@" > "results/gen2/_registro/$0.log" 2>&1' \
    "$HORA" "$@"
  echo "corriendo en segundo plano."
  echo "  log:      e-ovrt_experimental-setup/results/gen2/_registro/$HORA.log"
  echo "  progreso: $0 estado"
else
  exec docker exec -i -e PYTHONDONTWRITEBYTECODE=1 "$CONTENEDOR" sh -c \
    'cd "$EOVRT_CONSOLE_REPO_ROOT" && exec python -m tools.evidencia "$@"' sh "$@"
fi
