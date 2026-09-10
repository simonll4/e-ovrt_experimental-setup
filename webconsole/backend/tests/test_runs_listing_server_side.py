"""Filtrado, orden y paginación del listado de corridas, del lado del servidor.

Antes `listRuns()` traía todo y el cliente filtraba y ordenaba en memoria: anda
con nueve corridas y no escala. Además el filtro se aplica ANTES de hidratar, así
que buscar entre cien corridas ya no cuesta cien lecturas al motor de detección.

El contrato sigue siendo una lista y el total va en `X-Total-Count`, para no
romper a los consumidores por un dato que solo necesita la paginación.
"""

from eovrt_webconsole.routers.runs import _clave_de_orden, _coincide, _ordenar


class TestBusqueda:
    def test_busca_en_el_identificador_y_en_el_nombre(self):
        fila = {"run_id": "run_20260729_143641_x", "name": "Barrido largo — patio norte"}
        assert _coincide(fila, "143641")
        assert _coincide(fila, "patio")
        assert not _coincide(fila, "portón")

    def test_una_corrida_sin_nombre_no_revienta(self):
        assert _coincide({"run_id": "run_1", "name": None}, "run_1")


class TestOrden:
    @staticmethod
    def _valores(direccion):
        filas = [
            {"total_detections": 10},
            {"total_detections": None},
            {"total_detections": 884},
        ]
        _ordenar(filas, "total_detections", direccion)
        return [f["total_detections"] for f in filas]

    def test_ordena_ascendente_con_el_nulo_al_final(self):
        assert self._valores("asc") == [10, 884, None]

    def test_ordena_descendente_con_el_nulo_TAMBIEN_al_final(self):
        # Regresión: `reverse=True` invierte la clave entera, incluido el
        # indicador de "tiene valor", así que el nulo encabezaba el listado. Una
        # corrida fallida tiene casi todas las métricas en null: ordenar por
        # detecciones de mayor a menor mostraba primero las que no detectaron
        # nada, que es lo contrario de lo que se está pidiendo ver.
        assert self._valores("desc") == [884, 10, None]

    def test_el_texto_se_compara_sin_distinguir_mayusculas(self):
        assert _clave_de_orden({"name": "Zeta"}, "name") > _clave_de_orden({"name": "alfa"}, "name")


class TestEndpoint:
    def test_devuelve_una_lista_y_el_total_en_la_cabecera(self, client):
        r = client.get("/api/runs")
        assert r.status_code == 200
        assert isinstance(r.json(), list)
        assert r.headers["X-Total-Count"].isdigit()

    def test_filtra_por_estado(self, client):
        todas = client.get("/api/runs")
        terminadas = client.get("/api/runs?estado=succeeded")
        assert all(f["status"] == "succeeded" for f in terminadas.json())
        assert int(terminadas.headers["X-Total-Count"]) <= int(todas.headers["X-Total-Count"])

    def test_un_estado_inexistente_no_devuelve_nada_y_lo_dice(self, client):
        r = client.get("/api/runs?estado=no_existe")
        assert r.json() == []
        assert r.headers["X-Total-Count"] == "0"

    def test_pagina(self, client):
        r = client.get("/api/runs?page_size=1&pagina=1")
        assert len(r.json()) <= 1
        # El total es el del conjunto filtrado, no el de la página.
        assert int(r.headers["X-Total-Count"]) >= len(r.json())

    def test_una_pagina_mas_alla_del_final_viene_vacia(self, client):
        r = client.get("/api/runs?page_size=10&pagina=999")
        assert r.json() == []
        assert r.status_code == 200

    def test_un_campo_de_orden_desconocido_no_es_un_error(self, client):
        # Cae al orden por defecto en vez de 422: un parámetro viejo en un
        # marcador no debería dejar la pantalla sin listado.
        assert client.get("/api/runs?orden=inventado").status_code == 200

    def test_ordena_por_un_campo_que_requiere_hidratar(self, client):
        r = client.get("/api/runs?orden=total_detections&direccion=desc")
        assert r.status_code == 200
        valores = [f.get("total_detections") for f in r.json() if f.get("total_detections")]
        assert valores == sorted(valores, reverse=True)

    def test_las_corridas_sin_la_metrica_quedan_al_final(self, client, fake_state):
        # Una corrida en curso todavía no tiene métricas: junto con las fallidas,
        # es el caso que encabezaba el listado al ordenar de mayor a menor.
        fake_state.active_run_id = "run_active_1"
        r = client.get("/api/runs?orden=total_detections&direccion=desc")
        valores = [f.get("total_detections") for f in r.json()]
        con_valor = [v for v in valores if v is not None]
        # Sin un nulo en el conjunto no habría nada que comprobar y el test
        # pasaría por vacío: se afirma que el caso está representado.
        assert len(con_valor) < len(valores), "la fixture no tiene ninguna corrida sin métrica"
        # Ningún nulo intercalado: todos después del último valor medido.
        assert valores[: len(con_valor)] == con_valor
