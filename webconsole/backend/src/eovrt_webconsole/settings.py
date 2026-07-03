"""Configuración de la consola desde variables de entorno EOVRT_CONSOLE_*."""
from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

DEFAULT_FROZEN_SETS = frozenset({"cr01_cr02_bench_v2"})
# Policy MVP (Spec B §6): RTSP/oak_d quedan fuera por decisión de la consola,
# no del catálogo del servicio (que marca rtsp como disponible).
MVP_PLUGINS = frozenset({"image_folder", "video_file"})
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
    mvp_plugins: frozenset[str] = MVP_PLUGINS
    hydration_limit: int = 50
    protected_groups: frozenset[str] = DEFAULT_PROTECTED_GROUPS

    @property
    def prompts_dir(self) -> Path:
        return self.repo_root / "prompts"

    @property
    def experiments_dir(self) -> Path:
        return self.repo_root / "experiments"

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
            hydration_limit=int(env.get("EOVRT_CONSOLE_HYDRATION_LIMIT", "50")),
            protected_groups=protected,
        )
