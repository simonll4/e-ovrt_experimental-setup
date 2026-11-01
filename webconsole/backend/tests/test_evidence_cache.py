"""La clasificación de ejecuciones no relee lo que no cambió (era ~50 s por pedido)."""
import json
import os

from eovrt_webconsole import evidence
from eovrt_webconsole.evidence import corridas_consolidadas


def _ejecucion(tmp_path):
    d = tmp_path / "exp"
    (d / "media").mkdir(parents=True)
    (d / "media" / "detections.jsonl").write_text(
        "\n".join(json.dumps({"run_id": "r1", "det": [{"x": i}]}) for i in range(3)) + "\n"
    )
    (d / "report.json").write_text(json.dumps({"identificacion": {"control_run_id": "c1"}}))
    return d


def _contar_lecturas(monkeypatch):
    abiertas = []
    original = evidence.Path.open
    original_read = evidence.Path.read_text

    def abrir(self, *a, **k):
        abiertas.append(self.name)
        return original(self, *a, **k)

    def leer(self, *a, **k):
        abiertas.append(self.name)
        return original_read(self, *a, **k)

    monkeypatch.setattr(evidence.Path, "open", abrir)
    monkeypatch.setattr(evidence.Path, "read_text", leer)
    return abiertas


def test_segunda_llamada_no_relee_los_archivos(tmp_path, monkeypatch):
    d = _ejecucion(tmp_path)
    assert corridas_consolidadas(d) == ["c1", "r1"]
    lecturas = _contar_lecturas(monkeypatch)
    assert corridas_consolidadas(d) == ["c1", "r1"]
    assert lecturas == []


def test_un_archivo_modificado_se_vuelve_a_leer(tmp_path, monkeypatch):
    d = _ejecucion(tmp_path)
    assert corridas_consolidadas(d) == ["c1", "r1"]
    reporte = d / "report.json"
    reporte.write_text(json.dumps({"identificacion": {"control_run_id": "c2", "media_run_id": "r9"}}))
    st = reporte.stat()
    os.utime(reporte, ns=(st.st_atime_ns, st.st_mtime_ns + 5_000_000_000))
    lecturas = _contar_lecturas(monkeypatch)
    assert corridas_consolidadas(d) == ["c2", "r1", "r9"]
    assert set(lecturas) == {"report.json"}


def test_un_archivo_nuevo_o_borrado_se_refleja(tmp_path):
    d = _ejecucion(tmp_path)
    assert corridas_consolidadas(d) == ["c1", "r1"]
    (d / "extra.json").write_text(json.dumps({"run_id": "r7"}))
    assert corridas_consolidadas(d) == ["c1", "r1", "r7"]
    (d / "extra.json").unlink()
    assert corridas_consolidadas(d) == ["c1", "r1"]


def test_un_archivo_ilegible_no_se_cachea_como_vacio(tmp_path):
    d = _ejecucion(tmp_path)
    roto = d / "roto.json"
    roto.write_text('{"run_id": "r5"')  # JSON truncado, p. ej. escribiéndose en este momento
    assert corridas_consolidadas(d) == ["c1", "r1"]
    roto.write_text('{"run_id": "r5"}')
    st = roto.stat()
    os.utime(roto, ns=(st.st_atime_ns, st.st_mtime_ns + 5_000_000_000))
    assert corridas_consolidadas(d) == ["c1", "r1", "r5"]


def test_un_symlink_que_apunta_afuera_no_se_sigue(tmp_path):
    d = _ejecucion(tmp_path)
    afuera = tmp_path / "afuera"
    afuera.mkdir()
    (afuera / "secreto.json").write_text(json.dumps({"run_id": "r_ajeno"}))
    (d / "enlace.json").symlink_to(afuera / "secreto.json")
    (d / "carpeta").symlink_to(afuera, target_is_directory=True)
    assert corridas_consolidadas(d) == ["c1", "r1"]


def test_yaml_de_manifiesto_se_reparsea_solo_si_cambia(tmp_path):
    from eovrt_webconsole.evidence import cargar_yaml_archivo

    m = tmp_path / "manifest.effective.yaml"
    m.write_text("slug: uno\n")
    assert cargar_yaml_archivo(m) == {"slug": "uno"}
    m.write_text("slug: dos\n")
    st = m.stat()
    os.utime(m, ns=(st.st_atime_ns, st.st_mtime_ns + 5_000_000_000))
    assert cargar_yaml_archivo(m) == {"slug": "dos"}


async def test_pedidos_concurrentes_comparten_un_solo_calculo(tmp_path):
    import asyncio

    from eovrt_webconsole.evidence import ClasificacionCompartida

    llamadas = []

    def calculo(runs_dir):
        llamadas.append(runs_dir)
        return ("por_slug", ["ejecucion"])

    compartida = ClasificacionCompartida(calculo, ttl_s=0.0)
    # Sin TTL cada pedido secuencial recalcula, pero los CONCURRENTES comparten el vuelo.
    resultados = await asyncio.gather(*(compartida.obtener(tmp_path) for _ in range(5)))
    assert len(llamadas) == 1
    assert all(r == ("por_slug", ["ejecucion"]) for r in resultados)
    await compartida.obtener(tmp_path)
    assert len(llamadas) == 2


async def test_el_ttl_evita_recalcular_y_vencido_recalcula(tmp_path):
    from eovrt_webconsole.evidence import ClasificacionCompartida

    llamadas = []
    reloj = [100.0]
    compartida = ClasificacionCompartida(
        lambda d: llamadas.append(d) or "r", ttl_s=2.0, reloj=lambda: reloj[0]
    )
    await compartida.obtener(tmp_path)
    reloj[0] += 1.0
    await compartida.obtener(tmp_path)
    assert len(llamadas) == 1
    reloj[0] += 1.5
    await compartida.obtener(tmp_path)
    assert len(llamadas) == 2


async def test_un_error_no_se_cachea(tmp_path):
    import pytest

    from eovrt_webconsole.evidence import ClasificacionCompartida

    intentos = []

    def calculo(runs_dir):
        intentos.append(1)
        if len(intentos) == 1:
            raise OSError("disco ocupado")
        return "ok"

    compartida = ClasificacionCompartida(calculo, ttl_s=60.0)
    with pytest.raises(OSError):
        await compartida.obtener(tmp_path)
    assert await compartida.obtener(tmp_path) == "ok"
