"""Corrida anterior COMPARABLE y variación de los indicadores.

Los indicadores del detalle muestran "+0,3 vs la corrida anterior". "La anterior"
a secas no sirve: si entre las dos cambió el modelo o el conjunto de prompts, la
variación no mide una mejora sino un cambio de experimento.
"""

from eovrt_webconsole.routers.runs import _EJES_DE_COMPARACION, _METRICAS_COMPARABLES, _metricas_de


def test_los_ejes_de_comparacion_son_los_que_definen_el_experimento():
    assert set(_EJES_DE_COMPARACION) == {"model", "prompt_set_id", "source_type"}


def test_cada_metrica_declara_hacia_donde_es_mejor():
    # La interfaz pinta el delta con esto; sin la dirección no puede saber si
    # subir es bueno (cuadros por segundo) o malo (latencia).
    assert _METRICAS_COMPARABLES["fps_effective"] == "mas"
    assert _METRICAS_COMPARABLES["p95_latency_ms"] == "menos"
    # Más detecciones no es mejor ni peor: depende de la escena.
    assert _METRICAS_COMPARABLES["total_detections"] is None


def test_solo_toma_valores_numericos_del_summary():
    info = {"summary": {"fps_effective": 2.4, "p50_latency_ms": None, "duration_seconds": "raro"}}
    m = _metricas_de(info)
    assert m["fps_effective"] == 2.4
    assert m["p50_latency_ms"] is None
    # Un tipo inesperado no se propaga como si fuera una medición.
    assert m["duration_seconds"] is None


class TestEndpoint:
    def test_sin_candidata_no_inventa_variacion(self, client):
        # La fake tiene una sola corrida terminada, así que no hay anterior.
        # Devolver deltas en cero diría "no cambió nada", que es distinto de
        # "no hay con qué comparar".
        r = client.get("/api/runs/run_done_1/comparison")
        assert r.status_code == 200
        cuerpo = r.json()
        assert cuerpo["previous_run_id"] is None
        assert cuerpo["deltas"] == {}

    def test_declara_sobre_que_ejes_compara(self, client):
        cuerpo = client.get("/api/runs/run_done_1/comparison").json()
        assert set(cuerpo["matched_on"]) == {"model", "prompt_set_id", "source_type"}

    def test_run_inexistente_da_404(self, client, fake_state):
        fake_state.deleted.append("run_done_1")
        assert client.get("/api/runs/run_done_1/comparison").status_code == 404
