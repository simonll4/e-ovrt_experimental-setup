"""Índice de traza y vocabulario cerrado de `control`.

Dos problemas que resuelve, los dos del README del rediseño:

- La línea de tiempo necesita la corrida COMPLETA y `/trace` solo pagina, así que
  la consola bajaba hasta 40 páginas de 500 cuadros para dibujar tres carriles.
- `control` viajaba como cadena y la interfaz la parseaba por prefijo; un motivo
  de descarte nuevo se filtraba a la pantalla en inglés.
"""

from eovrt_webconsole.trace import build_trace_index, compose_trace, resolve_control


class TestVocabularioDeControl:
    def test_recibido_y_no_recibido(self):
        assert resolve_control("received")["control_state"] == "received"
        assert resolve_control("received")["control_label"] == "recibido"
        assert resolve_control("not_received")["control_label"] == "no recibido"

    def test_sin_dato_cuando_el_motor_de_reglas_no_evaluo(self):
        # `n/d` es lo que pone compose_trace cuando no hay corrida de control.
        resuelto = resolve_control("n/d")
        assert resuelto["control_state"] == "unknown"
        assert resuelto["control_label"] == "sin dato"

    def test_motivo_conocido_se_traduce(self):
        resuelto = resolve_control("dropped:rate_gate")
        assert resuelto["control_state"] == "dropped"
        assert resuelto["control_reason"] == "rate_gate"
        assert resuelto["control_label"] == "límite de tasa"

    def test_motivo_desconocido_no_se_filtra_crudo_a_la_pantalla(self):
        # El caso que motivó el cambio: un motivo nuevo del media-plane no debe
        # aparecer en inglés en la interfaz, pero tampoco perderse.
        resuelto = resolve_control("dropped:lo_que_sea")
        assert resuelto["control_state"] == "dropped"
        assert resuelto["control_reason"] == "otro"
        assert resuelto["control_label"] == "descartado"
        assert resuelto["control_reason_raw"] == "lo_que_sea"


def _compuesta():
    detections = [
        {"unit_id": "u0", "source": {"frame_index": 0, "timestamp_ms": 0.0},
         "detections": [{"label": "person", "confidence": 0.9, "bbox_norm_xyxy": [0, 0, 1, 1]}]},
        {"unit_id": "u1", "source": {"frame_index": 1, "timestamp_ms": 40.0}, "detections": []},
    ]
    dropped = [{"unit_id": "u2", "frame_index": 2, "reason": "rate_gate"}]
    alerts = [{"unit_id": "u1", "condition_id": "CR-01", "severity": "high"}]
    return compose_trace(
        detections=detections, dropped=dropped, progress=[], alerts=alerts,
        received_unit_ids={"u0", "u1"}, control_run_id="ctl_1", topology="single_host",
    )


class TestIndice:
    def test_arrays_paralelos_con_una_entrada_por_cuadro(self):
        idx = build_trace_index(_compuesta())
        assert idx["total"] == 3
        for clave in ("unit_id", "frame_index", "timestamp_ms", "detections",
                      "control_state", "alert"):
            assert len(idx[clave]) == 3, clave

    def test_cuenta_detecciones_por_cuadro_sin_mandar_las_cajas(self):
        # El punto del índice: la línea de tiempo solo necesita cuántas hubo.
        idx = build_trace_index(_compuesta())
        assert idx["detections"] == [1, 0, 0]

    def test_estado_de_entrega_por_cuadro(self):
        idx = build_trace_index(_compuesta())
        assert idx["control_state"] == ["received", "received", "dropped"]

    def test_marca_de_alerta_como_uno_o_cero(self):
        idx = build_trace_index(_compuesta())
        assert idx["alert"] == [0, 1, 0]

    def test_conserva_los_totales_de_la_traza(self):
        idx = build_trace_index(_compuesta())
        assert idx["totals"]["frames"] == 3
        assert idx["totals"]["dropped_by_reason"] == {"rate_gate": 1}


class TestEndpoint:
    def test_devuelve_la_corrida_completa_en_una_sola_respuesta(self, two_plane_client):
        r = two_plane_client.get("/api/runs/run_done_1/trace/index")
        assert r.status_code == 200
        cuerpo = r.json()
        assert cuerpo["media_run_id"] == "run_done_1"
        assert cuerpo["total"] == len(cuerpo["control_state"])
        assert "control_error" in cuerpo

    def test_no_choca_con_la_ruta_de_trace_paginada(self, two_plane_client):
        assert two_plane_client.get("/api/runs/run_done_1/trace").status_code == 200
        assert two_plane_client.get("/api/runs/run_done_1/trace/index").status_code == 200
