"""Las diez figuras del informe (plan de la consola de evidencia, §8): `results/evidence-vista/figuras.yaml`.

Para cada figura dice de qué pantalla, archivo o gráfico sale, a qué carpeta va —la pública
(`results/gen2/<prueba>/capturas/`, solo texto y gráficos) o la privada (`defensa/capturas/figuras/`,
personas y cuadros de terceros)— y si la imagen ya existe. Los gráficos llegan con sus cifras resueltas
contra results/gen2, igual que las preguntas. La consola lee las dos carpetas; la herramienta
`webconsole/tools/sacar_figuras.mjs` es la que escribe en ellas.
"""
from __future__ import annotations

import csv
import logging
from pathlib import Path

import yaml

from eovrt_webconsole.gen2 import Gen2
from eovrt_webconsole.preguntas import _Resolutor

logger = logging.getLogger(__name__)

CARPETA_PUBLICA = "results/gen2/{prueba}/capturas"
CARPETA_PRIVADA = "defensa/capturas/figuras"
# Las curvas del ajuste fino no tienen prueba de la campaña: sus datos y su figura viven juntos acá.
CARPETA_CURVAS = "finetuning/curvas"


class FiguraInexistente(KeyError):
    pass


class Figuras:
    def __init__(self, repo_root: Path, gen2: Gen2) -> None:
        self.repo_root = Path(repo_root)
        self.archivo = self.repo_root / "results" / "evidence-vista" / "figuras.yaml"
        self.gen2 = gen2

    def _declaradas(self) -> list[dict]:
        if not self.archivo.is_file():
            return []
        try:
            datos = yaml.safe_load(self.archivo.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError):
            logger.warning("figuras: %s no es YAML legible", self.archivo)
            return []
        figuras = datos.get("figuras") if isinstance(datos, dict) else None
        return [f for f in figuras or [] if isinstance(f, dict) and f.get("id")]

    @staticmethod
    def destino(figura: dict) -> str | None:
        """Dónde va la imagen, relativo al repo. Un gráfico o una figura pendiente no tienen archivo propio
        hasta que la herramienta los captura; un gráfico va a la carpeta pública de su prueba."""
        nombre = f"figura-{int(figura['numero']):02d}-{figura['id']}.png"
        if figura.get("privada"):
            return f"{CARPETA_PRIVADA}/{nombre}"
        if not figura.get("prueba"):
            return f"{CARPETA_CURVAS}/{nombre}" if (figura.get("fuente") or {}).get("grafico") == "curvas" else None
        return f"{CARPETA_PUBLICA.format(prueba=figura['prueba'])}/{nombre}"

    def _curvas(self, fuente: dict, r: _Resolutor, donde: str) -> dict:
        """Curvas por época leídas de archivos CSV versionados bajo `finetuning/curvas/` (los `results.csv` de
        Ultralytics). Se entregan como un gráfico de líneas: una categoría por época y una serie por archivo;
        una época que una serie no tiene queda vacía."""
        columna = str(fuente.get("columna") or "")
        decimales = fuente.get("decimales", 3)
        carpeta = (self.repo_root / CARPETA_CURVAS).resolve()
        series: list[tuple[str, dict[int, float]]] = []
        for i, s in enumerate(fuente.get("series") or []):
            nombre = str((s or {}).get("nombre") or f"serie {i + 1}")
            ruta = (self.repo_root / str((s or {}).get("csv") or "")).resolve()
            valores: dict[int, float] = {}
            if ruta.parent != carpeta or ruta.suffix != ".csv" or not ruta.is_file():
                r.errores.append(f"{donde}.series[{i}]: «{s.get('csv')}» no es un CSV de {CARPETA_CURVAS}/")
            else:
                with ruta.open(newline="", encoding="utf-8") as fh:
                    for fila in csv.DictReader(fh):
                        fila = {(k or "").strip(): (v or "").strip() for k, v in fila.items()}
                        try:
                            valores[int(float(fila["epoch"]))] = float(fila[columna])
                        except (KeyError, ValueError):
                            r.errores.append(f"{donde}.series[{i}]: falta la época o la columna «{columna}»")
                            break
            series.append((nombre, valores))
        epocas = sorted({e for _, v in series for e in v})
        return {"tipo": "lineas", "eje": fuente.get("eje"), "eje_x": fuente.get("eje_x"),
                "series": [n for n, _ in series],
                "puntos": [{"etiqueta": str(e), "valores": [
                    {"ok": True, "valor": v.get(e), "decimales": decimales, "prueba": None} for _, v in series]}
                    for e in epocas]}

    def _grafico(self, fuente: dict, r: _Resolutor, donde: str) -> dict:
        if fuente.get("grafico") == "barras":
            return {"tipo": "barras", "unidad": fuente.get("unidad"), "barras": [
                {"etiqueta": d.get("etiqueta"), "aparte": bool(d.get("aparte")),
                 "cifra": r.resolver(d, None, None, f"{donde}.datos[{i}]")}
                for i, d in enumerate(fuente.get("datos") or [])]}
        if fuente.get("grafico") == "curvas":
            return self._curvas(fuente, r, donde)
        if fuente.get("grafico") == "lineas":
            return {"tipo": "lineas", "eje": fuente.get("eje"), "series": fuente.get("series") or [], "puntos": [
                {"etiqueta": d.get("etiqueta"),
                 "valores": [r.resolver(v, None, None, f"{donde}.datos[{i}].valores[{j}]")
                             for j, v in enumerate(d.get("valores") or [])]}
                for i, d in enumerate(fuente.get("datos") or [])]}
        r.errores.append(f"{donde}: gráfico desconocido «{fuente.get('grafico')}»")
        return {"tipo": None}

    def vista(self) -> dict:
        r = _Resolutor(self.gen2)
        figuras = []
        for f in self._declaradas():
            fuente = f.get("fuente") or {}
            destino = None if f.get("pendiente") else self.destino(f)
            disponible = bool(destino) and (self.repo_root / destino).is_file()
            figuras.append({
                "id": f["id"], "numero": f.get("numero"), "titulo": f.get("titulo"),
                "preguntas": f.get("preguntas") or [], "seccion": f.get("seccion"), "prueba": f.get("prueba"),
                "pie": " ".join(str(f.get("pie") or "").split()) or None,
                "privada": bool(f.get("privada")), "solo_informe": bool(f.get("solo_informe")),
                "pendiente": " ".join(str(f["pendiente"]).split()) if f.get("pendiente") else None,
                "fuente": {k: v for k, v in fuente.items() if k in ("pantalla", "selector", "archivo", "recorte_arriba")},
                "grafico": self._grafico(fuente, r, f"figuras.{f['id']}") if fuente.get("grafico") else None,
                "destino": destino,
                "disponible": disponible,
                "url": f"/api/figuras/{f['id']}/imagen" if disponible else None,
            })
        return {"figuras": sorted(figuras, key=lambda x: x["numero"] or 0), "errores": r.errores}

    def imagen(self, figura_id: str) -> Path:
        for f in self._declaradas():
            if f["id"] == figura_id and not f.get("pendiente"):
                destino = self.destino(f)
                ruta = (self.repo_root / destino) if destino else None
                if ruta and ruta.is_file() and ruta.suffix.lower() == ".png":
                    return ruta
        raise FiguraInexistente(figura_id)
