import pytest

from eovrt_webconsole.clips.window import InvalidMarks, compute_window, compute_window_multi


def test_caso_nominal_p1():
    # Evento a los 10.5 s, fin a los 24.5 s de un master de 33 s (plantilla P1).
    w = compute_window(10.5, 24.5, 33.0, "P1")
    assert w.ss == 7.0                # 10.5 - 3.5
    assert w.duration == 20.5         # (24.5 + 3) - 7
    assert w.episodes[0].onset_ms == 3500
    assert w.episodes[0].end_ms == 17500
    assert w.episodes[0].condition == "CR-01"
    assert w.warnings == []


def test_pre_roll_corto_arranca_en_cero_y_avisa():
    # Evento a los 2 s: no se puede retroceder 3.5, el corte arranca en 0
    # y el onset queda en t_evento (spec §5.2).
    w = compute_window(2.0, 15.0, 33.0, "P1")
    assert w.ss == 0.0
    assert w.episodes[0].onset_ms == 2000
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


def test_escenario_sin_objetivo_no_inventa_advertencia_de_guion():
    # P4 no tiene "objetivo de guion" en SCENARIO_TARGET_S, pero SÍ tiene cola de
    # 10 s y piso de censura (CR-01, 17.5 s) — con margen, ningún warning.
    w = compute_window(10.0, 20.0, 60.0, "P4")
    assert w.ss == 6.5                 # 10.0 - 3.5
    assert w.duration == 23.5          # (20.0 + 10.0) - 6.5
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


def test_piso_s_por_condicion():
    from eovrt_webconsole.clips.window import piso_s
    assert piso_s("P1") == 17.5   # CR-01: 3.5 + 10.0 + 2.0 + 2.0
    assert piso_s("P2") == 28.5   # CR-02: 3.5 + 20.0 + 3.0 + 2.0
    assert piso_s("P4") == 17.5   # CR-01, misma condición que P1
    assert piso_s("P7") == 17.5   # CR-01
    assert piso_s("P9") == 17.5   # CR-01
    assert piso_s("P3") is None   # sin episodio: sub-umbral
    assert piso_s("P5") is None   # sin episodio: negativo


def test_p1_por_debajo_del_piso_avisa_censura():
    # Evento de 8 s: D = 8 + 6.5 = 14.5 s, por debajo del piso de 17.5 s.
    w = compute_window(10.0, 18.0, 60.0, "P1")
    assert any("piso" in msg and "censur" in msg for msg in w.warnings)


def test_p1_sobre_el_piso_pero_bajo_el_objetivo_solo_avisa_objetivo():
    # D = 18.5 s: por encima del piso (17.5) pero por debajo del objetivo (20).
    w = compute_window(10.0, 22.0, 60.0, "P1")
    assert not any("piso" in msg and "censur" in msg for msg in w.warnings)
    assert any("20" in msg for msg in w.warnings)


def test_p1_sobre_ambos_no_avisa_nada():
    w = compute_window(10.5, 24.5, 33.0, "P1")
    assert w.warnings == []


def test_p3_p5_nunca_avisan_censura_aunque_el_clip_sea_muy_corto():
    # Sin condición (P3, P5) no hay piso: solo puede avisar el objetivo de guion.
    w3 = compute_window(5.0, 6.0, 60.0, "P3")
    assert not any("censur" in msg for msg in w3.warnings)
    w5 = compute_window(5.0, 6.0, 60.0, "P5")
    assert not any("censur" in msg for msg in w5.warnings)


def test_p2_usa_cola_de_cinco_segundos():
    w = compute_window(10.0, 20.0, 60.0, "P2")
    assert w.duration == 18.5   # (20.0 + 5.0) - 6.5, no (20.0 + 3.0) - 6.5 = 16.5


def test_p7_y_p9_tambien_avisan_censura_sin_objetivo_cargado():
    # P7/P9 no tienen "objetivo de guion" en SCENARIO_TARGET_S salvo P9 (18 s);
    # ambos SÍ tienen que avisar el piso si el clip queda corto.
    w7 = compute_window(10.0, 15.0, 60.0, "P7")   # D = 5+6.5 = 11.5 < 17.5
    assert any("piso" in msg and "censur" in msg for msg in w7.warnings)
    w9 = compute_window(10.0, 15.0, 60.0, "P9")   # D = 5+6.5 = 11.5 < 17.5
    assert any("piso" in msg and "censur" in msg for msg in w9.warnings)


def test_episodes_de_un_escenario_sin_condicion_llevan_none():
    w = compute_window(5.0, 6.0, 60.0, "P3")
    assert w.episodes[0].condition is None


def test_p6_p8_con_dos_marcas_se_rechazan():
    with pytest.raises(InvalidMarks):
        compute_window(10.0, 20.0, 90.0, "P6")
    with pytest.raises(InvalidMarks):
        compute_window(10.0, 20.0, 90.0, "P8")


def test_p6_nominal_con_los_tiempos_guionados():
    # t1=10 (casco fuera), t2=13 (chaleco fuera, +3), t3=23 (chaleco puesto),
    # t4=33 (casco puesto). El episodio CR-02 (chaleco) queda ANIDADO dentro
    # del CR-01 (casco): [t1,t4] vs [t2,t3] — doc operacion/72 §4.6.
    w = compute_window_multi([10.0, 13.0, 23.0, 33.0], master_duration=90.0, scenario="P6")
    assert w.ss == 6.5   # 10.0 - 3.5
    assert len(w.episodes) == 2
    assert w.episodes[0].condition == "CR-01"
    assert w.episodes[0].onset_ms == 3500        # t1 - ss = 3.5s
    assert w.episodes[0].end_ms == 26500         # t4 - ss = 26.5s
    assert w.episodes[1].condition == "CR-02"
    assert w.episodes[1].onset_ms == 6500        # t2 - ss = 6.5s
    assert w.episodes[1].end_ms == 16500         # t3 - ss = 16.5s
    # cobertura = (33-10) + 6.5 = 29.5 ; piso CR-02 = 6.5 + 25 + 1 = 32.5 ; D = 32.5
    assert w.duration == pytest.approx(32.5)


def test_p8_nominal_con_los_tiempos_guionados():
    # t1=10 (casco fuera), t2=15 (sale de cuadro), t3=23 (vuelve, t3-t1=13),
    # t4=31 (casco puesto, t4-t1=21).
    w = compute_window_multi([10.0, 15.0, 23.0, 31.0], master_duration=90.0, scenario="P8")
    assert w.ss == 6.5
    assert w.episodes[0].condition == "CR-01"
    assert w.episodes[1].condition == "CR-01"
    assert w.episodes[1].onset_ms == 16500   # 3.5 + (23-10)
    # cobertura = (31-10)+6.5 = 27.5 ; piso ep2 = 16.5+14+1 = 31.5 ; D = 31.5
    assert w.duration == pytest.approx(31.5)


def test_multi_requiere_exactamente_cuatro_marcas():
    with pytest.raises(InvalidMarks):
        compute_window_multi([10.0, 20.0, 30.0], master_duration=90.0, scenario="P6")


def test_multi_rechaza_marcas_no_crecientes():
    with pytest.raises(InvalidMarks):
        compute_window_multi([10.0, 9.0, 20.0, 30.0], master_duration=90.0, scenario="P6")


def test_multi_rechaza_marcas_repetidas():
    with pytest.raises(InvalidMarks):
        compute_window_multi([10.0, 10.0, 20.0, 30.0], master_duration=90.0, scenario="P6")


def test_multi_rechaza_escenario_de_un_episodio():
    with pytest.raises(InvalidMarks):
        compute_window_multi([10.0, 13.0, 23.0, 33.0], master_duration=90.0, scenario="P1")


def test_multi_marcas_fuera_del_master_se_rechazan():
    with pytest.raises(InvalidMarks):
        compute_window_multi([10.0, 13.0, 23.0, 100.0], master_duration=90.0, scenario="P6")


def test_multi_clampea_si_el_master_no_alcanza_y_avisa():
    # El piso pide 32.5 s de duración, pero el master solo tiene 28.5 s desde ss.
    w = compute_window_multi([10.0, 13.0, 23.0, 33.0], master_duration=35.0, scenario="P6")
    assert w.duration == pytest.approx(28.5)   # 35.0 - 6.5
    assert any("no tiene" in msg for msg in w.warnings)
