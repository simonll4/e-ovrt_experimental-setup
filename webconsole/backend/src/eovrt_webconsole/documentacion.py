"""La documentación de la consola, leída del disco local.

Como `/api/evidencia`, no importa ningún cliente de los servicios: la pantalla
tiene que funcionar con los tres planos apagados.

La regla que gobierna este módulo: **un término sin definición no se ofrece
como término**. El índice plano `terminos` es lo único que la pantalla consulta
para decidir si algo se marca; lo que no está ahí se renderiza como texto plano
en vez de como un enlace que no dice nada.

Los conteos (`conteo_de`) los completa el servidor contra el registro de
evidencia, nunca el YAML: un número escrito a mano en un archivo de texto
envejece en silencio en cuanto el inventario crece.
"""
from __future__ import annotations

from pathlib import Path

import yaml

from eovrt_webconsole.evidence_archive import EvidenceArchive

TEXTO = ("titulo", "bajada", "hizo", "porque", "quedo", "que_es", "que_suma",
         "definicion", "nota", "en_la_consola", "es", "termino", "de", "nivel")


def _limpiar(valor):
    """Los bloques plegados de YAML traen saltos y espacios de más."""
    if isinstance(valor, str):
        return " ".join(valor.split())
    return valor


def _campos(fila: dict, claves) -> dict:
    return {k: _limpiar(fila.get(k)) for k in claves}


class Documentacion:
    """Carga `documentacion.yaml` una vez, al arranque.

    `available` mira CONTENIDO, no existencia: un archivo presente pero sin
    `vocabulario` carga sin excepción y dejaría la pantalla afirmando una
    documentación que no tiene. Los dos estados —ausente y vacío— tienen
    remedios distintos, así que se dicen por separado.
    """

    def __init__(self, repo_root: Path, archive: EvidenceArchive | None = None):
        self.root = repo_root
        self.archive = archive
        self.path = repo_root / "results/evidence-vista/documentacion.yaml"
        self.cfg: dict = {}
        self.presente = self.path.is_file()
        if self.presente:
            self.cfg = yaml.safe_load(self.path.read_text(encoding="utf-8")) or {}
        self.terminos: dict[str, dict] = {}
        for familia in self.cfg.get("vocabulario", []) or []:
            for termino in familia.get("terminos", []) or []:
                if not termino.get("id"):
                    continue
                self.terminos[termino["id"]] = {
                    **_campos(termino, ("termino", "definicion", "nivel")),
                    "id": termino["id"],
                    "mono": bool(termino.get("mono")),
                    "result_ids": list(termino.get("result_ids") or []),
                    "familia": familia.get("id"),
                    "familia_titulo": _limpiar(familia.get("titulo")),
                }

    @property
    def available(self) -> bool:
        return bool(self.terminos) and bool(self.cfg.get("metodo"))

    def _estado(self) -> dict:
        if self.available:
            return {"available": True, "message": None}
        remedio = (
            "El archivo está pero no declara método ni vocabulario: revisá que "
            "`metodo:` y `vocabulario:` no hayan quedado vacíos o renombrados"
            if self.presente else
            f"Falta {self.path}: restauralo del repositorio"
        )
        return {"available": False,
                "message": f"Documentación no disponible. {remedio} y reiniciá la consola."}

    def _conteo(self, clave: str | None) -> int | None:
        """El número sale del registro o no sale. Nunca del YAML."""
        if clave is None or self.archive is None or not self.archive.registry.available:
            return None
        if clave == "resultados":
            return len(self.archive.by_result)
        if clave == "corridas":
            return len(self.archive.by_run)
        return None

    def payload(self) -> dict:
        estado = self._estado()
        if not estado["available"]:
            return {**estado, "titulo": None, "bajada": None,
                    "metodo": [], "aportes": [], "vocabulario": [],
                    "colisiones": [], "terminos": {}}
        metodo = [{
            **_campos(paso, ("titulo", "hizo", "porque", "quedo")),
            "n": paso.get("n"),
            "evidencia_href": paso.get("evidencia_href"),
            "evidencia_label": _limpiar(paso.get("evidencia_label")),
            # Sólo los que EXISTEN en el vocabulario: un id mal escrito en el
            # YAML no puede llegar a la pantalla como un chip mudo. El test
            # `test_todo_termino_citado_esta_definido` lo caza antes, en el
            # repositorio; esto es la red de abajo, en tiempo de lectura.
            "terminos": [t for t in (paso.get("terminos") or []) if t in self.terminos],
        } for paso in self.cfg.get("metodo", []) or []]
        aportes = [{
            **_campos(fila, ("termino", "que_es", "que_suma")),
            "id": fila.get("id"),
            "identificador": fila.get("identificador"),
            "donde": _limpiar(fila.get("donde")),
            "href": fila.get("href"),
            "conteo": self._conteo(fila.get("conteo_de")),
            "conteo_de": fila.get("conteo_de"),
        } for fila in self.cfg.get("aportes", []) or []]
        vocabulario = [{
            "id": familia.get("id"),
            "titulo": _limpiar(familia.get("titulo")),
            "nota": _limpiar(familia.get("nota")),
            "terminos": [self.terminos[t["id"]] for t in (familia.get("terminos") or [])
                         if t.get("id") in self.terminos],
        } for familia in self.cfg.get("vocabulario", []) or []]
        colisiones = [{
            "simbolo": fila.get("simbolo"),
            "en_la_consola": _limpiar(fila.get("en_la_consola")),
            "sentidos": [_campos(s, ("de", "es")) for s in (fila.get("sentidos") or [])],
        } for fila in self.cfg.get("colisiones", []) or []]
        return {
            **estado,
            "titulo": _limpiar(self.cfg.get("titulo")),
            "bajada": _limpiar(self.cfg.get("bajada")),
            "metodo": metodo, "aportes": aportes, "vocabulario": vocabulario,
            "colisiones": colisiones, "terminos": self.terminos,
        }
