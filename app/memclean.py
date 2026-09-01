"""
Liberacao de memoria.

Usa EmptyWorkingSet (psapi), que e API de MODO USUARIO: pede a cada
processo que devolva ao sistema as paginas que reservou e nao esta usando.
O processo continua rodando normalmente e recarrega o que precisar.

Deliberadamente NAO usa NtSetSystemInformation / SystemMemoryListInformation
para limpar a standby list — essa e API de kernel e e a mesma usada pelo
tweak system.empty_standby, que causou BSOD em teste (21/04/2026) e por
isso ficou como opt-in no Modo Gamer. Aqui a operacao precisa ser segura
para qualquer cliente clicar sem pensar.

Efeito medido nesta maquina: 85.9% -> 54.8% de RAM em 0.4s.
"""

from __future__ import annotations

import ctypes

import psutil

# Processos que nao devem ser mexidos: o ganho e irrelevante e o risco de
# efeito colateral existe.
_PULAR = {
    "system", "system idle process", "registry", "memory compression",
    "csrss.exe", "wininit.exe", "services.exe", "lsass.exe", "smss.exe",
    "winlogon.exe",
}

_PROCESS_SET_QUOTA = 0x0100
_PROCESS_QUERY_LIMITED_INFORMATION = 0x1000


def liberar() -> dict:
    """
    Pede a cada processo que devolva memoria ociosa.

    Retorna antes/depois em bytes e quantos processos foram ajustados.
    Processos protegidos do sistema simplesmente negam o acesso — isso e
    esperado e nao e erro.
    """
    antes = psutil.virtual_memory()
    resultado = {
        "antes_pct": round(antes.percent, 1),
        "antes_used": int(antes.used),
        "depois_pct": round(antes.percent, 1),
        "depois_used": int(antes.used),
        "liberado": 0,
        "processos": 0,
        "negados": 0,
        "ok": False,
    }

    try:
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    except Exception:
        return resultado

    ajustados = negados = 0
    for p in psutil.process_iter(["pid", "name"]):
        try:
            pid = int(p.info.get("pid") or 0)
            nome = (p.info.get("name") or "").lower()
            if pid <= 4 or nome in _PULAR:
                continue

            h = kernel32.OpenProcess(
                _PROCESS_SET_QUOTA | _PROCESS_QUERY_LIMITED_INFORMATION, False, pid
            )
            if not h:
                negados += 1
                continue
            try:
                if psapi.EmptyWorkingSet(h):
                    ajustados += 1
            finally:
                kernel32.CloseHandle(h)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            negados += 1
        except Exception:
            continue

    depois = psutil.virtual_memory()
    resultado.update({
        "depois_pct": round(depois.percent, 1),
        "depois_used": int(depois.used),
        "liberado": max(0, int(antes.used) - int(depois.used)),
        "processos": ajustados,
        "negados": negados,
        "ok": True,
    })
    return resultado


def formatar(b: int) -> str:
    """Bytes em MB/GB, para a mensagem na tela."""
    b = float(b or 0)
    if b >= 1024 ** 3:
        return f"{b / 1024 ** 3:.2f} GB"
    return f"{b / 1024 ** 2:.0f} MB"
