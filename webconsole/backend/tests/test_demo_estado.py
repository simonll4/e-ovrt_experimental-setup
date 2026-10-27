"""Demo: las caras de cada tarjeta derivadas de `episodes[]` del control-plane."""
from __future__ import annotations

from eovrt_webconsole.demo.estado import HOLD_RESUELTA_S, Derivador


def _ep(condicion: str, state: str, **kw) -> dict:
    base = {"condition_id": condicion, "state": state, "severity": "high",
            "elapsed_ms": None, "confirm_after_ms": 4000.0,
            "clear_elapsed_ms": None, "resolve_after_ms": 2000.0}
    return {**base, **kw}


def _cara(derivador: Derivador, condicion: str) -> dict:
    return next(c for c in derivador.foto() if c["condicion"] == condicion)


def test_sin_episodios_todo_ok():
    d = Derivador()
    assert d.actualizar([], 0.0) == []
    assert [c["estado"] for c in d.foto()] == ["ok", "ok"]
    assert [c["nombre"] for c in d.foto()] == ["Casco", "Chaleco"]


def test_candidate_es_confirmando_con_su_avance():
    d = Derivador()
    d.actualizar([_ep("CR-01", "candidate", elapsed_ms=2100.0)], 1.0)
    cara = _cara(d, "CR-01")
    assert cara["estado"] == "confirmando"
    assert (cara["transcurrido_ms"], cara["umbral_ms"]) == (2100.0, 4000.0)
    assert cara["alertas"] == 0


def test_confirmed_es_alerta_y_cuenta_una_alerta():
    d = Derivador()
    d.actualizar([_ep("CR-01", "candidate", elapsed_ms=3000.0)], 1.0)
    trans = d.actualizar([_ep("CR-01", "confirmed", elapsed_ms=4100.0)], 2.0)
    assert trans == [{"condicion": "CR-01", "de": "confirmando", "a": "alerta"}]
    cara = _cara(d, "CR-01")
    assert cara["estado"] == "alerta" and cara["alertas"] == 1 and cara["alerta_desde"] == 2.0


def test_resolviendo_y_volver_a_alerta_no_es_otra_alerta():
    d = Derivador()
    d.actualizar([_ep("CR-02", "confirmed")], 1.0)
    d.actualizar([_ep("CR-02", "sustained", clear_elapsed_ms=800.0, resolve_after_ms=3000.0)], 2.0)
    cara = _cara(d, "CR-02")
    assert cara["estado"] == "resolviendo"
    assert (cara["transcurrido_ms"], cara["umbral_ms"]) == (800.0, 3000.0)
    # Reaparece la infracción antes de resolver: el motor no re-alerta (histéresis).
    d.actualizar([_ep("CR-02", "sustained")], 3.0)
    assert _cara(d, "CR-02")["estado"] == "alerta"
    assert _cara(d, "CR-02")["alertas"] == 1


def test_resuelta_se_muestra_cinco_segundos_y_vuelve_a_ok():
    d = Derivador()
    d.actualizar([_ep("CR-01", "confirmed")], 10.0)
    d.actualizar([], 11.0)
    assert _cara(d, "CR-01")["estado"] == "resuelta"
    d.actualizar([], 11.0 + HOLD_RESUELTA_S - 0.1)
    assert _cara(d, "CR-01")["estado"] == "resuelta"
    d.actualizar([], 11.0 + HOLD_RESUELTA_S + 0.1)
    assert _cara(d, "CR-01")["estado"] == "ok"


def test_un_candidato_que_se_cae_vuelve_a_ok_sin_resuelta():
    d = Derivador()
    d.actualizar([_ep("CR-01", "candidate", elapsed_ms=900.0)], 1.0)
    d.actualizar([], 2.0)
    assert _cara(d, "CR-01")["estado"] == "ok"


def test_una_segunda_infraccion_cuenta_otra_alerta():
    d = Derivador()
    d.actualizar([_ep("CR-01", "confirmed")], 1.0)
    d.actualizar([], 2.0)  # resuelta
    d.actualizar([_ep("CR-01", "confirmed")], 30.0)
    assert _cara(d, "CR-01")["alertas"] == 2


def test_con_varios_sujetos_gana_el_mas_avanzado():
    d = Derivador()
    d.actualizar(
        [_ep("CR-01", "candidate", elapsed_ms=100.0), _ep("CR-01", "confirmed")], 1.0
    )
    assert _cara(d, "CR-01")["estado"] == "alerta"
