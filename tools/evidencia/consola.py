"""Cliente de la consola (BFF :8090): el único camino por el que corre la generación 2.

Toda corrida se dispara con `POST /api/experiments/run` y un manifiesto en línea; el runner
de la consola orquesta media → control (y distribución en vivo) y deja los ids de cada plano
en el estado del experimento. Solo biblioteca estándar.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from collections.abc import Callable

TERMINALES = ("succeeded", "failed")


class ConsolaError(RuntimeError):
    """La consola respondió algo que impide seguir (con el detalle tal cual lo dio)."""


class Consola:
    def __init__(
        self,
        url: str,
        *,
        espera_s: float = 3.0,
        dormir: Callable[[float], None] = time.sleep,
        avisar: Callable[[str], None] = print,
    ) -> None:
        self.url = url.rstrip("/")
        self.espera_s = espera_s
        self._dormir = dormir
        self._avisar = avisar

    # --- HTTP -------------------------------------------------------------------------

    def _pedir(self, metodo: str, ruta: str, cuerpo: dict | None = None, timeout: float = 60.0):
        datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
        req = urllib.request.Request(
            self.url + ruta,
            data=datos,
            method=metodo,
            headers={"Content-Type": "application/json"} if datos is not None else {},
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                texto = resp.read().decode() or "null"
                return resp.status, json.loads(texto)
        except urllib.error.HTTPError as exc:
            texto = exc.read().decode(errors="replace")
            try:
                return exc.code, json.loads(texto)
            except json.JSONDecodeError:
                return exc.code, {"detail": texto}

    def _ok(self, metodo: str, ruta: str, cuerpo: dict | None = None, timeout: float = 60.0):
        estado, datos = self._pedir(metodo, ruta, cuerpo, timeout)
        if estado >= 400:
            raise ConsolaError(f"{metodo} {ruta} -> HTTP {estado}: {_detalle(datos)}")
        return datos

    # --- lectura ----------------------------------------------------------------------

    def salud(self) -> bool:
        try:
            estado, _ = self._pedir("GET", "/api/health", timeout=10)
        except (urllib.error.URLError, OSError):
            return False
        return estado == 200

    def objetivo(self) -> dict:
        """`GET /api/target`: salud del media-plane activo y el modelo que tiene cargado."""
        return self._ok("GET", "/api/target")

    def instancias(self) -> list[dict] | None:
        """Fleet del compose; None si la consola no orquesta (camino nativo)."""
        estado, datos = self._pedir("GET", "/api/platform/instances")
        if estado == 501:
            return None
        if estado >= 400:
            raise ConsolaError(f"GET /api/platform/instances -> HTTP {estado}: {_detalle(datos)}")
        return datos

    def experimento(self, experiment_id: str) -> dict | None:
        estado, datos = self._pedir("GET", f"/api/experiments/{experiment_id}")
        if estado == 404:
            return None
        if estado >= 400:
            raise ConsolaError(f"GET experimento {experiment_id} -> HTTP {estado}: {_detalle(datos)}")
        return datos

    def experimento_activo(self) -> dict | None:
        estado, datos = self._pedir("GET", "/api/experiments/current")
        return None if estado == 404 else datos

    # --- acciones ---------------------------------------------------------------------

    def activar(self, instancia: str) -> dict:
        """Activa una instancia del fleet (para la anterior y espera `readyz`: minutos)."""
        return self._ok("POST", f"/api/platform/instances/{instancia}/activate", timeout=900)

    def lanzar(self, manifiesto: dict, *, timeout_s: float | None = None, max_espera_s: float = 3600) -> str:
        """Dispara un experimento. Si hay otro en curso (409), espera a que termine."""
        cuerpo: dict = {"manifest": manifiesto}
        if timeout_s is not None:
            cuerpo["timeout_s"] = timeout_s
        limite = time.monotonic() + max_espera_s
        avisado = False
        while True:
            estado, datos = self._pedir("POST", "/api/experiments/run", cuerpo)
            if estado == 202:
                return datos["experiment_id"]
            if estado == 409 and time.monotonic() < limite:
                if not avisado:
                    self._avisar(
                        f"    hay un experimento en curso ({datos.get('active_experiment_id')}); espero"
                    )
                    avisado = True
                self._dormir(max(self.espera_s, 5.0))
                continue
            if estado == 503:
                bloqueos = (datos.get("preflight") or {}).get("blockers") or []
                raise ConsolaError("plataforma no lista: " + ("; ".join(bloqueos) or _detalle(datos)))
            raise ConsolaError(f"POST /api/experiments/run -> HTTP {estado}: {_detalle(datos)}")

    def esperar(self, experiment_id: str, *, tope_s: float) -> dict:
        """Estado terminal del experimento (`succeeded` | `failed`)."""
        limite = time.monotonic() + tope_s
        perdido = 0
        while True:
            estado = self.experimento(experiment_id)
            if estado is None:
                # La consola se reinició a mitad de corrida: el estado vivía en memoria.
                perdido += 1
                if perdido >= 5:
                    return {"experiment_id": experiment_id, "status": "failed",
                            "error": "la consola perdió el estado del experimento (¿reinicio?)"}
            elif estado.get("status") in TERMINALES:
                return estado
            if time.monotonic() > limite:
                return {"experiment_id": experiment_id, "status": "failed",
                        "error": f"el driver dejó de esperar a los {tope_s:.0f} s"}
            self._dormir(self.espera_s)

    def correr(self, manifiesto: dict, *, timeout_s: float) -> dict:
        """Lanza y espera. El tope del driver deja margen sobre el del runner (por plano)."""
        experiment_id = self.lanzar(manifiesto, timeout_s=timeout_s)
        estado = self.esperar(experiment_id, tope_s=3 * timeout_s + 600)
        return {**estado, "experiment_id": experiment_id}


def _detalle(datos) -> str:
    if isinstance(datos, dict) and "detail" in datos:
        detalle = datos["detail"]
        return detalle if isinstance(detalle, str) else json.dumps(detalle, ensure_ascii=False)
    return json.dumps(datos, ensure_ascii=False)[:500]
