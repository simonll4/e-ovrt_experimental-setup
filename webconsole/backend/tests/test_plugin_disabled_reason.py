"""El catálogo dice POR QUÉ un origen no se puede usar, no solo que no se puede.

Antes la interfaz solo podía mostrar "no soportado", que no distingue "la consola
no lo ofrece" de "falta instalar un SDK en el motor de detección" — que es lo
único de los dos sobre lo que alguien puede hacer algo.

Las cuatro ramas se prueban sobre la función pura: el catálogo de la fake declara
sus plugins como constantes, y no se le puede pedir a un mismo `client` que vea
el mismo plugin disponible y no disponible a la vez.
"""

from eovrt_webconsole.routers.catalog import _disabled_reason

SOPORTADOS = frozenset({"image_folder", "video_file", "rtsp", "oak_d"})


def test_disponible_y_soportado_no_lleva_motivo():
    assert _disabled_reason({"id": "image_folder", "available": True}, SOPORTADOS) is None


def test_no_soportado_por_la_consola():
    # Gana sobre `available`: aunque el servicio lo ofrezca, la consola no lo usa.
    plugin = {"id": "thermal_cam", "available": True}
    assert _disabled_reason(plugin, SOPORTADOS) == "La consola no ofrece este origen"


def test_soportado_pero_no_disponible_propaga_el_motivo_del_servicio():
    plugin = {
        "id": "oak_d",
        "available": False,
        "unavailable_reason": "Falta el SDK DepthAI en el motor de detección",
    }
    assert _disabled_reason(plugin, SOPORTADOS) == "Falta el SDK DepthAI en el motor de detección"


def test_sin_motivo_del_servicio_cae_a_un_texto_generico():
    # Un servicio viejo (o un plugin nuevo) puede no mandar `unavailable_reason`:
    # la interfaz igual tiene que poder decir algo.
    assert (
        _disabled_reason({"id": "oak_d", "available": False}, SOPORTADOS)
        == "No disponible en el motor de detección"
    )


def test_el_endpoint_expone_el_motivo_junto_a_enabled(client):
    plugins = {p["id"]: p for p in client.get("/api/catalog/ingest-plugins").json()}
    # thermal_cam es el único que la fake declara fuera del soporte de la consola.
    assert plugins["thermal_cam"]["enabled"] is False
    assert plugins["thermal_cam"]["disabled_reason"] == "La consola no ofrece este origen"
    assert plugins["image_folder"]["enabled"] is True
    assert plugins["image_folder"]["disabled_reason"] is None
