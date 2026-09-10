"""El nombre legible de una condición viaja desde el motor de reglas.

Antes vivía hardcodeado en el glosario de la consola: agregar una condición o
cambiarle el nombre dejaba la interfaz mostrando el código crudo o un nombre
viejo, sin que nada avisara.
"""

import pytest


def test_expone_las_condiciones_del_motor_de_reglas(two_plane_client, control_state):
    control_state.conditions = [
        {
            "condition_id": "CR-01",
            "pattern_id": "CR-01",
            "pattern_set_id": "cr01_cr02_v2",
            "name": "person_without_helmet",
            "display_name": None,
            "description": "Persona observada sin evidencia asociada de casco.",
            "severity": "high",
            "enabled": True,
        }
    ]
    r = two_plane_client.get("/api/catalog/conditions")
    assert r.status_code == 200
    assert r.json()[0]["condition_id"] == "CR-01"
    assert r.json()[0]["severity"] == "high"


def test_si_el_motor_de_reglas_no_responde_devuelve_vacio_y_no_502(two_plane_client):
    # El catálogo es de adorno para las etiquetas: la pantalla degrada mostrando
    # el código crudo, y tumbarla entera por esto sería peor que no tener los
    # nombres.
    #
    # El fallo se fuerza sobre el backend en vez de dejar el puerto sin atender:
    # así el test no depende de que no haya un control-plane escuchando en la
    # máquina donde corre.
    async def explota() -> list[dict]:
        raise RuntimeError("motor de reglas caído")

    two_plane_client.app.state.control_backend.conditions = explota
    r = two_plane_client.get("/api/catalog/conditions")
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.parametrize("clave", ["condition_id", "name", "description", "severity"])
def test_el_contrato_incluye_lo_que_la_interfaz_necesita(two_plane_client, control_state, clave):
    control_state.conditions = [
        {
            "condition_id": "CR-02",
            "pattern_id": "CR-02",
            "pattern_set_id": "cr01_cr02_v2",
            "name": "person_without_vest",
            "display_name": None,
            "description": "Persona sin chaleco reflectante.",
            "severity": "medium",
            "enabled": True,
        }
    ]
    assert clave in two_plane_client.get("/api/catalog/conditions").json()[0]
