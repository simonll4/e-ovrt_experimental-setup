"""Los metrics.json NO comparten forma: un adaptador por esquema, y lo desconocido degrada."""
import json
from pathlib import Path

import pytest

from eovrt_webconsole.evidence_metrics import campo_de, leer_metricas

REPO = Path(__file__).resolve().parents[3]
CAMPANAS = sorted(p.parent for p in (REPO / 'results').glob('*/*/metrics.json'))


def test_hay_17_campanas_con_artefacto():
    """Si aparece una campaña nueva, este test lo dice antes que la pantalla."""
    assert len(CAMPANAS) == 17


@pytest.mark.parametrize('directorio', CAMPANAS, ids=lambda p: p.name)
def test_toda_campana_despacha_a_un_adaptador(directorio):
    datos = leer_metricas(directorio / 'metrics.json')
    assert datos is not None, f'esquema no reconocido en {directorio.name}'
    assert datos['cabecera'], 'un adaptador sin cabecera no sirve de nada'
    # No alcanza con "no vacía", ni con "alguno resuelve": con `any` una
    # cabecera mayormente rota —cuatro campos mal leídos de cinco— pasaba en
    # verde. Un adaptador declara qué campos lee: TODOS tienen que resolver, o
    # el adaptador está leyendo un campo que no existe en esta forma.
    nulos = [c['label'] for c in datos['cabecera'] if c['valor'] is None]
    assert not nulos, f'campos declarados por el adaptador que no resuelven: {nulos}'


def test_clip_campaign_lee_cabecera_y_desgloses():
    datos = leer_metricas(
        REPO / 'results/clip_bench/t1_gdinotiny560_v2short_scene/metrics.json')
    assert datos['esquema'] == 'clip_campaign_metrics.v1'
    cabecera = {c['label']: c['valor'] for c in datos['cabecera']}
    assert cabecera['F1 micro'] == pytest.approx(0.788732, abs=1e-6)
    ids = [d['id'] for d in datos['desgloses']]
    assert ids == ['condicion', 'escenario', 'clip', 'negativos']


def test_escenario_sin_episodios_evaluables_no_vale_cero():
    """P3 y P5 se declaran, no se cuentan como recall 0 (ADR-006/013)."""
    datos = leer_metricas(
        REPO / 'results/clip_bench/t1_gdinotiny560_v2short_scene/metrics.json')
    escenarios = next(d for d in datos['desgloses'] if d['id'] == 'escenario')
    p3 = next(f for f in escenarios['filas'] if f['nombre'] == 'P3')
    assert p3['recall'] is None
    assert p3['no_aplica'] == 'sin episodios evaluables'


def test_esquema_desconocido_degrada_a_none(tmp_path):
    path = tmp_path / 'metrics.json'
    path.write_text(json.dumps({'schema_version': 'inventado.v9', 'x': 1}))
    assert leer_metricas(path) is None


def test_campo_de_lee_una_metrica_puntual():
    valor = campo_de(
        REPO / 'results/clip_bench/g1_gdinotiny560_v2short_subject/metrics.json',
        'f1_micro')
    assert valor == pytest.approx(0.929577, abs=1e-6)


def test_talert_notification_lee_cabecera_y_sonda_no_es_fases():
    """El schema_version real es talert_notification_metrics.v1, no una sonda por 'fases'."""
    datos = leer_metricas(
        REPO / 'results/realtime/t_alert_notification/metrics.json')
    assert datos['esquema'] == 'talert_notification_metrics.v1'
    cabecera = {c['label']: c['valor'] for c in datos['cabecera']}
    assert cabecera['p95 control→MQTT'] == pytest.approx(64.5341796875, abs=1e-6)
    ids = [d['id'] for d in datos['desgloses']]
    assert ids == ['origen', 'entrega']


def test_nivel_a_gate_no_declara_esquema_y_cabecera_usa_ratio_real():
    """La sonda es estructural (gate + complementarity); el campo real es 'ratio', no 'delta'."""
    datos = leer_metricas(
        REPO / 'results/bench_nivel_a/d1_gdinotiny560_edir_vs_eind/metrics.json')
    assert datos['esquema'] == 'nivel_a_gate'
    cabecera = {c['label']: c['valor'] for c in datos['cabecera']}
    assert cabecera['bench_obra/CR-02'] == pytest.approx(0.8723008190618019, abs=1e-9)


def test_clip_person_state_desglosa_por_clip_y_condicion():
    """La forma real anida por_condicion bajo cada clip; no hay 'f1' plano en por_clip."""
    datos = leer_metricas(
        REPO / 'results/bench_nivel_a/na1_gdinotiny560_v2short_video/metrics.json')
    assert datos['esquema'] == 'clip_person_state.v1'
    por_clip = next(d for d in datos['desgloses'] if d['id'] == 'clip')
    # v01_c02/CR-02: la fuente trae f1=0.0 con recall=null (sin person-frames GT
    # positivas). El adaptador NO debe repetir ese 0.0 — "F1" es la única columna
    # de métrica del desglose y un 0.0 ahí es indistinguible de un resultado malo.
    sin_dato = next(f for f in por_clip['filas']
                     if f['nombre'] == 'v01_c02' and f['condicion'] == 'CR-02')
    assert sin_dato['no_aplica'] == 'sin person-frames GT positivas'
    assert sin_dato['f1'] is None
    # v01_c02/CR-01 sí tiene person-frames GT positivas (recall=0.59375): el valor
    # real de f1 debe pasar sin tocar.
    con_dato = next(f for f in por_clip['filas']
                     if f['nombre'] == 'v01_c02' and f['condicion'] == 'CR-01')
    assert con_dato['no_aplica'] is None
    assert con_dato['f1'] == pytest.approx(0.31666666666666665, abs=1e-9)


def test_nivel_a_gate_desglosa_en_columnas_reales_no_en_json_crudo():
    """I-1: la fila viajaba como `{"valores": {...}}` y la pantalla la imprimía
    como JSON bajo un encabezado que prometía columnas. El desglose no es
    opcional (limitación L5)."""
    datos = leer_metricas(
        REPO / 'results/bench_nivel_a/d1_gdinotiny560_edir_vs_eind/metrics.json')
    estrato = next(d for d in datos['desgloses'] if d['id'] == 'estrato')
    assert len(estrato['columnas']) == 6
    fila = next(f for f in estrato['filas'] if f['nombre'] == 'bench_obra/CR-02')
    assert 'valores' not in fila, 'el dict crudo no puede sobrevivir al adaptador'
    assert fila['variante'] == 'cr02_obs'
    assert fila['eind_misses'] == 48
    assert fila['edir_misses'] == 49
    assert fila['recuperadas'] == 9
    assert fila['fraccion'] == pytest.approx(0.1875, abs=1e-9)
    # Una columna por campo declarado: si el adaptador agrega uno y nadie toca
    # `columnas`, la pantalla cae al genérico y vuelve a imprimir JSON.
    assert len(estrato['columnas']) == len(fila) - 1  # `no_aplica` no es columna


def test_metrics_json_ausente_no_es_un_warning(caplog):
    """I-5: 18 de los 35 resultados no tienen metrics.json POR DISEÑO. Gritar
    por el caso normal enterraba el aviso que sí importa."""
    import logging
    with caplog.at_level(logging.DEBUG, logger='eovrt_webconsole.evidence_metrics'):
        assert leer_metricas(REPO / 'results/no_existe/tampoco/metrics.json') is None
    assert [r for r in caplog.records if r.levelno >= logging.WARNING] == []
    assert any(r.levelno == logging.DEBUG for r in caplog.records)


def test_metrics_json_corrupto_si_es_un_warning(tmp_path, caplog):
    import logging
    path = tmp_path / 'metrics.json'
    path.write_text('{no es json')
    with caplog.at_level(logging.WARNING, logger='eovrt_webconsole.evidence_metrics'):
        assert leer_metricas(path) is None
    assert [r for r in caplog.records if r.levelno >= logging.WARNING], \
        'un metrics.json ilegible tiene que seguir gritando'
