# Inventario y archivo de runs de evidencia — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir y verificar el inventario exhaustivo de runs que sostienen los resultados DBE y EBE, junto con una copia versionable de sus artefactos textuales sin imágenes, video ni secretos.

**Architecture:** Un manifiesto YAML humano declara las fuentes, colecciones, selectores y excepciones; un paquete Python resuelve el catálogo completo, localiza media/control runs, crea una copia textual determinista y genera un lock JSON, CSV, Markdown y hashes. El mismo pipeline se ejecuta en modo `sync`, `--check` contra originales o `--check --archive-only` sobre un clon que solo conserva el archivo versionado.

**Tech Stack:** Python 3.11+, biblioteca estándar (`argparse`, `csv`, `dataclasses`, `gzip`, `hashlib`, `json`, `mimetypes`, `pathlib`, `tempfile`), PyYAML 6, Pytest 9, Markdown/CSV/JSON/YAML.

## Global Constraints

- Trabajar únicamente en `e-ovrt_experimental-setup`; los repos hermanos son fuentes de solo lectura.
- No crear commits: la indicación del usuario prevalece sobre los pasos de commit habituales del skill.
- No borrar ni alterar ningún run original ni ningún cambio local previo.
- El catálogo cubre exactamente `bench_imagenes`, `bench_nivel_a`, `clip_bench` y `realtime`, incluidos contrastes y resultados negativos citados.
- Toda campaña bajo `results/clip_bench/*` o `results/bench_nivel_a/*` con `metrics.json` debe quedar declarada; la línea de base actual es 16/16.
- La línea de base de campañas resuelve 273 media runs únicos y 434 control runs temporales; 400 controles conservan directorio y 34 controles de T1 son `archived_only`.
- La medición EBE de decimado empírico agrega 544 control runs desde 16 directorios `101-rt-*`; no se confunden con los controles de campaña.
- Cada run se copia una sola vez; las relaciones muchos-a-muchos viven en el lock y los CSV.
- No copiar imágenes, videos, previews, frames, presets de cámara, credenciales, payload binario ni imagen base64.
- Admitir por defecto solo `.json`, `.jsonl`, `.csv`, `.yaml`, `.yml`, `.txt`, `.log` y `.md`.
- Comprimir todo `.jsonl` como `.jsonl.gz` con `compresslevel=9`, `mtime=0` y nombre vacío en el header.
- El límite es 95 MiB por archivo en la representación versionada.
- Las rutas persistidas deben ser relativas a los repos hermanos; no codificar `/home/simonll4/projects`.
- `sync` debe construir en temporal y publicar solo tras validar todo; `--check` no escribe.
- Ningún scanner puede imprimir valores sensibles.

---

## File map

- Create `tools/evidence_archive/model.py`: dataclasses, errores de dominio y tipos compartidos.
- Create `tools/evidence_archive/manifest.py`: carga/validación YAML, selectores y descubrimiento exacto de campañas.
- Create `tools/evidence_archive/catalog.py`: resolución de media/control/archived-only, relaciones, rutas portables y conflictos.
- Create `tools/evidence_archive/archive.py`: política de archivos, redacción, scanner, gzip y copia determinista.
- Create `tools/evidence_archive/render.py`: lock JSON, CSV, Markdown, manifiesto de archivos y hashes.
- Create `tools/evidence_archive/workflow.py`: `sync`, checks completo/offline y publicación transaccional.
- Create `tools/evidence_archive/__init__.py`: API pública mínima del paquete.
- Create `tools/evidence_runs.py`: CLI delgada.
- Create `tests/test_evidence_manifest.py`: selectores, campañas y validación del YAML.
- Create `tests/test_evidence_catalog.py`: resolución, controles temporales, faltantes, duplicados y pares EBE.
- Create `tests/test_evidence_archive.py`: exclusiones, redacción, detección de secretos y gzip.
- Create `tests/test_evidence_render.py`: salidas deterministas y relaciones sin duplicación.
- Create `tests/test_evidence_workflow.py`: `sync`, `--check`, `--archive-only` y publicación atómica.
- Create `results/evidence-runs.yaml`: fuente de verdad revisable.
- Generate `results/evidence-runs.md`: índice humano exhaustivo.
- Generate `results/evidence-runs/**`: copias curadas, colecciones, lock y hashes.
- Modify `results/index.md`: enlazar el inventario canónico.
- Modify `results/clip_bench/README.md`: sustituir la afirmación de que las detecciones nunca se copian por la política del archivo curado.
- Modify `README.md`: documentar la excepción deliberada de `results/evidence-runs/`.

---

### Task 1: Modelo de dominio, selectores y campañas exactas

**Files:**
- Create: `tools/evidence_archive/__init__.py`
- Create: `tools/evidence_archive/model.py`
- Create: `tools/evidence_archive/manifest.py`
- Test: `tests/test_evidence_manifest.py`

**Interfaces:**
- Produces: `RunKey`, `Relation`, `RunRequest`, `ResolvedRun`, `Manifest`, `CheckReport`, `EvidenceError`.
- Produces: `load_manifest(path: Path) -> Manifest`.
- Produces: `extract_values(data: object, selector: str) -> list[str]`, con tokens separados por `.` y `*` como wildcard de listas u objetos.
- Produces: `discover_campaigns(repo_root: Path) -> dict[str, Path]`.
- Produces: `campaign_requests(manifest: Manifest, repo_root: Path) -> list[RunRequest]`.

- [ ] **Step 1: Escribir pruebas fallidas para selectors y contratos de campaña**

```python
def test_extract_values_walks_lists_and_object_values():
    data = {
        "rows": [{"run_id": "run_a"}, {"run_id": "run_b"}],
        "nested": {"left": {"run_id": "run_c"}},
    }
    assert extract_values(data, "rows.*.run_id") == ["run_a", "run_b"]
    assert extract_values(data, "nested.*.run_id") == ["run_c"]


def test_discover_campaigns_requires_metrics_and_provenance(tmp_path):
    campaign = tmp_path / "results/clip_bench/t1"
    campaign.mkdir(parents=True)
    (campaign / "metrics.json").write_text("{}")
    with pytest.raises(EvidenceError, match="provenance"):
        discover_campaigns(tmp_path)


def test_campaign_requests_extracts_media_and_control_runs(tmp_path):
    # El fixture contiene media_run_id en provenance y alerts_path en evals.
    requests = campaign_requests(manifest_fixture(tmp_path), tmp_path)
    assert RunKey("media-plane", "run_media") in {item.key for item in requests}
    assert RunKey("control-plane", "control_eval_20260803T000000Z") in {
        item.key for item in requests
    }
```

- [ ] **Step 2: Ejecutar las pruebas y confirmar el rojo**

Run: `python3 -m pytest tests/test_evidence_manifest.py -q`

Expected: FAIL por importación inexistente de `tools.evidence_archive`.

- [ ] **Step 3: Implementar tipos inmutables y errores con mensajes sin datos sensibles**

```python
@dataclass(frozen=True, order=True)
class RunKey:
    plane: Literal["media-plane", "control-plane"]
    run_id: str


@dataclass(frozen=True, order=True)
class Relation:
    collection: Literal["dbe_datasets", "dbe_video", "ebe_realtime", "shared"]
    result_id: str
    role: str
    source_ref: str


@dataclass(frozen=True)
class RunRequest:
    key: RunKey
    relations: tuple[Relation, ...]
    archived_substitute: str | None = None
```

- [ ] **Step 4: Implementar selector estricto y carga YAML validada**

`extract_values` debe fallar si un token no existe, si el valor final no es string, si un ID está vacío o si el selector devuelve cero elementos. `load_manifest` debe exigir `schema_version: evidence_runs.v1`, las cuatro colecciones, raíces permitidas y IDs únicos de fuentes/grupos.

- [ ] **Step 5: Implementar descubrimiento exacto de las 16 campañas**

`discover_campaigns` debe recorrer solo un nivel bajo `results/clip_bench/` y `results/bench_nivel_a/`, seleccionar directorios con `metrics.json` y exigir `campaign.yaml` más al menos un `provenance*.json`. `campaign_requests` debe:

```python
MEDIA_FIELDS = {
    "media_run_id",
    "eind_run_id",
    "edir_run_id",
    "detections_from",
    "run_id",
}
```

Recorrer recursivamente los provenance para esos campos, y obtener el control ID como `Path(alerts_path).parent.name` de cada `evals/eval_*.json` de `clip_bench`. Nivel A no produce control requests.

- [ ] **Step 6: Ejecutar pruebas y verificar verde**

Run: `python3 -m pytest tests/test_evidence_manifest.py -q`

Expected: PASS.

- [ ] **Step 7: Checkpoint sin commit**

Run: `git diff --check -- tools/evidence_archive tests/test_evidence_manifest.py`

Expected: salida vacía.

---

### Task 2: Catálogo, rutas de runs y estados de disponibilidad

**Files:**
- Create: `tools/evidence_archive/catalog.py`
- Test: `tests/test_evidence_catalog.py`
- Modify: `tools/evidence_archive/model.py`

**Interfaces:**
- Consumes: `Manifest`, `RunRequest`, `RunKey`, `Relation`.
- Produces: `merge_requests(requests: Iterable[RunRequest]) -> dict[RunKey, RunRequest]`.
- Produces: `portable_docs_path(raw_path: str, workspace_root: Path) -> Path | None`.
- Produces: `resolve_catalog(manifest: Manifest, requests: Iterable[RunRequest], workspace_root: Path) -> list[ResolvedRun]`.
- `ResolvedRun.status` es uno de `copied`, `archived_only`, `missing`, `conflict`.

- [ ] **Step 1: Escribir pruebas fallidas para deduplicación, paths y conflictos**

```python
def test_merge_requests_keeps_one_run_and_all_relations():
    merged = merge_requests([request("run_x", "dbe_video"), request("run_x", "ebe_realtime")])
    assert len(merged) == 1
    assert {r.collection for r in merged[RunKey("media-plane", "run_x")].relations} == {
        "dbe_video", "ebe_realtime"
    }


def test_portable_docs_path_reanchors_old_absolute_path(tmp_path):
    actual = portable_docs_path(
        "/old/machine/projects/docs/operacion/datos/x/control_runs/control_a/alerts.jsonl",
        tmp_path,
    )
    assert actual == tmp_path / "docs/operacion/datos/x/control_runs/control_a"


def test_non_identical_duplicate_is_conflict(tmp_path):
    make_run(tmp_path / "root_a/run_x", summary="a")
    make_run(tmp_path / "root_b/run_x", summary="b")
    result = resolve_one(tmp_path, ["root_a", "root_b"], "run_x")
    assert result.status == "conflict"
```

- [ ] **Step 2: Ejecutar pruebas y confirmar el rojo**

Run: `python3 -m pytest tests/test_evidence_catalog.py -q`

Expected: FAIL por `catalog.py` inexistente.

- [ ] **Step 3: Implementar merge muchos-a-muchos y validación de pares EBE**

Un grupo con `requires_pair: true` debe tener exactamente un media ID y un control ID por `pair_id`; cualquier miembro ausente deja el par en error. La deduplicación ordena relaciones y nunca copia dos veces un `RunKey`.

- [ ] **Step 4: Implementar resolución por raíces explícitas**

Para media/control principales, resolver `root / run_id`. Para controles de campañas, normalizar únicamente el sufijo posterior a `/docs/` de `alerts_path`; rechazar rutas que salgan del repo hermano `docs`. Comparar duplicados mediante un árbol de `(relative_path, sha256)` de los archivos fuente admitidos, no mediante mtime.

- [ ] **Step 5: Implementar `archived_only` sin degradación automática**

El manifiesto debe permitir:

```yaml
archived_only:
  - id: t1_control_runs
    request_source: campaign:t1_gdinotiny560_v2short_scene
    substitute_from: matching_eval
    reason: Los control runs originales vivían en un scratchpad ya ausente.
```

Solo los 34 controles resueltos desde los evals de T1 pueden usar esa regla de campaña. Los seis
runs históricos del doc 31 se asocian por `relation_result_id` a su JSON crudo; las entradas de
docs 37/39 declaran sus IDs y sustitutos nominales. Todo otro run ausente queda `missing` y aborta
`sync`/check completo.

- [ ] **Step 6: Ejecutar pruebas y verificar verde**

Run: `python3 -m pytest tests/test_evidence_catalog.py -q`

Expected: PASS.

- [ ] **Step 7: Checkpoint sin commit**

Run: `git diff --check -- tools/evidence_archive tests/test_evidence_catalog.py`

Expected: salida vacía.

---

### Task 3: Archivo seguro, redacción y compresión determinista

**Files:**
- Create: `tools/evidence_archive/archive.py`
- Test: `tests/test_evidence_archive.py`

**Interfaces:**
- Produces: `ArchivePolicy.from_manifest(data: Mapping[str, object]) -> ArchivePolicy`.
- Produces: `inspect_source_file(path: Path, relative_path: Path, policy: ArchivePolicy) -> FileDecision`.
- Produces: `redact_effective_config(data: bytes) -> tuple[bytes, bool]`.
- Produces: `archive_run(run: ResolvedRun, destination: Path, policy: ArchivePolicy) -> list[ArchivedFile]`.
- Produces: `validate_archive_tree(root: Path, policy: ArchivePolicy) -> None`.

- [ ] **Step 1: Escribir pruebas fallidas de medios, secretos y gzip**

```python
@pytest.mark.parametrize("name", ["frame.jpg", "clip.mp4", "preview.webp"])
def test_media_is_rejected_even_when_nested(tmp_path, name):
    source = tmp_path / "previews" / name
    source.parent.mkdir()
    source.write_bytes(b"not relevant")
    assert inspect_source_file(source, Path("previews") / name, policy()).action == "exclude"


def test_effective_config_redacts_uri_userinfo_without_printing_it():
    raw = b"source:\n  url: rtsp://alice:very-secret@camera/live\nmodel:\n  ref: gdino\n"
    output, redacted = redact_effective_config(raw)
    assert redacted is True
    assert b"very-secret" not in output
    assert b"[REDACTED]" in output
    assert b"gdino" in output


def test_jsonl_gzip_is_reproducible(tmp_path):
    first = deterministic_gzip(b'{"x":1}\n')
    second = deterministic_gzip(b'{"x":1}\n')
    assert first == second
    assert gzip.decompress(first) == b'{"x":1}\n'
```

- [ ] **Step 2: Ejecutar pruebas y confirmar el rojo**

Run: `python3 -m pytest tests/test_evidence_archive.py -q`

Expected: FAIL por `archive.py` inexistente.

- [ ] **Step 3: Implementar política cerrada de tipos**

Excluir componentes de ruta declarados (`previews`, `frames`, `images`, `annotated`, `videos`, `cameras`, `camera_presets`) y todas las extensiones de imagen/video del diseño. Rechazar extensiones desconocidas; no seguir symlinks. Verificar magic bytes de JPEG, PNG, GIF, WebP, TIFF, BMP, MP4/QuickTime, Matroska/WebM y AVI aunque la extensión parezca textual.

- [ ] **Step 4: Implementar scanner de texto y redacción estructural**

Para YAML/JSON, tratar como sensibles claves case-insensitive que coincidan con `password`, `passwd`, `token`, `secret`, `api_key`, `private_key`, `credential` o `auth`. Para todo texto, rechazar encabezados PEM de clave privada, URI con userinfo y payloads `data:image` codificados en base64. Solo `effective_config.y*ml` puede redactarse; cualquier secreto en otro archivo aborta. El error debe incluir únicamente run ID y ruta relativa.

- [ ] **Step 5: Implementar copia y manifiesto por archivo**

Todos los JSONL se escriben como gzip usando:

```python
buffer = io.BytesIO()
with gzip.GzipFile(filename="", mode="wb", fileobj=buffer, compresslevel=9, mtime=0) as gz:
    gz.write(source_bytes)
```

Los demás archivos admitidos se copian byte a byte, salvo `effective_config.redacted.yaml`. Cada `ArchivedFile` registra hash/tamaño fuente y archivado, compresión, redacción y ruta relativa portable. Fallar si el resultado supera `95 * 1024 * 1024` bytes.

- [ ] **Step 6: Implementar guard del árbol final y `.gitignore` defensivo**

`validate_archive_tree` debe inspeccionar también archivos ignorados y descomprimir `.jsonl.gz` para escanear su contenido. El `.gitignore` generado debe bloquear extensiones de medio y los directorios prohibidos en cualquier profundidad.

- [ ] **Step 7: Ejecutar pruebas y verificar verde**

Run: `python3 -m pytest tests/test_evidence_archive.py -q`

Expected: PASS.

- [ ] **Step 8: Checkpoint sin commit**

Run: `git diff --check -- tools/evidence_archive tests/test_evidence_archive.py`

Expected: salida vacía.

---

### Task 4: Lock, CSV, Markdown e integridad deterministas

**Files:**
- Create: `tools/evidence_archive/render.py`
- Test: `tests/test_evidence_render.py`

**Interfaces:**
- Produces: `render_resolved_runs(runs: Sequence[ResolvedRun], workspace_root: Path) -> bytes`.
- Produces: `render_collections(runs: Sequence[ResolvedRun]) -> dict[str, bytes]`.
- Produces: `render_inventory_markdown(generated_date: str, runs: Sequence[ResolvedRun], files: Sequence[ArchivedFile]) -> bytes`.
- Produces: `render_archive_readme(generated_date: str, runs: Sequence[ResolvedRun]) -> bytes`.
- Produces: `render_archive_files(files: Sequence[ArchivedFile], workspace_root: Path) -> bytes`.
- Produces: `render_checksums(root: Path) -> bytes`.

- [ ] **Step 1: Escribir pruebas fallidas para orden, shared y hashes**

```python
def test_render_is_byte_identical_under_input_permutation(sample_runs, workspace_root):
    assert render_resolved_runs(sample_runs, workspace_root) == render_resolved_runs(
        list(reversed(sample_runs)), workspace_root
    )


def test_shared_relation_does_not_duplicate_artifact(sample_runs):
    csvs = render_collections(sample_runs)
    assert b"run_shared" in csvs["dbe-video.csv"]
    assert b"run_shared" in csvs["ebe-realtime.csv"]
    assert sum(run.key.run_id == "run_shared" for run in sample_runs) == 1


def test_checksums_excludes_itself(tmp_path):
    (tmp_path / "a.txt").write_text("a")
    (tmp_path / "files.sha256").write_text("stale")
    output = render_checksums(tmp_path)
    assert b"a.txt" in output
    assert b"files.sha256" not in output
```

- [ ] **Step 2: Ejecutar pruebas y confirmar el rojo**

Run: `python3 -m pytest tests/test_evidence_render.py -q`

Expected: FAIL por `render.py` inexistente.

- [ ] **Step 3: Implementar lock y CSV canónicos**

`resolved-runs.json` usa JSON indentado, claves ordenadas, newline final y un registro por `RunKey`. Cada CSV usa columnas fijas:

```text
collection,result_id,role,plane,run_id,status,source_ref,artifact_path
```

`shared.csv` contiene únicamente runs con relaciones en más de una colección, sin quitar sus filas de las colecciones originales.

- [ ] **Step 4: Implementar inventario Markdown navegable**

El documento debe incluir: fecha de generación lógica tomada del manifiesto, conteos únicos por plano/estado/colección, resumen por resultado, las 16 campañas, grupos estructurados/manuales, 44 casos `archived_only`, conflictos/faltantes (cero al cerrar), política de exclusión y comandos de sync/check. Cada ID `copied` enlaza a `evidence-runs/artifacts/{plane}/{run_id}/`; cada sustituto enlaza a `artifacts/archived-only/{plane}--{run_id}/`.

- [ ] **Step 5: Implementar `archive-files.json` y `files.sha256`**

Ordenar por ruta archivada. `files.sha256` cubre todos los archivos bajo `results/evidence-runs/` salvo sí mismo, con formato `{sha256}  {ruta_posix}\n`.

- [ ] **Step 6: Ejecutar pruebas y verificar verde**

Run: `python3 -m pytest tests/test_evidence_render.py -q`

Expected: PASS.

- [ ] **Step 7: Checkpoint sin commit**

Run: `git diff --check -- tools/evidence_archive tests/test_evidence_render.py`

Expected: salida vacía.

---

### Task 5: Workflow transaccional y CLI

**Files:**
- Create: `tools/evidence_archive/workflow.py`
- Create: `tools/evidence_runs.py`
- Modify: `tools/evidence_archive/__init__.py`
- Test: `tests/test_evidence_workflow.py`

**Interfaces:**
- Produces: `sync(repo_root: Path, manifest_path: Path) -> CheckReport`.
- Produces: `check(repo_root: Path, manifest_path: Path, archive_only: bool = False) -> CheckReport`.
- CLI: `python3 tools/evidence_runs.py sync`.
- CLI: `python3 tools/evidence_runs.py --check [--archive-only]`.

- [ ] **Step 1: Escribir pruebas fallidas del ciclo completo**

```python
def test_sync_then_check_is_clean(workspace_fixture):
    sync(workspace_fixture.repo, workspace_fixture.manifest)
    report = check(workspace_fixture.repo, workspace_fixture.manifest)
    assert report.ok


def test_check_detects_extra_run_directory(workspace_fixture):
    sync(workspace_fixture.repo, workspace_fixture.manifest)
    extra = workspace_fixture.repo / "results/evidence-runs/artifacts/media-plane/run_extra"
    extra.mkdir(parents=True)
    assert not check(workspace_fixture.repo, workspace_fixture.manifest).ok


def test_archive_only_check_works_without_sibling_runs(workspace_fixture):
    sync(workspace_fixture.repo, workspace_fixture.manifest)
    workspace_fixture.remove_source_repos()
    assert check(workspace_fixture.repo, workspace_fixture.manifest, archive_only=True).ok
```

- [ ] **Step 2: Ejecutar pruebas y confirmar el rojo**

Run: `python3 -m pytest tests/test_evidence_workflow.py -q`

Expected: FAIL por `workflow.py` inexistente.

- [ ] **Step 3: Implementar build temporal y publicación segura**

Construir bajo un directorio creado por `tempfile.mkdtemp(prefix=".evidence-runs-build-", dir=repo_root / "results")`. Validar catálogo, medios, secretos, tamaño, documentación y hashes antes de publicar. Si ya existe destino, moverlo a un backup temporal dentro de `results/`, mover el build al destino y restaurar el backup ante excepción; eliminar el backup solo tras éxito. No tocar rutas fuera de `results/evidence-runs/` ni los dos archivos generados hermanos.

- [ ] **Step 4: Implementar comparación de `--check` sin escrituras**

El check completo reconstruye en un `TemporaryDirectory` fuera del repo y compara el árbol esperado con el real por ruta+hash, además de `results/evidence-runs.md`. Debe reportar listas de IDs/rutas faltantes, sobrantes o distintas. Confirmar en test que mtimes del repo no cambian.

- [ ] **Step 5: Implementar `--archive-only`**

Leer y validar `resolved-runs.json`, `archive-files.json`, CSV, Markdown, hashes, exclusiones y secretos sin abrir las raíces fuente. Imprimir una línea explícita indicando que no se comparó con originales.

- [ ] **Step 6: Implementar CLI y códigos de salida**

```text
0  verificación o sincronización correcta
1  catálogo/archivo desactualizado o inválido
2  uso inválido del CLI o manifiesto mal formado
```

El CLI captura `EvidenceError`, imprime solo mensajes sanitizados a stderr y nunca traceback por defecto.

- [ ] **Step 7: Ejecutar pruebas y verificar verde**

Run: `python3 -m pytest tests/test_evidence_workflow.py -q`

Expected: PASS.

- [ ] **Step 8: Ejecutar toda la suite nueva**

Run: `python3 -m pytest tests/test_evidence_*.py -q`

Expected: PASS.

- [ ] **Step 9: Checkpoint sin commit**

Run: `git diff --check -- tools tests`

Expected: salida vacía.

---

### Task 6: Manifiesto canónico y auditoría exacta de fuentes

**Files:**
- Create: `results/evidence-runs.yaml`
- Test: `tests/test_evidence_manifest.py`

**Interfaces:**
- Consumes: los schemas y selectores de Tasks 1–5.
- Produces: el conjunto canónico completo usado por `sync` y `--check`.

- [ ] **Step 1: Agregar prueba de integración del manifiesto real**

```python
def test_real_manifest_covers_every_current_campaign():
    repo = Path(__file__).resolve().parents[1]
    manifest = load_manifest(repo / "results/evidence-runs.yaml")
    discovered = set(discover_campaigns(repo))
    assert discovered == set(manifest.expected_campaigns)
    assert len(discovered) == 16


def test_real_campaign_baseline_has_every_media_and_control_run():
    repo = Path(__file__).resolve().parents[1]
    manifest = load_manifest(repo / "results/evidence-runs.yaml")
    requests = campaign_requests(manifest, repo)
    assert len({r.key for r in requests if r.key.plane == "media-plane"}) == 273
    assert len({r.key for r in requests if r.key.plane == "control-plane"}) == 434


def test_real_manifest_resolves_all_structured_and_manual_sources():
    repo = Path(__file__).resolve().parents[1]
    manifest = load_manifest(repo / "results/evidence-runs.yaml")
    structured = structured_requests(manifest, repo)
    assert len(structured) == 721
    assert len({r.key for r in structured if r.key.plane == "control-plane"}) == 544
```

- [ ] **Step 2: Ejecutar la prueba y confirmar el rojo**

Run: `python3 -m pytest tests/test_evidence_manifest.py::test_real_manifest_covers_every_current_campaign -q`

Expected: FAIL porque aún no existe `results/evidence-runs.yaml`.

- [ ] **Step 3: Declarar campañas y selectores estructurados con conteos auditables**

El YAML debe declarar:

```yaml
schema_version: evidence_runs.v1
generated_date: 2026-08-13
expected_campaigns:
  - clip_bench/b1_gdinobase560_barehead_scene
  - clip_bench/d1_gdinotiny560_edirpair_scene
  - clip_bench/g1_gdinotiny560_v2short_subject
  - clip_bench/h1_gdinotiny560_hybor_scene
  - clip_bench/i1_gdinotiny560_v2short_scene_internet
  - clip_bench/i2_gdinotiny560_v2short_subject_internet
  - clip_bench/r1_gdinotiny560_v2short_scene_s7
  - clip_bench/r2_gdinotiny560_v2short_subject_s7
  - clip_bench/r3_gdinotiny560_v2short_scene_s15
  - clip_bench/r4_gdinotiny560_v2short_subject_s15
  - clip_bench/r5_gdinotiny560_v2short_scene_s26
  - clip_bench/r6_gdinotiny560_v2short_subject_s26
  - clip_bench/t1_gdinotiny560_v2short_scene
  - clip_bench/t2_gdinobase560_v2short_scene
  - bench_nivel_a/d1_gdinotiny560_edir_vs_eind
  - bench_nivel_a/na1_gdinotiny560_v2short_video
structured_sources:
  - {id: bench31, path: ../docs/operacion/datos/31-benchmark-modelos-host-local.datos.json, selectors: ["*.bench.run_id"], expected_count: 6}
  - {id: s1, path: ../docs/operacion/datos/s1_matrix_results_2026-07-23.jsonl, selectors: ["*.run_id"], expected_count: 20}
  - {id: b5, path: ../docs/operacion/datos/b5_rescore_partial_2026-07-23.jsonl, selectors: ["*.run_id"], expected_count: 6}
  - {id: gdino560, path: ../docs/operacion/datos/bench_v2_gdino560_eval_2026-07-23.json, selectors: ["*.run_id"], expected_count: 2}
  - {id: nivel_a_tiny, path: ../docs/operacion/datos/83-fase-d-nivel-a/runs.json, selectors: ["*.run_id"], expected_count: 18}
  - {id: nivel_a_base, path: ../docs/operacion/datos/84-fase-d-nivel-a-base560/runs.json, selectors: ["*.run_id"], expected_count: 18}
  - {id: clase_nueva, path: ../docs/operacion/datos/94-piloto-clase-nueva/resultados.json, selectors: ["runs.clase_nueva_bench_obra_val.run_id", "runs.clase_nueva_bench_obra_test.run_id", "runs.clase_nueva_mocs_valid.run_id", "runs.vehiculo_aislado.*"], expected_count: 5}
  - {id: realtime_matrix, path: ../docs/operacion/datos/bench_realtime_person_2026-07-23.jsonl, selectors: ["*.run_id"], expected_count: 24}
  - {id: live_drop_distribution, path: ../docs/operacion/datos/101-descarte-live-distribucion.json, selectors: ["por_corrida.*.run_id"], expected_count: 76}
```

Los parsers JSONL presentan el archivo como lista antes de aplicar el selector. El source de
decimado (`kind: eval_control_runs`, `expected_count: 544`) enumera sus 16 directorios
`../docs/operacion/datos/101-rt-*` completos, sin glob. Cada fuente declara colección, resultado,
rol, documento y disposición.

- [ ] **Step 4: Declarar grupos manuales EBE con IDs completos**

Incluir sin abreviaturas:

```yaml
manual_groups:
  - id: doc65_l0
    pairs:
      - media_run_id: run_20260723_024636_dbe_grounding_dino_d4b938
        control_run_id: control_live_cr01_cr02_20260723T024608Z_7e0673
  - id: doc71_rodaje_final
    pairs:
      - {media_run_id: run_20260725_201020_dbe_grounding_dino_0ca90e, control_run_id: control_ebe_p1_live_20260725T201020Z_8dc1c2}
      - {media_run_id: run_20260725_201145_dbe_grounding_dino_0eb1fd, control_run_id: control_ebe_p2_live_20260725T201145Z_caacb3}
      - {media_run_id: run_20260725_201247_dbe_grounding_dino_12394a, control_run_id: control_ebe_p3_live_20260725T201247Z_c246e1}
      - {media_run_id: run_20260725_201820_dbe_yoloe_210d40, control_run_id: control_yoloe_p1_live_20260725T201820Z_2a56b5}
      - {media_run_id: run_20260725_201916_dbe_yoloe_73535e, control_run_id: control_yoloe_p2_live_20260725T201916Z_b5cc5b}
      - {media_run_id: run_20260725_202012_dbe_yoloe_e2bfe1, control_run_id: control_yoloe_p3_live_20260725T202012Z_fa1c9e}
  - id: doc91_regression_g1
    pairs:
      - {media_run_id: run_20260805_003533_dbe_grounding_dino_3246e1, control_run_id: smoke_ebe_a_20260805T003533Z_1593d8}
      - {media_run_id: run_20260805_003713_dbe_grounding_dino_70ace4, control_run_id: smoke_ebe_b_20260805T003713Z_ff0134}
  - id: doc101_claqueta
    pairs:
      - {media_run_id: run_20260805_171426_dbe_grounding_dino_0c2cbe, control_run_id: smoke_claqueta_20260805T171426Z_cada33}
      - {media_run_id: run_20260805_172632_dbe_grounding_dino_f4fc5f, control_run_id: smoke_claqueta_20260805T172632Z_fd7b16}
      - {media_run_id: run_20260805_173014_dbe_grounding_dino_376f78, control_run_id: smoke_claqueta_20260805T173014Z_843122}
      - {media_run_id: run_20260805_173354_dbe_grounding_dino_780a1c, control_run_id: smoke_claqueta_20260805T173350Z_b9c64e}
```

Las tres primeras claquetas son evidencia negativa de los guards; no se excluyen por haber fallado.

- [ ] **Step 5: Declarar los 23 bloques exactos F-RT5**

El grupo `doc73_frt5` debe listar los siete bloques de campaña 1, ocho de campaña 2 y cuatro de cada campaña 3/4:

```text
run_20260727_223425_dbe_grounding_dino_33563c
run_20260727_223648_dbe_grounding_dino_de5768
run_20260727_223921_dbe_grounding_dino_f8820f
run_20260727_224146_dbe_grounding_dino_ec021b
run_20260727_224425_dbe_grounding_dino_421cc5
run_20260727_224650_dbe_grounding_dino_0f76ca
run_20260727_224910_dbe_grounding_dino_b59fe1
run_20260728_001328_dbe_grounding_dino_ea3470
run_20260728_001544_dbe_grounding_dino_0e017f
run_20260728_001757_dbe_grounding_dino_e92a6a
run_20260728_002010_dbe_grounding_dino_e3d553
run_20260728_002223_dbe_grounding_dino_f27649
run_20260728_002440_dbe_grounding_dino_5eb4c0
run_20260728_002653_dbe_grounding_dino_966269
run_20260728_002906_dbe_grounding_dino_86c4e3
run_20260728_003207_dbe_grounding_dino_e60e13
run_20260728_003422_dbe_grounding_dino_d98693
run_20260728_003635_dbe_grounding_dino_0c7eb7
run_20260728_003848_dbe_grounding_dino_c5a2d9
run_20260728_004101_dbe_grounding_dino_a8dda4
run_20260728_004318_dbe_grounding_dino_4afc44
run_20260728_004538_dbe_grounding_dino_fa386c
run_20260728_004753_dbe_grounding_dino_5fd207
```

Excluir expresamente `run_20260727_222424_dbe_grounding_dino_599d5b` por ser la telemetría previa, y `run_20260727_225143_dbe_grounding_dino_258401` por ser el bloque parcial de 25 s; ninguno integra los 23 bloques/11 pares citados.

- [ ] **Step 6: Declarar archived-only de docs 31/37/39 y controles T1**

Doc 31 aporta seis runs cuyos directorios originales ya no existen y cuyo JSON crudo conserva
summary y evaluación completos. Doc 37 aporta `run_20260710_062654_dbe_mock_757a73`,
`e2e_live_control` y `e2e_replay_control`, con sustitutos exactos
`datos/37-2026-07-10-live-e2e-*`. Doc 39 aporta
`run_20260710_144331_dbe_mock_47e4b2`, sustituido por
`datos/39-2026-07-10-g2a-video-summary.json`. La regla T1 usa cada
`results/clip_bench/t1_gdinotiny560_v2short_scene/evals/eval_*.json` como sustituto del control ID
obtenido de su `alerts_path`.

- [ ] **Step 7: Declarar fuentes citadas sin runs adicionales**

Registrar docs 63, 64, 66, 74, 96 y los artefactos derivados de 101 como `duplicate_crosscheck` o `methodology_only`, con justificación concreta. Esto prueba que las secciones “Dónde está cada número” fueron auditadas sin convertir toda mención metodológica en un run extra.

- [ ] **Step 8: Ejecutar tests y resolución seca**

Run: `python3 -m pytest tests/test_evidence_manifest.py tests/test_evidence_catalog.py -q`

Expected: PASS y conteos esperados por fuente.

- [ ] **Step 9: Checkpoint sin commit**

Run: `git diff --check -- results/evidence-runs.yaml tests/test_evidence_manifest.py`

Expected: salida vacía.

---

### Task 7: Sincronizar el archivo y documentar su uso

**Files:**
- Generate: `results/evidence-runs.md`
- Generate: `results/evidence-runs/README.md`
- Generate: `results/evidence-runs/.gitignore`
- Generate: `results/evidence-runs/resolved-runs.json`
- Generate: `results/evidence-runs/archive-files.json`
- Generate: `results/evidence-runs/files.sha256`
- Generate: `results/evidence-runs/collections/*.csv`
- Generate: `results/evidence-runs/artifacts/**`
- Modify: `results/index.md`
- Modify: `results/clip_bench/README.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: CLI y manifiesto completos.
- Produces: árbol versionable y puntos de entrada documentales.

- [ ] **Step 1: Ejecutar la sincronización real**

Run: `python3 tools/evidence_runs.py sync`

Expected: exit 0; resumen con runs únicos por plano, `copied`, `archived_only`, cero `missing`, cero `conflict` y cero medios copiados.

- [ ] **Step 2: Inspeccionar los conteos generados antes de editar documentación**

Run:

```bash
jq '{total:(.runs|length), by_status:(.runs|group_by(.status)|map({key:.[0].status,value:length})|from_entries), by_plane:(.runs|group_by(.plane)|map({key:.[0].plane,value:length})|from_entries)}' results/evidence-runs/resolved-runs.json
```

Expected: 1.430 runs únicos (437 media-plane y 993 control-plane); `missing` y `conflict` ausentes; exactamente 44 entradas `archived_only`: 34 controles T1, seis runs históricos del doc 31 y cuatro entradas históricas de docs 37/39.

- [ ] **Step 3: Verificar manualmente muestras de cada familia**

Comprobar en el lock un run de `bench_imagenes`, T1, Nivel A, rodaje EBE, F-RT5, claqueta fallida y claqueta final. Para cada uno, verificar documento/resultado, colección, estado y enlace de artefacto.

- [ ] **Step 4: Actualizar los tres puntos de entrada**

En `results/index.md`, agregar una sección breve “Runs de evidencia” que enlace `evidence-runs.md` y explique `sync`/`--check`. En `results/clip_bench/README.md`, indicar que las detecciones originales siguen fuera de Git pero el subconjunto textual curado se archiva en el directorio común. En `README.md`, aclarar la misma excepción sin cambiar la regla general para `runs/`.

- [ ] **Step 5: Ejecutar sync de nuevo para confirmar estabilidad**

Run: `python3 tools/evidence_runs.py sync`

Expected: exit 0 y ningún cambio byte a byte dentro del archivo salvo los enlaces documentales externos, que no son generados.

- [ ] **Step 6: Checkpoint sin commit**

Run: `git diff --check -- README.md results tools tests`

Expected: salida vacía.

---

### Task 8: Verificación final exhaustiva

**Files:**
- Verify only: todos los archivos anteriores.

**Interfaces:**
- Consumes: repo terminado.
- Produces: evidencia de cierre sin crear commit.

- [ ] **Step 1: Ejecutar la suite nueva completa**

Run: `python3 -m pytest tests/test_evidence_*.py -q`

Expected: PASS.

- [ ] **Step 2: Ejecutar check completo contra originales**

Run: `python3 tools/evidence_runs.py --check`

Expected: exit 0; cero faltantes, extras, conflictos, drift, medios o secretos.

- [ ] **Step 3: Ejecutar check autocontenido de clon**

Run: `python3 tools/evidence_runs.py --check --archive-only`

Expected: exit 0 y aviso de que no compara originales.

- [ ] **Step 4: Verificar que Git puede ver el archivo curado y no ve medios**

Run: `git status --short --untracked-files=all results/evidence-runs results/evidence-runs.yaml results/evidence-runs.md`

Expected: manifiesto, documentación y artefactos textuales visibles; ninguna imagen/video.

Run: `find results/evidence-runs -type f | rg -i '\.(jpe?g|png|webp|bmp|gif|tiff?|mp4|avi|mkv|mov|webm|m4v)$'`

Expected: salida vacía.

- [ ] **Step 5: Revalidar índices existentes**

Run: `python3 ../docs/operacion/datos/96-verificar-indices.py`

Expected: las 16 campañas y cifras existentes continúan verdes.

Run: `python3 ../docs/operacion/datos/113-regenerar-provenance-estrato-b.py --check`

Expected: provenance del estrato B vigente.

- [ ] **Step 6: Verificar consistencia y estado final sin tocar cambios ajenos**

Run: `git diff --check`

Expected: salida vacía.

Run: `git status --short --branch`

Expected: solo se informan los cambios preexistentes y los nuevos de esta tarea; no hay commit nuevo.
