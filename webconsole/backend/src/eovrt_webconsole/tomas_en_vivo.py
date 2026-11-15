"""«Tomas en vivo» (plan de la consola de evidencia, §6): las sesiones guardadas de las jornadas, agrupadas
por la prueba en la que cuentan, no por fecha.

Qué toma cuenta en qué prueba no lo decide la consola: lo dejó escrito el programa de la campaña en
`results/gen2/<ID>/` (`evals/tomas.json`; en RT-09, los grupos de su resultado). Lo demás —calibraciones,
ensayos, exploraciones y tomas descartadas— va aparte, cada una con su motivo: el firmado en
`descartes.json`, el que dio el programa al no evaluarla o, si no hay ninguno, lo que la sesión dice de sí
misma (escena de calibración, ensayo de la demo, otro modo de prompts).

Es de solo lectura: no toca las sesiones ni los resultados.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)

# Las pruebas en vivo cuyas tomas son sesiones de la demo (RT-03 corrió con el programa, sin sesión).
PRUEBAS_EN_VIVO = ("RT-04", "RT-05", "RT-06", "RT-07", "RT-08", "RT-09")
CAMPOS_TOMA = ("escena", "remera", "stream", "motor", "camara", "como_se_esperaba")
MOTIVO = {
    "calibracion": "Calibración del encuadre antes de las tomas.",
    "ensayo": "Ensayo de la demo: no cuenta como toma de ninguna prueba.",
    "exploracion": "Exploración con otro modo de prompts: no cuenta como toma.",
    "sin_prueba": "No entra en ninguna prueba.",
}


def _leer_json(ruta: Path) -> Any | None:
    if not ruta.is_file():
        return None
    try:
        return json.loads(ruta.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        logger.warning("tomas: %s no es JSON legible", ruta)
        return None


class TomasEnVivo:
    def __init__(self, resultados_dir: Path, sesiones: Callable[[], list[dict]],
                 carpeta: Callable[[str], Path | None]) -> None:
        self.resultados_dir = Path(resultados_dir)
        self.sesiones = sesiones
        self.carpeta = carpeta

    def _tomas(self, pid: str, guardadas: set[str]) -> list[dict]:
        base = self.resultados_dir / pid
        tomas = []
        for t in _leer_json(base / "evals" / "tomas.json") or []:
            if not isinstance(t, dict) or not t.get("session_id"):
                continue
            sujeto = t.get("sujeto")
            tomas.append({
                "session_id": t["session_id"],
                **{k: t.get(k) for k in CAMPOS_TOMA},
                "sujeto_como_se_esperaba": sujeto.get("como_se_esperaba") if isinstance(sujeto, dict) else None,
                "disponible": t["session_id"] in guardadas,
            })
        if tomas:
            return tomas
        # RT-09 no deja tomas.json: sus tomas son las sesiones de cada grupo (escena, remera, modo, motor).
        resultado = _leer_json(base / "resultado.json") or {}
        for grupo in (resultado.get("metricas") or {}).get("grupos") or []:
            if not isinstance(grupo, dict):
                continue
            for sid in grupo.get("session_ids") or []:
                tomas.append({
                    "session_id": sid, "escena": grupo.get("escena"), "remera": grupo.get("remera"),
                    "motor": grupo.get("motor"), "modo": grupo.get("modo"), "stream": None, "camara": None,
                    "como_se_esperaba": None, "sujeto_como_se_esperaba": None, "disponible": sid in guardadas,
                })
        return tomas

    def _proposito(self, sid: str) -> str | None:
        carpeta = self.carpeta(sid)
        marcas = _leer_json(carpeta / "marcas.json") if carpeta else None
        return marcas.get("proposito") if isinstance(marcas, dict) else None

    def vista(self) -> dict:
        guardadas = {s["session_id"]: s for s in self.sesiones() if s.get("session_id")}
        pruebas, contadas = [], set()
        descartes: dict[str, dict] = {}
        no_evaluables: dict[str, str] = {}
        for pid in PRUEBAS_EN_VIVO:
            tomas = self._tomas(pid, set(guardadas))
            contadas |= {t["session_id"] for t in tomas}
            pruebas.append({"id": pid, "tomas": tomas})
            base = self.resultados_dir / pid
            for sid, d in (_leer_json(base / "descartes.json") or {}).items():
                if isinstance(d, dict):
                    descartes.setdefault(sid, {"motivo": d.get("motivo"), "quien": d.get("quien"), "prueba": pid})
            resultado = _leer_json(base / "resultado.json") or {}
            for ne in (resultado.get("metricas") or {}).get("no_evaluables") or []:
                if isinstance(ne, dict) and ne.get("session_id") and ne.get("motivo"):
                    no_evaluables.setdefault(ne["session_id"], ne["motivo"])

        otras = []
        for sid in sorted(set(guardadas) | set(descartes), reverse=True):
            if sid in contadas:
                continue
            s = guardadas.get(sid) or {}
            fila = {"session_id": sid, "escena": s.get("escena"), "iniciada_en": s.get("iniciada_en"),
                    "disponible": sid in guardadas, "quien": None, "prueba": None}
            proposito = self._proposito(sid) if sid in guardadas else None
            if sid in descartes:
                fila.update(tipo="descartada", motivo=descartes[sid]["motivo"], quien=descartes[sid]["quien"],
                            prueba=descartes[sid]["prueba"])
            elif s.get("escena") == "CAL":
                fila.update(tipo="calibracion", motivo=MOTIVO["calibracion"])
            elif s.get("exploracion") or proposito == "ensayo":
                fila.update(tipo="ensayo", motivo=MOTIVO["ensayo"])
            elif s.get("modo_prompts"):
                fila.update(tipo="exploracion", motivo=MOTIVO["exploracion"])
            elif sid in no_evaluables:
                fila.update(tipo="no_evaluable", motivo=no_evaluables[sid])
            else:
                fila.update(tipo="sin_prueba", motivo=MOTIVO["sin_prueba"])
            otras.append(fila)
        return {"pruebas": pruebas, "otras": otras}
