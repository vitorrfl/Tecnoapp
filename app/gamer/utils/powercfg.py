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
