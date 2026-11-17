"""Arma las figuras privadas 5 y 10 del informe (plan de la consola de evidencia, §8.2) desde la evidencia.

- **Figura 5 (RT-09, el chaleco falso).** El mismo instante de dos tomas P2 con el perfil operativo, después de
  sacarse el chaleco: a la izquierda con remera negra y a la derecha con blanca (las dos siguieron el mismo guion;
  cómo se elige el instante, en `chaleco_falso`). Cada cuadro se dibuja con las mismas funciones que el Resultado
  de la demo (`eovrt_webconsole.demo.render`): las cajas del motor, el estado de cada condición y la línea de
  tiempo.
- **Figura 10 (EXT-01, una clase nueva).** Una imagen de `construction_site_safety` (CC BY 4.0) con las cajas de
  `machinery` que detectó la corrida de la campaña. La imagen es la que tiene más maquinaria acertada contra la
  referencia, sin falsas ni perdidas, y la mayor confianza (ver `IMAGEN_CLASE_NUEVA`).

Las dos tienen personas o cuadros de la campaña: van a `defensa/figuras/<prueba>/`, que git ignora, con un `.json`
al lado que dice de qué corridas y cuadros salieron. De ahí `sacar_figuras.mjs` las copia a la carpeta privada.

Se corre donde estén las corridas. En la Victus, adentro de la consola, que monta el workspace en la misma ruta:

    docker compose exec console sh -c 'python "$EOVRT_CONSOLE_REPO_ROOT/webconsole/tools/armar_figuras_privadas.py"'

En la PC de desarrollo, con el venv del repo y `--raiz` apuntando a los paquetes privados que traen las corridas
(cada raíz es una carpeta con `e-ovrt_media-plane/`, `e-ovrt_control-plane/` o `e-ovrt_datasets/` adentro):

    .venv/bin/python webconsole/tools/armar_figuras_privadas.py --raiz <paquete 11-07> --raiz <ws de la Victus>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
WORKSPACE = REPO.parent
sys.path.insert(0, str(REPO / "webconsole" / "backend" / "src"))

from eovrt_webconsole.demo import render

GEN2 = REPO / "results" / "gen2"
SALIDA = REPO / "defensa" / "figuras"

# Figura 5: las dos tomas P2 del perfil operativo de RT-09 (grupos «campeon · gdino-tiny-560 · P2»).
TOMA_NEGRA = "demo_20261107T154526Z_P2"
TOMA_BLANCA = "demo_20261107T153316Z_P2"
# Figura 10: la corrida de obra de EXT-01 y la imagen elegida.
CORRIDA_CLASE_NUEVA = "obra_val"
IMAGEN_CLASE_NUEVA = "construction-2-_mp4-38_jpg.rf.0bb63aba0a9ebe5a4741a6207e2e1902.jpg"
CLASE_NUEVA = "machinery"


def _sha256(ruta: Path) -> str:
    return hashlib.sha256(ruta.read_bytes()).hexdigest()


def _buscar(raices: list[Path], relativa: str) -> Path:
    for raiz in raices:
        if (raiz / relativa).exists():
            return raiz / relativa
    donde = ", ".join(str(r) for r in raices)
    raise FileNotFoundError(f"no está {relativa} en ninguna raíz ({donde}); pasá la que lo tenga con --raiz")


def _rotulo(img, texto: str):
    """Una franja arriba del cuadro con el nombre de la toma."""
    from PIL import Image, ImageDraw

    ancho, alto = img.size
    fuente = render._fuente(max(16, alto // 20))
    franja = max(30, alto // 13)
    lienzo = Image.new("RGB", (ancho, alto + franja), (20, 20, 20))
    lienzo.paste(img, (0, franja))
    draw = ImageDraw.Draw(lienzo)
    _, arriba, _, abajo = draw.textbbox((0, 0), texto, font=fuente)
    draw.text((12, (franja - (abajo - arriba)) // 2 - arriba), texto, font=fuente, fill=(240, 240, 240))
    return lienzo


class _Toma:
    """Una toma de RT-09 con lo que hace falta para dibujar cualquiera de sus cuadros como en su Resultado."""

    def __init__(self, raices: list[Path], sesion: str) -> None:
        self.sesion = sesion
        self.toma = json.loads((GEN2 / "RT-09" / "tomas" / sesion / "toma.json").read_text(encoding="utf-8"))
        ids = self.toma["ids"]
        media_dir = _buscar(raices, f"e-ovrt_media-plane/runs/{ids['media_run_id']}")
        control_dir = _buscar(raices, f"e-ovrt_control-plane/runs/{ids['control_run_id']}")
        self.cuadros = render.leer_cuadros(media_dir)
        eventos = render._leer_jsonl(control_dir / "pattern_events.jsonl")
        self.alertas = render._leer_jsonl(control_dir / "alerts.jsonl")
        if not self.cuadros or not eventos:
            raise RuntimeError(f"{sesion}: faltan los cuadros o los eventos del motor de reglas")
        self.estados = render.estados_por_cuadro(self.cuadros, eventos)
        self.t0 = self.cuadros[0].timestamp_ms
        self.etiquetas = {
            (e.get("source") or {}).get("frame_index"): {d.get("label") for d in e.get("detections") or []}
            for e in render._leer_jsonl(media_dir / "detections.jsonl")}

    def cercano(self, desde_el_primero_ms: float) -> int:
        return min(range(len(self.cuadros)),
                   key=lambda i: abs(self.cuadros[i].timestamp_ms - self.t0 - desde_el_primero_ms))

    def desde_el_primero(self, idx: int) -> float:
        return self.cuadros[idx].timestamp_ms - self.t0

    def cr02(self, idx: int) -> str:
        return self.estados["CR-02"][idx]

    def con(self, idx: int, etiqueta: str) -> bool:
        return etiqueta in self.etiquetas.get(self.cuadros[idx].frame_index, set())

    def dibujar(self, idx: int):
        from PIL import Image

        cuadro = self.cuadros[idx]
        if cuadro.preview is None:
            raise RuntimeError(f"{self.sesion}: el cuadro {cuadro.frame_index} no tiene su imagen anotada")
        with Image.open(cuadro.preview) as original:
            img = original.convert("RGB")
        tira = render._tira_linea_de_tiempo(self.estados, img.size[0], alto_fila=8)
        marcas = [i for i in (render._indice_desde(self.cuadros, a.get("frame_index")) for a in self.alertas)
                  if i is not None]
        duracion = (self.cuadros[-1].timestamp_ms - self.t0) / 1000.0
        fps = round((len(self.cuadros) - 1) / duracion, 2) if duracion > 0 else None
        img = render._componer(img, idx, len(self.cuadros), cuadro, self.estados, tira, marcas, fps, self.t0)
        origen = {"sesion": self.sesion, "remera": self.toma.get("remera"),
                  "media_run_id": self.toma["ids"]["media_run_id"],
                  "control_run_id": self.toma["ids"]["control_run_id"], "cuadro": cuadro.frame_index,
                  "indice": idx, "de": len(self.cuadros), "desde_el_primero_ms": round(self.desde_el_primero(idx), 1),
                  "cr02": self.cr02(idx), "preview_sha256": _sha256(cuadro.preview)}
        return img, origen


def chaleco_falso(raices: list[Path]) -> Path:
    """El instante es el primero, desde que la toma con remera blanca confirmó su alerta de CR-02, en que la blanca
    sigue en alerta y la negra, a la misma distancia de su primer cuadro, ve el chaleco y no tiene a CR-02 en
    curso. Con la negra la regla entra y sale de «confirmando» sin llegar a confirmar: un cuadro de esa entrada
    diría lo contrario de lo que pasó en la toma."""
    from PIL import Image

    blanca, negra = _Toma(raices, TOMA_BLANCA), _Toma(raices, TOMA_NEGRA)
    alerta = next(a for a in blanca.toma["alertas"] if a["condicion"] == "CR-02")
    desde = blanca.cercano(alerta["captura_confirmacion_ms"] - blanca.t0)
    par = next(((ib, inn) for ib in range(desde, len(blanca.cuadros))
                for inn in [negra.cercano(blanca.desde_el_primero(ib))]
                if blanca.cr02(ib) in ("confirmed", "sustained")
                and negra.cr02(inn) == "inactive" and negra.con(inn, "vest")), None)
    if par is None:
        raise RuntimeError("no hay un instante con la blanca en alerta y la negra viendo el chaleco")
    img_blanca, origen_blanca = blanca.dibujar(par[0])
    img_negra, origen_negra = negra.dibujar(par[1])
    img_negra, img_blanca = _rotulo(img_negra, "Remera negra"), _rotulo(img_blanca, "Remera blanca")
    separacion = 12
    figura = Image.new("RGB", (img_negra.width + separacion + img_blanca.width,
                               max(img_negra.height, img_blanca.height)), (255, 255, 255))
    figura.paste(img_negra, (0, 0))
    figura.paste(img_blanca, (img_negra.width + separacion, 0))
    destino = SALIDA / "RT-09" / "chaleco-falso.png"
    return _guardar(figura, destino, {"figura": 5, "prueba": "RT-09", "criterio": " ".join(chaleco_falso.__doc__.split()),
                                      "izquierda": origen_negra, "derecha": origen_blanca})


def clase_nueva(raices: list[Path]) -> Path:
    from PIL import Image, ImageDraw

    corridas = json.loads((GEN2 / "EXT-01" / "corridas.json").read_text(encoding="utf-8"))["corridas"]
    run_id = corridas[CORRIDA_CLASE_NUEVA]["media_run_id"]
    media_dir = _buscar(raices, f"e-ovrt_media-plane/runs/{run_id}")
    evento = next((e for e in render._leer_jsonl(media_dir / "detections.jsonl")
                   if (e.get("source") or {}).get("source_id") == IMAGEN_CLASE_NUEVA), None)
    if evento is None:
        raise RuntimeError(f"{run_id}: no tiene la imagen {IMAGEN_CLASE_NUEVA}")
    ruta = _buscar(raices, f"e-ovrt_datasets/datasets/raw/construction_site_safety/valid/images/{IMAGEN_CLASE_NUEVA}")
    escala = 2
    with Image.open(ruta) as original:
        img = original.convert("RGB")
    img = img.resize((img.width * escala, img.height * escala), Image.Resampling.LANCZOS)
    draw = ImageDraw.Draw(img, "RGBA")
    fuente = render._fuente(max(18, img.height // 40))
    cajas = [d for d in evento["detections"] if d.get("label") == CLASE_NUEVA]
    color = (255, 140, 0)
    for d in sorted(cajas, key=lambda d: d["confidence"]):
        x0, y0, x1, y1 = (v * escala for v in d["bbox_xyxy"])
        draw.rectangle([x0, y0, x1, y1], outline=color + (255,), width=4)
        texto = f"{CLASE_NUEVA} {d['confidence']:.2f}".replace(".", ",")
        ancho_texto = draw.textlength(texto, font=fuente)
        alto_texto = max(22, img.height // 34)
        ty = y0 - alto_texto if y0 - alto_texto >= 0 else y0
        draw.rectangle([x0, ty, x0 + ancho_texto + 12, ty + alto_texto], fill=color + (230,))
        draw.text((x0 + 6, ty + 2), texto, font=fuente, fill=(20, 20, 20, 255))
    destino = SALIDA / "EXT-01" / "clase-nueva.png"
    return _guardar(img, destino, {
        "figura": 10, "prueba": "EXT-01", "corrida": CORRIDA_CLASE_NUEVA, "media_run_id": run_id,
        "imagen": IMAGEN_CLASE_NUEVA, "imagen_sha256": _sha256(ruta), "clase": CLASE_NUEVA,
        "cajas": [{"confianza": d["confidence"], "bbox_xyxy": d["bbox_xyxy"]} for d in cajas],
        "fuente": "construction_site_safety v27, Roboflow Universe (CC BY 4.0)"})


def _guardar(img, destino: Path, origen: dict) -> Path:
    destino.parent.mkdir(parents=True, exist_ok=True)
    img.save(destino, optimize=True)
    destino.with_suffix(".json").write_text(json.dumps(origen, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return destino


FIGURAS = {"chaleco-falso": chaleco_falso, "clase-nueva": clase_nueva}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--raiz", action="append", default=[], type=Path,
                   help="otra carpeta con e-ovrt_media-plane/, e-ovrt_control-plane/ o e-ovrt_datasets/ (se repite)")
    p.add_argument("--solo", default=",".join(FIGURAS), help="ids separados por coma")
    args = p.parse_args(argv)
    raices = [WORKSPACE, *args.raiz]
    fallas = 0
    for figura_id in [s.strip() for s in args.solo.split(",") if s.strip()]:
        try:
            destino = FIGURAS[figura_id](raices)
            print(f"{figura_id} → {destino.relative_to(REPO)}")
        except (KeyError, FileNotFoundError, RuntimeError, StopIteration) as e:
            fallas += 1
            print(f"{figura_id}: FALLA — {e!r}")
    return 1 if fallas else 0


if __name__ == "__main__":
    raise SystemExit(main())
