from pathlib import Path

from eovrt_webconsole.experiment import runner


def test_runner_uses_configured_repo_for_experiments_and_artifacts(monkeypatch, tmp_path):
    repo = tmp_path / "e-ovrt_experimental-setup"
    monkeypatch.setenv("EOVRT_CONSOLE_REPO_ROOT", str(repo))

    assert runner._repo_root() == repo
    assert runner._default_dest_root() == repo / "runs"
    assert runner._default_resolve_run_dir("media", "run-1") == (
        tmp_path / "e-ovrt_media-plane" / "runs" / "run-1"
    )


def test_runner_preserves_source_checkout_default(monkeypatch):
    monkeypatch.delenv("EOVRT_CONSOLE_REPO_ROOT", raising=False)

    assert runner._repo_root() == Path(runner.__file__).resolve().parents[5]
