"""Configuración de la consola desde variables de entorno EOVRT_CONSOLE_*."""
from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

# Override manual de ids "congelados" para el badge del catálogo, además del campo
# `status` propio de cada YAML (fuente de verdad). Vacío por default: el status del
# set ya alcanza; usar EOVRT_CONSOLE_FROZEN_SETS solo para casos excepcionales.
DEFAULT_FROZEN_SETS: frozenset[str] = frozenset()
# Fuentes de ingesta que la consola sabe lanzar (decisión 2026-07-07: rtsp queda
# habilitado de forma permanente; supersede la restricción "MVP" de
# 2026-07-01-webconsole-design.md §6). oak_d habilitado desde 2026-07-13 (hardware
# integrado al media-plane); si el servicio no tiene el SDK DepthAI lo marca
# available=False y la consola lo muestra deshabilitado igual que antes.
SUPPORTED_PLUGINS = frozenset({"image_folder", "video_file", "rtsp", "oak_d"})
# Grupos de manifiestos curados/versionados (p.ej. la matriz BENCH) cuyo write-path
# nunca debe pisar un archivo existente vía la API, ni con overwrite=true.
DEFAULT_PROTECTED_GROUPS = frozenset({"bench_v2"})


def _discover_repo_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / "prompts").is_dir() and (candidate / "experiments").is_dir():
            return candidate
    raise FileNotFoundError(
        "No se encontró la raíz del repo (directorio con prompts/ y experiments/); "
        "definí EOVRT_CONSOLE_REPO_ROOT"
    )


@dataclass(frozen=True)
class ConsoleSettings:
    service_url: str
    repo_root: Path
    frozen_set_ids: frozenset[str]
    supported_plugins: frozenset[str] = SUPPORTED_PLUGINS
    hydration_limit: int = 50
    protected_groups: frozenset[str] = DEFAULT_PROTECTED_GROUPS
    # Segundo backend (control-plane :8081, spec 44b tarea 1): target fijo, no
    # depende del swap de fleet del modo orquestado (ese swap es solo media-plane).
    control_service_url: str = "http://localhost:8081"
    # Orquestación de plataforma (None = modo static, la consola opera como cliente
    # de un único EOVRT_CONSOLE_SERVICE_URL fijo, sin tocar Docker).
    compose_dir: Path | None = None
    switch_timeout_seconds: float = 300.0
    # Dist de la SPA embebido en la imagen de la consola; None = repo_root/webconsole/frontend/dist.
    spa_dist: Path | None = None
    # Destino de los masters de rodaje. None = repo hermano e-ovrt_datasets.
    recordings_dir: Path | None = None
    # Intérprete con el SDK DepthAI para la rama OAK-D (el backend corre 3.14 y
    # depthai no tiene wheels para 3.14). None = venv del media-plane.
    oakd_python: Path | None = None

    @property
    def prompts_dir(self) -> Path:
        return self.repo_root / "prompts"

    @property
    def experiments_dir(self) -> Path:
        return self.repo_root / "experiments"

    @property
    def cameras_dir(self) -> Path:
        return self.repo_root / "cameras"

    @property
    def raw_dir(self) -> Path:
        if self.recordings_dir is not None:
            return self.recordings_dir
        return self.repo_root.parent / "e-ovrt_datasets" / "datasets-videos" / "raw"

    @property
    def oakd_interpreter(self) -> Path:
        if self.oakd_python is not None:
            return self.oakd_python
        return self.repo_root.parent / "e-ovrt_media-plane" / ".venv" / "bin" / "python"

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> ConsoleSettings:
        env = os.environ if env is None else env
        root_raw = env.get("EOVRT_CONSOLE_REPO_ROOT")
        if root_raw:
            repo_root = Path(root_raw)
            if not ((repo_root / "prompts").is_dir() and (repo_root / "experiments").is_dir()):
                raise FileNotFoundError(
                    f"EOVRT_CONSOLE_REPO_ROOT inválido (sin prompts/ y experiments/): {repo_root}"
                )
        else:
            repo_root = _discover_repo_root(Path(__file__).resolve())
        frozen_raw = env.get("EOVRT_CONSOLE_FROZEN_SETS")
        frozen = (
            frozenset(s.strip() for s in frozen_raw.split(",") if s.strip())
            if frozen_raw is not None
            else DEFAULT_FROZEN_SETS
        )
        protected_raw = env.get("EOVRT_CONSOLE_PROTECTED_GROUPS")
        protected = (
            frozenset(s.strip() for s in protected_raw.split(",") if s.strip())
            if protected_raw is not None
            else DEFAULT_PROTECTED_GROUPS
        )
        return cls(
            service_url=env.get("EOVRT_CONSOLE_SERVICE_URL", "http://localhost:8080").rstrip("/"),
            repo_root=repo_root,
            frozen_set_ids=frozen,
            control_service_url=env.get(
                "EOVRT_CONSOLE_CONTROL_SERVICE_URL", "http://localhost:8081"
            ).rstrip("/"),
            hydration_limit=int(env.get("EOVRT_CONSOLE_HYDRATION_LIMIT", "50")),
            protected_groups=protected,
            compose_dir=Path(env["EOVRT_CONSOLE_COMPOSE_DIR"]) if env.get("EOVRT_CONSOLE_COMPOSE_DIR") else None,
            switch_timeout_seconds=float(env.get("EOVRT_CONSOLE_SWITCH_TIMEOUT", "300")),
            spa_dist=Path(env["EOVRT_CONSOLE_SPA_DIST"]) if env.get("EOVRT_CONSOLE_SPA_DIST") else None,
            recordings_dir=(
                Path(env["EOVRT_CONSOLE_RECORDINGS_DIR"])
                if env.get("EOVRT_CONSOLE_RECORDINGS_DIR")
                else None
            ),
            oakd_python=(
                Path(env["EOVRT_CONSOLE_OAKD_PYTHON"])
                if env.get("EOVRT_CONSOLE_OAKD_PYTHON")
                else None
            ),
        )
