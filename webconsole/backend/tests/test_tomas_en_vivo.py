"""«Tomas en vivo» (plan de la consola de evidencia, §6): las sesiones guardadas agrupadas por la prueba en
la que cuentan; lo demás aparte, con su motivo."""
from __future__ import annotations

import json
from pathlib import Path

from eovrt_webconsole.tomas_en_vivo import MOTIVO, TomasEnVivo


def _escribir(ruta: Path, datos) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(datos), encoding="utf-8")


def _armar(tmp_path: Path):
    gen2 = tmp_path / "results" / "gen2"
    _escribir(gen2 / "RT-04" / "evals" / "tomas.json", [
        {"session_id": "s_p1", "escena": "P1", "remera": "blanca lisa", "como_se_esperaba": True,
         "sujeto": {"como_se_esperaba": False}},
        {"session_id": "s_ausente", "escena": "P2", "como_se_esperaba": False},
    ])
    _escribir(gen2 / "RT-04" / "descartes.json", {"s_desc": {"motivo": "Causa física.", "quien": "equipo"}})
    _escribir(gen2 / "RT-04" / "resultado.json", {"metricas": {"no_evaluables": [
        {"session_id": "s_amarillo", "motivo": "otro chaleco"}]}})
    _escribir(gen2 / "RT-09" / "resultado.json", {"metricas": {"grupos": [
        {"escena": "P2", "remera": "negra lisa", "modo": "campeon", "motor": "mp-gdino-tiny-560", "session_ids": ["s_prenda"]}]}})
    sesiones_dir = tmp_path / "sesiones"
    guardadas = {
        "s_p1": {"escena": "P1"}, "s_desc": {"escena": "P1"}, "s_amarillo": {"escena": "P1"}, "s_prenda": {"escena": "P2"},
        "s_cal": {"escena": "CAL"}, "s_ensayo": {"escena": "DEMO", "exploracion": {"motor": "x"}},
        "s_marca_ensayo": {"escena": "P2"}, "s_modo": {"escena": "P2", "modo_prompts": {"id": "edir"}}, "s_suelta": {"escena": "P4"},
    }
    for sid in guardadas:
        (sesiones_dir / sid).mkdir(parents=True)
    _escribir(sesiones_dir / "s_marca_ensayo" / "marcas.json", {"proposito": "ensayo"})

    def sesiones():
        return [{"session_id": sid, "iniciada_en": None, **datos} for sid, datos in guardadas.items()]

    def carpeta(sid):
        c = sesiones_dir / sid
        return c if c.is_dir() else None

    return TomasEnVivo(gen2, sesiones, carpeta).vista()


def test_agrupa_por_prueba_lo_que_dejo_escrito_el_programa(tmp_path):
    v = _armar(tmp_path)
    pruebas = {p["id"]: p["tomas"] for p in v["pruebas"]}
    assert [p["id"] for p in v["pruebas"]] == ["RT-04", "RT-05", "RT-06", "RT-07", "RT-08", "RT-09"]
    p1, ausente = pruebas["RT-04"]
    assert (p1["escena"], p1["como_se_esperaba"], p1["sujeto_como_se_esperaba"], p1["disponible"]) == ("P1", True, False, True)
    # Una toma que cuenta pero cuya carpeta no está en este equipo sigue en la lista, marcada.
    assert (ausente["session_id"], ausente["disponible"]) == ("s_ausente", False)
    # RT-09 no deja tomas.json: sus tomas salen de los grupos del resultado.
    assert pruebas["RT-09"] == [{"session_id": "s_prenda", "escena": "P2", "remera": "negra lisa", "motor": "mp-gdino-tiny-560",
                                 "modo": "campeon", "stream": None, "camara": None, "como_se_esperaba": None,
                                 "sujeto_como_se_esperaba": None, "disponible": True}]
    assert pruebas["RT-05"] == []


def test_lo_que_no_cuenta_lleva_su_motivo(tmp_path):
    otras = {o["session_id"]: o for o in _armar(tmp_path)["otras"]}
    assert "s_p1" not in otras and "s_prenda" not in otras
    assert (otras["s_desc"]["tipo"], otras["s_desc"]["motivo"], otras["s_desc"]["quien"], otras["s_desc"]["prueba"]) == (
        "descartada", "Causa física.", "equipo", "RT-04")
    assert (otras["s_cal"]["tipo"], otras["s_cal"]["motivo"]) == ("calibracion", MOTIVO["calibracion"])
    assert otras["s_ensayo"]["tipo"] == "ensayo" and otras["s_marca_ensayo"]["tipo"] == "ensayo"
    assert otras["s_modo"]["tipo"] == "exploracion"
    assert (otras["s_amarillo"]["tipo"], otras["s_amarillo"]["motivo"]) == ("no_evaluable", "otro chaleco")
    assert otras["s_suelta"]["tipo"] == "sin_prueba"


def test_la_ruta_responde(client):
    d = client.get("/api/tomas").json()
    assert [p["id"] for p in d["pruebas"]][:1] == ["RT-04"] and "otras" in d
