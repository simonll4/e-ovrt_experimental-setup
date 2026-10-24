# OAK-D en el deploy Docker sobre WSL — manual de conexión

Para quien levanta la plataforma completa (`infra/platform`, los 13 servicios) en
**Docker sobre WSL2** y necesita que la **OAK-D Pro PoE** llegue a los contenedores del
media-plane, con la red de esos contenedores **saliendo a internet**.

> **Estado (2026-10-24).** Lo que está probado: la OAK-D desde WSL *nativo* en modo
> espejo (julio–agosto de 2026; ver `docs/operacion/68` §2.1) y, desde el 2026-10-24,
> **la OAK-D desde un contenedor** con Docker Desktop: pasos 2 a 8 OK (ver el historial
> del final). Si en otra máquina el paso 7 falla, la tabla de diagnóstico dice qué mirar.

---

## Cómo funciona (leer antes de tocar nada)

```
  OAK-D 169.254.31.137 ──cable── inyector PoE ──cable── Ethernet de la notebook
                                                         (Windows le pone 169.254.x.x sola)
                                                        Wi-Fi de la notebook ── internet

  Windows ══ modo espejo ══ WSL: ve las MISMAS interfaces que Windows
                             ├─ ethN 169.254.x.x/16  → ruta directa a la cámara
                             └─ Wi-Fi                → ruta por defecto (internet)

  Docker: red `eovrt_eovrt` (bridge, los 13 servicios)
          └─ sale por NAT con las rutas del host:
               169.254.0.0/16 → Ethernet → OAK-D
               todo lo demás   → Wi-Fi    → internet
```

- **No hay que crear una red nueva.** La red de los servicios ya existe: es `eovrt`
  del `docker-compose.yml` (Docker la llama `eovrt_eovrt`). Es una red *bridge*: los
  contenedores salen hacia afuera por NAT —a internet y a la cámara— usando las rutas
  del host, y desde afuera solo entra lo que publica `ports:`.
- **La cámara solo necesita tráfico saliente desde el contenedor:** TCP 11490 (XLink,
  los cuadros) y UDP 11491 (la consulta a la IP de la cámara). Las dos atraviesan el NAT.
- **Lo que NO atraviesa el NAT es el *discovery* por broadcast.** Por eso la conexión es
  siempre **por IP fija** (`dai.DeviceInfo(ip)`), que es justo lo que hace `OakDSource`.
- **Por qué no `macvlan` ni `network_mode: host`:** `macvlan` necesita un enlace de
  capa 2 real y las interfaces de WSL son virtuales; `host` rompe los nombres de
  servicio que usa la plataforma (el control-plane consume `tcp://<servicio-mp>:5557`
  por la red interna).

---

## Requisitos

| Qué | Cómo se comprueba |
|---|---|
| Windows 11 22H2 o posterior | `winver` |
| WSL 2.0.0 o posterior | `wsl --version` (PowerShell) |
| Docker Desktop 4.26 o posterior, motor WSL 2 | `docker version` → la línea `Server: Docker Desktop 4.xx` |
| GPU NVIDIA con driver de Windows al día | paso 4 (con Docker Desktop **no** hace falta `nvidia-container-toolkit`) |
| Repos hermanos clonados bajo `EOVRT_WORKSPACE` | `infra/platform/README.md` §Bootstrap |
| El Dockerfile del media-plane instala `.[gpu,edge]` | `grep -n 'gpu,edge' e-ovrt_media-plane/infra/docker/Dockerfile` tiene que mostrar una línea |
| OAK-D Pro PoE, inyector PoE 802.3af (o switch PoE), dos cables Ethernet | — |
| Notebook con Ethernet (o adaptador USB-Ethernet) **y** Wi-Fi | — |

La IP de la cámara del laboratorio es **`169.254.31.137`**. Si tu OAK-D es otra unidad,
primero el [anexo](#anexo-si-la-oak-d-no-es-la-del-laboratorio).

---

## Paso 1 — Conexión física

1. Ethernet de la notebook → puerto **DATA IN** del inyector.
2. Puerto **PoE OUT** del inyector → OAK-D. Invertidos, la cámara no enciende.
3. **Directo, sin router ni switch con DHCP en el medio.** Si hay DHCP, Windows toma una
   IP de otra red y `169.254.31.137` queda inalcanzable.
4. El Wi-Fi queda conectado: es la salida a internet. **No hace falta apagarlo ni fijar
   ninguna IP a mano.**
5. Esperá a que bootee: entre 10 y 40 s después de darle energía.

## Paso 2 — Windows: la Ethernet toma `169.254.x.x` sola

Sin servidor DHCP, Windows le asigna a la Ethernet una IP del rango link-local
`169.254.0.0/16`, el mismo de la cámara. En PowerShell:

```powershell
Get-NetIPAddress -AddressFamily IPv4 | Where-Object IPAddress -like '169.254.*' |
    Format-Table InterfaceAlias, IPAddress, PrefixLength
ping 169.254.31.137
```

Tiene que aparecer la Ethernet (puede llamarse `Ethernet 2`, etc.) con `169.254.x.x` y
prefijo `16`, y el ping tiene que responder. Si la Ethernet quedó con una IP fija de
antes, volvela a automática: **Configuración → Red e Internet → Ethernet → Asignación
de IP → Editar → Automática (DHCP)**.

> El ping es solo un primer filtro: hay casos en que la cámara responde al ping con la
> aplicación caída (F-101.6). La prueba que vale es la del paso 7.

## Paso 3 — WSL en modo espejo

En modo NAT (el default de WSL), WSL no ve la Ethernet y **la cámara no se alcanza**.
El modo espejo hace que WSL vea las interfaces de Windows tal cual.

1. Creá o editá `C:\Users\<tu-usuario>\.wslconfig` (el nombre exacto: sin `.txt` al final):

   ```ini
   [wsl2]
   networkingMode=mirrored
   ```

   No agregues `hostAddressLoopback=true`: con Docker Desktop hay reportes de que no
   arranca con esa combinación.

2. Aplicalo. **`wsl --shutdown` mata todo lo que esté corriendo en WSL**, contenedores
   incluidos:
   - Docker Desktop → ícono de la bandeja → **Quit Docker Desktop**.
   - PowerShell: `wsl --shutdown`, esperá unos 10 s.
   - Abrí la terminal de Ubuntu y después iniciá Docker Desktop.

3. Comprobalo **dentro de WSL**:

   ```bash
   wslinfo --networking-mode          # → mirrored
   ip -br addr | grep 169.254         # → una interfaz ethN con 169.254.x.x/16
   ip route get 169.254.31.137        # → "dev ethN src 169.254.x.x", SIN "via"
   ping -c1 169.254.31.137            # → ttl=64
   ```

> **Trampa del ping en WSL:** si `ip route get` dice `via 172.x.x.1` y el ping responde
> con `ttl=63`, seguís en NAT. Ese "ping OK" lo contesta el gateway de Windows, no la
> cámara. Volvé al punto 1 y revisá el archivo; si aparece vacío, se truncó y hay que
> reescribirlo.

## Paso 4 — Docker Desktop

En **Settings**:

- **General** → *Use the WSL 2 based engine*: activado.
- **Resources → WSL integration** → activado para tu distro (Ubuntu). Sin esto, dentro
  de WSL `docker` responde *"could not be found in this WSL 2 distro"*.

Comprobá la versión y la GPU desde WSL:

```bash
docker version | grep -i 'docker desktop'            # 4.26 o posterior
docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi
```

## Paso 5 — Imagen del media-plane con DepthAI

La fuente `oak_d` necesita el SDK DepthAI v2 **dentro** de la imagen. El Dockerfile lo
instala con el extra `edge` (`.[gpu,edge]`), fijado en `constraints.txt` a
`depthai==2.32.0.0`, la misma versión que funcionó en nativo. Sin él, el plugin se
anuncia `available: false` y cualquier corrida con OAK-D devuelve 422.

```bash
cd "$EOVRT_WORKSPACE/e-ovrt_experimental-setup/infra/platform"
cp -n .env.example .env       # y poné EOVRT_WORKSPACE = raíz ABSOLUTA del workspace
docker compose build mp-mock  # construye eovrt/media-plane:latest, que comparten todos los mp-*
docker compose run --rm --no-deps mp-mock python3.11 -c "import depthai; print(depthai.__version__)"
# → 2.32.0.0
```

Si construiste la imagen antes de este cambio, alcanza con volver a correr `build`: el
paso de `pip install` cambió y Docker lo rehace.

## Paso 6 — La red `eovrt` y su salida a internet

```bash
docker compose up -d
docker network inspect eovrt_eovrt \
  --format 'driver={{.Driver}} internal={{.Internal}} subred={{(index .IPAM.Config 0).Subnet}}'
# → driver=bridge internal=false subred=172.x.0.0/16

docker compose run --rm --no-deps mp-mock \
  curl -sS -o /dev/null -w 'internet: HTTP %{http_code}\n' https://huggingface.co
# → internet: HTTP 200
```

Tres reglas para que siga así:

- **Nunca `internal: true`** en la red: corta internet **y** la cámara.
- **Nunca `network_mode: host`** en los `mp-*`: rompe los nombres de servicio.
- La subred de Docker no puede pisar `169.254.0.0/16` ni la red de tu casa u oficina.
  Docker usa `172.x` por default; si choca, se cambia `default-address-pools` en la
  configuración del daemon (Docker Desktop → Settings → Docker Engine).

## Paso 7 — La OAK-D desde dentro del contenedor (la prueba que vale)

`oakd_probe.py` abre la cámara por IP desde un contenedor `mp-mock`: misma imagen y
misma red que las instancias reales, pero sin GPU, así que una falla acá es de red o de
cámara, nunca del modelo.

```bash
cd "$EOVRT_WORKSPACE/e-ovrt_experimental-setup/infra/platform"
docker compose run --rm --no-deps -T mp-mock python3.11 - 169.254.31.137 < oakd_probe.py
```

Salida esperada (con la cámara del laboratorio):

```
depthai 2.32.0.0 → conectando a 169.254.31.137 (tarda ~10 s)...
conectada en 9.4 s: OAK-D-PRO-POE 194430105168741300
OK: cuadro 320x180 recibido.
```

Ignorá los avisos `USB protocol not available…` y `DeprecationWarning: … UsbSpeed`: la
PoE no usa USB. Si falla, el script imprime `FALLA:` y una `PISTA:`; seguí con la
[tabla de diagnóstico](#diagnóstico).

**Una sola conexión a la vez:** si hay un media-plane nativo, otra instancia `mp-*` o
una grabación usando la cámara, la prueba falla aunque la red esté bien.

## Paso 8 — Preset de cámara y primera corrida

`cameras/` está en `.gitignore` (ahí van credenciales RTSP), así que el preset no viene
con el clon. Creá `e-ovrt_experimental-setup/cameras/oak_d_lab.yaml`:

```yaml
camera:
  id: oak_d_lab
  name: OAK-D laboratorio
  plugin: oak_d
  config:
    url: 169.254.31.137   # la clave es `url`, NO `ip` (con `ip` el servicio devuelve 422)
    isp_scale: [1, 2]     # 960x540: 1080p no entra por la red de WSL (ver §Rendimiento)
    fps: 5                # debajo del ritmo de gdino-tiny-560: sin cola, G2A p50 ~150 ms
```

Corrida corta contra `mp-mock`, directo a la API del servicio (30 cuadros, sin GPU):

```bash
docker compose up -d mp-mock
docker compose exec -T mp-mock curl -s localhost:8080/api/catalog/ingest-plugins \
  | grep -o '"id":"oak_d","kind":"live","available":[a-z]*'
# → "id":"oak_d","kind":"live","available":true

docker compose exec -T mp-mock curl -s -X POST localhost:8080/api/runs \
  -H 'Content-Type: application/json' -d @- <<'EOF'
{"ingest": {"plugin": "oak_d", "config": {"url": "169.254.31.137", "isp_scale": [1, 2], "fps": 5, "warmup_frames": 20}},
 "prompts": {"set_inline": {"id": "smoke", "classes": [{"id": "person", "phrasings": {"default": ["person"]}}]},
             "active_ids": ["person"]},
 "run": {"name": "oakd_docker_smoke", "max_units": 30}}
EOF
# → {"run_id":"<id>"}

docker compose exec -T mp-mock curl -s localhost:8080/api/runs/<id>
# → "status":"succeeded" (si dice failed, el campo error explica por qué)
```

Después de **cada** corrida con la OAK-D, reiniciá la instancia antes de la siguiente
(`docker compose restart mp-mock`, o apagar y encender desde **Plataforma** en la
consola). Al detener la *segunda* corrida OAK-D de una misma vida del servicio, depthai
puede tirar abajo el proceso (F-101.5, `docs/operacion/101`).

Con esto andando, el resto se hace desde la consola (`http://localhost:8090`):
**Plataforma** para activar el modelo, **Cámaras** para el preset y **Nueva corrida**
con la cámara OAK-D.

> **`experiments/ebe_oakd_live` no sirve tal cual en Docker.** Es del setup nativo:
> rutas absolutas de otra máquina y el bus en `tcp://127.0.0.1:5557`. En el compose el
> control-plane consume `tcp://<servicio-mp>:5557` (README §Endpoints y buses). La
> cadena viva completa —control, distribución y broker— está en el paso 4 del smoke del
> README y queda fuera de este manual.
>
> ✎ 2026-10-24: la cadena viva completa con la OAK-D en Docker se corrió con
> `experiments/oakd_docker_live` (endpoints con nombres de servicio y MQTT a `mosquitto`),
> lanzado desde **Experimentos → Ejecutar** en la consola.

## Rendimiento: resolución y fps en Docker

**Config recomendada: 960x540 (`isp_scale: [1, 2]`) a 5 fps**, la del preset del paso 8.
Medida el 2026-10-24 con gdino-tiny-560 en la RTX 4060, notebook con cargador:

| Cámara | Inferencia p50 | Captura→host p50 | G2A p50 / p95 | Procesados/recibidos |
|---|---|---|---|---|
| 1080p @30 (el default de antes) | 193 ms | 961 ms | 435 / 540 ms | 77 % |
| 960x540 @8 | 150 ms | 77 ms | 334 / 417 ms | 74 % |
| **960x540 @5** | **147 ms** | **66 ms** | **150–154 / 273–449 ms** | **100 %** |
| 640x360 @5 | 145 ms | 47 ms | 149 / 472 ms | 100 % |
| Imágenes (referencia, sin cámara) | 140–145 ms | — | — | — |

Por qué:

- **La red de WSL en modo espejo corta en ~200 Mbit/s.** La misma cámara entrega
  507 Mbit/s a Windows nativo (1080p a 20 fps) y ~190 Mbit/s al contenedor (7.6 fps);
  con `--network host` da lo mismo, así que no es la NAT de Docker. 1080p@30 en NV12 pide
  ~750 Mbit/s: los cuadros se encolan en la cámara y llegan con ~1 s de atraso. 960x540
  @5 son ~31 Mbit/s.
- **Mandar más cuadros de los que el modelo procesa no suma:** en vivo el productor lee
  y prepara cada cuadro aunque después se descarte, y lo que sobra espera en la cola. Con
  gdino-tiny-560 (~150 ms por cuadro) el techo es ~6 cuadros/s; a 5 fps se procesan todos
  y el G2A es captura + inferencia. A 8 o 12 fps se procesa casi lo mismo con el doble de
  G2A. **Para otro modelo, ajustar `fps` a su ritmo:** más bajo para gdino-base, más
  alto para los YOLOE chicos.
- **No se pierde resolución útil:** gdino-560 reescala a 560 px de lado largo, así que
  960x540 y 1080p le llegan igual (560x315). 960 en vez de 640 deja margen para las
  variantes gdino de 800 px y para la vista previa. La confianza de `person` con persona
  en cuadro fue 0.78 (960x540) contra 0.77 (1080p).
- **Con batería todo empeora:** la primera corrida a 1080p@30 dio 330 ms de inferencia a
  batería y 193 ms con cargador. Medir y demostrar siempre enchufado.
- **El G2A p95 sigue arriba del presupuesto de 250 ms** (273–449 ms entre corridas
  iguales): lo fijan la cola de la inferencia (p95 ~200 ms) y picos sueltos, no la cámara.
- **La observación no le compite a la inferencia** (corregido el 2026-10-24):
  - El runner de experimentos de la consola consultaba el estado sin pausa: ~100 GET/s
    al media-plane durante toda la corrida, y la inferencia en vivo subía de ~150 a
    ~200 ms. Ahora consulta cada 1 s (`EOVRT_CONSOLE_EXPERIMENT_POLL_INTERVAL_S`).
  - Las previews (`save_previews`) se dibujaban y escribían en el hilo de inferencia
    antes de publicar la detección al control: ~19 ms por cuadro en el bind mount de
    Windows. Ahora las escribe un hilo aparte con cola acotada; si se atrasa, descarta
    la preview y nunca frena la inferencia.
  - La vista en vivo de la consola en el navegador no afecta (medido: 143 ms con la
    página abierta).

Para medir el enlace sin modelo (fps que llegan, Mbit/s, antigüedad del cuadro):

```bash
docker compose run --rm --no-deps -v "$PWD/oakd_throughput.py:/tmp/t.py:ro" mp-mock \
  python3.11 /tmp/t.py 169.254.31.137 <fps> 1 <divisor isp> 12   # p. ej. 5 1 2
```

Corre igual con Python en Windows (`depthai==2.32.0.0`, `numpy`, `opencv-python-headless`)
para comparar contra el nativo.

---

## Diagnóstico

| Síntoma | Causa probable | Qué hacer |
|---|---|---|
| Windows no muestra ninguna `169.254.x.x` | Cable, inyector invertido o IP fija vieja en la Ethernet | Paso 1 y paso 2 |
| En WSL, `ip route get` dice `via 172.x…` y el ping da `ttl=63` | WSL sigue en NAT | Paso 3: revisá `.wslconfig` y repetí el `wsl --shutdown` |
| `docker` *could not be found* dentro de WSL | Falta la integración WSL de Docker Desktop | Paso 4 |
| Prueba: `esta imagen no tiene depthai` · corrida: 422 *plugin no disponible* | Imagen construida sin el extra `edge` | Paso 5: rebuild |
| Prueba: `Cannot find any device with given deviceInfo`, con WSL OK (paso 3) | El tráfico del contenedor no llega a la cámara | (1) `internal=false` en el paso 6. (2) Docker Desktop reiniciado **después** del `wsl --shutdown`. (3) Probar el firewall de Hyper-V (abajo). (4) Si sigue, avisar con la salida de los pasos 3, 6 y 7 |
| Prueba: `Failed to find device after booting` | IP equivocada (¿la de fábrica, `169.254.1.222`?) o cámara colgada | La IP sale del preset, nunca del ping. Power-cycle: desenchufar el PoE 10 s |
| Conecta pero no llegan cuadros, o el log muestra `ping was missed, closing the device connection` | La aplicación de la cámara se cayó (F-101.6); el ping sigue respondiendo igual | Power-cycle de la OAK-D |
| Mensaje con `ALREADY_IN_USE` o `already` | Otro proceso tiene la cámara | Cerrar el otro cliente; una conexión a la vez |
| Corrida OAK-D con `capture_to_host` ~1 s y la mitad de los cuadros descartados | 1080p (o fps alto) satura la red de WSL, o la notebook está a batería | Preset del paso 8 (960x540 a 5 fps) y cargador; ver §Rendimiento |
| El media-plane muere (SIGABRT) al detener una corrida OAK-D | F-101.5: segunda corrida OAK-D en la misma vida del servicio | Reiniciar la instancia entre corridas (paso 8) |
| Cámara OK pero sin internet en el contenedor | DNS, VPN o subred de Docker que pisa la de tu red | Probar `curl` desde WSL; si WSL sale y el contenedor no, cambiar `default-address-pools` (paso 6) |
| La consola no abre en `localhost:8090` desde Windows | Fricción conocida entre Docker y el modo espejo | Probar `http://127.0.0.1:8090` y reiniciar Docker Desktop; si persiste, ver la fila siguiente |
| **Ningún** puerto publicado responde (8090, 8081, 8082), y dentro de WSL tampoco anda un servidor cualquiera por `127.0.0.1` | Se cayó el adaptador de Windows que rebota el loopback del modo espejo (`vEthernet (FSE HostVnic)`) | **Inicio → Reiniciar**. Ni `wsl --shutdown`, ni reiniciar Docker, ni **Apagar** (con Inicio rápido reanuda el mismo estado) lo levantan. Ver abajo cómo confirmarlo |

**Prueba del firewall de Hyper-V.** En modo espejo, WSL (y con él el motor de Docker
Desktop) queda detrás del firewall de Hyper-V. Para descartarlo, en PowerShell como
administrador, permitir la entrada, repetir el paso 7 y **revertir siempre**:

```powershell
Set-NetFirewallHyperVVMSetting -Name '{40E0AC32-46A5-438A-A0B2-2B479E8F2E90}' -DefaultInboundAction Allow
# ...repetir el paso 7...
Set-NetFirewallHyperVVMSetting -Name '{40E0AC32-46A5-438A-A0B2-2B479E8F2E90}' -DefaultInboundAction NotConfigured
```

Si con eso funciona, avisá: hay que reemplazarlo por una regla acotada a la cámara en
vez de dejar la entrada abierta.

**Loopback del modo espejo caído (adaptador FSE).** En modo espejo, todo el TCP a
`127.0.0.1` dentro de WSL (incluso de Linux a Linux) sale por `loopback0` hacia Windows
(`ip route get 127.0.0.1` → `via 169.254.73.152 dev loopback0`) y Windows lo rebota por
el adaptador oculto `vEthernet (FSE HostVnic)`. Docker Desktop publica los puertos sobre
ese loopback, así que si el adaptador se cae, no responde ningún puerto, aunque los
contenedores estén `healthy` y la red interna ande. Para confirmarlo sin permisos de
administrador:

```powershell
Get-WinEvent -LogName 'Microsoft-Windows-Hyper-V-VmSwitch-Operational' -MaxEvents 3000 |
  Where-Object { $_.Message -match 'FSE' -and $_.Id -in 124,125 } |
  Format-Table TimeCreated, Id -AutoSize
(Get-CimInstance Win32_OperatingSystem).LastBootUpTime   # fecha del último arranque COMPLETO
```

Un `124` ("restarted") sin un `125` ("Media connected") después es la falla. El
2026-10-24 pasó en medio de una sesión: tres reinicios del adaptador en 30 s, justo al
recrear el contenedor de la consola. Solo lo arregló **Inicio → Reiniciar**. Con
**Apagar**, el Inicio rápido de Windows hiberna y restaura el núcleo y la red, y
`LastBootUpTime` no cambia. `Restart-Service hns -Force` (como administrador) debería
alcanzar, pero no se probó. No es la red de la cámara: con el cable desenchufado y con
la Ethernet en `/24` falló igual, y después del reinicio anduvo con `169.254.x.x/16`.

---

## Si usás Docker Engine dentro de WSL (sin Docker Desktop)

Los pasos son los mismos; el NAT lo hace el kernel de WSL con iptables. Además:

```bash
sysctl net.ipv4.ip_forward                                  # → 1
sudo iptables -t nat -S POSTROUTING | grep MASQUERADE       # → una regla con la subred de eovrt_eovrt
grep -s iptables /etc/docker/daemon.json                    # no puede decir "iptables": false
```

La GPU necesita `nvidia-container-toolkit` instalado en la distro. Este camino tampoco
está verificado con la OAK-D.

## Anexo: si la OAK-D no es la del laboratorio

Una OAK PoE nueva trae IP fija de fábrica `169.254.1.222` (no DHCP). Está en el mismo
rango, así que este esquema le sirve igual: usá esa IP en el preset y en la prueba.
Para averiguar la IP de una unidad desconocida, hacé el discovery **desde Windows**
(el broadcast no cruza ni WSL ni Docker):

```powershell
py -m pip install "depthai>=2.24,<3"
py -c "import depthai as dai; [print(d.name, d.getMxId(), d.state) for d in dai.Device.getAllAvailableDevices()]"
```

`d.name` es la IP. **Usá depthai v2 (`<3`), nunca v3:** mezclar v2 y v3 contra la misma
cámara la deja inconsistente y no vuelve a bootear (`json.exception.type_error.302`).

La cámara del laboratorio **ya no está en `169.254.1.222`**, aunque esa IP siga
respondiendo al ping: ahí depthai falla con `Failed to find device after booting`.

---

## Notas para quien revise

- **Cambios en el repo que acompañan este manual:** el Dockerfile del media-plane pasa
  de `.[gpu]` a `.[gpu,edge]`; `constraints.txt` fija `depthai==2.32.0.0` y
  `blobconverter==1.4.3`; nuevo `infra/platform/oakd_probe.py`.
- **Prefilter EN-2 (opcional, apagado por default):** dentro del contenedor la ruta
  relativa de `prefilter.model_blob` se resuelve contra el directorio del paquete
  instalado y no encuentra el archivo. Si se activa, hay que pasar la absoluta
  `/app/models/edge/person-detection-retail-0013_6shave.blob` (los modelos se montan en
  `/app/models`). No probado.
- **La grabación OAK-D desde la consola no anda en Docker:** la imagen de la consola no
  trae depthai (`EOVRT_CONSOLE_OAKD_PYTHON`). Para grabar, usar el camino nativo.

## Historial de verificación

- **2026-10-24 — escrito.** Verificado: `depthai 2.32.0.0` y `blobconverter 1.4.3`
  resuelven contra `constraints.txt` para Python 3.11 / manylinux (resolución de pip en
  seco), y `oakd_probe.py` corrido en nativo con la cámara desconectada devuelve el error
  y la pista correctos. **Sin verificar:** el build de la imagen con `edge` y los pasos
  6 a 8 con la cámara. La primera corrida completa de este manual es el **G0** de la spec
  de la demo (`docs/superpowers/specs/2026-10-23-demo-defensa-design.md`).
- **2026-10-24 — primera vez OK desde un contenedor (G0).** Windows 11 (26200), WSL
  2.5.9 en modo espejo, Docker Desktop 4.91.0 (motor 29.8.0), RTX 4060 Laptop. Imagen
  `eovrt/media-plane:latest` construida desde el `main` del media-plane con `.[gpu,edge]`
  (más el paso de CLIP de YOLOE), `depthai 2.32.0.0` dentro. Compose corrido desde
  Windows con el wrapper `compose.ps1` (`docker:cli compose`; para el paso 7 se le pasó
  el script por stdin con `docker run -i`).
  - Paso 2: Ethernet `Up 1 Gbps` con `169.254.1.100/16` (IP fija, no APIPA: también
    sirve, está en el mismo `/16`); ping a `169.254.31.137` con `TTL=64`.
  - Paso 3: `wslinfo` → `mirrored`; `eth1 169.254.1.100/16`; `ip route get` →
    `169.254.31.137 dev eth1 src 169.254.1.100`, sin `via`; ping `ttl=64`.
  - Paso 6: `driver=bridge internal=false subred=172.20.0.0/16`; `internet: HTTP 200`.
  - Paso 7: `conectada en 7.5 s: OAK-D-PRO-POE 194430105168741300` →
    `OK: cuadro 320x180 recibido.` Con la cámara desenchufada, la misma prueba da
    `Cannot find any device with given deviceInfo` con la pista de red.
  - Paso 8: `oak_d` `available:true` en `mp-mock`; corrida
    `run_20261024_182609_dbe_mock_9cbb5f` (`oakd_docker_smoke`) `succeeded`: 30/30
    unidades, 0 fallidas, 0 descartadas, 15.7 s, `capture_to_host` p50 795 ms / p95
    872 ms. `mp-mock` se apagó después de la corrida.
  - No hizo falta tocar el firewall de Hyper-V. **Sin probar:** la cadena viva completa
    (control, distribución, broker) con la OAK-D y una corrida con un modelo GPU.
- **2026-10-24 — cadena viva completa y config de rendimiento.** `oakd_docker_live` con
  gdino-tiny-560 a 1080p@30: media, control y distribución `succeeded`, 5 alertas
  (4 CR-01, 1 CR-02), 2 entregadas por MQTT y 3 suprimidas por cooldown; pero 330 ms de
  inferencia (a batería), ~1 s de captura→host y 52 % de cuadros descartados. El
  diagnóstico y la matriz de configs están en §Rendimiento; el preset y el experimento
  pasan a 960x540 a 5 fps.
- **2026-10-24 — cadena viva completa con la config nueva y los arreglos.**
  `oakd_docker_live` (960x540 a 5 fps, gdino-tiny-560, consola con poll de 1 s,
  previews en hilo aparte), `ok: true`:

  | Corrida | Inferencia p50/p95 | G2A p50/p95 | Captura→host p50 | Procesados |
  |---|---|---|---|---|
  | Inicial (1080p@30, a batería) | 330 / 487 ms | 618 / 806 ms | 1020 ms | 121/250 |
  | Config nueva, sin los arreglos | 193 / 243 ms | 468 / 585 ms | 67 ms | 281/300 |
  | **Config nueva + arreglos** | **146 / 201 ms** | **148 / 285 ms** | **69 ms** | **300/300** |

  Control: 300 unidades por el bus, 0 perdidas, 3 alertas (2 CR-02, 1 CR-01).
  Distribución: 3 entregadas por MQTT, notificación p95 15 ms. CPU de la consola
  durante la corrida: 2 % (antes 50 %); GET al media-plane: ~200 en 3 min (antes ~25.000
  en 4 min). 300 previews escritas sin errores. El reporte consolidado de las corridas
  con `isp_scale` fallaba (`effective_config.yaml` con `!!python/tuple`, ilegible para
  `yaml.safe_load`); corregido en el media-plane. Corrida de verificación con la imagen
  corregida (`exp_20261024T201936Z_oakd_docker_live`): `ok: true`, reporte consolidado
  generado con los cuatro hitos en verdadero, 2 alertas, t_capture→alert 5.8 s,
  notificación 4.5 ms. G2A p50 160 ms / p95 423 ms: la mediana se repite entre corridas,
  el p95 no (273–449 ms en corridas iguales), por picos sueltos de inferencia.
