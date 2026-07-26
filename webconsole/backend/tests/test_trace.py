"""Trace compuesto media<->control (Spec B Tarea 3, spec 2026-07-17 SS4).

Dos niveles: (1) el merge puro `compose_trace` (sin HTTP), (2) el endpoint
`GET /api/runs/{run_id}/trace` via `two_plane_client`."""
from __future__ import annotations

from eovrt_webconsole.experiment.control_backend import (
    ServiceUnavailable as ControlServiceUnavailable,
)
from eovrt_webconsole.trace import compose_trace


def _det(fi, uid, labels, bboxes=None):  # DetectionEvent minimo del lado media
    dets = []
    for i, label in enumerate(labels):
        d = {"label": label, "confidence": 0.9}
        if bboxes is not None:
            d["bbox_norm_xyxy"] = bboxes[i]
        dets.append(d)
    return {"unit_id": uid, "source": {"frame_index": fi, "timestamp_ms": float(fi) * 100},
            "detections": dets}


def test_merge_interleaves_processed_and_dropped_ordered():
    frames = compose_trace(
        detections=[
            _det(0, "u0", ["person"], bboxes=[[0.1, 0.2, 0.3, 0.4]]),
            _det(2, "u2", ["person"]),
        ],
        dropped=[{"frame_index": 1, "unit_id": "u1", "reason": "rate_gate"}],
        progress=[], alerts=[], received_unit_ids={"u0", "u2"},
        control_run_id="ctrl-a", topology="single_host",
    )["frames"]
    assert [f["frame_index"] for f in frames] == [0, 1, 2]
    assert frames[1]["control"] == "dropped:rate_gate" and frames[1]["detections"] is None
    assert frames[0]["control"] == "received"
    assert frames[0]["detections"][0]["bbox_norm_xyxy"] == [0.1, 0.2, 0.3, 0.4]


def test_not_received_via_set_difference():
    out = compose_trace(
        detections=[_det(0, "u0", ["person"]), _det(1, "u1", ["person"])],
        dropped=[], progress=[], alerts=[], received_unit_ids={"u0"},
        control_run_id="ctrl-a", topology="single_host",
    )
    assert out["frames"][1]["control"] == "not_received"
    assert out["totals"]["not_received"] == 1


def test_progress_and_alert_attached_by_frame():
    out = compose_trace(
        detections=[_det(3, "u3", ["person"]), _det(4, "u4", ["person"])],
        dropped=[],
        progress=[{"frame_index": 3, "unit_id": "u3", "condition_id": "CR-01", "progress": 0.5,
                   "elapsed_ms": 500.0, "threshold_ms": 1000.0, "mode": "time"}],
        alerts=[{"frame_index": 4, "unit_id": "u4", "condition_id": "CR-01", "severity": "high"}],
        received_unit_ids={"u3", "u4"},
        control_run_id="ctrl-a", topology="single_host",
    )
    assert out["frames"][0]["progress"][0]["progress"] == 0.5
    assert out["frames"][1]["alert"][0]["condition_id"] == "CR-01"


def test_no_control_run_all_nd():
    out = compose_trace(
        detections=[_det(0, "u0", ["person"])], dropped=[], progress=[], alerts=[],
        received_unit_ids=None, control_run_id=None, topology="single_host",
    )
    assert out["frames"][0]["control"] == "n/d"
    assert out["totals"]["received"] is None


def test_totals_dropped_by_reason_and_alerts_count():
    out = compose_trace(
        detections=[_det(0, "u0", ["person"])],
        dropped=[
            {"frame_index": 1, "unit_id": "u1", "reason": "rate_gate"},
            {"frame_index": 2, "unit_id": "u2", "reason": "rate_gate"},
            {"frame_index": 3, "unit_id": "u3", "reason": "queue_full"},
        ],
        progress=[],
        alerts=[{"frame_index": 0, "condition_id": "CR-01", "severity": "high"}],
        received_unit_ids={"u0"},
        control_run_id="ctrl-a", topology="single_host",
    )
    assert out["totals"]["frames"] == 4
    assert out["totals"]["detections"] == 1
    assert out["totals"]["dropped_by_reason"] == {"rate_gate": 2, "queue_full": 1}
    assert out["totals"]["alerts"] == 1
    assert out["control_run_id"] == "ctrl-a"
    assert out["topology"] == "single_host"


def test_image_folder_run_keys_axis_by_unit_id_when_frame_index_is_none():
    """Fix wave 2: en corridas image_folder, frame_index es None en las 4
    fuentes (las imagenes no son frames de video). El eje debe seguir
    keyeando por unit_id en vez de colapsar a una sola fila None (bug real
    cazado por el smoke E2E: 4 detecciones + 4 descartes -> total: 1)."""

    def _img_det(uid, labels):
        return {
            "unit_id": uid,
            "source": {"frame_index": None, "timestamp_ms": None},
            "detections": [{"label": label, "confidence": 0.9} for label in labels],
        }

    out = compose_trace(
        detections=[
            _img_det("img_000000", ["person"]),
            _img_det("img_000002", ["helmet"]),
        ],
        dropped=[
            {"frame_index": None, "unit_id": "img_000001", "reason": "rate_gate"},
            {"frame_index": None, "unit_id": "img_000003", "reason": "queue_full"},
        ],
        progress=[],
        alerts=[{"frame_index": None, "unit_id": "img_000002", "condition_id": "CR-01", "severity": "high"}],
        received_unit_ids={"img_000000", "img_000002"},
        control_run_id="ctrl-a", topology="single_host",
    )
    frames = out["frames"]
    assert [f["unit_id"] for f in frames] == [
        "img_000000", "img_000001", "img_000002", "img_000003",
    ]
    assert all(f["frame_index"] is None for f in frames)
    assert out["totals"]["frames"] == 4
    assert frames[2]["unit_id"] == "img_000002"
    assert frames[2]["alert"][0]["condition_id"] == "CR-01"
    assert frames[1]["control"] == "dropped:rate_gate"


def test_frame_without_progress_or_alert_defaults_to_empty_lists():
    out = compose_trace(
        detections=[_det(0, "u0", ["person"])], dropped=[], progress=[], alerts=[],
        received_unit_ids={"u0"}, control_run_id="ctrl-a", topology="single_host",
    )
    assert out["frames"][0]["progress"] == []
    assert out["frames"][0]["alert"] == []


# --- active_patterns: reconstruccion del intervalo confirmed->resolved -----
#
# El bug real que motiva esto: alerts.jsonl solo tiene el flanco de subida
# (confirmed) y pattern_progress.jsonl solo tiene "candidate" -- ningun frame
# INTERMEDIO entre la confirmacion y la resolucion tenia ninguna senal en la
# traza, aunque el riesgo siguiera objetivamente activo (frame_000456 de una
# corrida real: CR-01 ya estaba "sustained" y la UI no mostraba nada).
# pattern_events.jsonl es la unica fuente con el ciclo completo
# candidate->confirmed->sustained->resolved; compose_trace lo pliega hacia
# adelante en el eje de frames ya ordenado.

def _pe(uid, pattern_id, state, subject_key="k1", condition_id=None, severity="high"):
    return {
        "unit_id": uid, "pattern_id": pattern_id, "state": state,
        "subject_key": subject_key, "condition_id": condition_id or pattern_id,
        "severity": severity,
    }


def test_active_patterns_persists_through_intervening_frames_until_resolved():
    out = compose_trace(
        detections=[_det(i, f"u{i}", ["person"]) for i in range(5)],
        dropped=[], progress=[], alerts=[],
        pattern_events=[
            _pe("u1", "CR-01", "confirmed"),
            _pe("u2", "CR-01", "sustained"),
            # u3: sin evento propio -- el riesgo sigue activo igual (era el bug)
            _pe("u4", "CR-01", "resolved"),
        ],
        received_unit_ids={f"u{i}" for i in range(5)},
        control_run_id="ctrl-a", topology="single_host",
    )
    frames = out["frames"]
    assert frames[0]["active_patterns"] == []  # antes de confirmar
    assert frames[1]["active_patterns"][0]["condition_id"] == "CR-01"  # el propio frame de confirmacion ya cuenta
    assert frames[2]["active_patterns"][0]["condition_id"] == "CR-01"
    assert frames[3]["active_patterns"][0]["condition_id"] == "CR-01"  # <- el frame sin evento propio: el gap del bug
    assert frames[4]["active_patterns"] == []  # el frame de resolved ya no esta activo


def test_active_patterns_tracks_independent_subjects_separately():
    out = compose_trace(
        detections=[_det(i, f"u{i}", ["person"]) for i in range(3)],
        dropped=[], progress=[], alerts=[],
        pattern_events=[
            _pe("u0", "CR-01", "confirmed", subject_key="personA"),
            _pe("u1", "CR-02", "confirmed", subject_key="personB", severity="medium"),
        ],
        received_unit_ids={f"u{i}" for i in range(3)},
        control_run_id="ctrl-a", topology="single_host",
    )
    frames = out["frames"]
    assert {p["subject_key"] for p in frames[2]["active_patterns"]} == {"personA", "personB"}


def test_active_patterns_defaults_to_empty_without_pattern_events():
    """Compatibilidad: los llamadores existentes (endpoint HTTP con control
    caido, tests viejos) no pasan pattern_events -- no debe romper ni requerir
    el kwarg."""
    out = compose_trace(
        detections=[_det(0, "u0", ["person"])], dropped=[], progress=[], alerts=[],
        received_unit_ids={"u0"}, control_run_id="ctrl-a", topology="single_host",
    )
    assert out["frames"][0]["active_patterns"] == []


def test_active_patterns_never_resolved_stays_active_through_last_frame():
    """Corrida cortada con el riesgo todavia activo (sin evento resolved):
    el ultimo frame de la traza tiene que seguir mostrando el patron activo."""
    out = compose_trace(
        detections=[_det(i, f"u{i}", ["person"]) for i in range(3)],
        dropped=[], progress=[], alerts=[],
        pattern_events=[_pe("u0", "CR-01", "confirmed")],
        received_unit_ids={f"u{i}" for i in range(3)},
        control_run_id="ctrl-a", topology="single_host",
    )
    assert out["frames"][-1]["active_patterns"][0]["condition_id"] == "CR-01"


def test_active_patterns_ignores_candidate_state():
    """candidate NO es riesgo confirmado todavia -- no debe aparecer como activo
    (mismo criterio que snapshot_active() del motor: solo confirmed/sustained)."""
    out = compose_trace(
        detections=[_det(0, "u0", ["person"])],
        dropped=[], progress=[], alerts=[],
        pattern_events=[_pe("u0", "CR-01", "candidate")],
        received_unit_ids={"u0"},
        control_run_id="ctrl-a", topology="single_host",
    )
    assert out["frames"][0]["active_patterns"] == []


# --- Nivel endpoint (two_plane_client) --------------------------------------


def test_trace_endpoint_merges_and_paginates(two_plane_client, control_state, fake_state):
    client = two_plane_client
    fake_state.dropped["run_done_1"] = []
    control_state.runs_index = [
        {"control_run_id": "control_run_x", "media_run_id": "run_done_1", "status": "succeeded"}
    ]
    control_state.pattern_progress["control_run_x"] = [
        {"frame_index": 0, "unit_id": "u0", "condition_id": "CR-01", "progress": 0.5,
         "elapsed_ms": 500.0, "threshold_ms": 1000.0, "mode": "time"}
    ]
    control_state.alerts["control_run_x"] = [
        {"frame_index": 1, "unit_id": "u1", "condition_id": "CR-01", "severity": "high"}
    ]
    control_state.received_units["control_run_x"] = [
        {"unit_id": "u0"}, {"unit_id": "u1"}
    ]

    r = client.get("/api/runs/run_done_1/trace", params={"page_size": 2})
    assert r.status_code == 200
    body = r.json()
    assert body["media_run_id"] == "run_done_1"
    assert body["control_run_id"] == "control_run_x"
    assert body["page"] == 1 and body["page_size"] == 2
    assert body["total"] == 5  # 5 detections en el fake, sin dropped sembrado
    assert len(body["frames"]) == 2
    assert body["frames"][0]["control"] == "received"
    assert body["frames"][0]["progress"][0]["progress"] == 0.5
    assert body["frames"][1]["control"] == "received"
    assert body["frames"][1]["alert"][0]["condition_id"] == "CR-01"
    assert body["control_error"] is None


def test_trace_endpoint_page_2_slices_correctly(two_plane_client, fake_state):
    """M5(a): la aritmetica de paginacion del endpoint (start = (page-1)*page_size)
    sobre las 5 detecciones del fake, sin dropped."""
    fake_state.dropped["run_done_1"] = []

    r = two_plane_client.get("/api/runs/run_done_1/trace", params={"page": 2, "page_size": 2})
    assert r.status_code == 200
    body = r.json()
    assert body["page"] == 2 and body["page_size"] == 2
    assert body["total"] == 5  # invariante: el total no depende de la pagina pedida
    assert [f["frame_index"] for f in body["frames"]] == [2, 3]


def test_trace_endpoint_interleaves_dropped_and_detections_via_http(two_plane_client, fake_state):
    """M5(b): el interleave del eje compuesto (detections + dropped, ordenado por
    frame_index) hoy solo se prueba en el unit de compose_trace; este ejercita el
    mismo caso a traves del endpoint HTTP real."""
    fake_state.dropped["run_done_1"] = [
        {"frame_index": 1.5, "unit_id": "ud1", "reason": "rate_gate"},
        {"frame_index": 3.5, "unit_id": "ud2", "reason": "queue_full"},
    ]

    r = two_plane_client.get("/api/runs/run_done_1/trace", params={"page_size": 100})
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 7  # 5 detections + 2 dropped
    frame_indexes = [f["frame_index"] for f in body["frames"]]
    assert frame_indexes == [0, 1, 1.5, 2, 3, 3.5, 4]
    dropped_frame = body["frames"][frame_indexes.index(1.5)]
    assert dropped_frame["control"] == "dropped:rate_gate"
    assert dropped_frame["detections"] is None


def test_trace_endpoint_control_down_degrades_to_nd(two_plane_client, fake_state):
    """Monkeypatch de `control_backend.list_runs` (mismo patron que
    test_experiment_alerts_report.py::test_alerts_502_service_unavailable):
    simula el control-plane caido sin depender de la red real."""
    fake_state.dropped["run_done_1"] = []

    async def boom(media_run_id: str | None = None):
        raise ControlServiceUnavailable("control-plane caido")

    two_plane_client.app.state.control_backend.list_runs = boom

    r = two_plane_client.get("/api/runs/run_done_1/trace")
    assert r.status_code == 200
    body = r.json()
    assert body["control_error"] is not None
    assert all(f["control"] == "n/d" for f in body["frames"])


def test_trace_endpoint_control_run_id_override_respected(
    two_plane_client, control_state, fake_state
):
    client = two_plane_client
    fake_state.dropped["run_done_1"] = []
    # runs_index NO tiene entrada para run_done_1: sin override, lookup da [].
    control_state.pattern_progress["ctrl-explicit"] = []
    control_state.alerts["ctrl-explicit"] = []
    control_state.received_units["ctrl-explicit"] = [{"unit_id": "u0"}]

    r = client.get("/api/runs/run_done_1/trace", params={"control_run_id": "ctrl-explicit"})
    assert r.status_code == 200
    body = r.json()
    assert body["control_run_id"] == "ctrl-explicit"
    assert body["control_error"] is None


def test_trace_endpoint_unknown_control_run_id_degrades_not_404(
    two_plane_client, fake_state
):
    """`control_run_id` explicito que el control-plane no conoce (no en
    runs_index/pattern_progress/received_units/alerts, ver `_known_run` del
    fake) -> ControlUnknownRun en la lectura -> degradacion (spec §6), NUNCA
    un 404 del trace (eso es solo para el run de medios inexistente)."""
    fake_state.dropped["run_done_1"] = []

    r = two_plane_client.get(
        "/api/runs/run_done_1/trace", params={"control_run_id": "ctrl-nope"}
    )
    assert r.status_code == 200
    body = r.json()
    assert body["control_run_id"] is None
    assert body["control_error"] is None
    assert all(f["control"] == "n/d" for f in body["frames"])


def test_trace_endpoint_unknown_media_run_404(two_plane_client):
    r = two_plane_client.get("/api/runs/nope/trace")
    assert r.status_code == 404


def test_trace_endpoint_active_patterns_via_http(two_plane_client, control_state, fake_state):
    """Ejercita active_patterns a traves del endpoint HTTP real: el fake sirve
    pattern-events, el router lo pasa a compose_trace."""
    client = two_plane_client
    fake_state.dropped["run_done_1"] = []
    control_state.runs_index = [
        {"control_run_id": "control_run_x", "media_run_id": "run_done_1", "status": "succeeded"}
    ]
    control_state.pattern_progress["control_run_x"] = []
    control_state.alerts["control_run_x"] = [
        {"frame_index": 1, "unit_id": "u1", "condition_id": "CR-01", "severity": "high"}
    ]
    control_state.pattern_events["control_run_x"] = [
        {"unit_id": "u1", "pattern_id": "CR-01", "condition_id": "CR-01",
         "severity": "high", "subject_key": "k1", "state": "confirmed"},
    ]
    control_state.received_units["control_run_x"] = [{"unit_id": f"u{i}"} for i in range(5)]

    r = client.get("/api/runs/run_done_1/trace", params={"page_size": 100})
    assert r.status_code == 200
    frames = r.json()["frames"]
    # u1 confirma; u2..u4 no tienen evento propio pero el riesgo sigue activo
    assert frames[1]["active_patterns"][0]["condition_id"] == "CR-01"
    assert frames[3]["active_patterns"][0]["condition_id"] == "CR-01"
