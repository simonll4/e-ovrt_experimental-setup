"""Driver de evidencia de la generación 2 (tools/evidencia, doc 134).

Sin servicios: la consola es un doble en memoria que «corre» cada experimento escribiendo
los artefactos que dejaría la plataforma. El catálogo y los prompt sets son los reales.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
import yaml

from tools.evidencia import catalogo as cat
from tools.evidencia import herramientas
from tools.evidencia.__main__ import main as cli
from tools.evidencia.comparar import proponer
from tools.evidencia.entorno import REPO, Entorno
from tools.evidencia.familias import Contexto, DependenciaIncompleta, clips
from tools.evidencia.huellas import (
    HuellaInvalida,
    armar_prompts,
    coincide,
    hash_clases,
    sha256_archivo,
    verificar_lista,
)
from tools.evidencia.registro import Carpeta, PreRegistroCambiado

CATALOGO = REPO / "experiments" / "evidencia"
V2_SHORT = {
    "set_id": "cr01_cr02_v2_short",
    "fuente": "prompts/cr01_cr02_v2_short.yaml",
    "clases": ["person", "helmet", "vest"],
    "frozen": {"prompts/cr01_cr02_v2_short.yaml": "df81fd48b6daf8924b5fb66aa1ce4acc0c880ac6ed8cd1245c6aca1babdb309a"},
}


# --- catálogo ------------------------------------------------------------------------


def test_el_catalogo_real_carga_y_tiene_las_41_pruebas():
    catalogo = cat.cargar_catalogo(CATALOGO)
    assert len(catalogo) == 41
    assert {"ALR-01", "ALR-02", "IMG-01", "PER-03", "RT-04", "RT-05", "DIST-01", "GT-02"} <= set(catalogo)
    # la enmienda del doc 137 (2026-10-29)
    assert {"ALR-09", "ALR-10", "IMG-04", "ERR-01", "ERR-02", "SEG-01", "VIS-01"} <= set(catalogo)
    for prueba in catalogo.values():
        assert prueba.familia in cat.FAMILIAS


def test_seleccionar_una_fase_respeta_dependencias():
    catalogo = cat.cargar_catalogo(CATALOGO)
    orden = [p.id for p in cat.seleccionar(catalogo, ["F3", "F5"])]
    assert orden.index("ALR-01") < orden.index("ALR-02")
    assert orden.index("ALR-07") < orden.index("ALR-08")
    assert orden.index("ALR-02") < orden.index("GT-02")
    assert "IMG-01" not in orden


CONTRASTES = {"ALR-03", "ALR-04", "ALR-05", "ALR-06", "IMG-02", "IMG-03", "PER-02"}


def test_los_contrastes_se_regeneran_con_sus_fases():
    # Enmienda del 2026-10-30 (doc 134 §13.10): todo se corre en la Victus.
    catalogo = cat.cargar_catalogo(CATALOGO)
    assert not [p.id for p in catalogo.values() if p.estado == "no_se_regenera"]
    for objetivo in (["todas"], ["F3", "F4", "F5"]):
        assert CONTRASTES <= {p.id for p in cat.seleccionar(catalogo, objetivo)}
    orden = [p.id for p in cat.seleccionar(catalogo, ["F3", "F5"])]
    assert orden.index("ALR-04") < orden.index("ALR-05") < orden.index("GT-02")
    assert orden.index("ALR-06") < orden.index("GT-02")
    for pid in CONTRASTES:
        assert catalogo[pid].gen1.get("cifras") or catalogo[pid].gen1.get("referencia"), pid


def test_no_se_regenera_exige_motivo_y_cifra_vigente(tmp_path):
    ruta = _prueba(tmp_path, "ALR-03", estado="no_se_regenera")
    with pytest.raises(cat.CatalogoInvalido, match="dice por qué"):
        cat.cargar_prueba(ruta)
    ruta = _prueba(tmp_path / "b", "ALR-03", estado="no_se_regenera", no_se_regenera="contraste")
    with pytest.raises(cat.CatalogoInvalido, match="cifra vigente"):
        cat.cargar_prueba(ruta)


def test_gt02_evalua_solo_las_conclusiones_de_las_campanas_que_corren():
    from tools.evidencia.familias.analisis import CHEQUEOS, chequeos_para

    receta = cat.cargar_catalogo(CATALOGO)["GT-02"].receta
    evaluables, solo_gen1 = chequeos_para(receta["campanas"])
    assert solo_gen1 == [] and set(evaluables) == set(CHEQUEOS) and len(evaluables) == 12
    parcial, faltan = chequeos_para(["T1", "G1", "R1", "R2", "R3", "R4", "R5", "R6", "I1", "I2"])
    assert sorted(faltan) == ["C2_T1>=T2", "C3_D1_prec<0.5", "C4_T1>H1", "C5_T1>B1"]
    assert len(parcial) == 8


def test_seleccionar_rechaza_objetivos_desconocidos():
    with pytest.raises(cat.CatalogoInvalido):
        cat.seleccionar(cat.cargar_catalogo(CATALOGO), ["ZZZ-99"])


def _prueba(tmp_path: Path, pid: str, **datos) -> Path:
    carpeta = tmp_path / pid
    carpeta.mkdir(parents=True)
    contenido = {"schema": "prueba.gen2.v1", "id": pid, "titulo": "t", "fase": "F3", "familia": "clips", **datos}
    (carpeta / "prueba.yaml").write_text(yaml.safe_dump(contenido, allow_unicode=True), encoding="utf-8")
    return carpeta / "prueba.yaml"


def test_prueba_con_id_distinto_de_su_carpeta_es_invalida(tmp_path):
    ruta = _prueba(tmp_path, "ALR-01")
    datos = yaml.safe_load(ruta.read_text())
    datos["id"] = "ALR-02"
    ruta.write_text(yaml.safe_dump(datos))
    with pytest.raises(cat.CatalogoInvalido, match="no coincide"):
        cat.cargar_prueba(ruta)


def test_dependencia_inexistente_es_invalida(tmp_path):
    _prueba(tmp_path, "ALR-02", depende_de=["ALR-99"])
    with pytest.raises(cat.CatalogoInvalido, match="dependencias"):
        cat.cargar_catalogo(tmp_path)


# --- huellas -------------------------------------------------------------------------


def test_prompts_salen_con_la_forma_exacta_de_la_generacion_1():
    payload, constancia = armar_prompts(V2_SHORT, REPO)
    # Transcripción literal de PROMPTS en docs/operacion/datos/81-ciclo-rodaje-runner.py
    assert payload == {
        "set_inline": {
            "id": "cr01_cr02_v2_short",
            "classes": [
                {"id": "person", "phrasings": {"default": ["person"]}},
                {"id": "helmet", "phrasings": {"default": ["helmet"]}},
                {"id": "vest", "phrasings": {"default": ["vest"]}},
            ],
        },
        "active_ids": ["person", "helmet", "vest"],
    }
    assert constancia["fuentes"]["prompts/cr01_cr02_v2_short.yaml"]["status"] == "frozen"


def test_prompts_de_dos_sets_para_e_dir():
    spec = {"set_id": "edir_v1_pair_nivel_b", "clases": [
        {"id": "person", "fuente": "prompts/eind_v1.yaml"},
        {"id": "cr01_spec", "fuente": "prompts/edir_v1.yaml"},
        {"id": "cr02_obs", "fuente": "prompts/edir_v1.yaml"}]}
    payload, _ = armar_prompts(spec, REPO)
    frases = {c["id"]: c["phrasings"]["default"] for c in payload["set_inline"]["classes"]}
    assert frases == {"person": ["person"],
                      "cr01_spec": ["construction worker without safety helmet"],
                      "cr02_obs": ["person without bright colored safety clothing"]}


def test_huella_de_prompts_que_no_coincide_no_corre():
    spec = {**V2_SHORT, "frozen": {"prompts/cr01_cr02_v2_short.yaml": "0" * 64}}
    with pytest.raises(HuellaInvalida):
        armar_prompts(spec, REPO)


def test_hash_de_clases_es_el_de_la_consola():
    from eovrt_webconsole.prompt_store import classes_sha256

    clases = [{"id": "person", "phrasings": {"default": ["person"]}}]
    assert hash_clases(clases) == classes_sha256(clases)


def test_verificar_lista_acepta_crlf_y_lo_declara(tmp_path):
    lf = tmp_path / "a.json"
    lf.write_bytes(b'{\n  "x": 1\n}\n')
    esperado = sha256_archivo(lf)
    lf.write_bytes(b'{\r\n  "x": 1\r\n}\r\n')  # lo que deja un clon con autocrlf
    (tmp_path / "otro.bin").write_bytes(b"\x00\x01")
    lista = tmp_path / "lista.sha256"
    lista.write_text(f"{esperado}  a.json\n{'0' * 64}  otro.bin\n{'1' * 64}  falta.bin\n")
    res = verificar_lista(lista, tmp_path)
    assert res["ok"] == 0 and res["ok_salvo_finales_de_linea"] == 1
    assert res["fallan"] == ["otro.bin"] and res["faltan"] == ["falta.bin"]
    assert coincide(lf, esperado) == "ok_crlf"


# --- veredictos ----------------------------------------------------------------------


class _P:
    def __init__(self, gen1=None, **datos):
        self.gen1 = gen1 or {}
        self.datos = datos


def test_veredicto_identico_tolera_redondeo_a_6_decimales():
    p = _P({"referencia": {"valores": {"f1_micro": 0.84058, "matched": 29}}})
    v = proponer({"f1_micro": 0.840580000001, "matched": 29}, p)
    assert v["propuesto"] == "identico"


def test_veredicto_a_revisar_sin_causa_declarada_y_equivalente_con_causa():
    p = _P({"referencia": {"valores": {"matched": 29}}})
    assert proponer({"matched": 28}, p)["propuesto"] == "a_revisar"
    p2 = _P({"referencia": {"valores": {"matched": 29}}}, diferencia_esperada="GT corregido")
    v = proponer({"matched": 28}, p2)
    assert v["propuesto"] == "equivalente_con_diferencia" and v["diferencias"]["matched"] == {"gen2": 28, "gen1": 29}


def test_veredicto_otra_combinacion_declarada():
    p = _P({"relacion": "otra_combinacion", "motivo": "corpus distinto"})
    assert proponer({"p95": 10}, p)["propuesto"] == "otra_combinacion"


# --- registro ------------------------------------------------------------------------


def _entorno(tmp_path: Path) -> Entorno:
    return Entorno(ws=tmp_path / "ws", repo=REPO, modo="docker", consola_url="http://consola",
                   datasets_medios="/e-ovrt_datasets")


def test_pre_registro_cambiado_frena_y_forzar_archiva(tmp_path, monkeypatch):
    monkeypatch.setenv("EOVRT_EVIDENCIA_SALIDA", str(tmp_path / "salida"))
    ruta = _prueba(tmp_path / "cat", "ALR-01")
    prueba = cat.cargar_prueba(ruta)
    carpeta = Carpeta(_entorno(tmp_path), prueba)
    carpeta.preparar()
    carpeta.guardar_corrida("a_p1_c02", {"estado": "ok"})
    ruta.write_text(ruta.read_text() + "# cambio\n")
    prueba = cat.cargar_prueba(ruta)
    carpeta = Carpeta(_entorno(tmp_path), prueba)
    with pytest.raises(PreRegistroCambiado):
        carpeta.preparar()
    carpeta.preparar(forzar=True)
    assert carpeta.corridas() == {}
    assert any(p.name.startswith("ALR-01.descartada-") for p in carpeta.dir.parent.iterdir())


def test_veredicto_confirmado_no_se_pisa_al_reagregar(tmp_path, monkeypatch):
    monkeypatch.setenv("EOVRT_EVIDENCIA_SALIDA", str(tmp_path / "salida"))
    prueba = cat.cargar_prueba(_prueba(tmp_path / "cat", "ALR-01"))
    carpeta = Carpeta(_entorno(tmp_path), prueba)
    carpeta.resultado({"estado": "completo", "veredicto": {"propuesto": "identico", "confirmado": None}})
    datos = carpeta.leer("resultado.json")
    datos["veredicto"]["confirmado"] = {"valor": "identico", "quien": "x"}
    carpeta.escribir("resultado.json", datos)
    carpeta.resultado({"estado": "completo", "veredicto": {"propuesto": "identico", "confirmado": None}})
    assert carpeta.leer("resultado.json")["veredicto"]["confirmado"]["quien"] == "x"


def test_ruta_medios_traduce_al_montaje_del_media_plane(tmp_path):
    ent = _entorno(tmp_path)
    video = ent.datasets / "datasets/raw/clip_bench/clips/a_p1_c02.mp4"
    assert ent.ruta_medios(video) == "/e-ovrt_datasets/datasets/raw/clip_bench/clips/a_p1_c02.mp4"


# --- familia clips con una consola falsa -----------------------------------------------


class ConsolaFalsa:
    """Hace lo que haría el runner de la consola: escribe los artefactos de cada plano."""

    def __init__(self, ent: Entorno, modelo="grounding-dino/gdino-tiny-560", fallar=(), unidades=None):
        self.ent = ent
        self.modelo = modelo
        self.fallar = set(fallar)
        self.unidades = unidades
        self.manifiestos: list[dict] = []
        self.activadas: list[str] = []
        self.n = 0

    def salud(self):
        return True

    def objetivo(self):
        return {"ready": True, "model": {"ref": self.modelo}}

    def instancias(self):
        return [{"name": "mp-gdino-tiny-560", "is_target": True, "ready": True}]

    def activar(self, nombre):
        self.activadas.append(nombre)

    def correr(self, manifiesto, *, timeout_s):
        self.manifiestos.append(manifiesto)
        self.n += 1
        clip = manifiesto.get("clip_id")
        if clip in self.fallar:
            return {"ok": False, "status": "failed", "media_status": "failed", "experiment_id": f"exp_{self.n}"}
        media = manifiesto["runs"]["media"]
        media_id = media.get("reuse_run_id") or (Path(media["reuse_run_dir"]).name if media.get("reuse_run_dir") else f"run_m{self.n}")
        if not (media.get("reuse_run_id") or media.get("reuse_run_dir")):
            d = self.ent.media_runs / media_id
            d.mkdir(parents=True)
            (d / "detections.jsonl").write_text("{}\n")
            (d / "summary.json").write_text(json.dumps({"status": "succeeded", "units_processed": self.unidades or 100}))
        control_id = f"ctl_{self.n}"
        c = self.ent.control_runs / control_id
        c.mkdir(parents=True)
        (c / "alerts.jsonl").write_text("")
        return {"ok": True, "status": "succeeded", "experiment_id": f"exp_{self.n}",
                "media_run_id": media_id, "control_run_id": control_id}


@pytest.fixture
def banco(tmp_path, monkeypatch):
    monkeypatch.setenv("EOVRT_EVIDENCIA_SALIDA", str(tmp_path / "salida"))
    ent = _entorno(tmp_path)
    clips_dir = ent.datasets / "datasets/raw/clip_bench/clips"
    clips_dir.mkdir(parents=True)
    ent.gt_banco.mkdir(parents=True)
    filas = []
    for clip in ("a_p1_c02", "a_p1_c03"):
        (clips_dir / f"{clip}.mp4").write_bytes(b"")
        (ent.gt_banco / f"{clip}.json").write_text("{}")
        filas.append({"clip_id": clip, "file": f"../../raw/clip_bench/clips/{clip}.mp4", "fps": 30, "duration_ms": 10000})
    (ent.banco / "manifest.yaml").write_text(yaml.safe_dump({"clips": filas}))
    ent.patrones.mkdir(parents=True)
    for nombre in ("cr01_cr02_v2", "cr01_cr02_v2_subject", "cr01_cr02_hyb_or_v1"):
        shutil.copy(REPO.parent / "e-ovrt_control-plane/configs/patterns" / f"{nombre}.yaml", ent.patrones)
    ent.media_runs.mkdir(parents=True)
    ent.control_runs.mkdir(parents=True)

    def evaluar(ent_, *, alertas, gt, detecciones, patrones, salida):
        salida.parent.mkdir(parents=True, exist_ok=True)
        salida.write_text(json.dumps({"alertas": str(alertas), "detecciones": str(detecciones)}))
        return ["eovrt-control", "evaluate-alerts", str(alertas)]

    monkeypatch.setattr(clips, "evaluar_alertas", evaluar)
    monkeypatch.setattr(clips, "_agregar", lambda ctx, prueba, evals_dir, v=None: {
        "positives": {"f1_micro": 0.5, "matched": len(list(Path(evals_dir).glob("eval_*.json")))},
        "negatives": {"false_positives": 0}})
    return ent


def _correr(ent, prueba_datos, consola, catalogo_extra=(), **ctx_kw):
    catalogo = {}
    for pid, datos in [("ALR-01", prueba_datos), *catalogo_extra]:
        ruta = _prueba(ent.ws.parent / "cat" / pid, pid, **datos)
        catalogo[pid] = cat.cargar_prueba(ruta)
    ctx = Contexto(ent=ent, consola=consola, catalogo=catalogo, avisar=lambda *_: None, **ctx_kw)
    prueba = catalogo[prueba_datos.get("_id", "ALR-01")]
    carpeta = Carpeta(ent, prueba)
    carpeta.preparar()
    return clips.correr(ctx, prueba, carpeta), carpeta, ctx


RECETA_INFERENCIA = {"tipo": "inferencia", "clips": ["a_p1_c02", "a_p1_c03"], "instancia": "mp-gdino-tiny-560",
                     "modelo": "grounding-dino/gdino-tiny-560", "medios": {"prompts": V2_SHORT},
                     "control": {"patrones": "cr01_cr02_v2", "activos": ["CR-01", "CR-02"]}}


def test_inferencia_dispara_un_experimento_por_clip_con_rutas_del_media_plane(banco):
    consola = ConsolaFalsa(banco)
    salida, carpeta, _ = _correr(banco, {"receta": RECETA_INFERENCIA}, consola)
    assert salida["estado"] == "completo"
    assert len(consola.manifiestos) == 2
    m = consola.manifiestos[0]
    assert m["sequencing"] == "media_first" and m["clip_id"] == "a_p1_c02"
    assert m["ground_truth"] == str(banco.gt_banco / "a_p1_c02.json")
    media = yaml.safe_load(Path(m["runs"]["media"]["config"]).read_text())
    assert media["ingest"]["config"]["path"] == "/e-ovrt_datasets/datasets/raw/clip_bench/clips/a_p1_c02.mp4"
    assert "stride" not in media["run"]  # stride 1 = el cuerpo de la gen 1, sin la clave
    control = yaml.safe_load(Path(m["runs"]["control"]["config"]).read_text())
    assert control["patterns"]["file"].endswith("cr01_cr02_v2.yaml")
    assert m["runs"]["control"]["mode"] == "replay"
    resultado = carpeta.leer("resultado.json")
    assert resultado["estado"] == "completo" and resultado["metricas"]["f1_micro"] == 0.5
    assert (carpeta.logs / "ejemplo" / "manifest.yaml").is_file()
    # Los generados no van bajo experiments/: la consola los listaría como experimentos.
    assert "experiments" not in Path(m["runs"]["control"]["config"]).parts


def test_se_retoma_donde_quedo_y_un_fallo_deja_la_prueba_parcial(banco):
    consola = ConsolaFalsa(banco, fallar={"a_p1_c03"})
    salida, carpeta, _ = _correr(banco, {"receta": RECETA_INFERENCIA}, consola)
    assert salida["estado"] == "parcial" and salida["pendientes"] == ["a_p1_c03"]
    assert carpeta.corridas()["a_p1_c03"]["estado"] == "fallo"
    consola2 = ConsolaFalsa(banco)
    consola2.n = 100
    salida2, _, _ = _correr_de_nuevo(banco, carpeta, consola2)
    assert salida2["estado"] == "completo"
    assert [m["clip_id"] for m in consola2.manifiestos] == ["a_p1_c03"]


def _correr_de_nuevo(ent, carpeta, consola):
    ctx = Contexto(ent=ent, consola=consola, catalogo={"ALR-01": carpeta.prueba}, avisar=lambda *_: None)
    return clips.correr(ctx, carpeta.prueba, carpeta), carpeta, ctx


def test_modelo_equivocado_no_corre(banco):
    consola = ConsolaFalsa(banco, modelo="grounding-dino/gdino-base-560")
    consola.instancias = lambda: [{"name": "mp-gdino-tiny-560", "is_target": True, "ready": True}]
    with pytest.raises(Exception, match="modelo cargado"):
        _correr(banco, {"receta": RECETA_INFERENCIA}, consola)


def test_guard_de_stride(banco):
    receta = {**RECETA_INFERENCIA, "medios": {"prompts": V2_SHORT, "stride": 7}}
    consola = ConsolaFalsa(banco, unidades=100)  # 10 s a 30 fps / 7 ≈ 43, no 100
    salida, carpeta, _ = _correr(banco, {"receta": receta}, consola)
    assert salida["estado"] == "parcial"
    assert "guard de stride" in carpeta.corridas()["a_p1_c02"]["error"]
    media = yaml.safe_load(Path(consola.manifiestos[0]["runs"]["media"]["config"]).read_text())
    assert media["run"]["stride"] == 7


def test_reuso_relee_las_detecciones_de_la_prueba_de_origen(banco):
    consola = ConsolaFalsa(banco)
    _, carpeta_origen, _ = _correr(banco, {"receta": RECETA_INFERENCIA}, consola)
    origen = carpeta_origen.corridas()
    receta = {"tipo": "reuso", "reusa": "ALR-01", "clips": ["a_p1_c02", "a_p1_c03"],
              "control": {"patrones": "cr01_cr02_v2_subject", "activos": ["CR-01", "CR-02"], "track_persons": True}}
    ruta = _prueba(banco.ws.parent / "cat2" / "ALR-02", "ALR-02", receta=receta, depende_de=["ALR-01"])
    prueba = cat.cargar_prueba(ruta)
    catalogo = {"ALR-01": carpeta_origen.prueba, "ALR-02": prueba}
    consola2 = ConsolaFalsa(banco)
    consola2.n = 50
    ctx = Contexto(ent=banco, consola=consola2, catalogo=catalogo, avisar=lambda *_: None)
    carpeta = Carpeta(banco, prueba)
    carpeta.preparar()
    assert clips.correr(ctx, prueba, carpeta)["estado"] == "completo"
    m = consola2.manifiestos[0]
    assert m["runs"]["media"]["reuse_run_id"] == origen["a_p1_c02"]["media_run_id"]
    control = yaml.safe_load(Path(m["runs"]["control"]["config"]).read_text())
    assert control["input"]["track_persons"] is True


def test_reuso_exige_que_el_origen_este_completo(banco):
    receta = {"tipo": "reuso", "reusa": "ALR-01", "clips": ["a_p1_c02"],
              "control": {"patrones": "cr01_cr02_v2", "activos": ["CR-01"]}}
    ruta_o = _prueba(banco.ws.parent / "cat3" / "ALR-01", "ALR-01", receta=RECETA_INFERENCIA)
    ruta = _prueba(banco.ws.parent / "cat3" / "ALR-02", "ALR-02", receta=receta, depende_de=["ALR-01"])
    catalogo = {"ALR-01": cat.cargar_prueba(ruta_o), "ALR-02": cat.cargar_prueba(ruta)}
    ctx = Contexto(ent=banco, consola=ConsolaFalsa(banco), catalogo=catalogo, avisar=lambda *_: None)
    carpeta = Carpeta(banco, catalogo["ALR-02"])
    carpeta.preparar()
    with pytest.raises(DependenciaIncompleta):
        clips.correr(ctx, catalogo["ALR-02"], carpeta)


def test_fusion_escribe_un_directorio_reusable_con_summary(banco, monkeypatch):
    llamadas = []

    class Merge:
        @staticmethod
        def merge_detection_streams(a, b, salida, clases):
            llamadas.append((a, b, clases))
            Path(salida).write_text("{}\n")
            return {"frames": 3, "direct_hits": 1}

    monkeypatch.setattr(clips, "importar_datasets", lambda ent, modulo: Merge)
    consola = ConsolaFalsa(banco)
    _, c1, _ = _correr(banco, {"receta": RECETA_INFERENCIA}, consola)
    ruta4 = _prueba(banco.ws.parent / "cat4" / "ALR-04", "ALR-04", receta=RECETA_INFERENCIA)
    p4 = cat.cargar_prueba(ruta4)
    c4 = Carpeta(banco, p4)
    c4.preparar()
    ctx4 = Contexto(ent=banco, consola=consola, catalogo={"ALR-04": p4}, avisar=lambda *_: None)
    clips.correr(ctx4, p4, c4)
    receta = {"tipo": "fusion", "clips": ["a_p1_c02", "a_p1_c03"],
              "fusion": {"eind": "ALR-01", "edir": "ALR-04", "clases_directas": ["cr01_spec", "cr02_obs"]},
              "control": {"patrones": "cr01_cr02_hyb_or_v1", "activos": ["CR-01", "CR-02"]}}
    ruta5 = _prueba(banco.ws.parent / "cat4" / "ALR-05", "ALR-05", receta=receta, depende_de=["ALR-01", "ALR-04"])
    p5 = cat.cargar_prueba(ruta5)
    c5 = Carpeta(banco, p5)
    c5.preparar()
    ctx5 = Contexto(ent=banco, consola=consola, catalogo={"ALR-01": c1.prueba, "ALR-04": p4, "ALR-05": p5},
                    avisar=lambda *_: None)
    assert clips.correr(ctx5, p5, c5)["estado"] == "completo"
    m = consola.manifiestos[-1]
    fusion_dir = Path(m["runs"]["media"]["reuse_run_dir"])
    assert fusion_dir.name == "fusion_a_p1_c03"
    assert json.loads((fusion_dir / "summary.json").read_text())["status"] == "succeeded"
    assert llamadas[0][2] == ("cr01_spec", "cr02_obs")


# --- CLI -----------------------------------------------------------------------------


def test_cli_lista_y_verificar_sobre_el_catalogo_real(capsys, monkeypatch, tmp_path):
    monkeypatch.setenv("EOVRT_EVIDENCIA_SALIDA", str(tmp_path))
    monkeypatch.setenv("EOVRT_EVIDENCIA_CONSOLA", "http://127.0.0.1:9")  # nadie escucha
    assert cli(["lista", "--fase", "F1"]) == 0
    salida = capsys.readouterr().out
    assert "INT-01" in salida and "ALR-01" not in salida
    assert cli(["verificar", "INT-03", "GT-01"]) == 0
    assert "la consola no responde" in capsys.readouterr().out


def test_cli_correr_sin_consola_falla_claro_si_la_prueba_la_necesita(capsys, monkeypatch, tmp_path):
    monkeypatch.setenv("EOVRT_EVIDENCIA_SALIDA", str(tmp_path))
    monkeypatch.setenv("EOVRT_EVIDENCIA_CONSOLA", "http://127.0.0.1:9")
    assert cli(["correr", "ALR-01"]) == 2
    assert "la consola no responde" in capsys.readouterr().err


def test_herramientas_clips_de_rodaje_e_internet():
    ent = Entorno(ws=REPO.parent, repo=REPO, modo="nativo", consola_url="x", datasets_medios="x")
    assert len(herramientas.clips_de(ent, "rodaje")) == 34
    assert len(herramientas.clips_de(ent, "internet")) == 13


# --- RT-04: el rodaje en vivo importado desde las sesiones de la demo -------------------

from tools.evidencia.familias import rodaje  # noqa: E402


def _sesion(ent, sesiones: Path, sid: str, escena: str, *, alertas, eventos, marcas, testigo,
            unidades=40, fase="done", exploracion=None):
    media_id, control_id = f"run_{sid}", f"ctl_{sid}"
    d = sesiones / sid
    (d / "config").mkdir(parents=True)
    (d / "config" / "media.yaml").write_text("ingest: {plugin: oak_d}\n")
    (d / "session.json").write_text(json.dumps({
        "session_id": sid, "escena": escena, "fase": fase, "experiment_id": f"exp_{sid}",
        "ids": {"media_run_id": media_id, "control_run_id": control_id},
        "fin_pedido_en": "2026-11-01T10:00:00+00:00", "terminada_en": "2026-11-01T10:00:12+00:00",
        "exploracion": exploracion}))
    (d / "witness.jsonl").write_text("".join(json.dumps(m) + "\n" for m in testigo))
    if marcas is not None:
        (d / "marcas.json").write_text("﻿" + json.dumps(marcas))  # con BOM, como PowerShell
    mr = ent.media_runs / media_id
    mr.mkdir(parents=True)
    (mr / "metrics.jsonl").write_text("".join(json.dumps({
        "unit_id": f"u{i}", "capture_wallclock_ms": 1_000_000 + 200 * i, "capture_monotonic_ns": i * 200_000_000,
        "capture_to_host_ms": 70.0, "g2a_ms": 150.0}) + "\n" for i in range(unidades)))
    (mr / "summary.json").write_text(json.dumps({"units_processed": unidades, "fps_effective": 5.0}))
    cr = ent.control_runs / control_id
    cr.mkdir(parents=True)
    (cr / "alerts.jsonl").write_text("".join(json.dumps(a) + "\n" for a in alertas))
    (cr / "pattern_events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in eventos))
    (cr / "summary.json").write_text(json.dumps({"bus_dropped_events": 0}))


class ConsolaSujeto(ConsolaFalsa):
    """La relectura por sujeto: deja una alerta CR-01 de un solo sujeto."""

    def correr(self, manifiesto, *, timeout_s):
        estado = super().correr(manifiesto, timeout_s=timeout_s)
        (self.ent.control_runs / estado["control_run_id"] / "alerts.jsonl").write_text(
            json.dumps({"condition_id": "CR-01", "subject_key": "CR-01:oak:subject_001"}) + "\n")
        return estado


def test_rodaje_importa_las_sesiones_y_las_compara_con_su_guion(tmp_path, monkeypatch):
    monkeypatch.setenv("EOVRT_EVIDENCIA_SALIDA", str(tmp_path / "salida"))
    ent = _entorno(tmp_path)
    ent.media_runs.mkdir(parents=True)
    ent.control_runs.mkdir(parents=True)
    ent.patrones.mkdir(parents=True)
    shutil.copy(REPO.parent / "e-ovrt_control-plane/configs/patterns/cr01_cr02_v2_subject.yaml", ent.patrones)
    sesiones = tmp_path / "sesiones"
    shutil.copy(REPO / "experiments/evidencia/RT-04/escenas.json", tmp_path / "escenas.json")
    ruta = _prueba(tmp_path / "cat", "RT-04", familia="rodaje", receta={
        "escenas": str(tmp_path / "escenas.json"), "sesiones": str(sesiones),
        "sujeto": {"patrones": "cr01_cr02_v2_subject", "activos": ["CR-01", "CR-02"], "track_persons": True},
        "ensayo_demo": {"escena": "DEMO", "cr01_max_s_desde_la_accion": 6.0, "resultado_max_s": 60.0}})
    alerta = {"alert_id": "al-1", "condition_id": "CR-01", "subject_key": "CR-01:oak",
              "first_evidence_unit_id": "u10", "unit_id": "u30"}
    # P1: el actor se saca el casco en t=1.001.500 (host = contenedor) y la alerta confirma después.
    _sesion(ent, sesiones, "demo_a_P1", "P1", alertas=[alerta],
            eventos=[{"condition_id": "CR-01", "state": "resolved", "unit_id": "u38"}],
            marcas={"desfase_contenedor_menos_host_ms": 0.0, "acciones": [
                {"accion": "sacar_casco", "condicion": "CR-01", "pared_ms": 1_001_500},
                {"accion": "poner_casco", "condicion": "CR-01", "pared_ms": 1_007_000}]},
            testigo=[{"recibido_ms": 1_006_520.0, "payload": {"alert_id": "al-1", "condition_id": "CR-01",
                                                              "confirmed_wall_ms": 1_006_500.0}}])
    # P3: no debía alertar y alertó.
    _sesion(ent, sesiones, "demo_b_P3", "P3", alertas=[{**alerta, "alert_id": "al-2"}], eventos=[],
            marcas=None, testigo=[])
    # Una sesión de la demo sin escena no es del rodaje; una fallida queda como no evaluable.
    _sesion(ent, sesiones, "demo_c", "NINGUNA", alertas=[], eventos=[], marcas=None, testigo=[])
    _sesion(ent, sesiones, "demo_d_P2", "P2", alertas=[], eventos=[], marcas=None, testigo=[], fase="failed")

    prueba = cat.cargar_prueba(ruta)
    consola = ConsolaSujeto(ent)
    ctx = Contexto(ent=ent, consola=consola, catalogo={"RT-04": prueba}, avisar=lambda *_: None)
    carpeta = Carpeta(ent, prueba)
    carpeta.preparar()
    salida = rodaje.correr(ctx, prueba, carpeta)
    assert salida == {"estado": "completo", "tomas": 2, "como_se_esperaba": 1}

    tomas = {t["session_id"]: t for t in carpeta.leer("evals/tomas.json")}
    p1 = tomas["demo_a_P1"]
    assert p1["como_se_esperaba"] is True
    (a,) = p1["alertas"]
    assert a["accion_a_confirmacion_ms"] == 5000.0          # 1.006.500 − 1.001.500
    assert a["accion_a_primera_evidencia_ms"] == 500.0       # u10 = 1.002.000
    assert a["confirmacion_a_broker_ms"] == 20.0
    assert a["primera_evidencia_a_confirmacion_ms"] == 4500.0
    assert a["resuelta"] is True and a["accion_fin_a_resolucion_ms"] == 600.0  # u38 = 1.007.600
    assert p1["sujeto"]["como_se_esperaba"] is True and p1["sujeto"]["sujetos_con_alerta"] == 1
    assert tomas["demo_b_P3"]["como_se_esperaba"] is False
    # La relectura por sujeto pasó por el runner de la consola, reusando la corrida de medios.
    m = consola.manifiestos[0]
    assert m["runs"]["media"]["reuse_run_id"] == "run_demo_a_P1" and m["runs"]["control"]["mode"] == "replay"
    resultado = carpeta.leer("resultado.json")
    assert resultado["metricas"]["por_escena"]["P1"] == {"tomas": 1, "como_se_esperaba": 1, "sujeto_como_se_esperaba": 1}
    assert [n["session_id"] for n in resultado["metricas"]["no_evaluables"]] == ["demo_d_P2"]
    assert resultado["metricas"]["latencia_por_cuadro"]["vidrio_a_resultado"]["p95"] == 220.0


def test_rt05_agrupa_la_exploracion_por_celda_y_rt04_no_la_cuenta(tmp_path, monkeypatch):
    """RT-05: las sesiones de exploración (otro motor u otra cámara, la misma escena DEMO) se
    agrupan por motor × cámara; RT-04 no las cuenta y RT-05 no cuenta la demo congelada."""
    monkeypatch.setenv("EOVRT_EVIDENCIA_SALIDA", str(tmp_path / "salida"))
    ent = _entorno(tmp_path)
    for d in (ent.media_runs, ent.control_runs, ent.patrones):
        d.mkdir(parents=True)
    shutil.copy(REPO.parent / "e-ovrt_control-plane/configs/patterns/cr01_cr02_v2_subject.yaml", ent.patrones)
    sesiones = tmp_path / "sesiones"
    shutil.copy(REPO / "experiments/evidencia/RT-04/escenas.json", tmp_path / "escenas.json")
    marcas = {"desfase_contenedor_menos_host_ms": 0.0, "acciones": [
        {"accion": "sacar_casco", "condicion": "CR-01", "pared_ms": 1_001_500},
        {"accion": "poner_casco", "condicion": "CR-01", "pared_ms": 1_007_000}]}
    cr01 = {"alert_id": "al-1", "condition_id": "CR-01", "subject_key": "CR-01:oak",
            "first_evidence_unit_id": "u10", "unit_id": "u30"}
    testigo = [{"recibido_ms": 1_006_520.0, "payload": {"alert_id": "al-1", "condition_id": "CR-01",
                                                        "confirmed_wall_ms": 1_006_500.0}}]
    yoloe = {"motor": "mp-yoloe-26s", "camara": "960x540@15", "modelo": "yoloe/yoloe-26s"}
    _sesion(ent, sesiones, "demo_e_DEMO_exp", "DEMO", alertas=[cr01], eventos=[], marcas=marcas,
            testigo=testigo, exploracion=yoloe)
    # Una alerta CR-02 que llega antes de que el guion saque el chaleco: alerta antes de la acción.
    _sesion(ent, sesiones, "demo_f_DEMO_exp", "DEMO",
            alertas=[{**cr01, "alert_id": "al-2", "condition_id": "CR-02"}], eventos=[], marcas=marcas,
            testigo=[], exploracion={"motor": "mp-gdino-tiny-560", "camara": "960x540@5",
                                     "modelo": "grounding-dino/gdino-tiny-560"})
    _sesion(ent, sesiones, "demo_g_DEMO", "DEMO", alertas=[cr01], eventos=[], marcas=marcas, testigo=testigo)

    ruta = _prueba(tmp_path / "cat", "RT-05", familia="rodaje", receta={
        "escenas": str(tmp_path / "escenas.json"), "escena": "DEMO", "sesiones": str(sesiones),
        "matriz": {"motores": ["mp-gdino-tiny-560", "mp-yoloe-26s"], "camaras": ["960x540@5", "960x540@15"],
                   "tomas_por_celda": 1}})
    prueba = cat.cargar_prueba(ruta)
    ctx = Contexto(ent=ent, consola=ConsolaSujeto(ent), catalogo={"RT-05": prueba}, avisar=lambda *_: None)
    carpeta = Carpeta(ent, prueba)
    carpeta.preparar()
    assert rodaje.correr(ctx, prueba, carpeta) == {"estado": "parcial", "tomas": 2, "celdas_completas": 2}
    celdas = carpeta.leer("resultado.json")["metricas"]["celdas"]
    assert set(celdas) == {f"{m} @ {c}" for m in ("mp-gdino-tiny-560", "mp-yoloe-26s")
                           for c in ("960x540@5", "960x540@15")}
    y = celdas["mp-yoloe-26s @ 960x540@15"]
    assert (y["tomas"], y["cr01_confirmo"], y["cr02_confirmo"], y["faltan"]) == (1, 1, 0, 0)
    assert y["accion_a_confirmacion_mediana_ms"]["CR-01"] == 5000.0 and y["modelo"] == "yoloe/yoloe-26s"
    g = celdas["mp-gdino-tiny-560 @ 960x540@5"]
    assert g["alertas_antes_de_la_accion"] == 1 and g["cr02_confirmo"] == 1
    assert celdas["mp-yoloe-26s @ 960x540@5"]["faltan"] == 1
    assert len(carpeta.leer("resultado.json")["resumen"]) == 2

    # RT-04, sobre las mismas sesiones, solo ve la de la demo congelada.
    ruta4 = _prueba(tmp_path / "cat", "RT-04", familia="rodaje", receta={
        "escenas": str(tmp_path / "escenas.json"), "sesiones": str(sesiones),
        "sujeto": {"patrones": "cr01_cr02_v2_subject", "activos": ["CR-01", "CR-02"], "track_persons": True},
        "ensayo_demo": {"escena": "DEMO", "cr01_max_s_desde_la_accion": 6.0, "resultado_max_s": 60.0}})
    prueba4 = cat.cargar_prueba(ruta4)
    ctx4 = Contexto(ent=ent, consola=ConsolaSujeto(ent), catalogo={"RT-04": prueba4}, avisar=lambda *_: None)
    carpeta4 = Carpeta(ent, prueba4)
    carpeta4.preparar()
    rodaje.correr(ctx4, prueba4, carpeta4)
    assert [t["session_id"] for t in carpeta4.leer("evals/tomas.json")] == ["demo_g_DEMO"]


def test_ensayo_de_la_demo_aprobado_y_reprobado():
    toma = {"alertas": [{"condicion": "CR-01", "accion_a_confirmacion_ms": 5200.0, "broker_ms": 1.0,
                         "resuelta": True}],
            "por_condicion": {"CR-02": {"ok": False}}, "bus_dropped_events": 0, "resultado_listo_s": 12.0}
    criterio = {"cr01_max_s_desde_la_accion": 6.0, "resultado_max_s": 60.0}
    assert rodaje.ensayo_demo(toma, criterio) == {"aprobado": True, "motivos": [], "cr02_en_vivo": False}
    lenta = {**toma, "alertas": [{**toma["alertas"][0], "accion_a_confirmacion_ms": 7400.0}]}
    assert rodaje.ensayo_demo(lenta, criterio)["motivos"] == ["CR-01 confirmó a 7.4 s de la acción"]
