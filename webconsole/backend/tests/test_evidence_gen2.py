"""Las corridas que cita una prueba de la generación 2 son evidencia.

Sin esto, Corridas mostraba los 405 runs de la Victus como «Fuera del registro de
evidencia»: el registro congelado es de la generación 1. La gen 2 entra por una capa
APARTE (lee `results/gen2/*/corridas.json`), así que nada de lo congelado cambia.
"""
import json
import os

from eovrt_webconsole.evidence import EvidenceRegistry
from tests.test_evidence import archive


def _prueba(gen2, prueba, corridas):
    d = gen2 / prueba
    d.mkdir(parents=True, exist_ok=True)
    (d / "corridas.json").write_text(json.dumps({
        "schema": "corridas.gen2.v1", "prueba": prueba, "corridas": corridas,
    }))
    return d / "corridas.json"


def _registro(tmp_path):
    registro = EvidenceRegistry(archive(tmp_path))
    gen2 = tmp_path / "results" / "gen2"
    gen2.mkdir(parents=True)
    return registro, gen2


def test_la_corrida_citada_por_una_prueba_es_evidencia_de_esa_prueba(tmp_path):
    registro, gen2 = _registro(tmp_path)
    _prueba(gen2, "ALR-01", {"a_p1_c02": {
        "experiment_id": "exp_1", "media_run_id": "run_m1", "control_run_id": "run_c1",
    }})
    registro.cargar_gen2(gen2)
    for run_id in ("run_m1", "run_c1"):
        d = registro.describe([run_id])
        assert d["is_evidence"] is True
        assert d["result_ids"] == ["ALR-01"]
        assert d["collections"] == ["generacion_2"]
        assert d["clase"] == "resultado"
        assert registro.es_evidencia(run_id) is True


def test_una_corrida_citada_por_dos_pruebas_figura_en_las_dos(tmp_path):
    registro, gen2 = _registro(tmp_path)
    corridas = {"a": {"media_run_id": "run_m1", "control_run_id": "run_c1"}}
    _prueba(gen2, "ALR-01", corridas)
    _prueba(gen2, "ALR-02", corridas)
    registro.cargar_gen2(gen2)
    assert registro.describe(["run_m1"])["result_ids"] == ["ALR-01", "ALR-02"]


def test_una_corrida_que_nadie_cita_no_se_inventa_como_evidencia(tmp_path):
    registro, gen2 = _registro(tmp_path)
    _prueba(gen2, "ALR-01", {"a": {"media_run_id": "run_m1"}})
    registro.cargar_gen2(gen2)
    d = registro.describe(["run_ajena"])
    assert d["is_evidence"] is False
    assert d["result_ids"] == []
    assert d["clase"] == "sin_clasificar"


def test_la_generacion_1_no_cambia(tmp_path):
    registro, gen2 = _registro(tmp_path)
    antes = (registro.resultados(), registro.filas(), registro.roles(), registro.available)
    _prueba(gen2, "ALR-01", {"a": {"media_run_id": "run_m1", "control_run_id": "run_c1"}})
    registro.cargar_gen2(gen2)
    # Los conteos del archivo congelado (35 resultados, roles, filas) son de la gen 1.
    assert (registro.resultados(), registro.filas(), registro.roles(), registro.available) == antes


def test_una_corrida_en_las_dos_generaciones_junta_ambas(tmp_path):
    registro, gen2 = _registro(tmp_path)
    registro._rows["run_x"].append({
        "collection": "dbe_video", "result_id": "clip_bench/t1", "role": "rol_cualquiera",
        "plane": "media-plane", "run_id": "run_x",
    })
    _prueba(gen2, "ALR-01", {"a": {"media_run_id": "run_x"}})
    registro.cargar_gen2(gen2)
    d = registro.describe(["run_x"])
    assert d["result_ids"] == ["ALR-01", "clip_bench/t1"]
    assert d["collections"] == ["dbe_video", "generacion_2"]


def test_los_ids_que_no_son_corridas_reales_se_ignoran(tmp_path):
    registro, gen2 = _registro(tmp_path)
    # Las recetas derivadas (`reumbral_v03_c02`) no tienen carpeta propia; un valor
    # nulo o que no es texto tampoco es una identidad.
    _prueba(gen2, "ALR-10", {
        "a": {"media_run_id": None, "control_run_id": 7},
        "b": {"media_run_id": "", "control_run_id": "run_c9"},
    })
    registro.cargar_gen2(gen2)
    assert registro.describe(["run_c9"])["result_ids"] == ["ALR-10"]
    assert registro.describe([""])["is_evidence"] is False


def test_un_corridas_json_ilegible_no_tumba_el_registro(tmp_path):
    registro, gen2 = _registro(tmp_path)
    (gen2 / "ALR-03").mkdir()
    (gen2 / "ALR-03" / "corridas.json").write_text('{"corridas": {"a": ')  # escribiéndose ahora
    _prueba(gen2, "ALR-01", {"a": {"media_run_id": "run_m1"}})
    registro.cargar_gen2(gen2)
    assert registro.describe(["run_m1"])["result_ids"] == ["ALR-01"]


def test_sin_carpeta_gen2_todo_sigue_igual(tmp_path):
    registro = EvidenceRegistry(archive(tmp_path))
    registro.cargar_gen2(tmp_path / "no_existe")
    assert registro.describe(["run_m1"])["is_evidence"] is False


def test_una_prueba_nueva_o_modificada_se_ve_sin_reiniciar(tmp_path):
    registro, gen2 = _registro(tmp_path)
    ruta = _prueba(gen2, "ALR-01", {"a": {"media_run_id": "run_m1"}})
    registro.cargar_gen2(gen2, refresco_s=0)
    assert registro.describe(["run_m2"])["is_evidence"] is False
    ruta.write_text(json.dumps({"corridas": {"a": {"media_run_id": "run_m1"}, "b": {"media_run_id": "run_m2"}}}))
    st = ruta.stat()
    os.utime(ruta, ns=(st.st_atime_ns, st.st_mtime_ns + 5_000_000_000))
    assert registro.describe(["run_m2"])["result_ids"] == ["ALR-01"]
    _prueba(gen2, "ALR-02", {"a": {"media_run_id": "run_m3"}})
    assert registro.describe(["run_m3"])["result_ids"] == ["ALR-02"]
