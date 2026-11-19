"""«Mostrame un run donde pasó esto»: un clip de una prueba de la campaña final, para verlo en la defensa.

Junta lo que ya existe, sin calcular cifras nuevas:

- la evaluación oficial del clip: `results/gen2/<ID>/evals/eval_<clip>.json` (en git) para la lectura principal; para
  las otras lecturas (por sujeto, otra regla…), la `temporal_evaluation.json` de su corrida;
- la referencia del clip: `e-ovrt_datasets/datasets/processed/clip_bench/gt/<clip>.json`;
- las alertas de la corrida (`e-ovrt_experimental-setup/runs/<experimento>/control/alerts.jsonl`) y las detecciones de
  cada cuadro (`e-ovrt_media-plane/runs/<corrida>/detections.jsonl`), donde estén: en la Victus, en su workspace; en
  otro equipo, en un workspace extra (`EOVRT_CONSOLE_WORKSPACES_EXTRA`, de solo lectura);
- la causa de cada falsa alarma por sujeto en obra real (ERR-01, `evals/principal_alertas.json`: sus 323 alertas son
  las de las corridas de ALR-08);
- el video original del clip (`e-ovrt_datasets/datasets/raw/clip_bench/clips/<clip>.mp4`).

Lo que no está en el equipo se dice (`faltan`), no se inventa. Los conteos son los del evaluador; la clase de cada
alerta sale de sus listas (`unexpected_alerts`, `missed_alerts`, `censored_episodes`) y de su ventana
(`effective_matching_windows`): acertó el primer episodio que cae en [inicio + persistencia, inicio + t_alert_max],
igual que en «Correr un clip».
"""
from __future__ import annotations

import io
import json
import logging
import re
import subprocess
from bisect import bisect_right
from collections import OrderedDict
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

ID_PRUEBA = re.compile(r"^[A-Z]+-\d{2}$")
ID_CLIP = re.compile(r"^[A-Za-z0-9_]{1,64}$")
ID_LECTURA = re.compile(r"^[a-z_]{1,64}$")
ID_ALERTA = re.compile(r"^[A-Za-z0-9-]{8,64}$")
ID_CORRIDA = re.compile(r"^[A-Za-z0-9_-]{1,128}$")

_VENTANA_MS = 10_000.0  # si la evaluación no trae la ventana: hasta cuánto después del inicio cuenta una alerta
_ANCHO_MAX = 1280       # los cuadros se sirven a este ancho como máximo
_CACHE_CUADROS = 64
_CACHE_INDICES = 4

# Colores de las cajas por clase (los de las figuras: persona azul, casco verde, chaleco naranja, cabeza roja).
COLOR = {"person": (37, 99, 235), "helmet": (22, 163, 74), "vest": (234, 88, 12), "bare_head": (220, 38, 38)}
NOMBRE_CLASE = {"person": "persona", "helmet": "casco", "vest": "chaleco", "bare_head": "cabeza descubierta"}
COLOR_SUJETO = (250, 204, 21)


class ClipNoDisponible(KeyError):
    """Ese clip no está en esa prueba (o la prueba, la lectura o la alerta no existen)."""


def _json(ruta: Path | None) -> Any | None:
    if ruta is None:
        return None
    try:
        return json.loads(ruta.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None


def _jsonl(ruta: Path) -> list[dict]:
    salida: list[dict] = []
    try:
        lineas = ruta.read_text(encoding="utf-8").splitlines()
    except OSError:
        return salida
    for linea in lineas:
        try:
            dato = json.loads(linea)
        except json.JSONDecodeError:
            continue
        if isinstance(dato, dict):
            salida.append(dato)
    return salida


def tolerancia_de_bordes(referencia: dict | None) -> float:
    """`annotation.start_end_tolerance_ms` de la referencia (0 si no la declara), como el evaluador."""
    crudo = ((referencia or {}).get("annotation") or {}).get("start_end_tolerance_ms")
    try:
        return max(float(crudo), 0.0) if crudo is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


def tipo_de_clip(clip: str) -> str:
    """El rodaje (obra simulada, clips `a_*`) o la obra real (los demás)."""
    return "rodaje" if clip.startswith("a_") else "obra_real"


class ClipsDePrueba:
    """Vista de solo lectura de un clip de una prueba: referencia, alertas, cuadros y video."""

    def __init__(self, repo_root: Path, workspaces_extra: tuple[Path, ...] = (), ffmpeg: str = "ffmpeg") -> None:
        self.repo_root = Path(repo_root)
        self.resultados = self.repo_root / "results" / "gen2"
        self.workspaces = [self.repo_root.parent, *(Path(w) for w in workspaces_extra)]
        self.ffmpeg = ffmpeg
        self._cuadros: OrderedDict[tuple, bytes] = OrderedDict()
        self._indices: OrderedDict[Path, tuple[list[int], dict[int, str]]] = OrderedDict()
        self._causas: dict[str, dict] | None = None

    # --- dónde está cada cosa -----------------------------------------------------------

    def _buscar(self, *partes: str) -> Path | None:
        for ws in self.workspaces:
            ruta = ws.joinpath(*partes)
            if ruta.exists():
                return ruta
        return None

    def _corrida(self, pid: str, clip: str, lectura: str | None) -> tuple[dict, dict]:
        """(la corrida de esa lectura, la corrida principal) del clip, de `results/gen2/<ID>/corridas.json`."""
        if not ID_PRUEBA.match(pid) or not ID_CLIP.match(clip) or (lectura and not ID_LECTURA.match(lectura)):
            raise ClipNoDisponible(pid)
        datos = _json(self.resultados / pid / "corridas.json")
        corridas = datos.get("corridas") if isinstance(datos, dict) else None
        base = corridas.get(clip) if isinstance(corridas, dict) else None
        if not isinstance(base, dict):
            raise ClipNoDisponible(clip)
        if not lectura:
            return base, base
        variante = (base.get("variantes") or {}).get(lectura)
        if not isinstance(variante, dict):
            raise ClipNoDisponible(lectura)
        return variante, base

    def _experimento(self, corrida: dict, *archivo: str) -> Path | None:
        exp = corrida.get("experiment_id")
        if not isinstance(exp, str) or not ID_CORRIDA.match(exp):
            return None
        return self._buscar("e-ovrt_experimental-setup", "runs", exp, *archivo)

    def _detecciones(self, corrida: dict) -> Path | None:
        run = corrida.get("media_run_id")
        if not isinstance(run, str) or not ID_CORRIDA.match(run):
            return None
        return self._buscar("e-ovrt_media-plane", "runs", run, "detections.jsonl")

    def _referencia(self, clip: str) -> dict | None:
        return _json(self._buscar("e-ovrt_datasets", "datasets", "processed", "clip_bench", "gt", f"{clip}.json"))

    def video(self, pid: str, clip: str) -> Path | None:
        self._corrida(pid, clip, None)  # el clip tiene que ser de la prueba
        return self._buscar("e-ovrt_datasets", "datasets", "raw", "clip_bench", "clips", f"{clip}.mp4")

    def _causas_err01(self) -> dict[str, dict]:
        if self._causas is None:
            filas = _json(self.resultados / "ERR-01" / "evals" / "principal_alertas.json")
            self._causas = ({f["alert_id"]: f for f in filas if isinstance(f, dict) and f.get("alert_id")}
                            if isinstance(filas, list) else {})
        return self._causas

    def _evaluacion(self, pid: str, clip: str, lectura: str | None, corrida: dict) -> tuple[dict | None, str | None]:
        if not lectura:
            ruta = self.resultados / pid / "evals" / f"eval_{clip}.json"
            datos = _json(ruta)
            if isinstance(datos, dict):
                return datos, f"results/gen2/{pid}/evals/eval_{clip}.json"
        ruta = self._experimento(corrida, "control", "temporal_evaluation.json")
        datos = _json(ruta)
        if isinstance(datos, dict):
            return datos, f"runs/{corrida.get('experiment_id')}/control/temporal_evaluation.json"
        return None, None

    def _alertas_crudas(self, corrida: dict) -> list[dict] | None:
        ruta = self._experimento(corrida, "control", "alerts.jsonl")
        if ruta is None:
            return None
        vistas: set[str] = set()
        salida = []
        for a in _jsonl(ruta):
            if a.get("event_type") != "alert_event" or a.get("alert_id") in vistas:
                continue
            vistas.add(a.get("alert_id"))
            salida.append(a)
        return sorted(salida, key=lambda a: a.get("timestamp_ms") or 0)

    # --- el clip ------------------------------------------------------------------------

    def clip(self, pid: str, clip: str, lectura: str | None = None) -> dict[str, Any]:
        corrida, base = self._corrida(pid, clip, lectura)
        evaluacion, origen = self._evaluacion(pid, clip, lectura, corrida)
        ref = self._referencia(clip)
        fps = float((ref or {}).get("fps_nominal") or 30.0)
        ev = evaluacion or {}
        ventanas = ev.get("effective_matching_windows") or {}
        # La evaluación v2 lista los episodios censurados y las falsas alarmas, pero no cuáles episodios se
        # perdieron (solo cuántos): eso sale de las alertas, con la misma ventana que el evaluador.
        censurados = {c.get("episode_id") for c in ev.get("censored_episodes") or [] if isinstance(c, dict)}
        inesperadas = {u.get("alert_id"): u for u in ev.get("unexpected_alerts") or [] if isinstance(u, dict)}

        # Como el evaluador (control-plane `temporal.py`, `_alert_in_episode_window`): la ventana se ensancha en los
        # dos bordes con la tolerancia que la referencia declara para sus propios bordes de episodio.
        tolerancia = tolerancia_de_bordes(ref)
        episodios = []
        for e in (ref or {}).get("episodes") or []:
            if not isinstance(e, dict):
                continue
            w = ventanas.get(e.get("condition_id")) or {}
            episodios.append({
                "id": e.get("id"), "condicion": e.get("condition_id"),
                "desde_ms": e.get("start_ms"), "hasta_ms": e.get("end_ms"),
                "estado": "censurado" if e.get("id") in censurados else None,
                # Desde cuándo y hasta cuándo una alerta de este episodio cuenta como acierto.
                "ventana_ms": [(e.get("start_ms") or 0) + float(w.get("persistencia_min_ms") or 0.0) - tolerancia,
                               (e.get("start_ms") or 0) + float(w.get("t_alert_max_ms") or _VENTANA_MS) + tolerancia],
            })

        causas = self._causas_err01()
        crudas = self._alertas_crudas(corrida)
        alertas: list[dict] = []
        if crudas is not None:
            creditados: set[Any] = set()
            for a in crudas:
                aid, cond, ms = a.get("alert_id"), a.get("condition_id"), a.get("timestamp_ms")
                if aid in inesperadas:
                    tipo = "falsa_alarma"
                else:
                    # La primera alerta dentro de la ventana de un episodio lo acierta; las demás que no son
                    # falsas alarmas son re-alertas (o quedaron bajo umbral): el evaluador no las penaliza.
                    tipo = "re_alerta"
                    for e in episodios:
                        lo, hi = e["ventana_ms"]
                        if (e["id"] not in creditados and e["condicion"] == cond and e["estado"] != "censurado"
                                and isinstance(ms, (int, float)) and lo <= ms <= hi):
                            tipo = "acierto"
                            creditados.add(e["id"])
                            break
                alertas.append(self._alerta(a, tipo, inesperadas.get(aid), causas.get(aid), fps))
            for e in episodios:
                if e["estado"] is None and evaluacion is not None:
                    e["estado"] = "acierto" if e["id"] in creditados else "perdido"
        else:
            # Sin las alertas, el estado de cada episodio se afirma solo cuando los conteos no dejan dudas.
            evaluables = [e for e in episodios if e["estado"] is None]
            if evaluacion is not None and evaluables:
                if ev.get("missed_alerts_count") == len(evaluables):
                    for e in evaluables:
                        e["estado"] = "perdido"
                elif ev.get("matched_alerts_count") == len(evaluables) and not ev.get("missed_alerts_count"):
                    for e in evaluables:
                        e["estado"] = "acierto"
            # Sin la corrida en el equipo, la evaluación dice igual cuáles fueron las falsas alarmas y en qué cuadro.
            for aid, u in inesperadas.items():
                cuadro = u.get("frame_index")
                alertas.append({
                    "alert_id": aid, "condicion": u.get("condition_id"), "tipo": "falsa_alarma",
                    "cuadro": cuadro, "ms": round(cuadro / fps * 1000, 1) if isinstance(cuadro, (int, float)) else None,
                    "motivo": u.get("reason"), "causa": (causas.get(aid) or {}).get("causa"),
                    "caja": (causas.get(aid) or {}).get("caja_sujeto"), "sujeto": _sujeto(u.get("subject_key")),
                    "primera_evidencia_ms": None,
                })
            alertas.sort(key=lambda a: a["ms"] if a["ms"] is not None else 0)

        detecciones = self._detecciones(corrida)
        video = self._buscar("e-ovrt_datasets", "datasets", "raw", "clip_bench", "clips", f"{clip}.mp4")
        faltan = []
        if evaluacion is None:
            faltan.append("la evaluación de esta lectura (está en su corrida, que no está en este equipo)")
        if ref is None:
            faltan.append("la referencia del clip")
        if crudas is None:
            faltan.append("las alertas de la corrida: se muestran solo las falsas alarmas, que dice la evaluación")
        if video is None:
            faltan.append("el video del clip")
        elif detecciones is None:
            faltan.append("las detecciones de la corrida: los cuadros se muestran sin cajas")
        return {
            "prueba": pid,
            "clip": clip,
            "tipo_clip": tipo_de_clip(clip),
            "lectura": lectura,
            "lecturas": [None, *[n for n in (base.get("variantes") or {}) if isinstance(n, str)]],
            "fps": fps,
            "duracion_ms": (ref or {}).get("duration_ms") or ev.get("observed_duration_ms"),
            "conteos": None if evaluacion is None else {
                "episodios": ev.get("expected_alerts_count"), "aciertos": ev.get("matched_alerts_count"),
                "perdidos": ev.get("missed_alerts_count"), "falsas_alarmas": ev.get("unexpected_alerts_count"),
                "re_alertas": ev.get("re_alerts_count"), "censurados": ev.get("censored_episodes_count"),
            },
            "episodios": episodios,
            "alertas": alertas,
            "alertas_completas": crudas is not None,
            "cuadros": video is not None,
            "cajas": video is not None and detecciones is not None,
            "video": video is not None,
            "faltan": faltan,
            "origen": {
                "evaluacion": origen,
                "experiment_id": corrida.get("experiment_id"),
                "media_run_id": corrida.get("media_run_id"),
                "control_run_id": corrida.get("control_run_id"),
            },
        }

    @staticmethod
    def _alerta(a: dict, tipo: str, inesperada: dict | None, causa: dict | None, fps: float) -> dict:
        evidencia = a.get("evidence") or {}
        sujeto = evidencia.get("subject") or {}
        primera = a.get("first_evidence_frame_index")
        return {
            "alert_id": a.get("alert_id"),
            "condicion": a.get("condition_id"),
            "tipo": tipo,
            "cuadro": a.get("frame_index"),
            "ms": a.get("timestamp_ms"),
            "motivo": (inesperada or {}).get("reason"),
            "causa": (causa or {}).get("causa"),
            "caja": sujeto.get("bbox_xyxy") or (causa or {}).get("caja_sujeto"),
            "sujeto": _sujeto(a.get("subject_key")),
            "primera_evidencia_ms": round(primera / fps * 1000, 1) if isinstance(primera, (int, float)) else None,
        }

    def falsas_alarmas_err01(self) -> dict[str, Any]:
        """Las 323 falsas alarmas por sujeto en obra real con su causa (ERR-01), para abrir cada una en su clip
        (son alertas de las corridas de ALR-08)."""
        filas = []
        for f in self._causas_err01().values():
            cuadro = f.get("cuadro_alerta")
            filas.append({
                "alert_id": f.get("alert_id"), "clip": f.get("clip"), "condicion": f.get("condicion"),
                "causa": f.get("causa"), "cuadro": cuadro, "banda": f.get("banda"), "iluminacion": f.get("iluminacion"),
            })
        filas.sort(key=lambda f: (str(f["clip"]), f["cuadro"] if isinstance(f["cuadro"], int) else 0))
        return {"prueba_de_las_alertas": "ALR-08", "falsas_alarmas": filas}

    # --- un cuadro, con sus cajas -------------------------------------------------------

    def _indice(self, ruta: Path) -> tuple[list[int], dict[int, str]]:
        if ruta in self._indices:
            self._indices.move_to_end(ruta)
            return self._indices[ruta]
        lineas: dict[int, str] = {}
        try:
            with ruta.open(encoding="utf-8") as fh:
                for linea in fh:
                    m = re.search(r'"frame_index":\s*(\d+)', linea)
                    if m:
                        lineas.setdefault(int(m.group(1)), linea)
        except OSError:
            pass
        indice = (sorted(lineas), lineas)
        self._indices[ruta] = indice
        while len(self._indices) > _CACHE_INDICES:
            self._indices.popitem(last=False)
        return indice

    def _evento(self, ruta: Path, cuadro: int) -> dict | None:
        """El evento de detección de ese cuadro o, si el sistema no procesó ese cuadro (densidad menor), el último
        procesado antes."""
        orden, lineas = self._indice(ruta)
        i = bisect_right(orden, cuadro) - 1
        if i < 0:
            return None
        try:
            dato = json.loads(lineas[orden[i]])
        except json.JSONDecodeError:
            return None
        return dato if isinstance(dato, dict) else None

    def _extraer(self, video: Path, segundo: float) -> bytes:
        proc = subprocess.run(
            [self.ffmpeg, "-v", "error", "-ss", f"{max(segundo, 0.0):.3f}", "-i", str(video),
             "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "-"],
            capture_output=True, timeout=30, check=False,
        )
        if proc.returncode != 0 or not proc.stdout:
            raise ClipNoDisponible(f"ffmpeg: {proc.stderr.decode(errors='replace')[:200]}")
        return proc.stdout

    def cuadro(self, pid: str, clip: str, cuadro: int, lectura: str | None = None,
               alerta: str | None = None, acercar: bool = False) -> bytes:
        """El cuadro del clip con las cajas que vio el sistema en ese cuadro y, si se pide una alerta, la persona
        que la disparó resaltada. JPEG, a lo sumo de `_ANCHO_MAX` de ancho. Con `acercar`, solo la zona de esa
        persona, agrandada: en obra real las personas ocupan pocos píxeles y sin acercar no se ve si el EPP estaba."""
        if cuadro < 0 or (alerta is not None and not ID_ALERTA.match(alerta)) or (acercar and not alerta):
            raise ClipNoDisponible(str(cuadro))
        corrida, _ = self._corrida(pid, clip, lectura)
        clave = (pid, clip, lectura, cuadro, alerta, acercar)
        if clave in self._cuadros:
            self._cuadros.move_to_end(clave)
            return self._cuadros[clave]
        video = self.video(pid, clip)
        if video is None:
            raise ClipNoDisponible("sin video")
        ref = self._referencia(clip) or {}
        fps = float(ref.get("fps_nominal") or 30.0)
        ruta = self._detecciones(corrida)
        evento = self._evento(ruta, cuadro) if ruta is not None else None
        fuente = (evento or {}).get("source") or {}
        segundo = (fuente.get("timestamp_ms") / 1000.0 if isinstance(fuente.get("timestamp_ms"), (int, float))
                   else cuadro / fps)
        caja_sujeto = None
        if alerta:
            caja_sujeto = next((a["caja"] for a in self.clip(pid, clip, lectura)["alertas"]
                                if a["alert_id"] == alerta), None)
            if acercar and not (isinstance(caja_sujeto, list) and len(caja_sujeto) == 4):
                raise ClipNoDisponible("la alerta no tiene la caja de la persona")
        imagen = self._dibujar(self._extraer(video, segundo), (evento or {}).get("detections") or [], caja_sujeto,
                               acercar)
        self._cuadros[clave] = imagen
        while len(self._cuadros) > _CACHE_CUADROS:
            self._cuadros.popitem(last=False)
        return imagen

    @staticmethod
    def _dibujar(png: bytes, detecciones: list[dict], caja_sujeto: list[float] | None, acercar: bool = False) -> bytes:
        from PIL import Image, ImageDraw, ImageFont

        img = Image.open(io.BytesIO(png)).convert("RGB")
        dx = dy = 0.0
        hay_sujeto = isinstance(caja_sujeto, list) and len(caja_sujeto) == 4
        if acercar and hay_sujeto:
            # La zona de la persona con margen (tres veces su alto, al menos 160 px), agrandada después.
            x0, y0, x1, y1 = caja_sujeto
            lado = max(160.0, 3.0 * max(x1 - x0, y1 - y0))
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            dx, dy = max(0.0, cx - lado / 2), max(0.0, cy - lado / 2)
            img = img.crop((round(dx), round(dy), round(min(img.width, dx + lado)), round(min(img.height, dy + lado))))
            escala = 640 / img.width
        else:
            escala = min(1.0, _ANCHO_MAX / img.width)
        if escala != 1.0:
            img = img.resize((round(img.width * escala), round(img.height * escala)))
        dibujo = ImageDraw.Draw(img)
        try:
            fuente = ImageFont.load_default(size=14)
        except TypeError:  # Pillow viejo
            fuente = ImageFont.load_default()

        def caja(xyxy: list[float], color: tuple[int, int, int], ancho: int) -> tuple[float, ...]:
            x0, y0, x1, y1 = ((xyxy[0] - dx) * escala, (xyxy[1] - dy) * escala,
                              (xyxy[2] - dx) * escala, (xyxy[3] - dy) * escala)
            dibujo.rectangle((x0, y0, x1, y1), outline=color, width=ancho)
            return x0, y0, x1, y1

        def rotulo(x0: float, y0: float, texto: str, color: tuple[int, int, int]) -> None:
            ancho_texto = dibujo.textlength(texto, font=fuente)
            y_texto = max(0.0, y0 - 18)
            dibujo.rectangle((x0, y_texto, x0 + ancho_texto + 6, y_texto + 18), fill=color)
            dibujo.text((x0 + 3, y_texto + 2), texto, fill=(255, 255, 255), font=fuente)

        for d in detecciones:
            xyxy = d.get("bbox_xyxy")
            if not (isinstance(xyxy, list) and len(xyxy) == 4):
                continue
            clase = d.get("label")
            color = COLOR.get(clase, (100, 116, 139))
            x0, y0, _, _ = caja(xyxy, color, 2 if clase == "person" else 3)
            # Solo el EPP lleva rótulo: con muchas personas chicas, los rótulos de persona se pisan y tapan.
            if clase != "person":
                confianza = d.get("confidence")
                texto = NOMBRE_CLASE.get(clase, str(clase))
                if isinstance(confianza, (int, float)):
                    texto += f" {confianza:.2f}".replace(".", ",")
                rotulo(x0, y0, texto, color)
        if hay_sujeto:
            x0, y0, _, _ = caja(caja_sujeto, COLOR_SUJETO, 4 if acercar else 5)
            rotulo(x0, y0, "persona de la alerta", (161, 98, 7))
        salida = io.BytesIO()
        img.save(salida, format="JPEG", quality=88)
        return salida.getvalue()


def _sujeto(subject_key: Any) -> str | None:
    """`CR-01:v01_c01:subject_001` → `subject_001`; una alerta por escena no tiene sujeto."""
    if not isinstance(subject_key, str):
        return None
    partes = subject_key.split(":")
    return partes[2] if len(partes) >= 3 else None
