"""La evidencia de la generación 2 (doc 135): se lee del disco, no consulta servicios."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from eovrt_webconsole.gen2 import Gen2

REPO = Path(__file__).resolve().parents[3]


def _prueba(repo: Path, pid: str, **extra) -> None:
    carpeta = repo / "experiments" / "evidencia" / pid
    carpeta.mkdir(parents=True, exist_ok=True)
    datos = {"schema": "prueba.gen2.v1", "id": pid, "titulo": f"Prueba {pid}", "fase": "F3",
             "familia": "clips", "informe": ["Tabla 53"], "pregunta": "¿Cuánto?",
             "gen1": {"result_id": "t1_x", "doc": "operacion/81",
                      "referencia": {"fuente": "gt02.json", "valores": {"f1_micro": 0.84}}}, **extra}
    (carpeta / "prueba.yaml").write_text(yaml.safe_dump(datos, allow_unicode=True), encoding="utf-8")


def _resultado(repo: Path, pid: str, **datos) -> Path:
    carpeta = repo / "results" / "gen2" / pid
    carpeta.mkdir(parents=True, exist_ok=True)
    cuerpo = {"schema": "resultado.gen2.v1", "id": pid, "estado": "completo",
              "resumen": [{"clave": "f1", "nombre": "F1", "valor": 0.84, "unidad": None, "gen1": 0.84}],
              "veredicto": {"propuesto": "identico", "confirmado": None}, **datos}
    (carpeta / "resultado.json").write_text(json.dumps(cuerpo), encoding="utf-8")
    return carpeta


def test_sin_resultados_las_pruebas_aparecen_sin_correr(client, repo):
    _prueba(repo, "ALR-01")
    _prueba(repo, "IMG-01", familia="imagenes", fase="F4")
    r = client.get("/api/gen2/pruebas")
    assert r.status_code == 200
    filas = {f["id"]: f for f in r.json()}
    assert set(filas) == {"ALR-01", "IMG-01"}
    assert filas["ALR-01"]["estado"] == "sin_correr"
    assert filas["ALR-01"]["gen1"]["result_id"] == "t1_x"
    assert filas["ALR-01"]["resumen"] == []


def test_un_contraste_que_no_se_regenera_trae_su_cifra_de_la_generacion_1(client, repo):
    _prueba(repo, "ALR-03", estado="no_se_regenera", no_se_regenera="Contraste contra el campeón.",
            gen1={"result_id": "t2_x", "doc": "operacion/84",
                  "cifras": [{"clave": "f1", "nombre": "F1 por episodio (micro)", "valor": 0.714286}]})
    fila = client.get("/api/gen2/pruebas").json()[0]
    assert fila["registro"] == "no_se_regenera"
    assert fila["estado"] == "sin_correr"
    assert fila["no_se_regenera"] == "Contraste contra el campeón."
    assert fila["gen1"]["cifras"] == [{"clave": "f1", "nombre": "F1 por episodio (micro)", "valor": 0.714286}]
    assert fila["resumen"] == []


def test_con_resultado_se_mezcla_cifra_y_veredicto(client, repo):
    _prueba(repo, "ALR-01")
    _resultado(repo, "ALR-01")
    fila = client.get("/api/gen2/pruebas").json()[0]
    assert fila["estado"] == "completo"
    assert fila["resumen"][0]["valor"] == 0.84
    assert fila["veredicto"]["propuesto"] == "identico"


def test_carpetas_con_guion_bajo_y_preregistros_invalidos_no_se_listan(client, repo):
    _prueba(repo, "ALR-01")
    (repo / "experiments" / "evidencia" / "_generados" / "x").mkdir(parents=True)
    (repo / "experiments" / "evidencia" / "_generados" / "prueba.yaml").write_text("id: ALR-09")
    malo = repo / "experiments" / "evidencia" / "ALR-02"
    malo.mkdir(parents=True)
    (malo / "prueba.yaml").write_text("id: OTRA-01\n")
    assert [f["id"] for f in client.get("/api/gen2/pruebas").json()] == ["ALR-01"]


def test_detalle_trae_preregistro_corridas_entorno_y_archivos(client, repo):
    _prueba(repo, "ALR-01")
    carpeta = _resultado(repo, "ALR-01")
    (carpeta / "corridas.json").write_text(json.dumps({"corridas": {"a_p1_c02": {
        "estado": "ok", "experiment_id": "exp_1", "media_run_id": "run_1", "control_run_id": "ctl_1"}}}))
    (carpeta / "entorno.json").write_text(json.dumps({"host": {"nombre": "victus"}, "gpu": "RTX 4060"}))
    (carpeta / "comandos.txt").write_text("[t] POST /api/experiments/run\n")
    (carpeta / "prueba.yaml").write_text(
        (repo / "experiments/evidencia/ALR-01/prueba.yaml").read_text(encoding="utf-8"), encoding="utf-8")
    (carpeta / "logs" / "ejemplo").mkdir(parents=True)
    (carpeta / "logs" / "ejemplo" / "manifest.yaml").write_text("slug: x\n")
    (carpeta / "evals").mkdir()
    (carpeta / "evals" / "eval_a_p1_c02.json").write_text("{}")
    (carpeta / "evals" / "detecciones.bin").write_bytes(b"\x00")  # no se lista: no se sirve
    r = client.get("/api/gen2/pruebas/ALR-01")
    assert r.status_code == 200
    d = r.json()
    assert d["pre_registro"]["origen"] == "copia_al_correr"
    assert d["pre_registro"]["coincide_con_catalogo"] is True
    assert d["corridas"]["a_p1_c02"]["experiment_id"] == "exp_1"
    assert d["entorno"]["gpu"] == "RTX 4060"
    assert d["comandos"].startswith("[t]")
    assert d["archivos"]["logs"] == ["logs/ejemplo/manifest.yaml"]
    assert d["archivos"]["evals"] == ["evals/eval_a_p1_c02.json"]
    assert d["archivos"]["capturas"] == []


def test_detalle_de_una_prueba_sin_correr_muestra_el_catalogo(client, repo):
    _prueba(repo, "RT-03", familia="vivo")
    d = client.get("/api/gen2/pruebas/RT-03").json()
    assert d["estado"] == "sin_correr"
    assert d["pre_registro"]["origen"] == "catalogo"
    assert "RT-03" in d["pre_registro"]["texto"]
    assert d["resultado"] is None and d["corridas"] is None


def test_detalle_inexistente_o_id_invalido_da_404(client, repo):
    assert client.get("/api/gen2/pruebas/ALR-99").status_code == 404
    assert client.get("/api/gen2/pruebas/..%2F..%2Fetc").status_code == 404
    assert client.get("/api/gen2/pruebas/alr-01").status_code == 404


def test_archivo_sirve_texto_e_imagenes_de_la_carpeta(client, repo):
    _prueba(repo, "ALR-01")
    carpeta = _resultado(repo, "ALR-01")
    (carpeta / "capturas").mkdir()
    (carpeta / "capturas" / "consola.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    r = client.get("/api/gen2/pruebas/ALR-01/archivo", params={"ruta": "capturas/consola.png"})
    assert r.status_code == 200 and r.headers["content-type"] == "image/png"
    r = client.get("/api/gen2/pruebas/ALR-01/archivo", params={"ruta": "resultado.json"})
    assert r.status_code == 200 and r.json()["estado"] == "completo"


def test_archivo_no_sale_de_la_carpeta_de_la_prueba(client, repo):
    _prueba(repo, "ALR-01")
    carpeta = _resultado(repo, "ALR-01")
    (repo / "results" / "gen2" / "secreto.json").write_text("{}")
    (carpeta / "datos.bin").write_bytes(b"\x00")
    for ruta in ("../secreto.json", "../../experiments/evidencia/ALR-01/prueba.yaml",
                 "/etc/passwd", "datos.bin", "no-existe.json", "."):
        assert client.get("/api/gen2/pruebas/ALR-01/archivo", params={"ruta": ruta}).status_code == 404, ruta


def test_observaciones_vinculan_las_pruebas_con_su_estado(client, repo):
    _prueba(repo, "ALR-01")
    _resultado(repo, "ALR-01")
    (repo / "results" / "gen2" / "observaciones.yaml").write_text(yaml.safe_dump({
        "schema": "observaciones.gen2.v1",
        "observaciones": [{"numero": 8, "titulo": "Observación de ejemplo", "pedido": "p", "respuesta": "r",
                           "pruebas": ["ALR-01", "ALR-07"], "secciones": ["resumen"]}],
    }, allow_unicode=True), encoding="utf-8")
    d = client.get("/api/gen2/observaciones").json()
    assert d["available"] is True
    obs = d["observaciones"][0]
    assert obs["pruebas"][0] == {"id": "ALR-01", "titulo": "Prueba ALR-01", "estado": "completo",
                                 "registro": "activa",
                                 "veredicto": {"propuesto": "identico", "confirmado": None}}
    assert obs["pruebas"][1]["estado"] == "desconocida"


def test_sin_observaciones_lo_dice_y_no_falla(client):
    d = client.get("/api/gen2/observaciones").json()
    assert d["available"] is False and d["observaciones"] == []


def test_las_observaciones_se_leen_del_repo_privado_docs_hermano(tmp_path):
    # El repo de la consola es público: las observaciones viven en `docs` (privado).
    repo = tmp_path / "ws" / "e-ovrt_experimental-setup"
    _prueba(repo, "ALR-01")
    privado = tmp_path / "ws" / "docs" / "observaciones-tribunal"
    privado.mkdir(parents=True)
    (privado / "observaciones.yaml").write_text(yaml.safe_dump({
        "schema": "observaciones.gen2.v1",
        "observaciones": [{"numero": 9, "titulo": "t", "pedido": "p", "respuesta": "r",
                           "pruebas": ["ALR-01"], "secciones": []}],
    }), encoding="utf-8")
    obs = Gen2(repo).observaciones()
    assert obs["available"] is True and obs["observaciones"][0]["pruebas"][0]["id"] == "ALR-01"
    # Una copia local (gitignorada) tiene prioridad.
    local = repo / "results" / "gen2"
    local.mkdir(parents=True)
    (local / "observaciones.yaml").write_text(yaml.safe_dump({"observaciones": []}), encoding="utf-8")
    assert Gen2(repo).observaciones() == {"available": True, "observaciones": []}


def test_el_repo_publico_no_trae_las_observaciones():
    assert not (REPO / "results" / "gen2" / "observaciones.yaml").exists()


def test_el_catalogo_y_las_observaciones_del_workspace_se_leen_completos():
    g = Gen2(REPO)
    pruebas = g.pruebas()
    # El catálogo puede crecer: se fija el piso y las pruebas que la consola nombra.
    assert len(pruebas) >= 30
    assert {"ALR-01", "IMG-01", "PER-03", "RT-04", "PLAT-01"} <= {p["id"] for p in pruebas}
    # Toda prueba que no se regenera llega a la consola con su motivo y su cifra vigente. Desde la
    # enmienda del 2026-10-30 (doc 134 §13.10) no queda ninguna en el catálogo real; el caso lo
    # cubre el test con catálogo sintético de arriba.
    for p in (p for p in pruebas if p["registro"] == "no_se_regenera"):
        assert p["no_se_regenera"] and p["gen1"]["cifras"], p["id"]
    obs = g.observaciones()
    if not obs["available"]:
        pytest.skip("sin el repo privado docs al lado: las observaciones no se pueden cotejar")
    # Pueden sumarse observaciones: se exige numeración corrida desde 1 y el piso de las primeras diez.
    numeros = [o["numero"] for o in obs["observaciones"]]
    assert len(numeros) >= 10 and numeros == list(range(1, len(numeros) + 1))
    ids = {p["id"] for p in pruebas}
    for o in obs["observaciones"]:
        for p in o["pruebas"]:
            assert p["id"] in ids, f"la observación {o['numero']} cita {p['id']}, que no está en el catálogo"
