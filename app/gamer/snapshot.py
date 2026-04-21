from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any


def appdata_dir() -> Path:
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    path = Path(base) / "TecnoApp"
    path.mkdir(parents=True, exist_ok=True)
    return path


def snapshots_dir() -> Path:
    path = appdata_dir() / "snapshots"
    path.mkdir(parents=True, exist_ok=True)
    return path


def history_dir() -> Path:
    path = snapshots_dir() / "history"
    path.mkdir(parents=True, exist_ok=True)
    return path


def active_pointer_path() -> Path:
    return appdata_dir() / "active_snapshot.json"


@dataclass
class TweakSnapshot:
    tweak_id: str
    category: str
    label: str
    previous_state: dict[str, Any] = field(default_factory=dict)


@dataclass
class Snapshot:
    run_id: str
    created_at: str
    windows_version: str
    tweaks: list[TweakSnapshot] = field(default_factory=list)

    @classmethod
    def new(cls, windows_version: str) -> "Snapshot":
        run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
        return cls(
            run_id=run_id,
            created_at=datetime.now().isoformat(timespec="seconds"),
            windows_version=windows_version,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "created_at": self.created_at,
            "windows_version": self.windows_version,
            "tweaks": [asdict(t) for t in self.tweaks],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Snapshot":
        return cls(
            run_id=data["run_id"],
            created_at=data["created_at"],
            windows_version=data.get("windows_version", ""),
            tweaks=[TweakSnapshot(**t) for t in data.get("tweaks", [])],
        )


class SnapshotStore:
    def save(self, snapshot: Snapshot) -> Path:
        path = snapshots_dir() / f"{snapshot.run_id}.json"
        path.write_text(json.dumps(snapshot.to_dict(), indent=2), encoding="utf-8")
        return path

    def mark_active(self, snapshot: Snapshot) -> None:
        pointer = {"run_id": snapshot.run_id, "activated_at": snapshot.created_at}
        active_pointer_path().write_text(json.dumps(pointer, indent=2), encoding="utf-8")

    def load_active(self) -> Snapshot | None:
        pointer = active_pointer_path()
        if not pointer.exists():
            return None
        try:
            data = json.loads(pointer.read_text(encoding="utf-8"))
            run_id = data["run_id"]
        except (json.JSONDecodeError, KeyError, OSError):
            return None
        snap_path = snapshots_dir() / f"{run_id}.json"
        if not snap_path.exists():
            return None
        try:
            return Snapshot.from_dict(json.loads(snap_path.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, KeyError, OSError):
            return None

    def archive_active(self) -> None:
        pointer = active_pointer_path()
        if not pointer.exists():
            return
        try:
            data = json.loads(pointer.read_text(encoding="utf-8"))
            run_id = data.get("run_id")
        except (json.JSONDecodeError, OSError):
            run_id = None
        pointer.unlink(missing_ok=True)
        if not run_id:
            return
        src = snapshots_dir() / f"{run_id}.json"
        if src.exists():
            dst = history_dir() / f"{run_id}.json"
            try:
                src.replace(dst)
            except OSError:
                pass

    def is_active(self) -> bool:
        return active_pointer_path().exists()
