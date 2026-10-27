"""La carpeta de resultados de una prueba: `results/gen2/<ID>/` (doc 134 §6).

    prueba.yaml     copia del pre-registro tal como estaba al correr
    resultado.json  métricas finales, resumen para la consola y veredicto contra la gen 1
    corridas.json   cada experimento disparado: ids de los planos, estado, huellas, tiempos
    entorno.json    dónde y con qué corrió (host, versiones, imágenes, commits)
    comandos.txt    lo que se ejecutó, en orden, con su hora
    logs/           evaluaciones y artefactos livianos (nunca detecciones pesadas)

Toda escritura es atómica (archivo temporal + `os.replace`): una corrida de horas que se
corta no deja un JSON a medio escribir, y `corridas.json` permite retomar donde quedó.
"""
from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path

from .catalogo import Prueba
from .entorno import Entorno


class PreRegistroCambiado(RuntimeError):
    """El `prueba.yaml` cambió después de que la prueba empezó a correr."""


def ahora() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def escribir_atomico(ruta: Path, texto: str) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    tmp = ruta.with_name(f".{ruta.name}.tmp")
    tmp.write_text(texto, encoding="utf-8")
    os.replace(tmp, ruta)


def escribir_json(ruta: Path, datos) -> None:
    escribir_atomico(ruta, json.dumps(datos, indent=2, ensure_ascii=False) + "\n")


class Carpeta:
    def __init__(self, ent: Entorno, prueba: Prueba) -> None:
        self.ent = ent
        self.prueba = prueba
        self.dir = ent.resultados / prueba.id
        self.logs = self.dir / "logs"

    # --- pre-registro -----------------------------------------------------------------

    def preparar(self, *, forzar: bool = False) -> None:
        """Copia el pre-registro. Si la copia existente difiere, no se sigue (salvo `forzar`)."""
        self.dir.mkdir(parents=True, exist_ok=True)
        copia = self.dir / "prueba.yaml"
        original = self.prueba.ruta.read_text(encoding="utf-8")
        if copia.is_file() and copia.read_text(encoding="utf-8") != original:
            if not forzar:
                raise PreRegistroCambiado(
                    f"{self.prueba.id}: el pre-registro cambió después de empezar a correr "
                    f"({copia} difiere de {self.prueba.ruta}). Una prueba no se re-ajusta: "
                    "volvé el prueba.yaml a como estaba, o usá --forzar para archivar la carpeta "
                    "actual y empezar de cero (queda constancia)."
                )
            archivo = self.dir.with_name(f"{self.prueba.id}.descartada-{ahora().replace(':', '')}")
            os.replace(self.dir, archivo)
            self.dir.mkdir(parents=True)
            self.comando(f"--forzar: la carpeta anterior se archivó en {archivo.name}")
        escribir_atomico(copia, original)

    # --- corridas ---------------------------------------------------------------------

    @property
    def _corridas_path(self) -> Path:
        return self.dir / "corridas.json"

    def corridas(self) -> dict[str, dict]:
        if not self._corridas_path.is_file():
            return {}
        return json.loads(self._corridas_path.read_text(encoding="utf-8")).get("corridas", {})

    def guardar_corrida(self, clave: str, registro: dict) -> None:
        corridas = self.corridas()
        corridas[clave] = registro
        escribir_json(
            self._corridas_path,
            {"schema": "corridas.gen2.v1", "prueba": self.prueba.id, "corridas": corridas},
        )

    def corrida_ok(self, clave: str) -> dict | None:
        registro = self.corridas().get(clave)
        return registro if registro and registro.get("estado") == "ok" else None

    # --- texto y JSON -----------------------------------------------------------------

    def comando(self, texto: str) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        with (self.dir / "comandos.txt").open("a", encoding="utf-8") as fh:
            fh.write(f"[{ahora()}] {texto}\n")

    def escribir(self, nombre: str, datos) -> Path:
        ruta = self.dir / nombre
        escribir_json(ruta, datos)
        return ruta

    def leer(self, nombre: str):
        ruta = self.dir / nombre
        return json.loads(ruta.read_text(encoding="utf-8")) if ruta.is_file() else None

    def guardar_ejemplo(self, dir_generado: Path) -> None:
        """Copia, una vez, el manifiesto y las configs expandidos de la primera corrida a
        `logs/ejemplo/`: lo que se envió exactamente, versionado junto al resultado (los
        generados viven en `runs/`, que git ignora)."""
        destino = self.logs / "ejemplo"
        if destino.exists():
            return
        destino.mkdir(parents=True)
        for archivo in sorted(Path(dir_generado).glob("*.yaml")):
            (destino / archivo.name).write_text(archivo.read_text(encoding="utf-8"), encoding="utf-8")
        (destino / "LEEME.txt").write_text(
            f"Configuración expandida de la primera corrida ({Path(dir_generado).name}). "
            "Las demás difieren solo en el clip/estrato y el nombre de la corrida; sus huellas "
            "están en corridas.json.\n",
            encoding="utf-8",
        )

    def resultado(self, datos: dict) -> Path:
        previo = self.leer("resultado.json") or {}
        confirmado = (previo.get("veredicto") or {}).get("confirmado")
        cuerpo = {"schema": "resultado.gen2.v1", "id": self.prueba.id, "titulo": self.prueba.titulo,
                  "informe": self.prueba.datos.get("informe") or [], "generado": ahora(), **datos}
        # Un veredicto confirmado por una persona no lo pisa una re-agregación.
        if confirmado and isinstance(cuerpo.get("veredicto"), dict):
            cuerpo["veredicto"]["confirmado"] = confirmado
        return self.escribir("resultado.json", cuerpo)
