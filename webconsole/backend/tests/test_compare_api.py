from tests.fake_service import EVAL_RESULT


def _seed_second_eval(fake_state, run_id="run_other"):
    fake_state.eval_results[run_id] = {
        **EVAL_RESULT,
        "run_id": run_id,
        "model": "yoloe",
        "mAP50": 0.3,
        "cr01_detection_recall": 0.1,
        "per_class": [
            {"class_name": "person", "AP50": 0.68, "n_gt": 82, "n_det": 80},
            {"class_name": "helmet", "AP50": 0.55, "n_gt": 60, "n_det": 65},
            {"class_name": "vest", "AP50": None, "n_gt": 0, "n_det": 4},
            {"class_name": "bare_head", "AP50": 0.1, "n_gt": 12, "n_det": 9},
        ],
    }


def test_compare_agrega_y_alinea_por_clase(client, fake_state):
    client.post("/api/runs/run_done_1/evaluate")
    _seed_second_eval(fake_state)

    body = client.get("/api/compare?runs=run_done_1,run_other").json()

    assert [row["run_id"] for row in body["runs"]] == ["run_done_1", "run_other"]
    assert body["runs"][0]["label"] == "mock · bench_v2_test"
    assert body["runs"][1]["model"] == "yoloe"
    assert body["classes"] == ["person", "helmet", "vest", "bare_head"]
    assert body["ap_by_class"]["person"] == [0.72, 0.68]
    assert body["ap_by_class"]["vest"] == [0.55, None]
    assert body["skipped"] == []


def test_compare_omite_runs_sin_eval(client, fake_state):
    _seed_second_eval(fake_state, run_id="run_a")
    body = client.get("/api/compare?runs=run_a,run_sin_eval").json()
    assert [row["run_id"] for row in body["runs"]] == ["run_a"]
    assert body["skipped"] == ["run_sin_eval"]


def test_compare_dedupe_preserva_orden(client, fake_state):
    _seed_second_eval(fake_state, run_id="run_a")
    body = client.get("/api/compare?runs=run_a,run_a").json()
    assert len(body["runs"]) == 1


def test_compare_tope_8_es_422(client):
    ids = ",".join(f"r{i}" for i in range(9))
    assert client.get(f"/api/compare?runs={ids}").status_code == 422


def test_compare_vacio_es_422(client):
    assert client.get("/api/compare?runs=,").status_code == 422
