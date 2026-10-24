"""Throughput de la OAK-D sin modelo: cuántos cuadros por segundo llegan al proceso,
con qué antigüedad y cuánto cuesta convertirlos a BGR. Mismo pipeline que OakDSource
(ColorCamera.video → XLinkOut, cola de host maxSize=1 no bloqueante).

    python3.11 oakd_throughput.py <ip> <fps> <isp_num> <isp_den> <segundos>
"""
from __future__ import annotations

import statistics as st
import sys
import time

import depthai as dai


def main() -> int:
    ip, fps = sys.argv[1], float(sys.argv[2])
    isp = (int(sys.argv[3]), int(sys.argv[4]))
    seconds = float(sys.argv[5])

    pipeline = dai.Pipeline()
    cam = pipeline.create(dai.node.ColorCamera)
    cam.setResolution(dai.ColorCameraProperties.SensorResolution.THE_1080_P)
    cam.setFps(fps)
    if isp != (1, 1):
        cam.setIspScale(*isp)
    xout = pipeline.create(dai.node.XLinkOut)
    xout.setStreamName("rgb")
    cam.video.link(xout.input)

    with dai.Device(pipeline, dai.DeviceInfo(ip)) as device:
        queue = device.getOutputQueue(name="rgb", maxSize=1, blocking=False)
        for _ in range(20):  # warm-up, como warmup_frames
            queue.get()
        ages, convs, sizes = [], [], []
        t0 = time.monotonic()
        n = 0
        while time.monotonic() - t0 < seconds:
            msg = queue.get()
            ages.append((dai.Clock.now() - msg.getTimestamp()).total_seconds() * 1000)
            c0 = time.perf_counter()
            frame = msg.getCvFrame()
            convs.append((time.perf_counter() - c0) * 1000)
            sizes.append(len(msg.getData()))
            n += 1
        elapsed = time.monotonic() - t0
    h, w = frame.shape[:2]
    mbps = sum(sizes) * 8 / elapsed / 1e6
    print(f"fps_cfg={fps:g} isp={isp[0]}/{isp[1]} frame={w}x{h} recibidos={n} en {elapsed:.1f}s "
          f"-> {n / elapsed:.1f} fps, {mbps:.0f} Mbit/s | antigüedad p50={st.median(ages):.0f} ms "
          f"p95={sorted(ages)[int(0.95 * (len(ages) - 1))]:.0f} ms | getCvFrame p50={st.median(convs):.1f} ms")
    return 0


if __name__ == "__main__":
    sys.exit(main())
