from __future__ import annotations

import subprocess

_CREATE_NO_WINDOW = 0x08000000

_VALID_AUTOTUNE_LEVELS = {"disabled", "highlyrestricted", "restricted", "normal", "experimental"}


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        capture_output=True,
        text=True,
        creationflags=_CREATE_NO_WINDOW,
        check=False,
    )


def get_autotuninglevel() -> str | None:
    """Read TCP autotuning level via PowerShell (locale-independent).

    netsh output is localized; Get-NetTCPSetting returns a stable enum string.
    """
    result = _run(
        [
            "powershell",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            "(Get-NetTCPSetting -SettingName Internet).AutoTuningLevelLocal",
        ]
    )
    if result.returncode != 0:
        return None
    level = result.stdout.strip().lower()
    return level if level in _VALID_AUTOTUNE_LEVELS else None


def set_autotuninglevel(level: str) -> bool:
    return _run(["netsh", "int", "tcp", "set", "global", f"autotuninglevel={level}"]).returncode == 0


def flush_dns() -> bool:
    return _run(["ipconfig", "/flushdns"]).returncode == 0
