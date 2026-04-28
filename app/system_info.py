"""
Coleta de informações do sistema para o TecnoApp.

Combina:
- psutil — métricas live rápidas (CPU, RAM, disco, processos)
- platform / os — info estática rápida (SO, usuário, máquina)
- WMI via PowerShell — hardware "lento" (GPU, placa-mãe, BIOS)
  → executado em QThread (HardwareInfoWorker) para não travar a UI.

Nenhuma função levanta — em caso de falha retorna placeholder ('—' ou 0).
"""

import os
import platform
import subprocess

import psutil
from PySide6.QtCore import QThread, Signal


# ─────────────────────────────────────────────────────────────────────
# Info estática rápida (fast, sub-100ms)
# ─────────────────────────────────────────────────────────────────────

def os_info() -> dict:
    """Sistema operacional, build, arquitetura, usuário, nome da máquina."""
    try:
        return {
            "system":  f"{platform.system()} {platform.release()}",
            "version": platform.version(),
            "arch":    platform.machine(),
            "user":    os.environ.get("USERNAME", "—"),
            "machine": platform.node() or "—",
        }
    except Exception:
        return {"system": "—", "version": "—", "arch": "—", "user": "—", "machine": "—"}


def cpu_static() -> dict:
    """Nome do processador, frequência, núcleos físicos e lógicos."""
    try:
        try:
            freq = psutil.cpu_freq()
            ghz = f"{freq.current/1000:.2f} GHz" if freq and freq.current else "—"
        except Exception:
            ghz = "—"
        return {
            "name":    platform.processor() or "—",
            "freq":    ghz,
            "cores":   psutil.cpu_count(logical=False) or 0,
            "threads": psutil.cpu_count(logical=True)  or 0,
        }
    except Exception:
        return {"name": "—", "freq": "—", "cores": 0, "threads": 0}


def memory_static() -> dict:
    """Total / usado / pct atual de memória RAM."""
    try:
        m = psutil.virtual_memory()
        return {"total": m.total, "used": m.used, "pct": m.percent}
    except Exception:
        return {"total": 0, "used": 0, "pct": 0.0}


# ─────────────────────────────────────────────────────────────────────
# Métricas live (chamadas a cada tick do timer)
# ─────────────────────────────────────────────────────────────────────

# Prime psutil.cpu_percent — primeira chamada sem interval retorna 0.
psutil.cpu_percent(interval=None)


def cpu_pct() -> float:
    """% de uso da CPU desde a última chamada. Não bloqueia."""
    try:
        return psutil.cpu_percent(interval=None)
    except Exception:
        return 0.0


def mem_live() -> dict:
    """Snapshot live da RAM."""
    try:
        m = psutil.virtual_memory()
        return {"used": m.used, "total": m.total, "pct": m.percent}
    except Exception:
        return {"used": 0, "total": 0, "pct": 0.0}


def disks_info() -> list[dict]:
    """Lista de discos com uso. Filtra unidades removíveis ausentes."""
    out = []
    try:
        for part in psutil.disk_partitions(all=False):
            try:
                u = psutil.disk_usage(part.mountpoint)
                out.append({
                    "drive": part.device.rstrip("\\"),
                    "fs":    part.fstype or "—",
                    "total": u.total,
                    "used":  u.used,
                    "free":  u.free,
                    "pct":   u.percent,
                })
            except Exception:
                pass
    except Exception:
        pass
    return out


def disk_c_info() -> dict:
    """Atalho: disco C: para o dashboard."""
    try:
        u = psutil.disk_usage("C:\\")
        return {"used": u.used, "total": u.total, "pct": u.percent}
    except Exception:
        return {"used": 0, "total": 0, "pct": 0.0}


def processes_count() -> int:
    """Número de processos atualmente em execução."""
    try:
        return len(psutil.pids())
    except Exception:
        return 0


def uptime_seconds() -> int:
    """Segundos desde o último boot."""
    try:
        import time
        return max(0, int(time.time() - psutil.boot_time()))
    except Exception:
        return 0


def format_uptime(secs: int) -> str:
    """'4d 12h' ou '5h 23m' ou '12m'."""
    if secs <= 0:
        return "—"
    d, r = divmod(secs, 86400)
    h, r = divmod(r, 3600)
    m, _ = divmod(r, 60)
    if d > 0: return f"{d}d {h}h"
    if h > 0: return f"{h}h {m}m"
    return f"{m}m"


def top_processes(n: int = 5) -> list[dict]:
    """Top N processos por uso de RAM (mais estável que CPU instantânea)."""
    try:
        items = []
        for p in psutil.process_iter(["pid", "name", "memory_info"]):
            try:
                mem = p.info["memory_info"].rss if p.info["memory_info"] else 0
                items.append({"pid": p.info["pid"], "name": p.info["name"] or "—", "mem": mem})
            except Exception:
                pass
        items.sort(key=lambda x: x["mem"], reverse=True)
        return items[:n]
    except Exception:
        return []


# ─────────────────────────────────────────────────────────────────────
# Hardware "lento" — WMI via PowerShell, em worker thread
# ─────────────────────────────────────────────────────────────────────

def _ps(cmd: str, timeout: int = 4) -> str:
    """Executa PowerShell e retorna stdout strip. '' em falha."""
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command",
             f"[Console]::OutputEncoding=[System.Text.Encoding]::UTF8; {cmd}"],
            capture_output=True,
            encoding="utf-8", errors="replace",
            creationflags=subprocess.CREATE_NO_WINDOW, timeout=timeout,
        )
        return (r.stdout or "").strip()
    except Exception:
        return ""


class HardwareInfoWorker(QThread):
    """
    Busca async de campos lentos:
        - GPU (nome, VRAM, driver)
        - Placa-mãe (fabricante, modelo)
        - BIOS (versão, data)

    Tipicamente leva 2-5 segundos. UI mostra placeholder até finished_info.
    """
    finished_info = Signal(dict)

    def run(self):
        info = {
            "gpu_name":          "—",
            "gpu_vram":          0,
            "gpu_driver":        "—",
            "mobo_manufacturer": "—",
            "mobo_model":        "—",
            "bios_version":      "—",
        }
        try:
            gpu = _ps(
                "Get-CimInstance Win32_VideoController | "
                "Select-Object -First 1 | "
                "ForEach-Object { \"$($_.Name)|$($_.AdapterRAM)|$($_.DriverVersion)\" }"
            )
            if "|" in gpu:
                parts = gpu.split("|")
                info["gpu_name"]   = parts[0] or "—"
                try:
                    info["gpu_vram"] = int(parts[1]) if len(parts) > 1 else 0
                except Exception:
                    info["gpu_vram"] = 0
                info["gpu_driver"] = parts[2] if len(parts) > 2 else "—"

            mobo = _ps(
                "Get-CimInstance Win32_BaseBoard | "
                "ForEach-Object { \"$($_.Manufacturer)|$($_.Product)\" }"
            )
            if "|" in mobo:
                parts = mobo.split("|")
                info["mobo_manufacturer"] = parts[0] or "—"
                info["mobo_model"]        = parts[1] if len(parts) > 1 else "—"

            bios = _ps(
                "Get-CimInstance Win32_BIOS | "
                "Select-Object -ExpandProperty SMBIOSBIOSVersion"
            )
            info["bios_version"] = bios or "—"
        except Exception:
            pass
        self.finished_info.emit(info)
