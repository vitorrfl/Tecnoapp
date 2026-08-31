"""
Deteccao de jogos em execucao e ajuste de prioridade.

O MMCSS que ja existe e generico: pede ao Windows que priorize "jogos" de
forma abstrata. Aqui o alvo e concreto — o processo do jogo que esta
rodando agora recebe prioridade ACIMA_DO_NORMAL/ALTA.

NUNCA usa REALTIME: nessa classe o processo compete com drivers de
entrada, audio e disco, e um jogo que trave leva o sistema inteiro junto.
ALTA ja entrega o ganho sem esse risco.
"""

from __future__ import annotations

import os

import psutil

# Classes de prioridade oferecidas. Realtime fica de fora de proposito.
PRIORITY_NORMAL = "normal"
PRIORITY_ABOVE = "above_normal"
PRIORITY_HIGH = "high"

_PRIORITY_MAP = {
    PRIORITY_NORMAL: psutil.NORMAL_PRIORITY_CLASS,
    PRIORITY_ABOVE: psutil.ABOVE_NORMAL_PRIORITY_CLASS,
    PRIORITY_HIGH: psutil.HIGH_PRIORITY_CLASS,
}

_PRIORITY_LABEL = {
    psutil.IDLE_PRIORITY_CLASS: "Muito baixa",
    psutil.BELOW_NORMAL_PRIORITY_CLASS: "Abaixo do normal",
    psutil.NORMAL_PRIORITY_CLASS: "Normal",
    psutil.ABOVE_NORMAL_PRIORITY_CLASS: "Acima do normal",
    psutil.HIGH_PRIORITY_CLASS: "Alta",
    psutil.REALTIME_PRIORITY_CLASS: "Tempo real",
}

# Launchers e apps que NAO sao o jogo em si — nao devem ser sugeridos.
_NOT_GAMES = {
    "steam.exe", "steamwebhelper.exe", "epicgameslauncher.exe",
    "battle.net.exe", "riotclientservices.exe", "eadesktop.exe",
    "ubisoftconnect.exe", "upc.exe", "galaxyclient.exe",
    "discord.exe", "spotify.exe", "chrome.exe", "msedge.exe",
    "firefox.exe", "explorer.exe", "code.exe", "obs64.exe",
    "nvcontainer.exe", "radeonsoftware.exe", "python.exe",
    "tecnoapp.exe", "svchost.exe", "dwm.exe",
    "msmpeng.exe", "claude.exe", "whatsapp.exe", "whatsapp.root.exe",
}

# Pastas de bibliotecas de jogos. WindowsApps NAO entra: e onde vivem
# todos os apps UWP do sistema, entao marcaria WhatsApp e Calculadora
# como jogo.
SEP = chr(92)  # barra invertida, sem escapes no fonte

_GAME_HINTS = (
    "steamapps", "steamlibrary", "epic games", "gog galaxy",
    "riot games", "battle.net", "origin games", "ea games",
    "ubisoft game launcher", "xboxgames", SEP + "games" + SEP,
)

# Servicos e utilitarios que aparecem por consumo mas nunca sao jogos.
_NEVER_GAME_HINTS = (
    SEP + "windows" + SEP, SEP + "system32" + SEP,
    SEP + "windowsapps" + SEP + "microsoft.",
    SEP + "microsoft" + SEP + "edge", SEP + "microsoft office",
    SEP + "intel" + SEP, SEP + "nvidia corporation" + SEP,
    SEP + "amd" + SEP, SEP + "realtek",
    "service.exe", "-svc.exe",
)


def _is_game_path(path: str) -> bool:
    low = (path or "").lower()
    if any(h in low for h in _NEVER_GAME_HINTS):
        return False
    return any(h in low for h in _GAME_HINTS)


def find_by_names(names: list[str]) -> list[dict]:
    """
    Processos com os nomes dados, ignorando as heuristicas.

    list_candidates() filtra launchers e servicos para nao poluir a
    sugestao, mas um alvo que o usuario escolheu tem de ser sempre
    encontrado — senao o tweak diz "nao esta em execucao" para um jogo
    que esta rodando.
    """
    alvos = {str(n).lower() for n in (names or [])}
    if not alvos:
        return []

    out: list[dict] = []
    for p in psutil.process_iter(["pid", "name", "memory_info"]):
        try:
            nome = (p.info.get("name") or "").strip()
            if nome.lower() not in alvos:
                continue
            mem = p.info.get("memory_info")
            try:
                nice = p.nice()
            except Exception:
                nice = None
            out.append({
                "pid": int(p.info.get("pid") or 0),
                "name": nome,
                "exe": "",
                "mem_mb": round((mem.rss if mem else 0) / (1024 * 1024)),
                "likely_game": True,
                "priority": _PRIORITY_LABEL.get(nice, "Normal"),
                "is_boosted": nice in (psutil.ABOVE_NORMAL_PRIORITY_CLASS,
                                       psutil.HIGH_PRIORITY_CLASS),
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
        except Exception:
            continue
    return out


def list_candidates(min_mb: int = 250) -> list[dict]:
    """
    Processos que parecem jogos, ordenados por consumo de memoria.

    Nao ha como saber com certeza o que e um jogo. A heuristica combina:
    estar numa pasta conhecida de jogos, consumir memoria relevante, e nao
    estar na lista de launchers/apps. O usuario confirma na tela — por isso
    ser generoso aqui e melhor que ser restritivo.
    """
    out: list[dict] = []
    for p in psutil.process_iter(["pid", "name", "exe", "memory_info"]):
        try:
            info = p.info
            name = (info.get("name") or "").strip()
            if not name or name.lower() in _NOT_GAMES:
                continue

            mem = info.get("memory_info")
            mb = round((mem.rss if mem else 0) / (1024 * 1024))
            exe = info.get("exe") or ""

            low_exe = (exe or "").lower()
            if any(h in low_exe for h in _NEVER_GAME_HINTS):
                continue

            provavel = _is_game_path(exe)
            if not provavel and mb < min_mb:
                continue

            try:
                nice = p.nice()
            except Exception:
                nice = None

            out.append({
                "pid": int(info.get("pid") or 0),
                "name": name,
                "exe": exe,
                "mem_mb": mb,
                "likely_game": provavel,
                "priority": _PRIORITY_LABEL.get(nice, "Normal"),
                "is_boosted": nice in (psutil.ABOVE_NORMAL_PRIORITY_CLASS,
                                       psutil.HIGH_PRIORITY_CLASS),
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
        except Exception:
            continue

    # Jogos provaveis primeiro, depois por memoria
    out.sort(key=lambda x: (not x["likely_game"], -x["mem_mb"]))
    return out[:25]


def set_priority(pid: int, level: str = PRIORITY_HIGH) -> tuple[bool, str]:
    """
    Ajusta a prioridade de um processo.

    Retorna (ok, mensagem). Recusa niveis fora do mapa — em especial
    REALTIME, que nao e oferecido.
    """
    klass = _PRIORITY_MAP.get(level)
    if klass is None:
        return False, "nivel de prioridade invalido"
    try:
        p = psutil.Process(int(pid))
        anterior = _PRIORITY_LABEL.get(p.nice(), "Normal")
        p.nice(klass)
        return True, f"{anterior} -> {_PRIORITY_LABEL.get(klass, level)}"
    except psutil.NoSuchProcess:
        return False, "processo nao esta mais em execucao"
    except psutil.AccessDenied:
        return False, "acesso negado (processo protegido)"
    except Exception as e:
        return False, type(e).__name__


def get_priority(pid: int) -> str | None:
    try:
        return _PRIORITY_LABEL.get(psutil.Process(int(pid)).nice())
    except Exception:
        return None


def restore_priority(pid: int) -> tuple[bool, str]:
    """Volta o processo para prioridade Normal."""
    return set_priority(pid, PRIORITY_NORMAL)


def list_all_processes(min_mb: int = 5) -> list[dict]:
    """
    Todos os processos com janela ou consumo relevante.

    A deteccao heuristica pode nao achar o jogo. Em vez de pedir para o
    usuario digitar o nome do executavel — que quase ninguem sabe e nao da
    para validar — esta lista mostra tudo e ele escolhe.

    Agrupa por nome: um jogo abre varios processos filhos, e listar 12
    linhas de chrome.exe nao ajuda ninguem.
    """
    agrupado: dict[str, dict] = {}

    for p in psutil.process_iter(["pid", "name", "exe", "memory_info"]):
        try:
            info = p.info
            nome = (info.get("name") or "").strip()
            if not nome:
                continue

            mem = info.get("memory_info")
            mb = (mem.rss if mem else 0) / (1024 * 1024)
            exe = info.get("exe") or ""

            item = agrupado.get(nome)
            if item is None:
                try:
                    nice = p.nice()
                except Exception:
                    nice = None
                agrupado[nome] = {
                    "pid": int(info.get("pid") or 0),
                    "name": nome,
                    "exe": exe,
                    "mem_mb": round(mb),
                    "instances": 1,
                    "likely_game": _is_game_path(exe),
                    "priority": _PRIORITY_LABEL.get(nice, "Normal"),
                    "is_boosted": nice in (psutil.ABOVE_NORMAL_PRIORITY_CLASS,
                                           psutil.HIGH_PRIORITY_CLASS),
                    "is_system": any(h in (exe or "").lower()
                                     for h in _NEVER_GAME_HINTS),
                }
            else:
                item["mem_mb"] = round(item["mem_mb"] + mb)
                item["instances"] += 1
                if not item["exe"] and exe:
                    item["exe"] = exe
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
        except Exception:
            continue

    itens = [v for v in agrupado.values() if v["mem_mb"] >= min_mb]
    # Provaveis jogos primeiro, depois nao-sistema, depois por memoria
    itens.sort(key=lambda x: (not x["likely_game"], x["is_system"], -x["mem_mb"]))
    return itens
