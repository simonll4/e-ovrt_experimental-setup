"""Qué cambió entre un conjunto de prompts y aquel del que deriva.

`derives_from` decía de dónde viene y `changes` es una nota escrita a mano, así
que podía decir cualquier cosa (o nada). Cuando un conjunto congelado se usa como
evidencia, el cambio real tiene que poder auditarse.
"""

from eovrt_webconsole.prompt_store import diff_sets

PADRE = {
    "id": "ps_v1",
    "classes": [
        {"id": "person", "phrasings": {"default": ["una persona"]}},
        {"id": "helmet", "phrasings": {"default": ["un casco", "casco de obra"]}},
    ],
}


def test_detecta_una_clase_nueva():
    hijo = {
        "id": "ps_v2",
        "classes": [*PADRE["classes"], {"id": "vest", "phrasings": {"default": ["un chaleco"]}}],
    }
    d = diff_sets(PADRE, hijo)
    assert d["classes_added"] == ["vest"]
    assert d["classes_removed"] == []
    assert d["from"] == "ps_v1"


def test_detecta_una_clase_que_se_fue():
    hijo = {"id": "ps_v2", "classes": [PADRE["classes"][0]]}
    assert diff_sets(PADRE, hijo)["classes_removed"] == ["helmet"]


def test_detecta_frases_agregadas_y_quitadas_en_una_clase_que_sigue():
    hijo = {
        "id": "ps_v2",
        "classes": [
            {"id": "person", "phrasings": {"default": ["una persona", "alguien caminando"]}},
            {"id": "helmet", "phrasings": {"default": ["un casco"]}},
        ],
    }
    d = diff_sets(PADRE, hijo)
    assert d["phrases_added"] == {"person": ["alguien caminando"]}
    assert d["phrases_removed"] == {"helmet": ["casco de obra"]}


def test_no_lista_las_frases_de_una_clase_nueva():
    # Sería ruido: que la clase es nueva ya lo dice `classes_added`.
    hijo = {
        "id": "ps_v2",
        "classes": [*PADRE["classes"], {"id": "vest", "phrasings": {"default": ["un chaleco"]}}],
    }
    assert "vest" not in diff_sets(PADRE, hijo)["phrases_added"]


def test_sin_cambios_todo_vacio():
    d = diff_sets(PADRE, {**PADRE, "id": "ps_copia"})
    assert d["classes_added"] == [] and d["classes_removed"] == []
    assert d["phrases_added"] == {} and d["phrases_removed"] == {}


def test_mira_todos_los_backends_de_phrasings_no_solo_default():
    # Hoy en disco solo se usa `default`, pero el modelo permite más de uno y un
    # diff que mirara solo ese se perdería cambios reales sin avisar.
    padre = {"id": "a", "classes": [{"id": "person", "phrasings": {"default": ["x"]}}]}
    hijo = {
        "id": "b",
        "classes": [{"id": "person", "phrasings": {"default": ["x"], "yoloe": ["y"]}}],
    }
    assert diff_sets(padre, hijo)["phrases_added"] == {"person": ["y"]}


class TestEndpoint:
    def test_un_conjunto_derivado_expone_su_diff(self, client):
        client.post("/api/prompt-sets", json=PADRE | {"id": "base_v1", "status": "exploratory"})
        client.post(
            "/api/prompt-sets",
            json={
                "id": "derivado_v2",
                "status": "exploratory",
                "derives_from": "base_v1",
                "classes": [
                    {"id": "person", "phrasings": {"default": ["una persona", "alguien"]}},
                    {"id": "helmet", "phrasings": {"default": ["un casco", "casco de obra"]}},
                ],
            },
        )
        diff = client.get("/api/prompt-sets/derivado_v2").json()["diff"]
        assert diff["from"] == "base_v1"
        assert diff["phrases_added"] == {"person": ["alguien"]}

    def test_un_conjunto_sin_padre_no_trae_diff(self, client):
        client.post("/api/prompt-sets", json=PADRE | {"id": "raiz_v1", "status": "exploratory"})
        assert client.get("/api/prompt-sets/raiz_v1").json()["diff"] is None

    def test_si_el_padre_ya_no_existe_no_es_un_error(self, client):
        # Se borró o se renombró: no tener con qué comparar no debe romper la
        # pantalla, simplemente no se muestra la tarjeta de cambios.
        client.post(
            "/api/prompt-sets",
            json={
                "id": "huerfano_v1",
                "status": "exploratory",
                "derives_from": "no_existe",
                "classes": [{"id": "person", "phrasings": {"default": ["x"]}}],
            },
        )
        r = client.get("/api/prompt-sets/huerfano_v1")
        assert r.status_code == 200
        assert r.json()["diff"] is None
