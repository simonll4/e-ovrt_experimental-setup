"""Prueba de la OAK-D desde DENTRO de un contenedor del fleet media-plane.

Abre la cámara por IP (TCP unicast, igual que OakDSource) y espera un cuadro.
Es la prueba que vale: el ping miente (el gateway de WSL en NAT, o la pila PoE
con la aplicación de la cámara caída — F-101.6). Ver MANUAL-OAKD-WSL.md.

Uso (desde infra/platform, el script entra por stdin porque la imagen no lo trae):

    docker compose run --rm --no-deps -T mp-mock python3.11 - 169.254.31.137 < oakd_probe.py

Exit 0 = cuadro recibido. Cualquier otro exit trae una pista del motivo.
"""
from __future__ import annotations

import sys
import time

DEFAULT_IP = "169.254.31.137"  # la del preset cameras/oak_d_lab.yaml, NUNCA la de fábrica
FRAME_TIMEOUT_S = 20.0

# Mensaje de depthai -> causa probable. El orden importa: el primero que matchea.
_HINTS = (
    (("after booting",),
     "Alcanzó el bootloader pero no pudo reconectar: IP equivocada (¿la de fábrica "
     "169.254.1.222?) o cámara colgada → power-cycle de la OAK-D (desenchufar el PoE 10 s)."),
    (("already", "in_use"),
     "Otro proceso tiene la cámara (media-plane nativo, otra instancia mp-*, record_oakd). "
     "Una sola conexión a la vez."),
    (("cannot find", "not found", "not_found"),
     "No hay camino de red hasta la IP: revisá los pasos 2, 3 y 6 del manual "
     "(IP 169.254 en Windows, modo espejo en WSL, red del compose)."),
)


def main() -> int:
    ip = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_IP
    try:
        import depthai as dai
    except ImportError:
        print("FALLA: esta imagen no tiene depthai. Rebuild del media-plane con el "
              "Dockerfile que instala '.[gpu,edge]' (paso 5 del manual).")
        return 2
    print(f"depthai {dai.__version__} → conectando a {ip} (tarda ~10 s)...", flush=True)

    pipeline = dai.Pipeline()
    cam = pipeline.create(dai.node.ColorCamera)
    cam.setPreviewSize(320, 180)
    xout = pipeline.create(dai.node.XLinkOut)
    xout.setStreamName("rgb")
    cam.preview.link(xout.input)

    t0 = time.monotonic()
    try:
        with dai.Device(pipeline, dai.DeviceInfo(ip)) as device:
            print(f"conectada en {time.monotonic() - t0:.1f} s: "
                  f"{device.getDeviceName()} {device.getMxId()}", flush=True)
            queue = device.getOutputQueue("rgb", maxSize=1, blocking=False)
            deadline = time.monotonic() + FRAME_TIMEOUT_S
            while time.monotonic() < deadline:
                frame = queue.tryGet()
                if frame is not None:
                    print(f"OK: cuadro {frame.getWidth()}x{frame.getHeight()} recibido.")
                    return 0
                time.sleep(0.05)
            print(f"FALLA: conectó pero no llegó ningún cuadro en {FRAME_TIMEOUT_S:.0f} s. "
                  "Power-cycle de la OAK-D y repetir.")
            return 3
    except RuntimeError as exc:
        msg = str(exc)
        print(f"FALLA: {msg}")
        for needles, hint in _HINTS:
            if any(n in msg.lower() for n in needles):
                print(f"PISTA: {hint}")
                break
        return 1


if __name__ == "__main__":
    sys.exit(main())
