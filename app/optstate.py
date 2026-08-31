"""
Deteccao do estado real das otimizacoes.

A tela mostrava "3 de 4 aplicadas" contando o que estava MARCADO, nao o
que estava de fato ativo no sistema. Sem isso o usuario podia reaplicar
indefinidamente sem nenhum retorno visual.

Cada checagem consulta o Windows diretamente, entao o estado continua
correto mesmo se algo mudar por fora do app.

disk_optimize e a excecao: e uma operacao de manutencao (TRIM/defrag),
nao um tweak persistente — nao ha "estado ligado" para consultar.
"""

from __future__ import annotations

import subprocess
import winreg

_NO_WINDOW = subprocess.CREATE_NO_WINDOW
_ULTIMATE_GUID = "e9a42b02-d5df-448d-aa00-03f14749eb61"


def _run(cmd: str, timeout: int = 15) -> tuple[bool, str]:
    """
    Roda um comando e devolve stdout normalizado.

    Le como bytes e decodifica pela codepage OEM do console: powercfg e sc
    imprimem em cp850/cp1252, nao UTF-8, e com encoding='utf-8' os acentos
    viravam � — o que quebrava qualquer comparacao por nome.
    """
    try:
        r = subprocess.run(
            cmd, shell=True, capture_output=True, timeout=timeout,
            creationflags=_NO_WINDOW,
        )
        raw = r.stdout or b""
        for enc in ("cp850", "cp1252", "utf-8"):
            try:
                return r.returncode == 0, raw.decode(enc)
            except UnicodeDecodeError:
                continue
        return r.returncode == 0, raw.decode("utf-8", "replace")
    except Exception:
        return False, ""


def _sem_acento(txt: str) -> str:
    """Remove acentos para comparar nomes localizados de forma estavel."""
    import unicodedata
    return "".join(
        c for c in unicodedata.normalize("NFD", txt)
        if unicodedata.category(c) != "Mn"
    )


def power_ultimate_active() -> bool:
    """
    True se o plano ativo for o Ultimate/Desempenho Maximo.

    Nao basta comparar com o GUID de fabrica: `powercfg -duplicatescheme`
    cria uma COPIA com GUID novo, entao o plano ativo raramente e o
    e9a42b02 original. Casa tambem pelo nome, que o powercfg imprime
    localizado.
    """
    ok, out = _run("powercfg /getactivescheme")
    if not ok:
        return False
    low = _sem_acento(out).lower()
    if _ULTIMATE_GUID.lower() in low:
        return True
    return "ultimate performance" in low or "desempenho maximo" in low


def hibernate_off() -> bool:
    """
    True se a hibernacao estiver desligada.

    Checa a ausencia/tamanho de hiberfil.sys via registro: HibernateEnabled
    em Power e o que powercfg -h alterna.
    """
    try:
        k = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SYSTEM\CurrentControlSet\Control\Power",
        )
        try:
            v, _ = winreg.QueryValueEx(k, "HibernateEnabled")
            return int(v) == 0
        finally:
            k.Close()
    except OSError:
        return False


def telemetry_off() -> bool:
    """True se DiagTrack estiver desabilitado."""
    ok, out = _run('sc qc DiagTrack')
    if not ok:
        return False
    low = _sem_acento(out).lower()
    # START_TYPE 4 = DISABLED: o numero e estavel, o rotulo e localizado
    return "4" in low and ("disabled" in low or "desativado" in low)


def get_states() -> dict:
    """
    Estado real de cada otimizacao.

    Retorna {id: True/False/None}; None significa "nao aplicavel" — o
    caso do disk_optimize, que e manutencao pontual e nao um estado.
    """
    states: dict[str, object] = {}
    try:
        states["power_ultimate"] = power_ultimate_active()
    except Exception:
        states["power_ultimate"] = False
    try:
        states["hibernate_off"] = hibernate_off()
    except Exception:
        states["hibernate_off"] = False
    try:
        # o id em _OPTIMIZE_CATEGORIES e telemetry_disable
        states["telemetry_disable"] = telemetry_off()
    except Exception:
        states["telemetry_disable"] = False

    states["disk_optimize"] = None
    return states
