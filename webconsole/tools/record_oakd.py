#!/usr/bin/env python3
"""Graba la OAK-D a H.264 crudo usando el encoder por hardware del dispositivo.

Standalone a propósito: NO importa nada del webconsole y corre con el intérprete
que tenga el SDK DepthAI (el backend de la consola es 3.14 y depthai no publica
wheels para 3.14). Se puede correr a mano desde una terminal, que es el plan B
si la consola falla en obra:

    python record_oakd.py --device 192.168.1.50 --out toma.h264 --fps 60

Contrato con el proceso padre: una línea JSON por evento en stdout
({"event": "started"} / {"event": "finished", "bytes_written": N}) y corte
limpio con SIGTERM o SIGINT. Códigos de salida: 0 ok, 2 argumentos inválidos,
3 SDK ausente, 4 fallo del dispositivo.
"""

from __future__ import annotations

import argparse
import json
import signal
import sys

RESOLUTIONS = {"720p": "THE_720_P", "1080p": "THE_1080_P", "4k": "THE_4_K"}

_stop = False


def _emit(**payload) -> None:
    sys.stdout.write(json.dumps(payload) + "\n")
    sys.stdout.flush()


def _handle_stop(signum, frame) -> None:
    global _stop
    _stop = True


def _load_sdk():
    """Costura de import: permite inyectar un stub por PYTHONPATH en los tests."""
    import depthai

    return depthai


def _parse_args(argv):
    parser = argparse.ArgumentParser(description="Grabador OAK-D por hardware")
    parser.add_argument("--device", required=True, help="IP fija de la OAK-D PoE")
    parser.add_argument("--out", required=True, help="Archivo de salida (.h264 crudo)")
    parser.add_argument("--fps", type=int, default=60)
    parser.add_argument("--resolution", choices=sorted(RESOLUTIONS), default="1080p")
    parser.add_argument("--bitrate", type=int, default=25_000_000)
    parser.add_argument("--keyframe-hz", type=float, default=1.0, dest="keyframe_hz")
    parser.add_argument(
        "--warmup-ms", type=int, default=300, dest="warmup_ms",
        help=(
            "Frames descartados al arrancar el pipeline mientras el sensor "
            "converge exposicion/balance de blancos (verificado en el "
            "dry-run 2026-07-22: 9 de 60 frames, ~150 ms, salen "
            "subexpuestos si se escriben tal cual). 0 desactiva el descarte."
        ),
    )
    args = parser.parse_args(argv)
    if args.fps <= 0:
        parser.error("--fps debe ser > 0")
    if args.bitrate <= 0:
        parser.error("--bitrate debe ser > 0")
    if args.warmup_ms < 0:
        parser.error("--warmup-ms no puede ser negativo")
    return args


def _build_pipeline(dai, args):
    pipeline = dai.Pipeline()
    cam = pipeline.create(dai.node.ColorCamera)
    cam.setBoardSocket(dai.CameraBoardSocket.CAM_A)
    cam.setResolution(
        getattr(dai.ColorCameraProperties.SensorResolution, RESOLUTIONS[args.resolution])
    )
    cam.setFps(args.fps)

    encoder = pipeline.create(dai.node.VideoEncoder)
    # Keyframes ~1 s: el re-ventaneo de la etapa 0 con --ss/--to es exacto y barato
    # si hay keyframes cerca; con GOP largo ffmpeg corta mal o re-encodea.
    encoder.setDefaultProfilePreset(args.fps, dai.VideoEncoderProperties.Profile.H264_MAIN)
    encoder.setBitrate(args.bitrate)
    encoder.setKeyframeFrequency(max(1, int(round(args.fps / max(args.keyframe_hz, 0.01)))))
    cam.video.link(encoder.input)

    xout = pipeline.create(dai.node.XLinkOut)
    xout.setStreamName("h264")
    encoder.bitstream.link(xout.input)
    return pipeline


def main(argv=None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)

    try:
        dai = _load_sdk()
    except ImportError as exc:
        _emit(event="error", reason=f"SDK depthai no disponible: {exc}")
        return 3

    signal.signal(signal.SIGTERM, _handle_stop)
    signal.signal(signal.SIGINT, _handle_stop)

    written = 0
    discarded = 0
    seen = 0
    # Descarte por CANTIDAD de frames, no por reloj de pared: la convergencia
    # de exposicion/balance de blancos es un fenomeno del sensor que corre en
    # tiempo real, pero contar frames es lo que hace determinista el descarte
    # (y lo que permite testearlo con el stub sin simular latencia real).
    warmup_frames = round(args.fps * args.warmup_ms / 1000)
    try:
        pipeline = _build_pipeline(dai, args)
        device_info = dai.DeviceInfo(args.device)
        with dai.Device(pipeline, device_info) as device:
            queue = device.getOutputQueue("h264", maxSize=30, blocking=True)
            with open(args.out, "wb") as handle:
                _emit(event="started")
                while not _stop:
                    packet = queue.get()
                    if packet is None:
                        continue
                    data = packet.getData()
                    seen += 1
                    if seen <= warmup_frames:
                        # El sensor todavia converge exposicion/balance de
                        # blancos: se descarta sin escribir (ver --warmup-ms).
                        discarded += len(data)
                        continue
                    handle.write(data)
                    written += len(data)
                handle.flush()
    except Exception as exc:  # noqa: BLE001 - cualquier fallo del dispositivo
        _emit(event="error", reason=str(exc), bytes_written=written)
        return 4

    if written == 0:
        # La toma no sobrevivio ni al calentamiento (corte casi inmediato):
        # salir "finished" con un archivo vacio seria la misma falla
        # silenciosa que un master corrupto marcado sano.
        _emit(
            event="error",
            reason=(
                f"toma descartada entera: se vieron {seen} frames y "
                f"warmup_frames={warmup_frames} -- no llego a grabar ni un "
                "frame util"
            ),
            bytes_written=0,
            discarded_bytes=discarded,
        )
        return 5

    _emit(event="finished", bytes_written=written, discarded_bytes=discarded)
    return 0


if __name__ == "__main__":
    sys.exit(main())
