#!/usr/bin/env bash
# Demo en vivo de la defensa — los mismos comandos que demo.ps1, desde WSL (bash).
# Spec: docs/superpowers/specs/2026-10-23-demo-defensa-design.md · manual: infra/demo/README.md
#
#   infra/demo/demo.sh up | check | smoke | camara-ensayo on|off | restart-motor
#                      | respaldo <sesion> | reset | down
#
# En la Victus el camino principal es PowerShell (demo.ps1). Este script existe porque el
# chequeo del host que mira WSL —memoria de la VM, disco real en /mnt/c, ruta a la cámara
# SIN `via`, ARP de la OAK-D— solo se ve desde adentro de WSL (spec §7.1).
# Nunca `docker compose up -d` que recree contenedores (doc 133 §5.5).
set -euo pipefail

CONSOLA="${EOVRT_CONSOLE_URL:-http://localhost:8090}"
MOTOR="mp-gdino-tiny-560"
PROYECTO="eovrt"
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$DIR/../.." && pwd)"
WORKSPACE="$(cd "$REPO/.." && pwd)"
PLATFORM="$REPO/infra/platform"
SESIONES="$REPO/defensa/sesiones"
NUCLEO=(mosquitto control-plane distribution console)
CAMARA_IP="169.254.31.137"
CAMARA_MAC="44:a9:2c:3f:9c:1e"

compose() {
  # Con Docker Desktop, EOVRT_WORKSPACE es la ruta de la VM de Docker
  # (/run/desktop/mnt/host/c/...), que WSL no ve: compose corre en un contenedor
  # con el workspace montado ahí, igual que infra/platform/compose.ps1.
  local ws_docker
  ws_docker="$(grep -E '^EOVRT_WORKSPACE=' "$PLATFORM/.env" | head -1 | cut -d= -f2-)"
  if [ -d "$ws_docker/e-ovrt_experimental-setup" ]; then
    (cd "$PLATFORM" && docker compose "$@")
  else
    docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v "$WORKSPACE:$ws_docker" \
      -w "$ws_docker/e-ovrt_experimental-setup/infra/platform" docker:cli compose "$@"
  fi
}
contenedor() { echo "$PROYECTO-$1-1"; }
estado_contenedor() { docker inspect -f '{{.State.Status}}' "$(contenedor "$1")" 2>/dev/null || echo ausente; }
api() {  # api METODO RUTA [JSON] [TIMEOUT]
  local args=(-sS -f -X "$1" "$CONSOLA$2" --max-time "${4:-30}")
  [ -n "${3:-}" ] && args+=(-H 'Content-Type: application/json' -d "$3")
  curl "${args[@]}"
}
campo() { python3 -c "import json,sys; d=json.load(sys.stdin); print(eval(sys.argv[1], {}, {'d': d}))" "$1"; }

esperar_consola() {
  for _ in $(seq 60); do api GET /api/health >/dev/null 2>&1 && return 0; sleep 2; done
  echo "la consola no respondió ($CONSOLA). Si ningún puerto responde: Inicio -> Reiniciar Windows." >&2
  return 1
}

restart_motor() {
  echo "Reiniciando el motor (~20-30 s) para dejarlo fresco..."
  api POST /api/demo/motor/reiniciar >/dev/null
  for _ in $(seq 165); do
    sleep 2
    local estado; estado="$(api GET /api/demo/state | campo 'd["motor"]["estado"]')"
    [ "$estado" = fresco ] && { echo "Motor fresco."; return 0; }
    [ "$estado" = error ] && { echo "el reinicio del motor falló" >&2; return 1; }
  done
  echo "el motor no quedó fresco a tiempo" >&2; return 1
}

up() {
  mkdir -p "$SESIONES"
  local ausentes=()
  for s in "${NUCLEO[@]}"; do
    case "$(estado_contenedor "$s")" in
      running) echo "  $s: corriendo" ;;
      ausente) ausentes+=("$s") ;;
      *) echo "  $s: arrancando el contenedor existente"; docker start "$(contenedor "$s")" >/dev/null ;;
    esac
  done
  if [ "${#ausentes[@]}" -gt 0 ]; then
    echo "AVISO: faltan contenedores (${ausentes[*]}): se CREAN con compose. Hacelo en la preparación, nunca el día de la demo." >&2
    compose up -d --no-build "${ausentes[@]}"
  fi
  esperar_consola
  echo "Activando $MOTOR (espera readyz)..."
  api POST "/api/platform/instances/$MOTOR/activate" "" 330 >/dev/null
  restart_motor
  echo "Listo: http://localhost:8090/demo (F11); después, demo.sh check."
}

check() {
  mkdir -p "$SESIONES"
  CAMARA_IP="$CAMARA_IP" CAMARA_MAC="$CAMARA_MAC" SESIONES="$SESIONES" MOTOR="$MOTOR" \
  NUCLEO="${NUCLEO[*]}" PROYECTO="$PROYECTO" python3 - <<'PY'
import datetime, json, os, shutil, subprocess

def sh(*cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=15).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""

ip, mac = os.environ["CAMARA_IP"], os.environ["CAMARA_MAC"]
chequeos = {}
mem_gb = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 2**30
chequeos["memoria_wsl"] = {"ok": mem_gb >= 9.5, "detalle": f"{mem_gb:.1f} GiB en la VM de WSL (doc 100: memory=10GB, swap=8GB en .wslconfig)"}
libre = shutil.disk_usage("/mnt/c").free / 2**30 if os.path.isdir("/mnt/c") else 0
chequeos["disco_c"] = {"ok": libre >= 8, "detalle": f"{libre:.1f} GB libres en /mnt/c (df -h / miente en WSL; mínimo 8)"}
zt = [l for l in sh("ip", "-br", "link").splitlines() if l.startswith("zt") and " UP " in f" {l} "]
chequeos["zerotier_caido"] = {"ok": not zt, "detalle": "ZeroTier arriba: bajarlo" if zt else "ok"}
ruta = sh("ip", "route", "get", ip)
chequeos["ruta_camara"] = {"ok": bool(ruta) and " via " not in f" {ruta} ", "detalle": ruta or "sin ruta (¿modo espejo?)"}
vecino = sh("ip", "neigh", "show", ip)
chequeos["arp_camara"] = {"ok": mac in vecino.lower(), "detalle": vecino or f"sin entrada ARP para {ip} (no se abre el dispositivo: F-101.5)"}
gpu = sh("nvidia-smi", "--query-gpu=name,memory.used,memory.total,temperature.gpu", "--format=csv,noheader")
chequeos["gpu"] = {"ok": bool(gpu), "detalle": gpu or "nvidia-smi no respondió"}
faltan = []
for s in os.environ["NUCLEO"].split() + [os.environ["MOTOR"]]:
    if sh("docker", "inspect", "-f", "{{.State.Status}}", f"{os.environ['PROYECTO']}-{s}-1") != "running":
        faltan.append(s)
chequeos["contenedores"] = {"ok": not faltan, "detalle": f"sin correr: {', '.join(faltan)}" if faltan else "núcleo y motor corriendo"}
datos = {
    "generado_en": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "origen": "demo.sh check (WSL)",
    "kernel": sh("uname", "-r"),
    "gpu": gpu,
    "docker": sh("docker", "version", "--format", "{{.Server.Platform.Name}} {{.Server.Version}}"),
    "chequeos": chequeos,
}
destino = os.path.join(os.environ["SESIONES"], "preflight_host.json")
with open(destino, "w", encoding="utf-8") as fh:
    json.dump(datos, fh, ensure_ascii=False, indent=2)
for k, c in chequeos.items():
    print(f"{'OK' if c['ok'] else 'XX'}  {k} — {c['detalle']}")
print(f"-> {destino}")
PY
}

camara_ensayo() {
  case "${1:-}" in
    on) compose -f docker-compose.yml -f docker-compose.demo.yml up -d --no-build mediamtx ensayo-camara
        echo "Cámara de ensayo: rtsp://mediamtx:8554/ensayo (host: rtsp://127.0.0.1:8554/ensayo)" ;;
    off) compose -f docker-compose.yml -f docker-compose.demo.yml stop ensayo-camara mediamtx ;;
    *) echo "uso: demo.sh camara-ensayo on|off" >&2; return 2 ;;
  esac
}

smoke() {
  camara_ensayo on
  sleep 5
  [ "$(api GET /api/demo/preflight | campo 'd["listo"]')" = True ] || { echo "chequeo previo en rojo: ver /demo" >&2; return 1; }
  local sid; sid="$(api POST /api/demo/start '{"variante": "ensayo"}' 60 | campo 'd["session_id"]')"
  echo "Sesión $sid: esperando el primer cuadro..."
  for _ in $(seq 90); do [ "$(api GET /api/demo/state | campo 'd["fase"]')" = live ] && break; sleep 1; done
  echo "Esperando un CR-01 confirmado y su mensaje en el broker (hasta 90 s)..."
  local cr01=""
  for _ in $(seq 90); do
    cr01="$(api GET /api/demo/state | campo 'next(c for c in d["condiciones"] if c["condicion"]=="CR-01")["alertas"] >= 1 and next(c for c in d["condiciones"] if c["condicion"]=="CR-01")["broker"] == "recibido"')"
    [ "$cr01" = True ] && break; sleep 1
  done
  api POST /api/demo/finish >/dev/null
  local fase=""
  for _ in $(seq 90); do fase="$(api GET /api/demo/state | campo 'd["fase"]')"; [[ "$fase" =~ ^(done|failed)$ ]] && break; sleep 2; done
  local video; video="$(api GET "/api/demo/sessions/$sid" | campo 'bool((d.get("resumen") or {}).get("video"))')"
  camara_ensayo off
  echo "CR-01 confirmado y en el broker: $cr01 | sesión: $fase | video: $video"
  echo "Resultado: $CONSOLA/demo/resultado/$sid"
  [ "$cr01" = True ] && [ "$fase" = done ] && [ "$video" = True ] && echo "SMOKE G1 EN VERDE" || { echo "SMOKE G1 EN ROJO" >&2; return 1; }
}

case "${1:-help}" in
  up) up ;;
  check) check ;;
  smoke) smoke ;;
  camara-ensayo) camara_ensayo "${2:-}" ;;
  restart-motor) restart_motor ;;
  respaldo) [ -n "${2:-}" ] || { echo "uso: demo.sh respaldo <session_id>" >&2; exit 2; }
            api POST "/api/demo/sessions/$2/respaldo" >/dev/null && echo "Respaldo nivel 1 (tecla R): $2" ;;
  reset) docker restart "$(contenedor control-plane)" "$(contenedor distribution)" >/dev/null
         esperar_consola && restart_motor ;;
  down) compose stop && echo "Stack detenido (los contenedores quedan: el próximo up no los recrea)." ;;
  native-up|native-down)
    echo "La Victus no tiene entorno nativo (doc 133 §6): el respaldo nativo de la spec (D-3) no aplica."
    echo "Respaldo: nivel 1 (tecla R), nivel 2 (grabación del ensayo) y el plan B de cámara (camara-ensayo)." ;;
  *) sed -n '2,11p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//' ;;
esac
