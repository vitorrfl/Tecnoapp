from __future__ import annotations

import subprocess

_CREATE_NO_WINDOW = 0x08000000

START_TYPES = {
    "boot": "boot",
    "system": "system",
    "auto": "auto",
    "demand": "demand",
    "disabled": "disabled",
    "delayed-auto": "delayed-auto",
}


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        capture_output=True,
        text=True,
        creationflags=_CREATE_NO_WINDOW,
        check=False,
    )


def query_start_type(service: str) -> str | None:
    """Return current start type as string ('auto'/'demand'/'disabled'/...) or None."""
    result = _run(["sc", "qc", service])
    if result.returncode != 0:
        return None
    for line in result.stdout.splitlines():
        line = line.strip()
        if "START_TYPE" not in line:
            continue
        lower = line.lower()
        if "disabled" in lower:
            return "disabled"
        if "demand_start" in lower:
            return "demand"
        if "auto_start" in lower:
            if "delayed" in lower:
                return "delayed-auto"
            return "auto"
        if "boot_start" in lower:
            return "boot"
        if "system_start" in lower:
            return "system"
    return None


def set_start_type(service: str, start_type: str) -> bool:
    if start_type not in START_TYPES:
        return False
    result = _run(["sc", "config", service, f"start={start_type}"])
    return result.returncode == 0


def is_running(service: str) -> bool:
    result = _run(["sc", "query", service])
    return result.returncode == 0 and "RUNNING" in result.stdout.upper()
