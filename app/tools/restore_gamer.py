"""Standalone restore tool for Modo Gamer.

Reverts every tweak recorded in the active snapshot at %APPDATA%\\TecnoApp\\
without launching the Qt UI. Intended to be invoked by the uninstaller or
manually by support if a user removes the main app while Modo Gamer is on.

Usage:
    python -m tools.restore_gamer [--check]

    --check  Prints status without making changes.
"""
from __future__ import annotations

import argparse
import ctypes
import os
import sys

# Allow running directly ("python restore_gamer.py") as well as via -m.
if __package__ is None or __package__ == "":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gamer import build_engine
from gamer.snapshot import active_pointer_path


def _is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _relaunch_as_admin() -> None:
    params = " ".join(f'"{a}"' for a in sys.argv)
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)


def main() -> int:
    parser = argparse.ArgumentParser(description="Restore TecnoApp Modo Gamer state.")
    parser.add_argument("--check", action="store_true", help="Status only, no changes.")
    args = parser.parse_args()

    engine = build_engine()
    pointer = active_pointer_path()

    if not engine.is_active():
        print(f"[ok] Modo Gamer não está ativo ({pointer}).")
        return 0

    snapshot = engine.active_snapshot()
    if snapshot is None:
        print(f"[warn] snapshot ativo não pôde ser lido: {pointer}")
        return 2

    print(f"[info] snapshot ativo: run_id={snapshot.run_id} criado={snapshot.created_at}")
    print(f"[info] {len(snapshot.tweaks)} tweak(s) a reverter.")

    if args.check:
        for entry in snapshot.tweaks:
            print(f"  - {entry.tweak_id} ({entry.category})")
        return 0

    if sys.platform == "win32" and not _is_admin():
        print("[info] re-executando com elevação para reverter...")
        _relaunch_as_admin()
        return 0

    report = engine.deactivate()
    print(f"[done] revertidos={len(report.applied)} pulados={len(report.skipped)} falhas={len(report.failed)}")
    for r in report.failed:
        print(f"  [fail] {r.tweak_id}: {r.message} {r.error or ''}")
    return 0 if not report.failed else 1


if __name__ == "__main__":
    sys.exit(main())
