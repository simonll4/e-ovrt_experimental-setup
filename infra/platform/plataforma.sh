#!/usr/bin/env bash
# Plataforma E-OVRT: levanta lo que falte y verifica que todo este listo para ejecutar
# cualquier cosa en ella (corridas, experimentos, la demo, la evidencia).
#
#   infra/platform/plataforma.sh [up]            asegura la plataforma (default)
#   infra/platform/plataforma.sh estado          solo mira y informa; no cambia nada
#   infra/platform/plataforma.sh construir [svc...] [--con-media] [--recrear]
#                                                reconstruye imagenes (con guarda de disco)
#   infra/platform/plataforma.sh bajar           detiene todo SIN borrar contenedores
#
# Opciones de `up`:  --modelo <instancia>   (default mp-gdino-tiny-560, el campeon)
#                    --sin-modelo           no activa ninguna instancia de modelo
#                    --sin-motor-fresco     no reinicia el motor para dejarlo "fresco"
#                    --forzar               sigue aunque falte memoria / haya una sesion en curso
#
# Que hace `up`, en orden: Docker responde -> recursos (disco C:, memoria de WSL) -> nucleo
# (mosquitto, control-plane, distribution, console: arranca los que existen, crea los que faltan,
# espera "healthy") -> consola -> instancia del modelo activa y lista -> motor "fresco" -> chequeos
# de la plataforma y de la demo. Termina con un resumen y exit 0 solo si todo esta en verde.
#
# Reglas que respeta (doc 133 §5.5 y la memoria del proyecto):
#  * NUNCA `docker compose up -d` a secas: el .env trae COMPOSE_PROFILES=models y arrancaria los
#    9 modelos juntos (OOM de la VM de WSL). Aca siempre se nombran los servicios.
#  * Nunca recrea un contenedor que ya existe: arranca el existente. Recrear es explicito
#    (`construir ... --recrear`) y, en la Victus, se hace en la preparacion, no el dia de la demo.
#  * Un solo modelo a la vez (lo garantiza la consola al activar).
#  * Ningun build del media-plane sin >= 35 GB libres en C: (los discos virtuales crecen sobre C:).
set -uo pipefail

CONSOLA="${EOVRT_CONSOLE_URL:-http://localhost:8090}"
MODELO="${EOVRT_MODELO:-mp-gdino-tiny-560}"
PROYECTO="eovrt"
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$DIR/../.." && pwd)"
WORKSPACE="$(cd "$REPO/.." && pwd)"
NUCLEO=(mosquitto control-plane distribution console)   # orden de arranque

DISCO_MIN_GB=8        # por debajo: aviso; por debajo de DISCO_CRITICO_GB: no se crea ni se carga nada
DISCO_CRITICO_GB=4
DISCO_BUILD_GB=8      # build liviano (consola, control, distribucion)
DISCO_BUILD_MEDIA_GB=35
RAM_MIN_MB=2500       # disponible en la VM de WSL para cargar un modelo

FALLAS=0
AVISOS=0
ok()   { echo "  ✓ $*"; }
av()   { echo "  ! $*"; AVISOS=$((AVISOS + 1)); }
fa()   { echo "  ✗ $*"; FALLAS=$((FALLAS + 1)); }
paso() { echo; echo "== $*"; }
muere() { echo "  ✗ $*" >&2; exit 2; }

imagen_de() {
  case "$1" in
    mosquitto) echo "eclipse-mosquitto:2" ;;
    console|control-plane|distribution) echo "eovrt/$1:latest" ;;
    mp-*) echo "eovrt/media-plane:latest" ;;
    *) echo "" ;;
  esac
}
contenedor() { echo "$PROYECTO-$1-1"; }
estado_contenedor() { docker inspect -f '{{.State.Status}}' "$(contenedor "$1")" 2>/dev/null || echo ausente; }
salud_contenedor() { docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}sin-healthcheck{{end}}' "$(contenedor "$1")" 2>/dev/null || echo ausente; }

compose() {
  # Con Docker Desktop, EOVRT_WORKSPACE es la ruta de la VM de Docker (/run/desktop/mnt/host/c/...),
  # que WSL no ve: compose corre en un contenedor con el workspace montado ahi (como compose.ps1).
  local ws_docker
  ws_docker="$(grep -E '^EOVRT_WORKSPACE=' "$DIR/.env" | head -1 | cut -d= -f2-)"
  if [ -d "$ws_docker/e-ovrt_experimental-setup" ]; then
    (cd "$DIR" && docker compose "$@")
  else
    docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v "$WORKSPACE:$ws_docker" \
      -w "$ws_docker/e-ovrt_experimental-setup/infra/platform" docker:cli compose "$@"
  fi
}

api() {  # api METODO RUTA [TIMEOUT_S]  -> cuerpo por stdout; exit 22 si HTTP>=400, 7 si no responde
  python3 - "$1" "$CONSOLA$2" "${3:-30}" <<'PY'
import sys, urllib.error, urllib.request
metodo, url, espera = sys.argv[1], sys.argv[2], float(sys.argv[3])
pedido = urllib.request.Request(url, method=metodo, data=b"" if metodo == "POST" else None)
try:
    sys.stdout.write(urllib.request.urlopen(pedido, timeout=espera).read().decode())
except urllib.error.HTTPError as e:
    sys.stdout.write(e.read().decode()); sys.exit(22)
except Exception as e:
    sys.stderr.write(str(e)); sys.exit(7)
PY
}
campo() { python3 -c "import json,sys; d=json.load(sys.stdin); print(eval(sys.argv[1], {}, {'d': d}))" "$1" 2>/dev/null; }

disco_libre_gb() { [ -d /mnt/c ] && df -B1M /mnt/c 2>/dev/null | awk 'NR==2{printf "%d", $4/1024}'; }
ram_libre_mb() { awk '/MemAvailable/{printf "%d", $2/1024}' /proc/meminfo 2>/dev/null; }

# ---------------------------------------------------------------------------------------------
verificar_docker() {
  paso "Docker"
  if ! docker info >/dev/null 2>&1; then
    muere "Docker no responde. Abri Docker Desktop (y revisa Settings > Resources > WSL integration). Si ningun puerto responde: Inicio -> Reiniciar Windows."
  fi
  ok "Docker $(docker version --format '{{.Server.Version}}' 2>/dev/null) responde"
}

verificar_recursos() {
  paso "Recursos"
  local d r
  d="$(disco_libre_gb)"; r="$(ram_libre_mb)"
  if [ -z "$d" ]; then av "no se ve /mnt/c: no se puede medir el disco (el que importa es C:)"
  elif [ "$d" -lt "$DISCO_CRITICO_GB" ]; then fa "C: con $d GB libres (< $DISCO_CRITICO_GB): no se crea ni se carga nada hasta liberar espacio"
  elif [ "$d" -lt "$DISCO_MIN_GB" ]; then av "C: con $d GB libres (< $DISCO_MIN_GB): justo; los discos virtuales de Docker/WSL crecen sobre C:"
  else ok "C: con $d GB libres"; fi
  [ -n "$r" ] && ok "memoria disponible en la VM de WSL: ${r} MB"
}

esperar_saludable() {  # esperar_saludable SERVICIO [SEGUNDOS]
  local s="$1" t="${2:-120}" i
  for ((i = 0; i < t; i += 2)); do
    case "$(salud_contenedor "$s")" in healthy|sin-healthcheck) return 0 ;; esac
    sleep 2
  done
  return 1
}

levantar_nucleo() {
  paso "Nucleo (mosquitto, control-plane, distribution, console)"
  local s ausentes=() creados=()
  for s in "${NUCLEO[@]}"; do
    case "$(estado_contenedor "$s")" in
      running) ok "$s: corriendo" ;;
      ausente)
        if docker image inspect "$(imagen_de "$s")" >/dev/null 2>&1; then ausentes+=("$s")
        else fa "$s: no existe el contenedor ni la imagen $(imagen_de "$s") -> infra/platform/plataforma.sh construir $s"; fi ;;
      *) echo "  · $s: arrancando el contenedor existente"; docker start "$(contenedor "$s")" >/dev/null && creados+=("$s") ;;
    esac
  done
  if [ "${#ausentes[@]}" -gt 0 ]; then
    av "faltan contenedores (${ausentes[*]}): se CREAN con compose, nombrandolos. Hacelo en la preparacion, no el dia de la demo."
    if compose up -d --no-build "${ausentes[@]}" >/dev/null 2>&1; then creados+=("${ausentes[@]}")
    else fa "compose no pudo crear: ${ausentes[*]}"; fi
  fi
  for s in "${NUCLEO[@]}"; do
    [ "$(estado_contenedor "$s")" = ausente ] && continue
    if esperar_saludable "$s" 120; then
      [[ " ${creados[*]-} " == *" $s "* ]] && ok "$s: healthy"
    else
      fa "$s: no quedo healthy en 120 s (docker logs $(contenedor "$s"))"
    fi
  done
  # Un contenedor creado con una imagen anterior a la actual no recoge un build nuevo.
  for s in "${NUCLEO[@]}"; do
    local cid iid
    cid="$(docker inspect -f '{{.Image}}' "$(contenedor "$s")" 2>/dev/null || true)"
    iid="$(docker image inspect -f '{{.Id}}' "$(imagen_de "$s")" 2>/dev/null || true)"
    if [ -n "$cid" ] && [ -n "$iid" ] && [ "$cid" != "$iid" ]; then
      av "$s corre con una imagen anterior a la construida: aplicarla con  plataforma.sh construir $s --recrear"
    fi
  done
}

esperar_consola() {
  paso "Consola ($CONSOLA)"
  local i
  for ((i = 0; i < 120; i += 2)); do
    api GET /api/health 5 >/dev/null 2>&1 && { ok "la consola responde"; return 0; }
    sleep 2
  done
  fa "la consola no respondio en 120 s. Si ningun puerto responde: Inicio -> Reiniciar Windows."
  return 1
}

asegurar_modelo() {
  paso "Instancia de modelo: $MODELO"
  local lista fila ready target
  lista="$(api GET /api/platform/instances 20 2>/dev/null)" || { fa "no pude leer /api/platform/instances"; return 1; }
  fila="$(printf '%s' "$lista" | campo "[i for i in d if i['name']=='$MODELO']")"
  if [ -z "$fila" ] || [ "$fila" = "[]" ]; then
    fa "$MODELO no esta en el fleet: $(printf '%s' "$lista" | campo "', '.join(i['name'] for i in d)")"
    return 1
  fi
  ready="$(printf '%s' "$lista" | campo "[i for i in d if i['name']=='$MODELO'][0]['ready']")"
  target="$(printf '%s' "$lista" | campo "[i for i in d if i['name']=='$MODELO'][0]['is_target']")"
  if [ "$ready" = True ] && [ "$target" = True ] && [ "$(estado_contenedor "$MODELO")" = running ]; then ok "$MODELO ya es el target y esta listo"; return 0; fi

  if [ "$(estado_contenedor "$MODELO")" = ausente ]; then
    if ! docker image inspect "$(imagen_de "$MODELO")" >/dev/null 2>&1; then
      fa "falta la imagen $(imagen_de "$MODELO") -> plataforma.sh construir media-plane --con-media (necesita >= $DISCO_BUILD_MEDIA_GB GB libres)"
      return 1
    fi
    av "$MODELO no existe: se CREA (sin arrancar) con compose. Hacelo en la preparacion, no el dia de la demo."
    compose --profile models create "$MODELO" >/dev/null 2>&1 || { fa "compose no pudo crear $MODELO"; return 1; }
  fi
  local d r
  d="$(disco_libre_gb)"; r="$(ram_libre_mb)"
  if [ -n "$d" ] && [ "$d" -lt "$DISCO_CRITICO_GB" ] && [ "$FORZAR" != 1 ]; then
    fa "C: con $d GB libres: no cargo el modelo (--forzar para seguir igual)"; return 1
  fi
  if [ -n "$r" ] && [ "$r" -lt "$RAM_MIN_MB" ] && [ "$FORZAR" != 1 ]; then
    fa "solo ${r} MB de memoria disponible en WSL (< $RAM_MIN_MB): cargar un modelo puede tirar la VM (--forzar para seguir igual)"
    return 1
  fi
  echo "  · activando $MODELO (la consola apaga cualquier otro modelo y espera readyz; hasta ~5 min)..."
  local salida
  if salida="$(api POST "/api/platform/instances/$MODELO/activate" 340 2>&1)"; then
    ok "activa: $(printf '%s' "$salida" | campo "d.get('model_ref')")"
  else
    fa "no se pudo activar $MODELO: $(printf '%s' "$salida" | head -c 300)"; return 1
  fi
}

reiniciar_motor() {
  echo "  · reiniciando el motor (~20-30 s) para dejarlo fresco..."
  api POST /api/demo/motor/reiniciar 30 >/dev/null 2>&1 || { fa "la consola no acepto reiniciar el motor"; return 1; }
  local i estado
  for ((i = 0; i < 330; i += 2)); do
    sleep 2
    estado="$(api GET /api/demo/state 10 2>/dev/null | campo 'd["motor"]["estado"]')"
    [ "$estado" = fresco ] && { ok "motor fresco"; return 0; }
    [ "$estado" = error ] && { fa "el reinicio del motor fallo"; return 1; }
  done
  fa "el motor no quedo fresco en 330 s"; return 1
}

asegurar_motor_fresco() {
  paso "Motor fresco (lo pide la demo: una corrida con la OAK-D por vida del proceso, F-101.5)"
  local estado fase sesion
  estado="$(api GET /api/demo/state 10 2>/dev/null | campo 'd["motor"]["estado"]')"
  [ "$estado" = fresco ] && { ok "el motor ya esta fresco"; return 0; }
  fase="$(api GET /api/demo/state 10 2>/dev/null | campo 'd["fase"]')"
  sesion="$(api GET /api/demo/preflight 20 2>/dev/null | campo "[i['estado'] for i in d['items'] if i['id']=='sesion'][0]")"
  if [ "$FORZAR" != 1 ] && { [ "$sesion" != ok ] || [[ "$fase" =~ ^(preparing|live|finishing|rendering)$ ]]; }; then
    av "hay una sesion o un experimento en curso (fase=$fase): no reinicio el motor (--forzar para hacerlo igual)"
    return 0
  fi
  reiniciar_motor
}

verificar_plataforma() {
  paso "Chequeo de la plataforma (/api/preflight)"
  local pf bloqueos
  pf="$(api GET /api/preflight 30 2>/dev/null)" || { fa "no pude leer /api/preflight"; return 1; }
  if [ "$(printf '%s' "$pf" | campo 'd["ready"]')" = True ]; then
    ok "lista: motor $(printf '%s' "$pf" | campo "(d['media'].get('model') or {}).get('ref')"), control y distribucion respondiendo"
  else
    bloqueos="$(printf '%s' "$pf" | campo "'; '.join(d['blockers'])")"
    fa "no lista: $bloqueos"
  fi
}

verificar_demo() {
  paso "Chequeo de la demo (/api/demo/preflight)"
  local pf
  pf="$(api GET /api/demo/preflight 30 2>/dev/null)" || { fa "no pude leer /api/demo/preflight"; return 1; }
  printf '%s' "$pf" | python3 -c "
import json, sys
d = json.load(sys.stdin)
for i in d['items']:
    marca = {'ok': '✓', 'aviso': '!', 'error': '✗'}.get(i['estado'], '?')
    extra = ' -> ' + i['accion'] if i.get('accion') and i['estado'] != 'ok' else ''
    print(f\"  {marca} {i['nombre']}: {i['detalle']}{extra}\")
"
  if [ "$(printf '%s' "$pf" | campo 'd["listo"]')" = True ]; then ok "la demo puede iniciarse (la tecla I funciona)"
  else fa "la demo todavia no puede iniciarse"; fi
  local host_estado
  host_estado="$(printf '%s' "$pf" | campo "[i['estado'] for i in d['items'] if i['id']=='host'][0]")"
  [ "$host_estado" != ok ] && av "el chequeo del host es el de la PC de la demo con la OAK-D: infra/demo/demo.sh check (no bloquea la tecla I)"
  return 0
}

resumen() {
  paso "Resumen"
  local s
  for s in "${NUCLEO[@]}" "$MODELO"; do
    printf '  %-28s %s (%s)\n' "$(contenedor "$s")" "$(estado_contenedor "$s")" "$(salud_contenedor "$s")"
  done
  echo
  if [ "$FALLAS" -eq 0 ]; then
    echo "  PLATAFORMA LISTA ($AVISOS aviso(s))  ·  consola: $CONSOLA/#/demo   (P = proyeccion)"
    return 0
  fi
  echo "  NO ESTA LISTA: $FALLAS falla(s), $AVISOS aviso(s). Revisa los ✗ de arriba."
  echo "  Para dejarla lista:  infra/platform/plataforma.sh up"
  return 1
}

# ---------------------------------------------------------------------------------------------
cmd_up() {
  verificar_docker
  verificar_recursos
  levantar_nucleo
  esperar_consola || { resumen; return 1; }
  [ "$SIN_MODELO" = 1 ] || asegurar_modelo
  [ "$SIN_MOTOR" = 1 ] || [ "$SIN_MODELO" = 1 ] || asegurar_motor_fresco
  if [ "$SIN_MODELO" != 1 ] && [ "$(estado_contenedor "$MODELO")" = running ]; then
    esperar_saludable "$MODELO" 120 || av "$MODELO no quedo healthy en 120 s (docker logs $(contenedor "$MODELO"))"
  fi
  verificar_plataforma
  verificar_demo
  resumen
}

cmd_estado() {
  verificar_docker
  verificar_recursos
  paso "Contenedores"
  local s
  for s in "${NUCLEO[@]}"; do
    case "$(estado_contenedor "$s")" in
      running) case "$(salud_contenedor "$s")" in healthy|sin-healthcheck) ok "$s: corriendo ($(salud_contenedor "$s"))" ;; *) av "$s: corriendo pero $(salud_contenedor "$s")" ;; esac ;;
      ausente) fa "$s: no existe" ;;
      *) fa "$s: $(estado_contenedor "$s")" ;;
    esac
  done
  api GET /api/health 5 >/dev/null 2>&1 || { fa "la consola no responde en $CONSOLA"; resumen; return 1; }
  paso "Modelos"
  api GET /api/platform/instances 20 2>/dev/null | python3 -c "
import json, sys
for i in json.load(sys.stdin):
    if i['state'] == 'running' or i['is_target']:
        print('  ' + ('★' if i['is_target'] else '·') + f\" {i['name']}: {i['state']}{' listo' if i['ready'] else ''}\")
" || av "no pude leer las instancias"
  verificar_plataforma
  verificar_demo
  resumen
}

cmd_construir() {
  local servicios=() CON_MEDIA=0 RECREAR=0 a
  for a in "$@"; do
    case "$a" in
      --con-media) CON_MEDIA=1 ;;
      --recrear) RECREAR=1 ;;
      *) servicios+=("$a") ;;
    esac
  done
  [ "${#servicios[@]}" -eq 0 ] && servicios=(console control-plane distribution)
  verificar_docker
  local d minimo="$DISCO_BUILD_GB" s
  for s in "${servicios[@]}"; do
    case "$s" in media-plane|mp-*) minimo="$DISCO_BUILD_MEDIA_GB"; [ "$CON_MEDIA" = 1 ] || muere "el media-plane pesa 13 GB y duplica capas: agregá --con-media (necesita >= $DISCO_BUILD_MEDIA_GB GB libres en C:)" ;; esac
  done
  d="$(disco_libre_gb)"
  if [ -n "$d" ] && [ "$d" -lt "$minimo" ]; then muere "C: con $d GB libres; este build necesita >= $minimo GB. Libera espacio (o compacta los vhdx) antes."; fi
  echo "  C: libres antes: ${d:-?} GB — construyendo: ${servicios[*]}"
  compose build "${servicios[@]}" || muere "el build fallo"
  echo "  C: libres despues: $(disco_libre_gb) GB"
  if [ "$RECREAR" = 1 ]; then
    echo "  recreando SOLO: ${servicios[*]} (en la Victus recrear tira a veces la red de WSL: si ningun puerto responde, Inicio -> Reiniciar)"
    compose up -d --no-build "${servicios[@]}"
  else
    echo "  imagen lista. Para que la use el contenedor:  plataforma.sh construir ${servicios[*]} --recrear   (o recrear a mano)"
  fi
}

cmd_bajar() {
  verificar_docker
  if [ "$FORZAR" != 1 ] && api GET /api/health 5 >/dev/null 2>&1; then
    local sesion
    sesion="$(api GET /api/demo/preflight 20 2>/dev/null | campo "[i['estado'] for i in d['items'] if i['id']=='sesion'][0]")"
    [ -n "$sesion" ] && [ "$sesion" != ok ] && muere "hay una sesion o un experimento en curso: terminalo antes (o --forzar)"
  fi
  paso "Deteniendo (sin borrar contenedores)"
  local c
  for c in $(docker ps --format '{{.Names}}' | grep -E "^$PROYECTO-mp-" || true); do docker stop "$c" >/dev/null && ok "$c detenido"; done
  for s in console distribution control-plane mosquitto; do
    [ "$(estado_contenedor "$s")" = running ] && docker stop "$(contenedor "$s")" >/dev/null && ok "$s detenido"
  done
  echo "  Para volver:  infra/platform/plataforma.sh up"
}

# ---------------------------------------------------------------------------------------------
CMD="up"; SIN_MODELO=0; SIN_MOTOR=0; FORZAR=0
if [ $# -gt 0 ] && [[ "$1" != --* ]]; then CMD="$1"; shift; fi
RESTO=()
while [ $# -gt 0 ]; do
  case "$1" in
    --modelo) MODELO="${2:?--modelo necesita un nombre de instancia}"; shift ;;
    --sin-modelo) SIN_MODELO=1 ;;
    --sin-motor-fresco) SIN_MOTOR=1 ;;
    --forzar) FORZAR=1 ;;
    -h|--help) CMD=ayuda ;;
    *) RESTO+=("$1") ;;
  esac
  shift
done

case "$CMD" in
  up) cmd_up ;;
  estado) cmd_estado ;;
  construir) cmd_construir "${RESTO[@]+"${RESTO[@]}"}" ;;
  bajar) cmd_bajar ;;
  ayuda|help) sed -n '2,19p' "$0" ;;
  *) echo "comando desconocido: $CMD" >&2; sed -n '2,19p' "$0" >&2; exit 2 ;;
esac
