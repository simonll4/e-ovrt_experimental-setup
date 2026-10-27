"""DIST-01 dentro del contenedor `distribution`: alerta → PUBACK MQTT QoS 1.

Se ejecuta con `docker exec -i <contenedor> python3 - '<json de parámetros>' < este archivo`
(lo hace `tools.evidencia`; en nativo, con el Python del venv). Misma mecánica que
`tools/talert_campaign/workflows.run_live_series` y que la réplica del doc 133
(`datos/133-pc-demo/scripts/pcdemo_talert.py`): por corrida del corpus, un
`eovrt-distribute live` nuevo, un XPUB con el envelope `bus.envelope.v1` que espera las dos
suscripciones, las alertas con `ts_publish_ms` nuevo y el sentinela `run_finished`.

Diferencia deliberada con el doc 133: el ledger (`notifications.jsonl`) se escribe en el
disco del contenedor (`ledger_tmp`, ext4) y recién al final se copia al workspace — en el bind
mount de Windows una ráfaga acumula hasta 1,6 s (doc 133 §3.4). Solo usa lo que la imagen de
la distribución ya trae (pyzmq, msgpack, eovrt-distribute).
"""
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

import msgpack
import zmq

P = json.loads(sys.argv[1])
CORPUS = Path(P["corpus"])
SALIDA = Path(P["salida"])
TMP = Path(P["ledger_tmp"])
EP = P["endpoint"]
CFG = f"""notification_policy:
  cooldown_ms: 30000
  key: [condition_id, source_id]
channel:
  mode: live
  host: {P["broker_host"]}
  port: {P["broker_port"]}
  topic_prefix: eovrt/alerts
  qos: 1
retry:
  max_attempts: 3
  wait_ms: 500
"""


def envelope(topic, key, seq, payload):
    return msgpack.packb({"schema_version": "bus.envelope.v1", "topic": topic, "key": key,
                          "seq": seq, "ts_publish_ms": time.time() * 1000.0,
                          "payload": payload}, use_bin_type=True)


def publicar(run_id, alertas):
    sock = zmq.Context.instance().socket(zmq.XPUB)
    sock.setsockopt(zmq.SNDHWM, 1000)
    sock.setsockopt(zmq.LINGER, 0)
    sock.setsockopt(zmq.XPUB_VERBOSE, 1)
    sock.bind(EP)
    try:
        poller = zmq.Poller()
        poller.register(sock, zmq.POLLIN)
        limite = time.monotonic() + 5.0
        suscripciones = 0
        while suscripciones < 2 and time.monotonic() < limite:
            if dict(poller.poll(timeout=max(1, (limite - time.monotonic()) * 1000))):
                sock.recv()
                suscripciones += 1
        if suscripciones < 2:
            raise RuntimeError(f"{run_id}: {suscripciones}/2 suscripciones")
        seq = 0
        for a in alertas:
            topic = f"control.alert.v1.{run_id}"
            payload = json.dumps(a, ensure_ascii=True, separators=(",", ":")).encode()
            sock.send_multipart([topic.encode(), envelope(topic, str(a.get("source_id", run_id)), seq, payload)])
            seq += 1
        topic = f"run.lifecycle.v1.{run_id}"
        fin = json.dumps({"schema_version": "run.lifecycle.v1", "event": "run_finished",
                          "control_run_id": run_id, "status": "completed"}).encode()
        sock.send_multipart([topic.encode(), envelope(topic, run_id, seq, fin)])
        time.sleep(0.05)
    finally:
        sock.close(linger=0)


def main():
    if TMP.exists():
        shutil.rmtree(TMP)
    TMP.mkdir(parents=True)
    cfg = TMP / "distribution-live.yaml"
    cfg.write_text(CFG)
    corridas = json.loads(Path(P["runs"]).read_text())
    t0 = time.time()
    fallas = []
    for i, run_id in enumerate(corridas, 1):
        alertas = [json.loads(l) for l in (CORPUS / f"{run_id}.jsonl").read_text().splitlines() if l.strip()]
        proc = subprocess.Popen(
            ["eovrt-distribute", "live", "--endpoint", EP, "--control-run-id", run_id,
             "--config", str(cfg), "--out-dir", str(TMP / run_id), "--idle-timeout-ms", "10000"],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            publicar(run_id, alertas)
            _, err = proc.communicate(timeout=20)
            if proc.returncode != 0:
                fallas.append([run_id, proc.returncode, err.decode()[-300:]])
        except Exception as exc:  # noqa: BLE001
            proc.kill()
            proc.wait()
            fallas.append([run_id, "exc", str(exc)])
        if i % 50 == 0:
            print(f"{i}/{len(corridas)} {time.time() - t0:.0f}s", flush=True)
    SALIDA.mkdir(parents=True, exist_ok=True)
    for d in TMP.iterdir():
        if d.is_dir():
            shutil.copytree(d, SALIDA / d.name, dirs_exist_ok=True)
    (SALIDA / "_fallas.json").write_text(json.dumps(fallas, indent=1))
    print(f"FIN {len(corridas)} corridas en {time.time() - t0:.0f}s; fallas={len(fallas)}", flush=True)
    return 1 if fallas else 0


if __name__ == "__main__":
    sys.exit(main())
