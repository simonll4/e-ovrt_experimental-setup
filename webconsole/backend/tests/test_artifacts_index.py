"""GET /api/runs/{id}/artifacts — inventario de lo que dejó la corrida.

Sin esto la pestaña "Archivos" solo podía pedir rutas adivinadas: no había forma
de saber qué archivos existen ni cuánto pesan.
"""


def test_lista_los_artefactos_con_tamano_y_descripcion(client):
    r = client.get("/api/runs/run_done_1/artifacts")
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["run_id"] == "run_done_1"
    por_nombre = {i["name"]: i for i in cuerpo["items"]}
    assert por_nombre["summary.json"]["size_bytes"] == 23
    assert por_nombre["summary.json"]["description"] == "Métricas de la corrida"


def test_las_previews_van_como_una_fila_con_su_cantidad(client):
    # Son una por unidad procesada: listarlas de a una convierte la respuesta en
    # miles de filas que nadie lee.
    items = client.get("/api/runs/run_done_1/artifacts").json()["items"]
    previews = next(i for i in items if i["name"] == "previews/")
    assert previews["n_files"] == 1


def test_run_inexistente_da_404(client, fake_state):
    fake_state.deleted.append("run_done_1")
    assert client.get("/api/runs/run_done_1/artifacts").status_code == 404


def test_no_choca_con_la_ruta_de_un_artefacto_puntual(client):
    """La ruta del índice se declara antes que la de `{artifact_path:path}`.

    `:path` acepta el segmento vacío, así que si se registraran al revés el
    índice caería en el handler del archivo y daría 404.
    """
    assert client.get("/api/runs/run_done_1/artifacts").status_code == 200
    assert client.get("/api/runs/run_done_1/artifacts/summary.json").status_code == 200
