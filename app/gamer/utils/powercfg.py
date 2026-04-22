from __future__ import annotations

import re
import subprocess

ULTIMATE_PERFORMANCE_TEMPLATE = "e9a42b02-d5df-448d-aa00-03f14749eb61"
_GUID_RE = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")

_CREATE_NO_WINDOW = 0x08000000


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        capture_output=True,
        text=True,
        creationflags=_CREATE_NO_WINDOW,
        check=False,
    )


def get_active_scheme_guid() -> str | None:
    result = _run(["powercfg", "/getactivescheme"])
    if result.returncode != 0:
        return None
    match = _GUID_RE.search(result.stdout)
    return match.group(0) if match else None


def list_schemes() -> list[tuple[str, str]]:
    """Return [(guid, friendly_name), ...]."""
    result = _run(["powercfg", "/list"])
    if result.returncode != 0:
        return []
    schemes: list[tuple[str, str]] = []
    for line in result.stdout.splitlines():
        m = _GUID_RE.search(line)
        if not m:
            continue
        guid = m.group(0)
        name_match = re.search(r"\((.*?)\)", line)
        name = name_match.group(1) if name_match else ""
        schemes.append((guid, name))
    return schemes


def scheme_exists(guid: str) -> bool:
    return any(g.lower() == guid.lower() for g, _ in list_schemes())


def duplicate_scheme(source_guid: str) -> str | None:
    """Duplicate a scheme template and return the new GUID."""
    result = _run(["powercfg", "-duplicatescheme", source_guid])
    if result.returncode != 0:
        return None
    match = _GUID_RE.search(result.stdout)
    return match.group(0) if match else None


def set_active(guid: str) -> bool:
    return _run(["powercfg", "/setactive", guid]).returncode == 0


def delete_scheme(guid: str) -> bool:
    return _run(["powercfg", "/delete", guid]).returncode == 0


# Processor subgroup constants
SUB_PROCESSOR = "54533251-82be-4824-96c1-47b60b740d00"
SETTING_CPMINCORES = "0cc5b647-c1df-4637-891a-dec35c318583"


def query_setting_index(scheme: str, subgroup: str, setting: str) -> tuple[int | None, int | None]:
    """Return (ac_value, dc_value) indices for a power setting, or (None, None)."""
    result = _run(["powercfg", "/query", scheme, subgroup, setting])
    if result.returncode != 0:
        return None, None
    ac, dc = None, None
    for line in result.stdout.splitlines():
        stripped = line.strip()
        lower = stripped.lower()
        if lower.startswith("current ac power setting index"):
            ac = _parse_hex_tail(stripped)
        elif lower.startswith("current dc power setting index"):
            dc = _parse_hex_tail(stripped)
    return ac, dc


def _parse_hex_tail(line: str) -> int | None:
    parts = line.split(":")
    if len(parts) < 2:
        return None
    token = parts[-1].strip()
    try:
        return int(token, 16) if token.lower().startswith("0x") else int(token)
    except ValueError:
        return None


def unhide_attribute(subgroup: str, setting: str) -> bool:
    """Remove ATTRIB_HIDE from a power setting so it becomes visible/editable.

    Several processor subgroup settings (like CPMINCORES) are hidden by default.
    """
    return _run(["powercfg", "/attributes", subgroup, setting, "-ATTRIB_HIDE"]).returncode == 0


def set_ac_value_index(scheme: str, subgroup: str, setting: str, value: int) -> bool:
    return _run(["powercfg", "/setacvalueindex", scheme, subgroup, setting, str(value)]).returncode == 0


def set_dc_value_index(scheme: str, subgroup: str, setting: str, value: int) -> bool:
    return _run(["powercfg", "/setdcvalueindex", scheme, subgroup, setting, str(value)]).returncode == 0


def is_on_ac_power() -> bool:
    """True if plugged in (not on battery). Defaults True on desktops with no battery."""
    import ctypes

    class _Status(ctypes.Structure):
        _fields_ = [
            ("ACLineStatus", ctypes.c_byte),
            ("BatteryFlag", ctypes.c_byte),
            ("BatteryLifePercent", ctypes.c_byte),
            ("SystemStatusFlag", ctypes.c_byte),
            ("BatteryLifeTime", ctypes.c_ulong),
            ("BatteryFullLifeTime", ctypes.c_ulong),
        ]

    status = _Status()
    if not ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(status)):
        return True
    # 0 = offline (battery), 1 = online (AC), 255 = unknown (desktop)
    return status.ACLineStatus != 0
