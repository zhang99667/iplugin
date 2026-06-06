#!/usr/bin/env python3
"""Stable Codex hook entry for iPlugin skill telemetry."""

import os
import runpy
from pathlib import Path


CODEX_HOME = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()
os.environ.setdefault("CODEX_HOME", str(CODEX_HOME))


def version_key(path: Path) -> tuple[int, ...]:
    parts: list[int] = []
    for part in path.name.split("."):
        try:
            parts.append(int(part))
        except ValueError:
            parts.append(-1)
    return tuple(parts)


def latest_cached_script() -> Path | None:
    cache_root = CODEX_HOME / "plugins/cache/personal/iplugin"
    if not cache_root.exists():
        return None

    scripts: list[Path] = []
    for version_dir in cache_root.iterdir():
        if not version_dir.is_dir():
            continue
        script = version_dir / "hooks" / "skill-telemetry.py"
        if script.is_file():
            scripts.append(script)

    if not scripts:
        return None
    return max(scripts, key=lambda script: (version_key(script.parent.parent), script.stat().st_mtime))


def candidates() -> list[Path]:
    values: list[Path] = []

    override = os.environ.get("IPPLUGIN_TELEMETRY_SCRIPT")
    if override:
        values.append(Path(override).expanduser())

    values.append(Path("/Users/markz/code/tools/iplugin/hooks/skill-telemetry.py"))

    cached = latest_cached_script()
    if cached:
        values.append(cached)

    return values


def main() -> None:
    for script in candidates():
        if script.is_file():
            try:
                runpy.run_path(str(script), run_name="__main__")
            except Exception:
                pass
            return


if __name__ == "__main__":
    main()
