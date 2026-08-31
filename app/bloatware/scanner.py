"""
Scanner de bloatware — SOMENTE LEITURA.

Varre tres fontes, porque nenhuma sozinha ve tudo:
    1. Registro Uninstall (HKLM + HKCU, 64 e 32 bits) — MSI/InstallShield
    2. Pacotes UWP via Get-AppxPackage — apps da Store e pre-instalados
    3. Servicos do Windows — para mostrar o que o programa deixa rodando

Nada e removido aqui. O scanner apenas classifica pelo catalogo.
"""

from __future__ import annotations

import json
import subprocess
import winreg

from PySide6.QtCore import QThread, Signal

from .catalog import classify, is_removable, RISK_KEEP

_UNINSTALL_KEYS = [
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall", winreg.KEY_WOW64_64KEY),
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall", winreg.KEY_WOW64_32KEY),
    (winreg.HKEY_CURRENT_USER,  r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall", 0),
]


def _read_str(key, name: str) -> str:
    try:
        v, _ = winreg.QueryValueEx(key, name)
        return str(v).strip()
    except OSError:
        return ""


def _read_int(key, name: str) -> int:
    try:
        v, _ = winreg.QueryValueEx(key, name)
        return int(v)
    except (OSError, ValueError, TypeError):
        return 0


def scan_registry() -> list[dict]:
    """Programas do registro Uninstall. Ignora entradas de sistema."""
    seen: set[str] = set()
    out: list[dict] = []

    for hive, path, flag in _UNINSTALL_KEYS:
        try:
            root = winreg.OpenKey(hive, path, 0, winreg.KEY_READ | flag)
        except OSError:
            continue

        try:
            i = 0
            while True:
                try:
                    sub = winreg.EnumKey(root, i)
                except OSError:
                    break
                i += 1

                try:
                    k = winreg.OpenKey(root, sub, 0, winreg.KEY_READ | flag)
                except OSError:
                    continue

                try:
                    name = _read_str(k, "DisplayName")
                    if not name:
                        continue
                    # SystemComponent=1 e updates nao aparecem no painel
                    if _read_int(k, "SystemComponent") == 1:
                        continue
                    if _read_str(k, "ParentKeyName") or _read_str(k, "ReleaseType") in ("Update", "Hotfix"):
                        continue

                    dedup = name.lower()
                    if dedup in seen:
                        continue
                    seen.add(dedup)

                    publisher = _read_str(k, "Publisher")
                    risk, why = classify(name, publisher)
                    if not is_removable(risk):
                        continue

                    out.append({
                        "name": name,
                        "publisher": publisher,
                        "version": _read_str(k, "DisplayVersion"),
                        "size_mb": round(_read_int(k, "EstimatedSize") / 1024),
                        "uninstall": _read_str(k, "QuietUninstallString") or _read_str(k, "UninstallString"),
                        "kind": "registry",
                        "risk": risk,
                        "why": why,
                    })
                finally:
                    k.Close()
        finally:
            root.Close()

    return out


def scan_appx() -> list[dict]:
    """Pacotes UWP. Usa PowerShell — nao ha API winreg equivalente."""
    cmd = (
        "Get-AppxPackage | Where-Object { -not $_.IsFramework } | "
        "Select-Object Name,PackageFullName,Publisher | ConvertTo-Json -Compress"
    )
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", cmd],
            capture_output=True, encoding="utf-8", errors="replace",
            creationflags=subprocess.CREATE_NO_WINDOW, timeout=25,
        )
        data = json.loads(r.stdout or "[]")
    except Exception:
        return []

    if isinstance(data, dict):
        data = [data]

    out = []
    for p in data:
        name = (p.get("Name") or "").strip()
        if not name:
            continue
        risk, why = classify(name, p.get("Publisher") or "")
        if not is_removable(risk):
            continue
        out.append({
            "name": name,
            "publisher": p.get("Publisher") or "",
            "version": "",
            "size_mb": 0,          # Appx nao expoe tamanho barato
            "uninstall": p.get("PackageFullName") or "",
            "kind": "appx",
            "risk": risk,
            "why": why,
        })
    return out


def scan_installed() -> list[dict]:
    """Varredura completa, ordenada por tamanho (maior primeiro)."""
    items = scan_registry() + scan_appx()
    items.sort(key=lambda x: (-x["size_mb"], x["name"].lower()))
    return items


class BloatScanner(QThread):
    """
    Varredura em background — leva 2-5s, nao pode rodar no tick de 1s
    das metricas. Mesmo padrao do HardwareInfoWorker.
    """

    finished_scan = Signal("QVariant")

    def run(self):
        try:
            items = scan_installed()
        except Exception:
            items = []
        total = sum(i["size_mb"] for i in items)
        self.finished_scan.emit({"items": items, "count": len(items), "total_mb": total})
