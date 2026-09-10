"""Catálogos in-repo: prompt sets (prompts/) y manifiestos (experiments/)."""
from __future__ import annotations

from pathlib import Path

import yaml


def _load_yaml(path: Path) -> dict | None:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (yaml.YAMLError, OSError):
        return None
    return data if isinstance(data, dict) else None


def list_prompt_sets(prompts_dir: Path, frozen_ids: frozenset[str]) -> list[dict]:
    out: list[dict] = []
    if not prompts_dir.is_dir():
        return out
    for path in sorted(prompts_dir.glob("*.yaml")):
        data = _load_yaml(path)
        prompt_set = (data or {}).get("prompt_set")
        if not isinstance(prompt_set, dict) or "id" not in prompt_set:
            continue  # archivo ilegible o sin formato prompt_set: se omite
        out.append(
            {
                "id": prompt_set["id"],
                "description": prompt_set.get("description"),
                "language": prompt_set.get("language"),
                "status": prompt_set.get("status", "exploratory"),
                "track": prompt_set.get("track"),
                "frozen": (
                    prompt_set.get("status") == "frozen" or prompt_set["id"] in frozen_ids
                ),
                "classes": [
                    {
                        "id": c.get("id"),
                        "role": c.get("role"),
                        "enabled_by_default": c.get("enabled_by_default", True),
                        "phrasings": c.get("phrasings", {}),
                    }
                    for c in prompt_set.get("classes", [])
                ],
            }
        )
    return out


def get_prompt_set(prompts_dir: Path, set_id: str) -> dict | None:
    """Devuelve el dict interno de `prompt_set:` — el shape exacto de `set_inline`."""
    if not prompts_dir.is_dir():
        return None
    for path in sorted(prompts_dir.glob("*.yaml")):
        prompt_set = (_load_yaml(path) or {}).get("prompt_set")
        if isinstance(prompt_set, dict) and prompt_set.get("id") == set_id:
            return prompt_set
    return None


def list_experiments(experiments_dir: Path) -> list[dict]:
    out: list[dict] = []
    if not experiments_dir.is_dir():
        return out
    for path in sorted(experiments_dir.rglob("*.yaml")):
        manifest = _load_yaml(path)
        if manifest is None:
            continue
        rel = path.relative_to(experiments_dir)
        out.append(
            {
                "id": rel.with_suffix("").as_posix(),
                "group": rel.parent.as_posix() if rel.parent != Path(".") else "",
                "manifest": manifest,
            }
        )
    return out
