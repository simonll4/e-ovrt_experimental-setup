"""El listado de experimentos trae grupo, estado, conteo y fecha.

Antes cada fila era `{slug, experiment_id, sequencing, runs}`, así que la tabla
no podía mostrar ni en qué grupo está el manifiesto, ni cómo terminó la última
ejecución, ni cuántas veces se corrió, ni cuándo — cuatro de las siete columnas
que pide el prototipo.
"""

import yaml

from eovrt_webconsole.routers.experiments import _ejecuciones_por_slug, _estado_de


def _consolidada(runs_dir, experiment_id: str, slug: str, *, con_reporte: bool):
    d = runs_dir / experiment_id
    (d / "report").mkdir(parents=True, exist_ok=True)
    (d / "manifest.effective.yaml").write_text(
        yaml.safe_dump({"slug": slug, "schema_version": "experiment.manifest.v1"}),
        encoding="utf-8",
    )
    if con_reporte:
        (d / "report" / "report.json").write_text("{}", encoding="utf-8")
    return d


class TestEjecucionesPorSlug:
    def test_agrupa_por_el_slug_del_manifiesto_efectivo(self, tmp_path):
        _consolidada(tmp_path, "exp_1", "perimetro", con_reporte=True)
        _consolidada(tmp_path, "exp_2", "perimetro", con_reporte=True)
        _consolidada(tmp_path, "exp_3", "interior", con_reporte=True)
        por_slug = _ejecuciones_por_slug(tmp_path)
        assert len(por_slug["perimetro"]) == 2
        assert len(por_slug["interior"]) == 1

    def test_la_mas_reciente_queda_primera(self, tmp_path):
        import os
        import time

        a = _consolidada(tmp_path, "exp_viejo", "s", con_reporte=True)
        b = _consolidada(tmp_path, "exp_nuevo", "s", con_reporte=True)
        ahora = time.time()
        os.utime(a, (ahora - 3600, ahora - 3600))
        os.utime(b, (ahora, ahora))
        assert _ejecuciones_por_slug(tmp_path)["s"][0][0] == "exp_nuevo"

    def test_ignora_directorios_que_no_son_ejecuciones(self, tmp_path):
        (tmp_path / "suelto").mkdir()
        _consolidada(tmp_path, "exp_1", "s", con_reporte=True)
        assert list(_ejecuciones_por_slug(tmp_path)) == ["s"]

    def test_sin_directorio_de_corridas_no_revienta(self, tmp_path):
        assert _ejecuciones_por_slug(tmp_path / "no-existe") == {}


class TestEstado:
    def test_con_reporte_consolidado_termino(self, tmp_path):
        d = _consolidada(tmp_path, "exp_1", "s", con_reporte=True)
        assert _estado_de(d) == "succeeded"

    def test_sin_reporte_quedo_a_medias(self, tmp_path):
        # El estado en memoria del manager se pierde al reiniciar el BFF; el
        # rastro en disco es lo único que sobrevive.
        d = _consolidada(tmp_path, "exp_1", "s", con_reporte=False)
        assert _estado_de(d) == "failed"

    def test_sin_ejecucion_no_hay_estado(self, tmp_path):
        assert _estado_de(tmp_path / "nunca-corrio") is None


# Los manifiestos del repo de prueba son single-plane (formato viejo) y el
# listado solo devuelve los paraguas, así que el test crea el suyo.
UMBRELLA = {
    "schema_version": "experiment.manifest.v1",
    "slug": "perimetro_nocturno",
    "runs": {
        "media": {"service": "media-plane", "config": "configs/media_run.yaml", "mode": "run"},
        "control": {"service": "control-plane", "config": "configs/control_run.yaml", "mode": "live"},
    },
}


def test_el_endpoint_expone_los_campos_nuevos(client):
    assert client.post("/api/experiments/manifests", json=UMBRELLA).status_code == 201
    filas = client.get("/api/experiments/manifests").json()
    fila = next(f for f in filas if f["slug"] == "perimetro_nocturno")
    for clave in ("group", "last_status", "last_run_at", "n_runs", "last_experiment_id"):
        assert clave in fila, clave


def test_un_manifiesto_sin_ejecutar_no_inventa_estado_ni_fecha(client):
    client.post("/api/experiments/manifests", json=UMBRELLA)
    fila = next(
        f for f in client.get("/api/experiments/manifests").json()
        if f["slug"] == "perimetro_nocturno"
    )
    assert fila["n_runs"] == 0
    assert fila["last_run_at"] is None
    assert fila["last_status"] is None


def test_en_la_raiz_de_experiments_no_hay_grupo(client):
    client.post("/api/experiments/manifests", json=UMBRELLA)
    fila = next(
        f for f in client.get("/api/experiments/manifests").json()
        if f["slug"] == "perimetro_nocturno"
    )
    assert fila["group"] is None


def test_el_grupo_sale_de_la_carpeta_que_lo_contiene(client, repo):
    destino = repo / "experiments" / "perimetro" / "nocturno.yaml"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        yaml.safe_dump({**UMBRELLA, "slug": "agrupado"}), encoding="utf-8"
    )
    fila = next(
        f for f in client.get("/api/experiments/manifests").json() if f["slug"] == "agrupado"
    )
    assert fila["group"] == "perimetro"
