"""El filtro de la lista de cuadros se aplica ANTES de paginar.

Filtrar en el cliente obligaba a tener la traza entera en memoria. Con miles de
cuadros, "solo alertas" habría mostrado las alertas de la página actual y no las
de la corrida — lo contrario de lo que alguien espera de un filtro.
"""

from eovrt_webconsole.trace import filtrar_frames, frame_tiene_actividad


def _frame(**kw):
    base = {
        "detections": [],
        "control_state": "received",
        "progress": [],
        "alert": [],
        "active_patterns": [],
    }
    return {**base, **kw}


class TestActividad:
    def test_un_cuadro_vacio_no_tiene_actividad(self):
        assert not frame_tiene_actividad(_frame())

    def test_con_detecciones(self):
        assert frame_tiene_actividad(_frame(detections=[{"label": "person"}]))

    def test_un_descarte_es_actividad(self):
        # Que un cuadro NO llegue al motor de reglas es justo lo que hay que ver.
        assert frame_tiene_actividad(_frame(control_state="dropped"))
        assert frame_tiene_actividad(_frame(control_state="not_received"))

    def test_progreso_de_condicion_y_patron_abierto_cuentan(self):
        assert frame_tiene_actividad(_frame(progress=[{"condition_id": "CR-01"}]))
        assert frame_tiene_actividad(_frame(active_patterns=[{"pattern_id": "CR-01"}]))


class TestFiltro:
    def _frames(self):
        return [
            _frame(unit_id="u0"),
            _frame(unit_id="u1", detections=[{"label": "person"}]),
            _frame(unit_id="u2", alert=[{"condition_id": "CR-01"}]),
            _frame(unit_id="u3", control_state="dropped"),
        ]

    def test_sin_filtro_pasan_todos(self):
        assert len(filtrar_frames(self._frames(), None)) == 4

    def test_solo_actividad(self):
        ids = [f["unit_id"] for f in filtrar_frames(self._frames(), "actividad")]
        assert ids == ["u1", "u2", "u3"]

    def test_solo_alertas(self):
        ids = [f["unit_id"] for f in filtrar_frames(self._frames(), "alertas")]
        assert ids == ["u2"]

    def test_un_valor_desconocido_no_filtra(self):
        assert len(filtrar_frames(self._frames(), "loquesea")) == 4


class TestEndpoint:
    def test_el_total_es_el_del_conjunto_filtrado(self, two_plane_client):
        # Es lo que la lista tiene que paginar. `totals.frames` sigue siendo el
        # de la corrida entera.
        completo = two_plane_client.get("/api/runs/run_done_1/trace").json()
        filtrado = two_plane_client.get("/api/runs/run_done_1/trace?solo=alertas").json()
        assert filtrado["total"] <= completo["total"]
        assert filtrado["totals"]["frames"] == completo["totals"]["frames"]

    def test_un_filtro_invalido_es_422(self, two_plane_client):
        assert two_plane_client.get("/api/runs/run_done_1/trace?solo=nada").status_code == 422
