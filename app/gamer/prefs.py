"""Persistent user preferences for Modo Gamer (opt-in tweak selections).

Stored at %APPDATA%\\TecnoApp\\gamer_prefs.json. Separate from snapshots —
prefs survive activate/deactivate cycles.
"""
from __future__ import annotations

import json
from pathlib import Path

from .snapshot import appdata_dir


def _prefs_path() -> Path:
    return appdata_dir() / "gamer_prefs.json"


def load_enabled_optins() -> set[str]:
    path = _prefs_path()
    if not path.exists():
        return set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    ids = data.get("enabled_optins", [])
    return set(ids) if isinstance(ids, list) else set()


def save_enabled_optins(ids: set[str]) -> None:
    _prefs_path().write_text(
        json.dumps({"enabled_optins": sorted(ids)}, indent=2),
        encoding="utf-8",
    )
