"""Limpieza de las rutas del workspace antes de commitear `results/gen2/` (doc 134 §13.12)."""
from __future__ import annotations

import json
from pathlib import Path

import yaml
from test_evidencia_driver import _prueba

from tools.evidencia import catalogo as cat
from tools.evidencia import rutas
from tools.evidencia.entorno import MARCA_WORKSPACE, REPO, Entorno
from tools.evidencia.registro import Carpeta

# La forma que tiene en la Victus: Docker Desktop monta la carpeta de un usuario de Windows.
WS_VICTUS = "/run/desktop/mnt/host/c/Users/fulano/Documents/tfg"


def _carpeta(tmp_path: Path, monkeypatch, ws: str = WS_VICTUS) -> Carpeta:
    monkeypatch.setenv("EOVRT_EVIDENCIA_SALIDA", str(tmp_path / "salida"))
    ent = Entorno(ws=Path(ws), repo=REPO, modo="docker", consola_url="http://consola",
                  datasets_medios="/e-ovrt_datasets")
    return Carpeta(ent, cat.cargar_prueba(_prueba(tmp_path / "cat", "ALR-07")))


def _poblar(carpeta: Carpeta) -> None:
    ws = str(carpeta.ent.ws)
    det = f"{ws}/e-ovrt_media-plane/runs/r1/detections.jsonl"
    carpeta.guardar_corrida("v01_c01", {"estado": "ok", "detecciones": det,
                                        "control_config": f"{ws}/e-ovrt_experimental-setup/runs/c.yaml"})
    carpeta.escribir("entorno.json", {"workspace": ws, "host": {"nombre": "f0eb677d63d7"}})
    carpeta.comando(f"reumbralar({det}, umbral>0.35)")
    (carpeta.logs / "ejemplo").mkdir(parents=True)
    (carpeta.logs / "ejemplo" / "control.yaml").write_text(
        yaml.safe_dump({"output": {"run_dir": f"{ws}/e-ovrt_control-plane/runs"}, "patterns": [ws]}),
        encoding="utf-8")


def test_limpia_el_workspace_de_todos_los_archivos_y_deja_constancia(tmp_path, monkeypatch):
    carpeta = _carpeta(tmp_path, monkeypatch)
    _poblar(carpeta)
    informe = rutas.limpiar(carpeta.ent.resultados, WS_VICTUS)
    assert informe["escrito"] and informe["archivos"] == 4 and not informe["restos"]
    for archivo in carpeta.ent.resultados.rglob("*"):
        if archivo.is_file():
            assert "fulano" not in archivo.read_text(encoding="utf-8")
    ejemplo = yaml.safe_load((carpeta.logs / "ejemplo" / "control.yaml").read_text())
    assert ejemplo["patterns"] == [MARCA_WORKSPACE]
    constancia = json.loads((carpeta.ent.resultados / rutas.CONSTANCIA).read_text())
    assert [a["ruta"] for a in constancia[0]["archivos"]] == [
        "ALR-07/comandos.txt", "ALR-07/corridas.json", "ALR-07/entorno.json", "ALR-07/logs/ejemplo/control.yaml"]
    assert all(a["sha256_antes"] != a["sha256_despues"] for a in constancia[0]["archivos"])


def test_las_rutas_limpias_se_siguen_leyendo_en_esta_maquina(tmp_path, monkeypatch):
    # VIS-01 y ERR-01 siguen `detecciones` de corridas.json: tienen que funcionar después de limpiar.
    carpeta = _carpeta(tmp_path, monkeypatch)
    _poblar(carpeta)
    antes = carpeta.corridas()
    rutas.limpiar(carpeta.ent.resultados, WS_VICTUS)
    assert MARCA_WORKSPACE in carpeta._corridas_path.read_text()
    assert carpeta.corridas() == antes
    otra_maquina = Entorno(ws=Path("/home/alguien/ws"), repo=REPO, modo="nativo", consola_url="http://consola",
                           datasets_medios="/e-ovrt_datasets")
    otra = Carpeta(otra_maquina, carpeta.prueba)
    assert otra.corridas()["v01_c01"]["detecciones"] == "/home/alguien/ws/e-ovrt_media-plane/runs/r1/detections.jsonl"


def test_es_idempotente_y_lo_nuevo_se_limpia_en_la_pasada_siguiente(tmp_path, monkeypatch):
    carpeta = _carpeta(tmp_path, monkeypatch)
    _poblar(carpeta)
    rutas.limpiar(carpeta.ent.resultados, WS_VICTUS)
    assert rutas.limpiar(carpeta.ent.resultados, WS_VICTUS)["archivos"] == 0
    # el driver vuelve a escribir rutas absolutas (guardar_corrida expande lo que lee)
    carpeta.guardar_corrida("v02_c01", {"estado": "ok"})
    segunda = rutas.limpiar(carpeta.ent.resultados, WS_VICTUS)
    assert segunda["escrito"] and segunda["archivos"] == 1
    assert len(json.loads((carpeta.ent.resultados / rutas.CONSTANCIA).read_text())) == 2


def test_si_el_usuario_queda_en_otra_forma_no_escribe_nada(tmp_path, monkeypatch):
    carpeta = _carpeta(tmp_path, monkeypatch)
    _poblar(carpeta)
    (carpeta.dir / "nota.txt").write_text("C:\\Users\\fulano\\Documents\\tfg\n", encoding="utf-8")
    original = carpeta._corridas_path.read_text()
    informe = rutas.limpiar(carpeta.ent.resultados, WS_VICTUS)
    assert informe["restos"] == ["ALR-07/nota.txt"] and not informe["escrito"]
    assert carpeta._corridas_path.read_text() == original
    assert not (carpeta.ent.resultados / rutas.CONSTANCIA).exists()


def test_simular_no_escribe(tmp_path, monkeypatch):
    carpeta = _carpeta(tmp_path, monkeypatch)
    _poblar(carpeta)
    original = carpeta._corridas_path.read_text()
    informe = rutas.limpiar(carpeta.ent.resultados, WS_VICTUS, simular=True)
    assert informe["archivos"] == 4 and not informe["escrito"]
    assert carpeta._corridas_path.read_text() == original


def test_usuario_de_la_ruta():
    assert rutas.usuario_de(WS_VICTUS) == "fulano"
    assert rutas.usuario_de("/home/alguien/projects") is None
