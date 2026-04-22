from __future__ import annotations

import winreg
from typing import Any

HIVES = {
    "HKLM": winreg.HKEY_LOCAL_MACHINE,
    "HKCU": winreg.HKEY_CURRENT_USER,
    "HKCR": winreg.HKEY_CLASSES_ROOT,
    "HKU": winreg.HKEY_USERS,
}


def _resolve_hive(hive: str | int) -> int:
    if isinstance(hive, int):
        return hive
    return HIVES[hive]


def read_value(hive: str | int, path: str, name: str) -> tuple[Any, int] | None:
    """Return (value, reg_type) or None if missing."""
    try:
        with winreg.OpenKey(_resolve_hive(hive), path, 0, winreg.KEY_READ) as key:
            value, reg_type = winreg.QueryValueEx(key, name)
            return value, reg_type
    except FileNotFoundError:
        return None
    except OSError:
        return None


def write_value(
    hive: str | int,
    path: str,
    name: str,
    value: Any,
    reg_type: int = winreg.REG_DWORD,
) -> None:
    with winreg.CreateKeyEx(_resolve_hive(hive), path, 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, name, 0, reg_type, value)


def delete_value(hive: str | int, path: str, name: str) -> bool:
    try:
        with winreg.OpenKey(_resolve_hive(hive), path, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, name)
            return True
    except FileNotFoundError:
        return False


def snapshot_value(hive: str | int, path: str, name: str) -> dict[str, Any]:
    """Return a JSON-serializable dict describing the current value.

    existed=False means the value did not exist — revert should delete it
    instead of writing something back.
    """
    current = read_value(hive, path, name)
    if current is None:
        return {"existed": False, "hive": str(hive), "path": path, "name": name}
    value, reg_type = current
    return {
        "existed": True,
        "hive": str(hive),
        "path": path,
        "name": name,
        "value": value,
        "type": reg_type,
    }


def restore_value(snapshot: dict[str, Any]) -> None:
    hive = snapshot["hive"]
    path = snapshot["path"]
    name = snapshot["name"]
    if not snapshot.get("existed"):
        delete_value(hive, path, name)
        return
    write_value(hive, path, name, snapshot["value"], snapshot["type"])


# --- batch helpers for tweaks that toggle multiple values ------------------

def snapshot_many(entries: list[tuple[str | int, str, str]]) -> list[dict[str, Any]]:
    """entries: list of (hive, path, name)."""
    return [snapshot_value(h, p, n) for (h, p, n) in entries]


def write_many(entries: list[tuple[str | int, str, str, Any, int]]) -> None:
    """entries: list of (hive, path, name, value, reg_type)."""
    for h, p, n, v, t in entries:
        write_value(h, p, n, v, t)


def enum_subkeys(hive: str | int, path: str) -> list[str]:
    try:
        with winreg.OpenKey(_resolve_hive(hive), path, 0, winreg.KEY_READ) as key:
            names: list[str] = []
            i = 0
            while True:
                try:
                    names.append(winreg.EnumKey(key, i))
                    i += 1
                except OSError:
                    break
            return names
    except FileNotFoundError:
        return []
    except OSError:
        return []


def restore_many(snapshots: list[dict[str, Any]]) -> list[str]:
    """Restore a list of snapshots; return list of error messages (empty = success)."""
    errors: list[str] = []
    for snap in snapshots:
        try:
            restore_value(snap)
        except OSError as exc:
            errors.append(f"{snap.get('name')}: {exc}")
    return errors
