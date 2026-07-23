import pytest

from eovrt_webconsole.clips.window import InvalidMarks, compute_window


def test_caso_nominal_p1():
    # Evento a los 10.5 s, fin a los 24.5 s de un master de 33 s (plantilla P1).
    w = compute_window(10.5, 24.5, 33.0, "P1")
    assert w.ss == 7.0                # 10.5 - 3.5
    assert w.duration == 20.5         # (24.5 + 3) - 7
    assert w.onset_ms == 3500
    assert w.end_ms == 17500
    assert w.warnings == []


def test_pre_roll_corto_arranca_en_cero_y_avisa():
    # Evento a los 2 s: no se puede retroceder 3.5, el corte arranca en 0
    # y el onset queda en t_evento (spec §5.2).
    w = compute_window(2.0, 15.0, 33.0, "P1")
    assert w.ss == 0.0
    assert w.onset_ms == 2000
    assert any("pre-roll" in msg for msg in w.warnings)


def test_cola_corta_recorta_al_master_y_avisa():
    # Fin a 1 s del final del master: no entran los 3 s de cola.
    w = compute_window(10.5, 32.0, 33.0, "P1")
    assert w.duration == pytest.approx(33.0 - 7.0)
    assert any("cola" in msg for msg in w.warnings)


def test_clip_bajo_el_objetivo_del_escenario_avisa():
    # P2 pide ~30 s; esta ventana da ~16.5 s.
    w = compute_window(5.0, 15.0, 60.0, "P2")
    assert any("30" in msg for msg in w.warnings)


def test_escenario_sin_objetivo_no_inventa_advertencia():
    # P4 no está cuantificado en el guion: clip corto pero sin advertencia
    # de duración (las de pre-roll/cola sí aplican, acá no se disparan).
    w = compute_window(10.0, 14.0, 60.0, "P4")
    assert w.warnings == []


def test_fin_antes_del_evento_se_rechaza():
    with pytest.raises(InvalidMarks):
        compute_window(20.0, 10.0, 33.0, "P1")


def test_fin_igual_al_evento_se_rechaza():
    with pytest.raises(InvalidMarks):
        compute_window(20.0, 20.0, 33.0, "P1")


def test_marcas_fuera_del_master_se_rechazan():
    with pytest.raises(InvalidMarks):
        compute_window(-1.0, 10.0, 33.0, "P1")
    with pytest.raises(InvalidMarks):
        compute_window(10.0, 40.0, 33.0, "P1")
