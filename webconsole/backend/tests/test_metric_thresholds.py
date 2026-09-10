"""Cada métrica del reporte lleva su criterio de aceptación.

Antes el reporte decía cuánto midió pero no contra qué: la consola mostraba
"4,2 falsos positivos por hora" sin poder decir si eso pasa o no pasa, que es lo
único que se le pregunta a un experimento. El prototipo lo muestra en su propia
columna, al lado del valor medido.
"""

import pytest

from eovrt_webconsole.experiment.applicability import MetricResult
from eovrt_webconsole.experiment.report import apply_thresholds


class TestDerivacionDePassed:
    @pytest.mark.parametrize(
        "valor,umbral,direccion,esperado",
        [
            (4.2, 2.0, "max", False),   # falsos positivos por encima del límite
            (1.1, 2.0, "max", True),
            (2.0, 2.0, "max", True),    # el límite se cumple en el borde
            (0.91, 0.85, "min", True),  # exhaustividad por encima del mínimo
            (0.70, 0.85, "min", False),
            (0.85, 0.85, "min", True),
        ],
    )
    def test_compara_segun_la_direccion_del_umbral(self, valor, umbral, direccion, esperado):
        m = MetricResult(
            name="m", value=valor, status="computed",
            threshold=umbral, threshold_direction=direccion,
        )
        assert m.passed is esperado

    def test_sin_umbral_declarado_no_dictamina(self):
        assert MetricResult(name="m", value=1.0, status="computed").passed is None

    def test_una_metrica_que_no_se_pudo_medir_no_dictamina(self):
        # "sin dato" no es "no cumple": pintarla de rojo diría algo falso.
        m = MetricResult(
            name="m", status="not_applicable",
            threshold=2.0, threshold_direction="max",
        )
        assert m.passed is None


class TestAplicacionDesdeElManifiesto:
    def _resultados(self):
        return [
            MetricResult(name="far_per_hour", value=4.2, unit="1/h", status="computed"),
            MetricResult(name="recall CR-01", value=0.91, status="computed"),
            MetricResult(name="mAP", value=0.63, status="computed"),
        ]

    def test_adjunta_umbral_y_dictamen(self):
        salida = apply_thresholds(
            self._resultados(),
            {"far_per_hour": {"max": 2.0}, "recall CR-01": {"min": 0.85}},
        )
        por_nombre = {m.name: m for m in salida}
        assert por_nombre["far_per_hour"].threshold == 2.0
        assert por_nombre["far_per_hour"].passed is False
        assert por_nombre["recall CR-01"].passed is True

    def test_las_metricas_sin_criterio_quedan_intactas(self):
        salida = apply_thresholds(self._resultados(), {"far_per_hour": {"max": 2.0}})
        mapa = {m.name: m for m in salida}
        assert mapa["mAP"].threshold is None
        assert mapa["mAP"].passed is None

    def test_sin_criterios_en_el_manifiesto_devuelve_lo_mismo(self):
        original = self._resultados()
        assert apply_thresholds(original, None) == original
        assert apply_thresholds(original, {}) == original

    def test_un_criterio_mal_formado_no_rompe_el_reporte(self):
        # Ni `max` ni `min`: se ignora en vez de tumbar la generación entera.
        salida = apply_thresholds(self._resultados(), {"far_per_hour": {"cerca_de": 2.0}})
        assert {m.name: m.threshold for m in salida}["far_per_hour"] is None
