"""`created_at` viaja siempre, en las tres formas de fila del listado.

Antes solo estaba en las filas hidratadas (las primeras `hydration_limit`), así
que ordenar por fecha obligaba al cliente a reconstruirla parseando el `run_id`
— y comparados como texto, `"run_2026…"` queda por encima de un ISO-8601, con lo
que las corridas más nuevas terminaban enterradas.
"""

from eovrt_webconsole.routers.runs import _created_at


def test_prefiere_started_at_cuando_existe():
    info = {"run_id": "run_20260729_143641_dbe_mock_271b9f",
            "started_at": "2026-07-29T14:36:41+00:00"}
    assert _created_at(info) == "2026-07-29T14:36:41+00:00"


def test_lo_toma_del_summary_si_no_esta_arriba():
    info = {"run_id": "run_x", "summary": {"started_at": "2026-07-29T10:00:00+00:00"}}
    assert _created_at(info) == "2026-07-29T10:00:00+00:00"


def test_lo_reconstruye_del_run_id_cuando_no_hay_started_at():
    # Caso de las filas no hidratadas: el id es determinístico.
    assert _created_at({"run_id": "run_20260729_143641_dbe_mock_271b9f"}) == (
        "2026-07-29T14:36:41+00:00"
    )


def test_un_id_sin_fecha_no_inventa_una():
    assert _created_at({"run_id": "corrida-a-mano"}) is None


def test_una_fecha_imposible_en_el_id_no_revienta():
    # 32 de mes: el id existe pero no es una fecha.
    assert _created_at({"run_id": "run_20261332_250000_x"}) is None


def test_el_listado_lo_expone_en_todas_las_filas(client):
    filas = client.get("/api/runs").json()
    assert filas, "la fake debería devolver al menos una corrida"
    assert all("created_at" in f for f in filas)
