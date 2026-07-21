from pathlib import Path

from eovrt_webconsole.settings import ConsoleSettings


def _settings(repo: Path, **kwargs) -> ConsoleSettings:
    return ConsoleSettings(
        service_url="http://service.fake",
        repo_root=repo,
        frozen_set_ids=frozenset(),
        **kwargs,
    )


def test_raw_dir_default_es_el_repo_hermano_de_datasets(repo):
    s = _settings(repo)
    assert s.raw_dir == repo.parent / "e-ovrt_datasets" / "datasets-videos" / "raw"


def test_raw_dir_respeta_el_override(repo, tmp_path):
    s = _settings(repo, recordings_dir=tmp_path / "otro")
    assert s.raw_dir == tmp_path / "otro"


def test_oakd_interpreter_default_es_el_venv_del_media_plane(repo):
    s = _settings(repo)
    assert s.oakd_interpreter == repo.parent / "e-ovrt_media-plane" / ".venv" / "bin" / "python"


def test_oakd_interpreter_respeta_el_override(repo, tmp_path):
    s = _settings(repo, oakd_python=tmp_path / "py")
    assert s.oakd_interpreter == tmp_path / "py"


def test_from_env_lee_las_dos_variables(repo):
    s = ConsoleSettings.from_env(
        {
            "EOVRT_CONSOLE_REPO_ROOT": str(repo),
            "EOVRT_CONSOLE_RECORDINGS_DIR": "/data/raw",
            "EOVRT_CONSOLE_OAKD_PYTHON": "/opt/py312/bin/python",
        }
    )
    assert s.raw_dir == Path("/data/raw")
    assert s.oakd_interpreter == Path("/opt/py312/bin/python")
