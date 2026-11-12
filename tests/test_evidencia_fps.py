"""Cuadros por segundo del vivo, entre el primer y el último cuadro (corrección del 2026-11-12, doc 134 §13.22).

El `fps_effective` del media-plane divide los cuadros procesados por la duración ENTERA de la corrida, que en vivo
incluye abrir y cerrar la cámara: RT-04 daba 2,59 con la OAK-D entregando y el sistema procesando 5 cuadros por
segundo. «Cuadros por segundo procesados» se mide ahora con las marcas de captura, entre el primer y el último
cuadro; la cifra anterior queda al lado, con su nombre (`fps_sobre_duracion`).
"""
from __future__ import annotations

import json
from pathlib import Path

import yaml

from tools.evidencia import catalogo as cat
from tools.evidencia.entorno import REPO, Entorno
from tools.evidencia.familias import Contexto, vivo
from tools.evidencia.registro import Carpeta

T0 = 1_000_000  # reloj de pared de la primera captura (ms)


def _entorno(tmp_path: Path) -> Entorno:
    return Entorno(ws=tmp_path / "ws", repo=REPO, modo="docker", consola_url="http://consola",
                   datasets_medios="/e-ovrt_datasets")


def _corrida_media(ent: Entorno, run_id: str, *, n: int = 150, paso_ms: int = 200,
                   fps_effective: float = 2.5) -> None:
    """Una corrida en vivo: `n` cuadros cada `paso_ms` (150 × 200 ms = 30 s de cuadros) dentro de una corrida que,
    con la apertura y el cierre de la cámara, dura el doble (por eso `fps_effective` = 2,5)."""
    mr = ent.media_runs / run_id
    mr.mkdir(parents=True)
    (mr / "metrics.jsonl").write_text("".join(json.dumps({
        "unit_id": f"u{i}", "capture_wallclock_ms": T0 + paso_ms * i, "capture_monotonic_ns": i * paso_ms * 1_000_000,
        "capture_to_host_ms": 65.0, "g2a_ms": 150.0}) + "\n" for i in range(n)), encoding="utf-8")
    (mr / "summary.json").write_text(json.dumps({
        "units_processed": n, "units_dropped": 0, "fps_effective": fps_effective, "duration_seconds": 60.0}),
        encoding="utf-8")


def _ctx(ent: Entorno, catalogo: dict | None = None, **extra) -> Contexto:
    return Contexto(ent=ent, consola=None, catalogo=catalogo or {}, avisar=lambda *_: None, **extra)


def test_los_cuadros_por_segundo_se_miden_entre_el_primero_y_el_ultimo(tmp_path):
    ent = _entorno(tmp_path)
    _corrida_media(ent, "run_a")
    metricas = vivo._metricas_toma(_ctx(ent), "run_a")
    assert metricas["fps_efectivos"] == 5.0          # la cadencia procesada
    assert metricas["fps_sobre_duracion"] == 2.5      # la cifra anterior, con su nombre


def test_con_un_solo_cuadro_no_hay_cadencia(tmp_path):
    ent = _entorno(tmp_path)
    _corrida_media(ent, "run_b", n=1)
    assert vivo._metricas_toma(_ctx(ent), "run_b")["fps_efectivos"] is None


def _rt03(tmp_path: Path) -> cat.Prueba:
    carpeta = tmp_path / "cat" / "RT-03"
    carpeta.mkdir(parents=True)
    datos = {
        "schema": "prueba.gen2.v1", "id": "RT-03", "titulo": "latencia", "fase": "F7", "familia": "vivo",
        "gen1": {"result_id": "rodaje", "doc": "operacion/133", "relacion": "otra_combinacion", "motivo": "otra PC"},
        "veredictos_posibles": ["otra_combinacion"],
        "receta": {"instancia": "mp-gdino-tiny-560", "modelo": "grounding-dino/gdino-tiny-560",
                   "configs": {"960x540@5": {"camara": {"fps": 5}, "unidades": 300}},
                   "config_demo": "960x540@5"},
    }
    (carpeta / "prueba.yaml").write_text(yaml.safe_dump(datos, allow_unicode=True), encoding="utf-8")
    return cat.cargar_prueba(carpeta / "prueba.yaml")


def test_rt03_al_re_agregar_vuelve_a_medir_las_tomas_ya_registradas(tmp_path, monkeypatch):
    """Las tomas de RT-03 guardan sus métricas al correr: las del 2026-11-01 traen el `fps_effective` del media-plane
    como «fps_efectivos». `correr --reagregar` las vuelve a medir desde la corrida, sin repetir la toma."""
    monkeypatch.setenv("EOVRT_EVIDENCIA_SALIDA", str(tmp_path / "salida"))
    prueba = _rt03(tmp_path)
    ent = _entorno(tmp_path)
    _corrida_media(ent, "run_rt03")
    carpeta = Carpeta(ent, prueba)
    carpeta.preparar()
    (carpeta.dir / "tomas" / "lat_960_a").mkdir(parents=True)
    (carpeta.dir / "tomas" / "lat_960_a" / "series.json").write_text(json.dumps(
        {"g2a": [150.0], "captura_a_host": [65.0], "vidrio_a_resultado": [215.0]}), encoding="utf-8")
    carpeta.guardar_corrida("lat_960_a", {"estado": "ok", "config": "960x540@5", "media_run_id": "run_rt03",
                                          "metricas": {"contaminada": False, "fps_efectivos": 2.5}})

    vivo.correr(_ctx(ent, {"RT-03": prueba}, reagregar=True), prueba, carpeta)

    resultado = carpeta.leer("resultado.json")
    assert resultado["metricas"]["960x540@5"]["fps_efectivos"] == 5.0
    assert resultado["metricas"]["960x540@5"]["fps_sobre_duracion"] == 2.5
    fps = next(x for x in resultado["resumen"] if x["clave"] == "fps_efectivos")
    assert fps["valor"] == 5.0 and "entre el primer y el último cuadro" in fps["nombre"]
    # La toma queda registrada con la medición nueva (y la anterior, con su nombre).
    toma = carpeta.corridas()["lat_960_a"]["metricas"]
    assert (toma["fps_efectivos"], toma["fps_sobre_duracion"]) == (5.0, 2.5)


def test_rt03_una_toma_sin_su_corrida_en_disco_conserva_lo_registrado(tmp_path, monkeypatch):
    monkeypatch.setenv("EOVRT_EVIDENCIA_SALIDA", str(tmp_path / "salida"))
    prueba = _rt03(tmp_path)
    ent = _entorno(tmp_path)
    carpeta = Carpeta(ent, prueba)
    carpeta.preparar()
    (carpeta.dir / "tomas" / "lat_960_a").mkdir(parents=True)
    (carpeta.dir / "tomas" / "lat_960_a" / "series.json").write_text(json.dumps(
        {"g2a": [150.0], "captura_a_host": [65.0], "vidrio_a_resultado": [215.0]}), encoding="utf-8")
    carpeta.guardar_corrida("lat_960_a", {"estado": "ok", "config": "960x540@5", "media_run_id": "run_no_esta",
                                          "metricas": {"contaminada": False, "fps_efectivos": 3.9}})

    vivo.correr(_ctx(ent, {"RT-03": prueba}, reagregar=True), prueba, carpeta)

    assert carpeta.leer("resultado.json")["metricas"]["960x540@5"]["fps_efectivos"] == 3.9
