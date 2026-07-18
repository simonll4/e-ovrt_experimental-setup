from pathlib import Path

import pytest

from eovrt_webconsole.settings import ConsoleSettings


def _repo(tmp_path: Path) -> Path:
    (tmp_path / "prompts").mkdir()
    (tmp_path / "experiments").mkdir()
    return tmp_path


def test_from_env_minimo(tmp_path):
    s = ConsoleSettings.from_env({"EOVRT_CONSOLE_REPO_ROOT": str(_repo(tmp_path))})
    assert s.service_url == "http://localhost:8080"
    assert s.frozen_set_ids == frozenset()
    assert s.supported_plugins == frozenset({"image_folder", "video_file", "rtsp", "oak_d"})
    assert s.prompts_dir == tmp_path / "prompts"
    assert s.experiments_dir == tmp_path / "experiments"


def test_from_env_completo(tmp_path):
    s = ConsoleSettings.from_env({
        "EOVRT_CONSOLE_REPO_ROOT": str(_repo(tmp_path)),
        "EOVRT_CONSOLE_SERVICE_URL": "http://gpu-node:8080/",
        "EOVRT_CONSOLE_FROZEN_SETS": "a, b",
    })
    assert s.service_url == "http://gpu-node:8080"  # sin slash final
    assert s.frozen_set_ids == frozenset({"a", "b"})


def test_autodiscover_repo_root():
    # El repo real tiene prompts/ y experiments/ en la raíz: el discovery sube desde el módulo.
    s = ConsoleSettings.from_env({})
    assert (s.repo_root / "prompts").is_dir()
    assert (s.repo_root / "experiments").is_dir()


def test_repo_root_invalido(tmp_path):
    with pytest.raises(FileNotFoundError):
        ConsoleSettings.from_env({"EOVRT_CONSOLE_REPO_ROOT": str(tmp_path / "nada")})


def test_compose_dir_default_none_y_override(tmp_path):
    repo = _repo(tmp_path)
    base = {"EOVRT_CONSOLE_REPO_ROOT": str(repo)}
    assert ConsoleSettings.from_env(base).compose_dir is None
    s = ConsoleSettings.from_env({**base, "EOVRT_CONSOLE_COMPOSE_DIR": "/x/infra/platform"})
    assert s.compose_dir == Path("/x/infra/platform")


def test_switch_timeout_default_y_override(tmp_path):
    repo = _repo(tmp_path)
    base = {"EOVRT_CONSOLE_REPO_ROOT": str(repo)}
    assert ConsoleSettings.from_env(base).switch_timeout_seconds == 300.0
    s = ConsoleSettings.from_env({**base, "EOVRT_CONSOLE_SWITCH_TIMEOUT": "45"})
    assert s.switch_timeout_seconds == 45.0


def test_spa_dist_override(tmp_path):
    repo = _repo(tmp_path)
    base = {"EOVRT_CONSOLE_REPO_ROOT": str(repo)}
    assert ConsoleSettings.from_env(base).spa_dist is None
    s = ConsoleSettings.from_env({**base, "EOVRT_CONSOLE_SPA_DIST": "/app/spa-dist"})
    assert s.spa_dist == Path("/app/spa-dist")
