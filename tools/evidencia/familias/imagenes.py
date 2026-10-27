"""Percepción sobre imágenes (Tabla 51) y clase nueva sin entrenar (EXT-01).

IMG: una corrida de medios por estrato de `bench_v3` (obra `test` y `valid` sobre las
carpetas crudas, CHV, SHEL5K), evaluada contra el COCO CURADO de su estrato con la
evaluación del media-plane (`run_evaluation`, que carga `evaluate_bench.py` del repo de
datasets y restringe el GT a las imágenes procesadas). Agregado ponderado por `n_gt` y por
violadores reales (`curate/bench_v3_report.py`). Es exactamente como se armó la confirmación
B5 de la generación 1 (doc 66): con las corridas de julio este código devuelve mAP50 0,5505.

EXT: las cinco corridas de `docs/operacion/datos/94-piloto-clase-nueva.py` (más el par
"vehículo aislado") y su misma puntuación.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from ..catalogo import Prueba
from ..comparar import proponer
from ..herramientas import escribir_yaml, importar_datasets, importar_media_plane, resumen_media
from ..huellas import armar_prompts, sha256_archivo
from ..registro import Carpeta, ahora
from . import Contexto, familia, preparar_modelo
from .clips import experiment_id_de, slug_de

TIMEOUT_S = 7200.0


def _correr_medios(ctx: Contexto, prueba: Prueba, carpeta: Carpeta, clave: str, media_cfg: dict,
                   timeout_s: float) -> dict:
    """Un experimento de medios solos (sin control: no hay alertas que evaluar)."""
    ent = ctx.ent
    nombre = media_cfg["run"]["name"]
    dir_gen = ent.generados / prueba.id / nombre
    media_path = escribir_yaml(dir_gen / "media.yaml", media_cfg)
    manifiesto = {
        "schema_version": "experiment.manifest.v1",
        "slug": slug_de(prueba),
        "experiment_id": experiment_id_de(nombre),
        "runs": {"media": {"service": "media-plane", "config": str(media_path), "mode": "run"}},
        "sequencing": "media_first",
        "timeout_s": timeout_s,
        "changes": f"generación 2 — prueba {prueba.id} ({prueba.titulo})",
    }
    escribir_yaml(dir_gen / "manifest.yaml", manifiesto)
    carpeta.guardar_ejemplo(dir_gen)
    carpeta.comando(f"POST /api/experiments/run  manifiesto={dir_gen / 'manifest.yaml'}")
    t0, inicio = time.monotonic(), ahora()
    estado = ctx.consola.correr(manifiesto, timeout_s=timeout_s)
    registro = {
        "estado": "ok" if estado.get("ok") else "fallo",
        "experiment_id": estado.get("experiment_id"),
        "media_run_id": estado.get("media_run_id"),
        "media_status": estado.get("media_status"),
        "inicio": inicio,
        "fin": ahora(),
        "segundos": round(time.monotonic() - t0, 1),
        "media_config": str(media_path),
        "sha256": {"media_config": sha256_archivo(media_path)},
    }
    if not estado.get("ok"):
        registro["error"] = estado.get("error") or f"media={estado.get('media_status')}"
        return registro
    resumen_m = resumen_media(ent, registro["media_run_id"])
    registro["unidades"] = resumen_m.get("units_processed")
    registro["detecciones_totales"] = resumen_m.get("total_detections")
    registro["por_clase"] = resumen_m.get("detections_by_label")
    return registro


def _correr_trabajos(ctx: Contexto, prueba: Prueba, carpeta: Carpeta, trabajos: list[tuple[str, dict]],
                     timeout_s: float) -> list[str]:
    """Corre los que faltan; devuelve las claves que siguen pendientes."""
    for i, (clave, media_cfg) in enumerate(trabajos, 1):
        if carpeta.corrida_ok(clave) or ctx.reagregar:
            continue
        if ctx.solo and clave not in ctx.solo:
            continue
        ctx.avisar(f"  [{i}/{len(trabajos)}] {prueba.id} {clave}")
        registro = _correr_medios(ctx, prueba, carpeta, clave, media_cfg, timeout_s)
        carpeta.guardar_corrida(clave, registro)
        if registro["estado"] != "ok":
            ctx.avisar(f"      FALLÓ: {registro.get('error')}")
    corridas = carpeta.corridas()
    return [c for c, _ in trabajos if (corridas.get(c) or {}).get("estado") != "ok"]


def _media_cfg(ctx: Contexto, prueba: Prueba, clave: str, carpeta_imgs: str, prompts: dict,
               previews: bool = False) -> dict:
    ruta = ctx.ent.datasets / carpeta_imgs
    if not ruta.is_dir():
        raise FileNotFoundError(f"no existe la carpeta de imágenes {ruta}")
    return {
        "ingest": {"plugin": "image_folder", "config": {"path": ctx.ent.ruta_medios(ruta)}},
        "prompts": prompts,
        "run": {"name": f"gen2_{prueba.id.lower().replace('-', '')}_{clave}", "save_previews": previews},
    }


# --- IMG: bench_v3 por estrato -------------------------------------------------------


def evaluar_estrato(ctx: Contexto, run_dir: Path, coco: Path, person_gt: Path) -> dict:
    """`run_evaluation` del media-plane (persist=False) + el conteo de violadores CR-01,
    que el resultado del media-plane no expone y el agregado ponderado necesita."""
    runner = importar_media_plane(ctx.ent, "eovrt_media.evaluation.runner")
    # El media-plane busca el evaluador por ruta relativa al cwd; acá se fija absoluta.
    runner.EVALUATE_BENCH_SCRIPT = ctx.ent.scripts_datasets / "bench" / "evaluate_bench.py"
    res = runner.run_evaluation(
        run_dir=run_dir, bench_coco=coco, person_gt=person_gt,
        restrict_gt_to_detections=True, persist=False,
    ).model_dump(mode="json")
    eb = runner._load_evaluate_bench()
    dets = eb.load_detections([run_dir / "detections.jsonl"])
    imgs, _gt, _cats = eb.load_bench_coco(coco)
    detectadas = set(dets)
    imgs = {n: i for n, i in imgs.items() if n in detectadas}
    registros = [r for r in eb.load_person_gt(person_gt) if Path(r["file_name"]).name in detectadas]
    cr01 = eb.evaluate_cr01(registros, dets, imgs, res["iou_threshold"])
    res["cr01_n_violators"] = cr01.get("n_violators")
    res["cr01_n_detected"] = cr01.get("n_detected")
    res["bench_coco"] = str(coco)
    res["person_gt"] = str(person_gt)
    return res


@familia("imagenes")
def correr_imagenes(ctx: Contexto, prueba: Prueba, carpeta: Carpeta) -> dict:
    r = prueba.receta
    prompts, constancia = armar_prompts(r["prompts"], ctx.ent.repo)
    objetivo = None if ctx.reagregar else preparar_modelo(ctx, r, carpeta)
    estratos = r["estratos"]
    carpeta.escribir("configuracion.json", {"prompts": constancia, "modelo_cargado": objetivo,
                                            "estratos": estratos})
    trabajos = [(e["id"], _media_cfg(ctx, prueba, e["id"], e["imagenes"], prompts)) for e in estratos]
    pendientes = _correr_trabajos(ctx, prueba, carpeta, trabajos, float(r.get("timeout_s", TIMEOUT_S)))
    if pendientes:
        carpeta.resultado({"familia": "imagenes", "estado": "parcial", "pendientes": pendientes})
        return {"estado": "parcial", "pendientes": pendientes}

    reporte = importar_datasets(ctx.ent, "curate.bench_v3_report")
    corridas = carpeta.corridas()
    evals = {}
    for e in estratos:
        run_dir = ctx.ent.media_runs / corridas[e["id"]]["media_run_id"]
        ev = evaluar_estrato(ctx, run_dir, ctx.ent.datasets / e["coco"], ctx.ent.datasets / e["person_gt"])
        carpeta.escribir(f"evals/eval_{e['id']}.json", ev)
        evals[e["id"]] = ev
    clases = list(r.get("clases") or ["person", "helmet", "vest", "bare_head"])
    ponderado = reporte.weighted_map50(list(evals.values()), clases)
    presentes = [v for v in ponderado.values() if v is not None]
    recall = reporte.weighted_cr01_recall(list(evals.values()))
    metricas: dict = {
        "mAP50": round(sum(presentes) / len(presentes), 6) if presentes else None,
        **{f"ap50_{c}": (round(v, 6) if v is not None else None) for c, v in ponderado.items()},
        "recall_cr01": round(recall, 6) if recall is not None else None,
        "n_violadores_cr01": sum(ev.get("cr01_n_violators") or 0 for ev in evals.values()),
    }
    for eid, ev in evals.items():
        for c in ev["per_class"]:
            metricas[f"{eid}.{c['class_name']}"] = c["AP50"]
            metricas[f"{eid}.{c['class_name']}.n_gt"] = c["n_gt"]
        metricas[f"{eid}.cr01_recall"] = ev.get("cr01_detection_recall")
    gen1 = (prueba.gen1.get("referencia") or {}).get("valores") or {}
    resumen = [
        {"clave": "map50", "nombre": "mAP50 ponderado (bench_v3, 6.477 imágenes)", "valor": metricas["mAP50"],
         "unidad": None, "gen1": gen1.get("mAP50")},
        *[
            {"clave": f"ap50_{c}", "nombre": f"AP50 {c} (ponderado por n_gt)", "valor": metricas[f"ap50_{c}"],
             "unidad": None, "gen1": gen1.get(f"ap50_{c}")}
            for c in clases
        ],
        {"clave": "recall_cr01", "nombre": "Recall CR-01 por la vía directa (bare_head)",
         "valor": metricas["recall_cr01"], "unidad": None, "gen1": gen1.get("recall_cr01"),
         "n": metricas["n_violadores_cr01"]},
    ]
    datos = {
        "familia": "imagenes",
        "estado": "completo",
        "metricas": metricas,
        "resumen": resumen,
        "por_estrato": {eid: {"mAP50": ev.get("mAP50"), "cr01_recall": ev.get("cr01_detection_recall"),
                              "cr01_n_violators": ev.get("cr01_n_violators"),
                              "por_clase": {c["class_name"]: {"AP50": c["AP50"], "n_gt": c["n_gt"]}
                                            for c in ev["per_class"]}}
                        for eid, ev in evals.items()},
        "veredicto": proponer(metricas, prueba),
    }
    carpeta.resultado(datos)
    return {"estado": "completo", "mAP50": metricas["mAP50"], "veredicto": datos["veredicto"]["propuesto"]}


# --- EXT-01: clase nueva sin entrenar ------------------------------------------------


def _gt_obra_nuevas(ctx: Contexto):
    """Transcripción de `gt_bench_obra_nuevas()` del runner 94: machinery/vehicle del crudo,
    restringido a las 147 curadas."""
    ds = ctx.ent.datasets
    pgt = importar_datasets(ctx.ent, "bench.person_gt_cr02")
    curated = [json.loads((ds / "datasets/processed/coco/bench/curated" / f).read_text())
               for f in ("construction_site_safety_bench_obra_val.json",
                         "construction_site_safety_bench_obra_test.json")]
    labels = pgt.resolve_label_paths(curated, ds / "datasets/raw/construction_site_safety")
    images_by_filename, gt_by_image_id = {}, {}
    cat_by_id = {1: "machinery", 2: "vehicle"}
    idx = {"machinery": pgt.CSS_CLASSES.index("machinery"), "vehicle": pgt.CSS_CLASSES.index("vehicle")}
    next_id = 1
    for coco in curated:
        for img in coco["images"]:
            base = Path(img["file_name"]).name
            if base in images_by_filename:
                continue
            iid = next_id
            next_id += 1
            images_by_filename[base] = {"id": iid}
            anns = []
            lab = labels.get(base)
            if lab and lab.exists():
                for line in lab.read_text().splitlines():
                    if not line.strip():
                        continue
                    cid, xyxy = pgt.yolo_line_to_xyxy(line, img["width"], img["height"])
                    for cname, raw_idx in idx.items():
                        if cid == raw_idx:
                            anns.append({"category_id": 1 if cname == "machinery" else 2,
                                         "bbox": [xyxy[0], xyxy[1], xyxy[2] - xyxy[0], xyxy[3] - xyxy[1]]})
            gt_by_image_id[iid] = anns
    return images_by_filename, gt_by_image_id, cat_by_id


def _gt_mocs_person(ctx: Contexto):
    """Transcripción de `gt_mocs_person()` del runner 94: Worker renombrado a person."""
    coco = json.loads((ctx.ent.datasets / "datasets/raw/MOCS/valid/_annotations.coco.json").read_text())
    images_by_filename, gt_by_image_id = {}, {}
    for img in coco["images"]:
        images_by_filename[Path(img["file_name"]).name] = {"id": img["id"]}
        gt_by_image_id[img["id"]] = []
    worker_ids = {c["id"] for c in coco["categories"] if c["name"].lower() == "worker"}
    for ann in coco["annotations"]:
        if ann["category_id"] in worker_ids:
            gt_by_image_id.setdefault(ann["image_id"], []).append({"category_id": 99, "bbox": ann["bbox"]})
    return images_by_filename, gt_by_image_id, {99: "person"}


@familia("clase_nueva")
def correr_clase_nueva(ctx: Contexto, prueba: Prueba, carpeta: Carpeta) -> dict:
    r = prueba.receta
    objetivo = None if ctx.reagregar else preparar_modelo(ctx, r, carpeta)
    trabajos, constancias = [], {}
    for t in r["corridas"]:
        spec = {**r["prompts"], "clases": t["clases"]}
        prompts, constancias[t["id"]] = armar_prompts(spec, ctx.ent.repo)
        trabajos.append((t["id"], _media_cfg(ctx, prueba, t["id"], t["imagenes"], prompts,
                                             previews=bool(t.get("previews")))))
    carpeta.escribir("configuracion.json", {"prompts": constancias, "modelo_cargado": objetivo,
                                            "corridas": r["corridas"]})
    pendientes = _correr_trabajos(ctx, prueba, carpeta, trabajos, float(r.get("timeout_s", TIMEOUT_S)))
    if pendientes:
        carpeta.resultado({"familia": "clase_nueva", "estado": "parcial", "pendientes": pendientes})
        return {"estado": "parcial", "pendientes": pendientes}

    eb = importar_datasets(ctx.ent, "bench.evaluate_bench")
    corridas = carpeta.corridas()

    def dets(*claves):
        return eb.load_detections([ctx.ent.media_runs / corridas[c]["media_run_id"] / "detections.jsonl"
                                   for c in claves])

    puntajes: dict = {}
    imgs, gt, cats = _gt_obra_nuevas(ctx)
    d_obra = dets("obra_val", "obra_test")
    for cname in ("machinery", "vehicle"):
        puntajes[f"bench_obra/{cname}"] = eb.evaluate_class(cname, d_obra, imgs, gt, cats, iou_threshold=0.5)
    d_veh = dets("vehiculo_val", "vehiculo_test")
    puntajes["bench_obra/vehicle_sin_machinery"] = eb.evaluate_class("vehicle", d_veh, imgs, gt, cats,
                                                                     iou_threshold=0.5)
    d_mocs = dets("mocs_valid")
    imgs_m, gt_m, cats_m = _gt_mocs_person(ctx)
    puntajes["mocs/person_vs_worker"] = eb.evaluate_class("person", d_mocs, imgs_m, gt_m, cats_m, iou_threshold=0.5)
    stats = {}
    for cname in ("excavator", "dump_truck", "tower_crane"):
        por_img = {f: [d for d in ds if d.get("prompt_id") == cname] for f, ds in d_mocs.items()}
        stats[cname] = {
            "imgs_con_deteccion@0.30": sum(1 for v in por_img.values() if any(d["confidence"] >= .30 for d in v)),
            "imgs_con_deteccion@0.50": sum(1 for v in por_img.values() if any(d["confidence"] >= .50 for d in v)),
            "total_detecciones": sum(len(v) for v in por_img.values()),
        }
    puntajes["mocs/maquinas_sin_gt"] = {"imgs_total": len(d_mocs), **stats}
    carpeta.escribir("evals/puntajes.json", puntajes)

    metricas = {
        "ap50_machinery_obra": puntajes["bench_obra/machinery"]["AP50"],
        "ap50_vehicle_obra": puntajes["bench_obra/vehicle"]["AP50"],
        "ap50_vehicle_sin_machinery": puntajes["bench_obra/vehicle_sin_machinery"]["AP50"],
        "ap50_person_vs_worker_mocs": puntajes["mocs/person_vs_worker"]["AP50"],
        **{f"mocs_{c}_imgs@0.50": s["imgs_con_deteccion@0.50"] for c, s in stats.items()},
    }
    gen1 = (prueba.gen1.get("referencia") or {}).get("valores") or {}
    nombres = {
        "ap50_machinery_obra": "AP50 machinery (obra, 147 imgs, clase jamás configurada)",
        "ap50_vehicle_obra": "AP50 vehicle (obra, con machinery en el caption)",
        "ap50_vehicle_sin_machinery": "AP50 vehicle (obra, sin machinery en el caption)",
        "ap50_person_vs_worker_mocs": "AP50 person contra Worker (MOCS valid, 151 imgs)",
    }
    resumen = [{"clave": k, "nombre": n, "valor": metricas[k], "unidad": None, "gen1": gen1.get(k)}
               for k, n in nombres.items()]
    datos = {"familia": "clase_nueva", "estado": "completo", "metricas": metricas, "resumen": resumen,
             "puntajes": puntajes, "veredicto": proponer(metricas, prueba)}
    carpeta.resultado(datos)
    return {"estado": "completo", "veredicto": datos["veredicto"]["propuesto"]}
