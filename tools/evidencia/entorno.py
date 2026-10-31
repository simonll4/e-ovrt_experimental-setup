"""Rutas del workspace, modo de despliegue y la foto del entorno (`entorno.json`).

Dos modos, el mismo código:

- **docker** (la Victus, doc 134): el driver corre dentro del contenedor `console`. El
  workspace está montado con paridad de rutas, así que las rutas del host sirven tal cual
  para la consola, el control-plane y la distribución. El media-plane NO comparte esa
  paridad: monta `e-ovrt_datasets` en `/e-ovrt_datasets` y sus corridas en `/data/runs`, así
  que toda ruta que se le manda a él pasa por `ruta_medios`.
- **nativo** (una PC con los servicios levantados a mano): todo ve las rutas del host.

Se detecta por `EOVRT_CONSOLE_COMPOSE_DIR`, que el compose le define a la consola. Se puede
forzar con `EOVRT_EVIDENCIA_MODO`.
"""
from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]  # e-ovrt_experimental-setup

# Lo que reemplaza al workspace en los resultados versionados (`rutas.limpiar`).
MARCA_WORKSPACE = "$EOVRT_WORKSPACE"

# Repos del workspace cuyo commit queda registrado en cada prueba.
REPOS = (
    "e-ovrt_datasets",
    "e-ovrt_media-plane",
    "e-ovrt_control-plane",
    "e-ovrt_alert-distribution",
    "e-ovrt_experimental-setup",
    "docs",
)

# Imágenes del compose de la plataforma (infra/platform/docker-compose.yml).
IMAGENES = (
    "eovrt/console:latest",
    "eovrt/control-plane:latest",
    "eovrt/distribution:latest",
    "eovrt/media-plane:latest",
)


@dataclass(frozen=True)
class Entorno:
    ws: Path
    repo: Path
    modo: str  # "docker" | "nativo"
    consola_url: str
    datasets_medios: str  # raíz de e-ovrt_datasets tal como la ve el media-plane
    compose_dir: Path | None = None

    @property
    def datasets(self) -> Path:
        return self.ws / "e-ovrt_datasets"

    @property
    def scripts_datasets(self) -> Path:
        return self.datasets / "datasets" / "scripts"

    @property
    def media_plane(self) -> Path:
        return self.ws / "e-ovrt_media-plane"

    @property
    def media_runs(self) -> Path:
        return self.media_plane / "runs"

    @property
    def control_plane(self) -> Path:
        return self.ws / "e-ovrt_control-plane"

    @property
    def control_runs(self) -> Path:
        return self.control_plane / "runs"

    @property
    def patrones(self) -> Path:
        return self.control_plane / "configs" / "patterns"

    @property
    def banco(self) -> Path:
        return self.datasets / "datasets" / "processed" / "clip_bench"

    @property
    def gt_banco(self) -> Path:
        return self.banco / "gt"

    @property
    def catalogo(self) -> Path:
        return self.repo / "experiments" / "evidencia"

    @property
    def generados(self) -> Path:
        """Manifiestos y configs expandidos por corrida. NO van bajo `experiments/`: la consola
        recorre esa carpeta con `rglob` y los listaría como experimentos."""
        return self.trabajo / "_generados"

    @property
    def resultados(self) -> Path:
        """`results/gen2/` (versionado). `EOVRT_EVIDENCIA_SALIDA` lo redirige para ensayar el
        driver fuera de la Victus sin dejar resultados que parezcan de la generación 2."""
        salida = os.environ.get("EOVRT_EVIDENCIA_SALIDA")
        return Path(salida) / "results" / "gen2" if salida else self.repo / "results" / "gen2"

    @property
    def trabajo(self) -> Path:
        """Intermedios pesados (fusiones, ledgers): `runs/` del repo, git-ignorado."""
        salida = os.environ.get("EOVRT_EVIDENCIA_SALIDA")
        return Path(salida) / "runs" / "evidencia" if salida else self.repo / "runs" / "evidencia"

    def expandir(self, datos):
        """`datos` con `MARCA_WORKSPACE` reemplazada por el workspace de esta máquina, en todo
        string: la inversa de `rutas.limpiar`, para seguir las rutas de un resultado limpio."""
        if isinstance(datos, str):
            return datos.replace(MARCA_WORKSPACE, str(self.ws)) if MARCA_WORKSPACE in datos else datos
        if isinstance(datos, dict):
            return {k: self.expandir(v) for k, v in datos.items()}
        if isinstance(datos, list):
            return [self.expandir(v) for v in datos]
        return datos

    def ruta_medios(self, ruta: Path | str) -> str:
        """Ruta de un archivo de `e-ovrt_datasets` tal como la ve el media-plane."""
        rel = Path(ruta).relative_to(self.datasets)
        return f"{self.datasets_medios.rstrip('/')}/{rel.as_posix()}"


def detectar() -> Entorno:
    ws = Path(os.environ.get("EOVRT_WORKSPACE") or REPO.parent)
    compose = os.environ.get("EOVRT_CONSOLE_COMPOSE_DIR")
    modo = os.environ.get("EOVRT_EVIDENCIA_MODO") or ("docker" if compose else "nativo")
    if modo not in ("docker", "nativo"):
        raise ValueError(f"EOVRT_EVIDENCIA_MODO inválido: {modo!r} (docker | nativo)")
    datasets_medios = os.environ.get("EOVRT_EVIDENCIA_DATASETS_MEDIOS") or (
        "/e-ovrt_datasets" if modo == "docker" else str(ws / "e-ovrt_datasets")
    )
    return Entorno(
        ws=ws,
        repo=REPO,
        modo=modo,
        consola_url=os.environ.get("EOVRT_EVIDENCIA_CONSOLA", "http://127.0.0.1:8090").rstrip("/"),
        datasets_medios=datasets_medios,
        compose_dir=Path(compose) if compose else None,
    )


# --- foto del entorno ---------------------------------------------------------------


def _correr(cmd: list[str], timeout: float = 20.0, cwd: Path | None = None) -> str | None:
    """Salida de un comando, o None si no existe o falla (la foto nunca rompe la prueba)."""
    if shutil.which(cmd[0]) is None:
        return None
    try:
        out = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, check=False, cwd=cwd
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def git_head(repo: Path) -> dict:
    """Commit y rama leídos de `.git` (la imagen de la consola no trae el binario git)."""
    git = repo / ".git"
    if git.is_file():  # worktree: `gitdir: <ruta>`
        texto = git.read_text(encoding="utf-8").strip()
        if texto.startswith("gitdir:"):
            git = (repo / texto.split(":", 1)[1].strip()).resolve()
    if not (git / "HEAD").is_file():
        return {"commit": None, "rama": None, "nota": "sin .git"}
    head = (git / "HEAD").read_text(encoding="utf-8").strip()
    rama = None
    commit = head
    if head.startswith("ref: "):
        ref = head[5:]
        rama = ref.removeprefix("refs/heads/")
        commit = None
        candidatos = [git / ref]
        commondir = git / "commondir"
        if commondir.is_file():
            comun = (git / commondir.read_text(encoding="utf-8").strip()).resolve()
            candidatos.append(comun / ref)
        for archivo in candidatos:
            if archivo.is_file():
                commit = archivo.read_text(encoding="utf-8").strip()
                break
        if commit is None:
            for base in [git, *(c.parent.parent.parent for c in candidatos[1:])]:
                packed = base / "packed-refs"
                if packed.is_file():
                    for linea in packed.read_text(encoding="utf-8").splitlines():
                        if linea.endswith(" " + ref):
                            commit = linea.split(" ", 1)[0]
                            break
                if commit:
                    break
    sucio = None
    porcelana = _correr(["git", "-C", str(repo), "status", "--porcelain"])
    if porcelana is not None:
        sucio = len([l for l in porcelana.splitlines() if l.strip()])
    return {"commit": commit, "rama": rama, "archivos_sin_commitear": sucio}


def _memoria_total_gb() -> float | None:
    try:
        for linea in Path("/proc/meminfo").read_text().splitlines():
            if linea.startswith("MemTotal:"):
                return round(int(linea.split()[1]) / 1024 / 1024, 1)
    except OSError:
        return None
    return None


def _cpu_modelo() -> str | None:
    try:
        for linea in Path("/proc/cpuinfo").read_text().splitlines():
            if linea.startswith("model name"):
                return linea.split(":", 1)[1].strip()
    except OSError:
        return None
    return platform.processor() or None


def _json_o_texto(texto: str | None):
    if texto is None:
        return None
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        filas = []
        for linea in texto.splitlines():
            try:
                filas.append(json.loads(linea))
            except json.JSONDecodeError:
                return texto
        return filas


PROYECTO_COMPOSE = "eovrt"  # el mismo `--project-name` que usa el orquestador de la consola


def docker_compose(ent: Entorno, *args: str, timeout: float = 60.0) -> str | None:
    if ent.compose_dir is None:
        return None
    return _correr(
        ["docker", "compose", "--project-name", PROYECTO_COMPOSE, *args],
        timeout=timeout,
        cwd=ent.compose_dir,
    )


def contenedor_de(ent: Entorno, servicio: str) -> str | None:
    """Nombre del contenedor de un servicio del compose (p.ej. `eovrt-mp-gdino-tiny-560-1`)."""
    salida = docker_compose(ent, "ps", "--all", "--format", "json", servicio)
    filas = _json_o_texto(salida)
    if isinstance(filas, dict):
        filas = [filas]
    if not isinstance(filas, list):
        return None
    for fila in filas:
        if isinstance(fila, dict) and fila.get("Service") == servicio:
            return fila.get("Name")
    return None


def gpu(ent: Entorno, servicio_gpu: str | None = None) -> str | None:
    consulta = ["nvidia-smi", "--query-gpu=name,driver_version,memory.total", "--format=csv,noheader"]
    if ent.modo == "docker":
        contenedor = contenedor_de(ent, servicio_gpu) if servicio_gpu else None
        if contenedor:
            return _correr(["docker", "exec", contenedor, *consulta])
        return None
    return _correr(consulta)


def foto(ent: Entorno, *, objetivo: dict | None = None, servicio_gpu: str | None = None) -> dict:
    """Todo lo que identifica dónde y con qué corrió una prueba."""
    datos: dict = {
        "schema": "entorno.gen2.v1",
        "fecha_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "modo": ent.modo,
        "workspace": str(ent.ws),
        "host": {
            "nombre": platform.node(),
            "plataforma": platform.platform(),
            "cpu": _cpu_modelo(),
            "nucleos": os.cpu_count(),
            "memoria_gb": _memoria_total_gb(),
            "python": platform.python_version(),
        },
        "gpu": gpu(ent, servicio_gpu),
        "modelo_cargado": objetivo,
        "repos": {nombre: git_head(ent.ws / nombre) for nombre in REPOS if (ent.ws / nombre).exists()},
    }
    if ent.modo == "docker":
        datos["docker"] = {
            "version": _json_o_texto(_correr(["docker", "version", "--format", "{{json .}}"])),
            "compose_ps": _json_o_texto(docker_compose(ent, "ps", "--all", "--format", "json")),
            "imagenes": {
                imagen: _json_o_texto(
                    _correr(
                        [
                            "docker",
                            "image",
                            "inspect",
                            imagen,
                            "--format",
                            '{"id": {{json .Id}}, "creada": {{json .Created}}, "digests": {{json .RepoDigests}}}',
                        ]
                    )
                )
                for imagen in IMAGENES
            },
        }
    return datos
