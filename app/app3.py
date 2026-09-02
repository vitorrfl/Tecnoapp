import sys
import os
import re
import json
import subprocess
import ctypes
from datetime import datetime
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QMessageBox,
                             QHBoxLayout, QPushButton, QLabel, QFrame, QGraphicsDropShadowEffect,
                             QCheckBox, QScrollArea, QGridLayout, QSizePolicy, QProgressBar)
from PySide6.QtGui import QFont, QColor, QCursor, QPainter, QPen, QBrush, QIcon, QPixmap
from PySide6.QtCore import Qt, QTimer, QThread, Signal, QSize
import shiboken6

from gamer import build_engine, load_enabled_optins, save_enabled_optins
from gamer.tweaks import Category
from version import APP_VERSION
from ui import (
    Card, HeroCard, MetricLabel, Chip, ResponsiveCardRow,
    Palette, Spacing, GLOBAL_STYLESHEET,
    SidebarButton, SidebarRestoreButton, SidebarExitButton, GamerSidebarButton,
)
from ui.icons import lucide_pixmap
from system_info import (
    os_info, cpu_static, cpu_pct, mem_live, disk_c_info, disks_info,
    processes_count, uptime_seconds, format_uptime, top_processes,
    HardwareInfoWorker,
)

_CLEAN_CATEGORIES = [
    {
        "id": "temp_user",
        "label": "Temporários do Usuário (%TEMP%)",
        "desc": "Arquivos criados por programas durante o uso — jogos, editores, browsers. "
                "Nunca são reusados após a execução.",
        "impact": "~100 MB – 2 GB",
        "default": True,
        "warning": "",
    },
    {
        "id": "temp_windows",
        "label": "Temporários do Windows",
        "desc": "Arquivos criados pelo sistema operacional para operações internas. "
                "Acumulam após instalações e atualizações.",
        "impact": "~50 MB – 500 MB",
        "default": True,
        "warning": "",
    },
    {
        "id": "prefetch",
        "label": "Prefetch do Windows",
        "desc": "Cache que acelera a abertura de programas. Após limpar, a primeira "
                "abertura de cada programa fica levemente mais lenta — isso é normal.",
        "impact": "~20 MB – 200 MB",
        "default": True,
        "warning": "",
    },
    {
        "id": "dns_cache",
        "label": "Cache DNS (Endereços de Sites)",
        "desc": "Tabela local de endereços de sites visitados. Limpar resolve problemas "
                "de conexão e sites que não abrem corretamente.",
        "impact": "Desprezível",
        "default": True,
        "warning": "",
    },
    {
        "id": "recycle_bin",
        "label": "Lixeira",
        "desc": "Arquivos que você deletou mas estão reservados na Lixeira. "
                "Esvaziar é permanente.",
        "impact": "Varia (pode ser GBs)",
        "default": True,
        "warning": "Não é possível recuperar arquivos após esvaziar.",
    },
    {
        "id": "thumbnail_cache",
        "label": "Cache de Miniaturas (Fotos/Vídeos)",
        "desc": "Pré-visualizações de imagens criadas pelo Windows Explorer. "
                "São recriadas automaticamente na próxima abertura da pasta.",
        "impact": "~50 MB – 300 MB",
        "default": True,
        "warning": "",
    },
    {
        "id": "update_cache",
        "label": "Cache do Windows Update",
        "desc": "Arquivos usados para instalar atualizações já concluídas. "
                "O Windows baixa novamente se precisar reinstalar.",
        "impact": "~200 MB – 5 GB",
        "default": False,
        "warning": "O Windows pode baixar esses arquivos novamente automaticamente se precisar.",
    },
    {
        "id": "event_logs",
        "label": "Logs de Eventos do Windows",
        "desc": "Histórico de atividades, erros e avisos do sistema. "
                "Técnicos usam para diagnosticar problemas.",
        "impact": "~10 MB – 100 MB",
        "default": False,
        "warning": "Apaga o histórico de erros — pode dificultar diagnóstico de problemas futuros.",
    },
    {
        "id": "minidumps",
        "label": "Relatórios de Travamento (Minidumps)",
        "desc": "Arquivos gerados automaticamente quando o Windows ou um programa trava. "
                "Técnicos usam esses arquivos para descobrir a causa do crash.",
        "impact": "~10 MB – 100 MB",
        "default": False,
        "warning": "Remove informações úteis para diagnosticar travamentos e BSODs futuros.",
    },
]

# ═══════════════════════════════════════════════════════════════════════
# OTIMIZAÇÃO — tweaks persistentes de sistema
# ═══════════════════════════════════════════════════════════════════════
_OPTIMIZE_CATEGORIES = [
    {
        "id": "power_ultimate",
        "label": "Plano de Energia: Desempenho Máximo",
        "desc": "Ativa o plano oculto 'Ultimate Performance' do Windows, mais agressivo que "
                "'Alto Desempenho'. Ideal para desktops ou notebooks na tomada.",
        "impact": "Responsividade da CPU",
        "default": True,
        "reboot": False,
        "warning": "",
    },
    {
        "id": "disk_optimize",
        "label": "Otimizar Disco (TRIM ou Defrag automático)",
        "desc": "Detecta automaticamente o tipo de disco: TRIM para SSD (mantém performance "
                "ao longo do tempo) ou desfragmentação para HDD.",
        "impact": "Saúde do disco",
        "default": True,
        "reboot": False,
        "warning": "",
    },
    {
        "id": "hibernate_off",
        "label": "Desativar Hibernação (libera espaço em C:)",
        "desc": "Apaga o arquivo hiberfil.sys, que ocupa o tamanho aproximado da RAM. "
                "O computador ainda poderá suspender, mas não hibernar.",
        "impact": "4 GB – 16 GB em disco",
        "default": False,
        "reboot": False,
        "warning": "Em notebooks, hibernação permite retomar após bateria esgotar. Suspender continua funcionando.",
    },
    {
        "id": "telemetry_disable",
        "label": "Desativar Telemetria do Windows",
        "desc": "Para e desabilita os serviços DiagTrack e dmwappushservice (rastreamento e "
                "coleta de uso). Reduz CPU e rede em background.",
        "impact": "CPU/rede em background",
        "default": False,
        "reboot": False,
        "warning": "Pode ser revertido em 'Restaurar padrões'. Alguns recursos de diagnóstico da Microsoft ficam limitados.",
    },
]

# ═══════════════════════════════════════════════════════════════════════
# REPAROS — ferramentas individuais de diagnóstico/restauração
# ═══════════════════════════════════════════════════════════════════════
_REPAIR_TOOLS = [
    {
        "id": "sfc_dism",
        "label": "Reparar Arquivos do Sistema (DISM + SFC)",
        "desc": "Executa DISM para reparar o repositório de componentes, seguido de SFC para "
                "validar e restaurar arquivos corrompidos do Windows. Ordem correta: DISM → SFC.",
        "duration": "~30 – 50 min",
        "reboot": False,
        "warning": "Não desligue o computador durante o processo. A porcentagem pode parecer travada — é normal.",
        "category": "essential",
    },
    {
        "id": "network_reset",
        "label": "Reparar Conexão de Rede",
        "desc": "Reset completo: Winsock, pilha TCP/IP, liberação/renovação de IP e flush de DNS. "
                "Corrige erros de conexão, drops e falhas de DHCP.",
        "duration": "~1 min",
        "reboot": True,
        "warning": "Reinicialização é necessária para o Winsock entrar em efeito.",
        "category": "essential",
    },
    {
        "id": "wu_reset",
        "label": "Reparar Windows Update",
        "desc": "Reset completo: para os serviços (wuauserv, cryptSvc, bits, msiserver), "
                "limpa SoftwareDistribution e catroot2, reinicia serviços. Destrava updates corrompidos.",
        "duration": "~3 min",
        "reboot": False,
        "warning": "",
        "category": "essential",
    },
    {
        "id": "store_reset",
        "label": "Reparar Microsoft Store",
        "desc": "Executa wsreset para limpar o cache da Store. Corrige apps UWP que não abrem "
                "(Calculadora, Fotos, Loja etc.).",
        "duration": "~1 min",
        "reboot": False,
        "warning": "Uma janela da Store abrirá ao finalizar — pode fechar normalmente.",
        "category": "advanced",
    },
    {
        "id": "printer_reset",
        "label": "Reparar Fila de Impressão",
        "desc": "Para o spooler de impressão, limpa a fila travada e reinicia o serviço. "
                "Corrige impressões paradas e erros de spooler.",
        "duration": "~1 min",
        "reboot": False,
        "warning": "",
        "category": "advanced",
    },
    {
        "id": "explorer_restart",
        "label": "Reiniciar o Explorer",
        "desc": "Encerra e reabre o Windows Explorer. Corrige barra de tarefas travada, "
                "ícones sumidos, menu Iniciar que não abre e áreas da tela congeladas.",
        "duration": "~5 seg",
        "reboot": False,
        "warning": "A tela pisca e a barra de tarefas some por alguns segundos — é normal.",
        "category": "essential",
    },
    {
        "id": "chkdsk",
        "label": "Verificar e Reparar o Disco (ChkDsk)",
        "desc": "Procura e corrige erros no sistema de arquivos e setores defeituosos. "
                "Só roda na próxima inicialização, porque precisa do disco livre de uso.",
        "duration": "AGENDADO — de 20 min a várias horas no próximo boot",
        "reboot": True,
        "warning": "MUITO IMPORTANTE: na próxima vez que ligar o PC, uma tela azul de "
                   "verificação aparecerá e pode ficar PARADA na mesma porcentagem por "
                   "muito tempo. ISSO É NORMAL E NÃO É TRAVAMENTO. Em discos grandes ou "
                   "com defeito pode levar VÁRIAS HORAS. NÃO desligue o computador durante "
                   "o processo — interromper pode corromper o disco. Só use se suspeitar "
                   "de problema físico no disco, e quando puder deixar o PC ligado.",
        "category": "advanced",
    },
]


class GamerWorker(QThread):
    finished = Signal(object, str)

    def __init__(self, engine, action, enabled_optins=None):
        super().__init__()
        self.engine = engine
        self.action = action
        self.enabled_optins = enabled_optins or set()

    def run(self):
        if self.action == "activate":
            report = self.engine.activate(enabled_optins=self.enabled_optins)
        else:
            report = self.engine.deactivate()
        self.finished.emit(report, self.action)


class CleanWorker(QThread):
    step_done   = Signal(str, int)  # (label, bytes_freed)
    calculating = Signal()           # emitido antes do snapshot final
    finished    = Signal(int)        # total bytes freed

    _STEPS = [
        ("temp_user",       "Temporários do usuário",
         ['del /s /f /q "%TEMP%\\*.*"'], []),
        ("temp_windows",    "Temporários do Windows",
         ['del /s /f /q "C:\\Windows\\Temp\\*.*"'], []),
        ("prefetch",        "Prefetch do Windows",
         ['del /s /f /q "C:\\Windows\\Prefetch\\*.*"'], []),
        ("dns_cache",       "Cache DNS",
         ["ipconfig /flushdns"], []),
        ("recycle_bin",     "Lixeira",
         [], ["Clear-RecycleBin -Force -ErrorAction SilentlyContinue"]),
        ("thumbnail_cache", "Cache de miniaturas",
         ['del /f /q "%LocalAppData%\\Microsoft\\Windows\\Explorer\\thumbcache_*.db"'], []),
        # Sem parar o serviço — Remove-Item tenta deletar o que não estiver bloqueado
        ("update_cache",    "Cache do Windows Update",
         [], ["Get-ChildItem 'C:\\Windows\\SoftwareDistribution\\Download' "
              "-ErrorAction SilentlyContinue | "
              "Remove-Item -Force -Recurse -ErrorAction SilentlyContinue"]),
        # Security omitido: requer SeAuditPrivilege além de admin
        ("event_logs",      "Logs de eventos",
         [], ['wevtutil cl "System" 2>$null',
              'wevtutil cl "Application" 2>$null',
              'wevtutil cl "Setup" 2>$null']),
        ("minidumps",       "Relatórios de travamento",
         ['del /s /f /q "C:\\Windows\\Minidump\\*.*"'], []),
    ]

    def __init__(self, selected_ids: set):
        super().__init__()
        self.selected_ids = selected_ids

    def _free_bytes(self) -> int:
        free = ctypes.c_ulonglong(0)
        ctypes.windll.kernel32.GetDiskFreeSpaceExW(
            ctypes.c_wchar_p("C:\\"), None, None, ctypes.pointer(free)
        )
        return free.value

    def run(self):
        try:
            space_before = self._free_bytes()
            for step_id, label, shell_cmds, ps_cmds in self._STEPS:
                if step_id not in self.selected_ids:
                    continue
                before = self._free_bytes()
                try:
                    if shell_cmds:
                        subprocess.run(
                            " & ".join(shell_cmds),
                            shell=True,
                            creationflags=subprocess.CREATE_NO_WINDOW,
                            timeout=120,
                        )
                    if ps_cmds:
                        subprocess.run(
                            ["powershell", "-NoProfile", "-NonInteractive", "-Command",
                             "; ".join(ps_cmds)],
                            creationflags=subprocess.CREATE_NO_WINDOW,
                            timeout=120,
                        )
                except Exception:
                    pass
                try:
                    freed = max(0, self._free_bytes() - before)
                except Exception:
                    freed = 0
                self.step_done.emit(label, freed)
            self.calculating.emit()
            self.msleep(700)   # aguarda NTFS propagar os deletes
            try:
                total = max(0, self._free_bytes() - space_before)
            except Exception:
                total = 0
        except Exception:
            total = 0
        self.finished.emit(total)


_OPTIMIZE_STATE_FILE = os.path.join(
    os.environ.get("LOCALAPPDATA", os.environ.get("TEMP", ".")),
    "TecnoApp", "optimize_state.json"
)
_CLEAN_STATE_FILE = os.path.join(
    os.environ.get("LOCALAPPDATA", os.environ.get("TEMP", ".")),
    "TecnoApp", "clean_state.json"
)
_STATUS_FILE = os.path.join(
    os.environ.get("LOCALAPPDATA", os.environ.get("TEMP", ".")),
    "TecnoApp", "module_status.json"
)

def _load_optimize_state() -> dict:
    try:
        with open(_OPTIMIZE_STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}

def _save_optimize_state(state: dict) -> bool:
    try:
        os.makedirs(os.path.dirname(_OPTIMIZE_STATE_FILE), exist_ok=True)
        with open(_OPTIMIZE_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False

def _load_clean_state() -> dict:
    try:
        with open(_CLEAN_STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}

def _save_clean_state(state: dict) -> bool:
    try:
        os.makedirs(os.path.dirname(_CLEAN_STATE_FILE), exist_ok=True)
        with open(_CLEAN_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


_MODULE_LABELS = {
    "clean":    "limpeza",
    "optimize": "otimização",
    "repair":   "reparo",
    "gamer":    "ativação do Modo Gamer",
}

def _load_module_statuses() -> dict:
    try:
        with open(_STATUS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}

def _save_module_status(module: str, message: str) -> None:
    statuses = _load_module_statuses()
    statuses[module] = {
        "message": message,
        "timestamp": datetime.now().strftime("%d/%m/%Y às %H:%M"),
    }
    try:
        os.makedirs(os.path.dirname(_STATUS_FILE), exist_ok=True)
        with open(_STATUS_FILE, "w", encoding="utf-8") as f:
            json.dump(statuses, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def _get_module_status(module: str) -> str:
    """Retorna string formatada com timestamp, ou '' se não houver histórico."""
    entry = _load_module_statuses().get(module)
    if not isinstance(entry, dict):
        return ""
    message = entry.get("message")
    timestamp = entry.get("timestamp")
    if not (isinstance(message, str) and isinstance(timestamp, str) and message and timestamp):
        return ""
    label = _MODULE_LABELS.get(module, module)
    return f"> Última {label}: {timestamp} — {message}"


class OptimizeWorker(QThread):
    step_done = Signal(str, bool, str)   # (label, ok, detail)
    finished  = Signal(int, int)          # (applied, failed)

    # GUIDs oficiais de planos de energia
    _ULTIMATE_PERFORMANCE = "e9a42b02-d5df-448d-aa00-03f14749eb61"
    _BALANCED            = "381b4222-f694-41f0-9685-ff5bb260df2e"

    def __init__(self, selected_ids: set, mode: str = "apply"):
        super().__init__()
        self.selected_ids = selected_ids
        self.mode = mode   # "apply" ou "revert"

    def _run_shell(self, cmd: str, timeout: int = 120) -> tuple[bool, str]:
        try:
            r = subprocess.run(
                cmd, shell=True, capture_output=True,
                encoding="cp850", errors="replace",
                creationflags=subprocess.CREATE_NO_WINDOW, timeout=timeout,
            )
            return (r.returncode == 0, (r.stdout or r.stderr or "").strip())
        except subprocess.TimeoutExpired:
            return (False, "Tempo limite excedido")
        except Exception as e:
            return (False, str(e))

    def _run_ps(self, cmd: str, timeout: int = 120) -> tuple[bool, str]:
        try:
            r = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command",
                 f"[Console]::OutputEncoding=[System.Text.Encoding]::UTF8; {cmd}"],
                capture_output=True,
                encoding="utf-8", errors="replace",
                creationflags=subprocess.CREATE_NO_WINDOW, timeout=timeout,
            )
            return (r.returncode == 0, (r.stdout or r.stderr or "").strip())
        except subprocess.TimeoutExpired:
            return (False, "Tempo limite excedido")
        except Exception as e:
            return (False, str(e))

    # ─── Helpers de plano de energia ────────────────────────────────
    def _get_active_plan(self) -> tuple[str, str]:
        """Retorna (guid, nome) do plano ativo. Strings vazias se falhar."""
        ok, out = self._run_shell("powercfg /getactivescheme")
        if not ok or not out:
            return ("", "")
        m = re.search(r"([0-9a-fA-F\-]{36})\s*\(([^)]+)\)", out)
        if m:
            return (m.group(1).lower(), m.group(2).strip())
        return ("", "")

    def _list_plans(self) -> list[tuple[str, str]]:
        """Lista todos os planos disponíveis como (guid, nome)."""
        ok, out = self._run_shell("powercfg /list")
        if not ok:
            return []
        plans = []
        for line in out.splitlines():
            m = re.search(r"([0-9a-fA-F\-]{36})\s*\(([^)]+)\)", line)
            if m:
                plans.append((m.group(1).lower(), m.group(2).strip()))
        return plans

    def _find_ultimate_guid(self) -> str | None:
        """Procura pelo Ultimate Performance já instalado na máquina."""
        for guid, name in self._list_plans():
            ln = name.lower()
            if ("desempenho máximo" in ln
                or "desempenho maximo" in ln
                or "ultimate performance" in ln
                or guid == self._ULTIMATE_PERFORMANCE):
                return guid
        return None

    def _create_ultimate_plan(self) -> str | None:
        """Duplica o master Ultimate e captura o novo GUID gerado."""
        ok, out = self._run_shell(f"powercfg -duplicatescheme {self._ULTIMATE_PERFORMANCE}")
        if not ok:
            return None
        m = re.search(r"([0-9a-fA-F\-]{36})", out)
        return m.group(1).lower() if m else None

    def _detect_disk_type(self) -> str:
        ok, out = self._run_ps(
            "(Get-PhysicalDisk | Where-Object DeviceID -eq 0).MediaType"
        )
        if ok and out:
            t = out.strip().upper()
            if "SSD" in t: return "SSD"
            if "HDD" in t: return "HDD"
        return "Desconhecido"

    def _apply(self, step_id: str) -> tuple[bool, str]:
        if step_id == "power_ultimate":
            current_guid, current_name = self._get_active_plan()

            existing = self._find_ultimate_guid()
            if existing:
                target_guid = existing
                source = "existente"
            else:
                target_guid = self._create_ultimate_plan()
                source = "criado"
                if not target_guid:
                    atual = current_name or "desconhecido"
                    return (False, f"Falha ao criar plano Desempenho Máximo (atual: {atual})")

            # Já está ativo — nada a fazer
            if current_guid and current_guid == target_guid:
                return (True, f"Já ativo: Desempenho Máximo (plano {source})")

            # Salva plano anterior para reversão futura
            if current_guid:
                state = _load_optimize_state()
                state["previous_power_plan"] = {"guid": current_guid, "name": current_name}
                _save_optimize_state(state)

            ok, _ = self._run_shell(f"powercfg /setactive {target_guid}")
            if ok:
                prev = f"Anterior: {current_name} → " if current_name else ""
                return (True, f"{prev}Desempenho Máximo ativado ({source})")
            atual = current_name or "desconhecido"
            return (False, f"Falha ao ativar plano (atual: {atual})")

        if step_id == "disk_optimize":
            disk_type = self._detect_disk_type()
            ok, _ = self._run_shell("defrag C: /O", timeout=1800)
            detail = f"Disco: {disk_type} — otimização concluída"
            return (ok, detail if ok else "Falha na otimização do disco")

        if step_id == "hibernate_off":
            ok, _ = self._run_shell("powercfg -h off")
            return (ok, "Hibernação desativada (hiberfil.sys removido)" if ok else "Falha")

        if step_id == "telemetry_disable":
            # Para e desabilita os dois serviços
            self._run_shell("sc stop DiagTrack")
            self._run_shell("sc config DiagTrack start= disabled")
            self._run_shell("sc stop dmwappushservice")
            self._run_shell("sc config dmwappushservice start= disabled")
            return (True, "Telemetria desativada (DiagTrack + dmwappushservice)")

        return (False, "Desconhecido")

    def _revert(self, step_id: str) -> tuple[bool, str]:
        if step_id == "power_ultimate":
            current_guid, current_name = self._get_active_plan()
            state = _load_optimize_state()
            prev = state.get("previous_power_plan") or {}
            prev_guid = (prev.get("guid") or "").lower()
            prev_name = prev.get("name") or "anterior"

            if prev_guid:
                if current_guid == prev_guid:
                    state.pop("previous_power_plan", None)
                    _save_optimize_state(state)
                    return (True, f"Já ativo: {prev_name}")

                # Confirma que o GUID salvo ainda existe
                available = {g for g, _ in self._list_plans()}
                if prev_guid in available:
                    ok, _ = self._run_shell(f"powercfg /setactive {prev_guid}")
                    if ok:
                        state.pop("previous_power_plan", None)
                        _save_optimize_state(state)
                        return (True, f"Restaurado para: {prev_name}")
                    return (False, f"Falha ao restaurar {prev_name}")

                # Fallback: plano salvo sumiu
                ok, _ = self._run_shell(f"powercfg /setactive {self._BALANCED}")
                if ok:
                    state.pop("previous_power_plan", None)
                    _save_optimize_state(state)
                return (ok, "Plano salvo indisponível — revertido para Balanceado"
                        if ok else "Falha ao reverter")

            # Sem histórico
            if current_guid == self._BALANCED:
                return (True, "Já ativo: Balanceado")
            ok, _ = self._run_shell(f"powercfg /setactive {self._BALANCED}")
            return (ok, "Plano restaurado para Balanceado (sem histórico)"
                    if ok else "Falha ao reverter")

        if step_id == "disk_optimize":
            return (True, "Sem reversão necessária (operação de manutenção)")

        if step_id == "hibernate_off":
            ok, _ = self._run_shell("powercfg -h on")
            return (ok, "Hibernação reativada" if ok else "Falha")

        if step_id == "telemetry_disable":
            self._run_shell("sc config DiagTrack start= auto")
            self._run_shell("sc start DiagTrack")
            self._run_shell("sc config dmwappushservice start= manual")
            return (True, "Telemetria restaurada ao padrão do Windows")

        return (False, "Desconhecido")

    def run(self):
        applied = 0
        failed  = 0
        try:
            for cat in _OPTIMIZE_CATEGORIES:
                if cat["id"] not in self.selected_ids:
                    continue
                try:
                    if self.mode == "apply":
                        ok, detail = self._apply(cat["id"])
                    else:
                        ok, detail = self._revert(cat["id"])
                except Exception as e:
                    ok, detail = (False, str(e))
                if ok:
                    applied += 1
                else:
                    failed += 1
                self.step_done.emit(cat["label"], ok, detail)
        except Exception:
            pass
        self.finished.emit(applied, failed)


class RepairWorker(QThread):
    step_done = Signal(str, bool, str)   # (sub-step label, ok, detail)
    finished  = Signal(bool, str)         # (overall_ok, summary)

    def __init__(self, tool_id: str):
        super().__init__()
        self.tool_id = tool_id

    def _run_shell(self, cmd: str, timeout: int = 180) -> tuple[bool, str]:
        try:
            r = subprocess.run(
                cmd, shell=True, capture_output=True,
                encoding="cp850", errors="replace",
                creationflags=subprocess.CREATE_NO_WINDOW, timeout=timeout,
            )
            return (r.returncode == 0, (r.stdout or r.stderr or "").strip())
        except subprocess.TimeoutExpired:
            return (False, "Tempo limite excedido")
        except Exception as e:
            return (False, str(e))

    def _repair_sfc_dism(self):
        # DISM primeiro (repara o repositório de componentes), depois SFC
        self.step_done.emit("Executando DISM (RestoreHealth)…", True, "Pode levar 20-30 min")
        ok_dism, _ = self._run_shell(
            "DISM.exe /Online /Cleanup-image /Restorehealth", timeout=3600
        )
        self.step_done.emit(
            "DISM concluído" if ok_dism else "DISM falhou",
            ok_dism,
            "Imagem do Windows reparada" if ok_dism else "Verifique conexão com Windows Update",
        )

        self.step_done.emit("Executando SFC (scannow)…", True, "Pode levar 10-20 min")
        ok_sfc, _ = self._run_shell("sfc /scannow", timeout=3600)
        self.step_done.emit(
            "SFC concluído" if ok_sfc else "SFC falhou",
            ok_sfc,
            "Arquivos de sistema validados" if ok_sfc else "Alguns arquivos podem não ter sido reparados",
        )

        overall = ok_dism and ok_sfc
        summary = "Reparo do sistema concluído com sucesso." if overall else \
                  "Reparo concluído com alertas. Reinicie e execute novamente se necessário."
        self.finished.emit(overall, summary)

    def _repair_network(self):
        steps = [
            ("Resetando Winsock",         "netsh winsock reset"),
            ("Resetando pilha TCP/IP",    "netsh int ip reset"),
            ("Liberando IP",              "ipconfig /release"),
            ("Renovando IP",              "ipconfig /renew"),
            ("Limpando cache DNS",        "ipconfig /flushdns"),
        ]
        any_fail = False
        for label, cmd in steps:
            ok, detail = self._run_shell(cmd, timeout=60)
            self.step_done.emit(label, ok, detail[:80] if detail else ("OK" if ok else "Falha"))
            if not ok:
                any_fail = True
        overall = not any_fail
        summary = "Rede reparada. Reinicie o computador para efetivar o reset do Winsock." if overall \
                  else "Reparo concluído com alertas. Reinicie e tente novamente se os problemas persistirem."
        self.finished.emit(overall, summary)

    def _repair_windows_update(self):
        # Para serviços
        services = ["wuauserv", "cryptSvc", "bits", "msiserver"]
        for svc in services:
            ok, _ = self._run_shell(f"net stop {svc}", timeout=60)
            self.step_done.emit(f"Parando serviço {svc}", ok, "OK" if ok else "Já parado ou sem permissão")

        # Limpa caches
        self.step_done.emit("Limpando SoftwareDistribution…", True, "")
        ok1, _ = self._run_shell(
            'powershell -NoProfile -Command "Get-ChildItem \'C:\\Windows\\SoftwareDistribution\' '
            '-Recurse -Force -ErrorAction SilentlyContinue | '
            'Remove-Item -Recurse -Force -ErrorAction SilentlyContinue"',
            timeout=180,
        )
        self.step_done.emit("SoftwareDistribution limpo", ok1, "OK" if ok1 else "Alguns arquivos em uso")

        self.step_done.emit("Limpando catroot2…", True, "")
        ok2, _ = self._run_shell(
            'powershell -NoProfile -Command "Get-ChildItem \'C:\\Windows\\System32\\catroot2\' '
            '-Recurse -Force -ErrorAction SilentlyContinue | '
            'Remove-Item -Recurse -Force -ErrorAction SilentlyContinue"',
            timeout=180,
        )
        self.step_done.emit("catroot2 limpo", ok2, "OK" if ok2 else "Alguns arquivos em uso")

        # Reinicia serviços
        for svc in services:
            ok, _ = self._run_shell(f"net start {svc}", timeout=60)
            self.step_done.emit(f"Iniciando serviço {svc}", ok, "OK" if ok else "Falha ao iniciar")

        overall = ok1 and ok2
        summary = "Windows Update reparado. Verifique atualizações novamente." if overall \
                  else "Reparo concluído com alertas — alguns arquivos estavam em uso."
        self.finished.emit(overall, summary)

    def _repair_store(self):
        # wsreset: limpa o cache da Store e abre a janela ao final
        self.step_done.emit("Executando wsreset…", True, "Cache da Microsoft Store será limpo")
        ok, _ = self._run_shell("wsreset.exe", timeout=120)
        self.step_done.emit(
            "wsreset concluído" if ok else "wsreset falhou",
            ok,
            "Uma janela da Store abrirá" if ok else "Falha",
        )
        summary = "Microsoft Store reparada. Uma janela da Store abrirá em seguida." if ok \
                  else "Reparo falhou. Tente novamente."
        self.finished.emit(ok, summary)

    def _repair_explorer(self):
        """Reinicia o Windows Explorer. Corrige shell travado."""
        self.step_done.emit("Encerrando o Explorer", True, "")
        ok1, _ = self._run_shell("taskkill /f /im explorer.exe", timeout=30)

        # O Windows costuma reabrir sozinho; garantimos que volte de todo jeito.
        ok2, det = self._run_shell("start explorer.exe", timeout=30)
        self.step_done.emit("Reabrindo o Explorer", True, "")

        self.finished.emit(True, "Explorer reiniciado.")

    def _repair_chkdsk(self):
        """
        Agenda o ChkDsk para a proxima inicializacao.

        Nao roda com o Windows ativo: /f e /r exigem uso exclusivo do
        volume. O `echo S|` responde ao prompt de agendamento — sem isso o
        comando fica esperando entrada para sempre.
        """
        self.step_done.emit("Agendando verificacao do disco C:", True, "")
        ok, det = self._run_shell("echo S| chkdsk C: /f /r", timeout=120)

        if ok:
            self.step_done.emit(
                "Agendado — a verificacao roda na proxima inicializacao", True, "")
            self.finished.emit(
                True,
                "ChkDsk agendado. Ao reiniciar, a verificacao vai rodar antes do "
                "Windows abrir e PODE PARECER TRAVADA por muito tempo — nao desligue.")
        else:
            self.finished.emit(False, f"Nao foi possivel agendar o ChkDsk. {det}")

    def _repair_printer(self):
        self.step_done.emit("Parando Spooler de Impressão", True, "")
        ok1, _ = self._run_shell("net stop spooler", timeout=60)
        self.step_done.emit("Spooler parado" if ok1 else "Falha ao parar", ok1, "")

        self.step_done.emit("Limpando fila travada", True, "")
        ok2, _ = self._run_shell(
            'del /F /Q /S "C:\\Windows\\System32\\spool\\PRINTERS\\*.*"', timeout=60
        )
        self.step_done.emit("Fila limpa" if ok2 else "Nada a limpar", ok2, "")

        self.step_done.emit("Reiniciando Spooler", True, "")
        ok3, _ = self._run_shell("net start spooler", timeout=60)
        self.step_done.emit("Spooler ativo" if ok3 else "Falha ao iniciar", ok3, "")

        overall = ok3  # o essencial é o serviço estar rodando ao fim
        summary = "Serviço de impressão reiniciado. Tente imprimir novamente." if overall \
                  else "Falha ao reiniciar o serviço. Reinicie o computador."
        self.finished.emit(overall, summary)

    def run(self):
        try:
            if   self.tool_id == "sfc_dism":       self._repair_sfc_dism()
            elif self.tool_id == "network_reset":  self._repair_network()
            elif self.tool_id == "wu_reset":       self._repair_windows_update()
            elif self.tool_id == "store_reset":    self._repair_store()
            elif self.tool_id == "printer_reset":  self._repair_printer()
            elif self.tool_id == "explorer_restart": self._repair_explorer()
            elif self.tool_id == "chkdsk":         self._repair_chkdsk()
            else:
                self.finished.emit(False, "Ferramenta desconhecida.")
        except Exception as e:
            self.finished.emit(False, f"Erro inesperado: {e}")


class ToggleSwitch(QCheckBox):
    """Checkbox estilizado como interruptor on/off. Mantém API do QCheckBox."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(46, 22)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        # Esconde o indicator nativo do QCheckBox — vamos pintar o nosso
        self.setStyleSheet("QCheckBox::indicator { width: 0px; height: 0px; margin: 0px; }")

    def hitButton(self, pos):
        # Garante que o clique em qualquer ponto do widget seja aceito
        return self.rect().contains(pos)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.toggle()
            event.accept()
            return
        super().mousePressEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width() - 1, self.height() - 1

        if self.isChecked():
            bg_color    = QColor(Palette.CYAN)
            border_col  = QColor(Palette.CYAN)
            knob_color  = QColor(Palette.FG_PRIMARY)
            knob_x      = w - 18
        else:
            bg_color    = QColor("#1a1f2b")          # pill off-bg (spec: #1a1f2b)
            border_col  = QColor(Palette.STATE_OFF_BRD)
            knob_color  = QColor(Palette.STATE_OFF)
            knob_x      = 3

        p.setPen(QPen(border_col, 1))
        p.setBrush(QBrush(bg_color))
        p.drawRoundedRect(0, 0, w, h, 11, 11)

        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(knob_color))
        p.drawEllipse(knob_x, 3, 16, 16)


def is_admin():
    try: return ctypes.windll.shell32.IsUserAnAdmin()
    except: return False

class TecnoApp(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Garante que as funções de registro e sistema funcionem
        if not is_admin():
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
            sys.exit()

        # Este e o processo que fica: toma posse da instancia unica.
        # O nao-elevado nao pode segurar o mutex, porque morre na linha
        # acima assim que dispara a elevacao.
        try:
            import singleton
            if not singleton.acquire():
                if not singleton.focus_existing():
                    QMessageBox.information(
                        None, "TecnoApp",
                        "O TecnoApp ja esta aberto.\n\n"
                        "Procure a janela na barra de tarefas."
                    )
                sys.exit(0)
        except SystemExit:
            raise
        except Exception:
            pass

        self.setWindowTitle("Tecnosup · Soluções Digitais")
        self.resize(1100, 720)
        self.setMinimumSize(900, 620)

        # Aliases de token — usados nos f-strings do stylesheet abaixo
        self.primary   = Palette.CYAN
        self.secondary = Palette.PURPLE
        self.danger    = Palette.STATE_DANGER
        self.bg_dark   = Palette.BG_BASE
        self.log_file = os.path.join(os.environ.get('TEMP'), 'tecnosup_clean_log.txt')
        
        self._pending_status: dict = {}
        self._clean_checkboxes: dict = {}
        self._clean_worker: CleanWorker | None = None
        self._clean_log_lines: list = []
        self._clean_calc_timer: QTimer | None = None
        self._optimize_checkboxes: dict = {}
        self._optimize_worker: OptimizeWorker | None = None
        self._optimize_log_lines: list = []
        self._repair_worker: RepairWorker | None = None
        self._repair_log_lines: list = []
        self.gamer_engine = build_engine()
        self._gamer_worker = None

        self.setStyleSheet(f"""
            QMainWindow {{ background-color: {Palette.BG_BASE}; }}
            #Sidebar {{
                background-color: rgba(3, 4, 7, 247);
                border-right: 1px solid rgba(14, 179, 255, 0.10);
            }}
            QLabel {{ color: {Palette.FG_PRIMARY}; background: transparent; }}

            QPushButton#ActionBtn {{
                background-color: {Palette.CYAN}; color: {Palette.BG_BASE};
                font-weight: bold; font-family: 'Segoe UI'; font-size: 14px;
                border-radius: {Spacing.RADIUS_BTN}px; padding: 12px; border: none;
            }}
            QPushButton#ActionBtn:hover {{ background-color: {Palette.FG_PRIMARY}; }}
            QPushButton#ActionBtn:pressed {{ background-color: #2dc3ff; }}

            QPushButton#InfoBtn {{
                background: rgba(14, 179, 255, 0.10);
                border: 1px solid {Palette.CYAN};
                color: {Palette.CYAN};
                font-size: 14px; border-radius: 15px; font-weight: bold;
            }}
            QPushButton#InfoBtn:hover {{ background: {Palette.CYAN}; color: {Palette.BG_BASE}; }}

            QPushButton#ExitBtn {{
                background: transparent;
                border: 1px solid rgba(255, 75, 75, 0.55);
                color: {Palette.STATE_DANGER};
                border-radius: {Spacing.RADIUS_BTN}px;
                font-family: 'Segoe UI'; font-weight: bold; letter-spacing: 1px;
            }}
            QPushButton#ExitBtn:hover {{
                background: {Palette.STATE_DANGER}; color: {Palette.FG_PRIMARY};
                border: 1px solid {Palette.STATE_DANGER};
            }}

            QScrollArea {{ background: transparent; border: none; }}
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        sidebar = QFrame(); sidebar.setObjectName("Sidebar"); sidebar.setFixedWidth(220)
        self._qt_sidebar = sidebar
        side_lyt = QVBoxLayout(sidebar); side_lyt.setContentsMargins(15, 24, 15, 18); side_lyt.setSpacing(10)

        side_lyt.addWidget(self._build_logo_widget(), alignment=Qt.AlignCenter)
        side_lyt.addSpacing(8)

        self._menu_buttons = {}
        btn_home = SidebarButton("home",       "HOME")
        btn_limp = SidebarButton("limpeza",    "LIMPEZA")
        btn_otim = SidebarButton("otimizacao", "OTIMIZAÇÃO")
        btn_rep  = SidebarButton("reparos",    "REPAROS")
        btn_spec = SidebarButton("specs",      "ESPECIFICAÇÕES")
        btn_home.clicked.connect(self.show_home)
        btn_limp.clicked.connect(self.show_limpeza)
        btn_otim.clicked.connect(self.show_otimizacao)
        btn_rep.clicked.connect(self.show_reparos)
        btn_spec.clicked.connect(self.show_specs)
        self._menu_buttons["home"]       = btn_home
        self._menu_buttons["limpeza"]    = btn_limp
        self._menu_buttons["otimizacao"] = btn_otim
        self._menu_buttons["reparos"]    = btn_rep
        self._menu_buttons["specs"]      = btn_spec
        side_lyt.addWidget(btn_home)
        side_lyt.addWidget(btn_limp)
        side_lyt.addWidget(btn_otim)
        side_lyt.addWidget(btn_rep)
        side_lyt.addWidget(btn_spec)

        self.btn_gamer_nav = GamerSidebarButton()
        self.btn_gamer_nav.clicked.connect(self.show_gamer)
        side_lyt.addWidget(self.btn_gamer_nav)

        side_lyt.addStretch()

        self.btn_restore = SidebarRestoreButton()
        self.btn_restore.clicked.connect(self.criar_ponto_restauracao)
        side_lyt.addWidget(self.btn_restore)

        side_lyt.addSpacing(2)

        btn_sair = SidebarExitButton()
        btn_sair.clicked.connect(self.finalizar_app)
        side_lyt.addWidget(btn_sair)

        side_lyt.addSpacing(4)
        ver = QLabel(f"v {APP_VERSION} · Tecnosup")
        ver.setStyleSheet(f"color: {Palette.FG_SUBTLE}; font-family: 'Consolas'; font-size: 9px; background: transparent;")
        ver.setAlignment(Qt.AlignCenter)
        side_lyt.addWidget(ver)

        main_layout.addWidget(sidebar)

        self.content_container = QWidget()
        self.content_container.paintEvent = self.paint_grid 
        self.content_lyt = QVBoxLayout(self.content_container)
        self.content_lyt.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.content_container)

        web_mode = True  # UI migrada para WebEngine
        print(f"[TecnoApp] startup mode = {'WEB (Qt WebEngine)' if web_mode else 'CLASSIC (QWidgets)'}", flush=True)
        if web_mode:
            self.show_web()
        else:
            self.show_home()

    def show_web(self):
        """Substitui toda a área de conteúdo pelo WebView (PoC pixel-perfect)."""
        from web_screen import WebScreen
        self.clear_screen()
        if hasattr(self, "_qt_sidebar") and self._qt_sidebar is not None:
            self._qt_sidebar.hide()
        # Desliga o paint do grid Qt — o HTML já desenha o próprio bg_grid.png
        self.content_container.paintEvent = lambda e: None
        if hasattr(self, "_web_view") and self._web_view is not None:
            self._web_view.deleteLater()
        self._web_view = WebScreen(main_window=self, parent=self.content_container)
        self.content_lyt.setContentsMargins(0, 0, 0, 0)
        self.content_lyt.setSpacing(0)
        self.content_lyt.setAlignment(Qt.AlignTop)
        self.content_lyt.addWidget(self._web_view, 1)

    def get_free_space(self):
        free_bytes = ctypes.c_ulonglong(0)
        ctypes.windll.kernel32.GetDiskFreeSpaceExW(ctypes.c_wchar_p("C:\\"), None, None, ctypes.pointer(free_bytes))
        return free_bytes.value

    def format_size(self, size):
        if size < 1024*1024: return f"{(size/1024):.2f} KB"
        return f"{(size/(1024*1024)):.2f} MB" if size < 1024*1024*1024 else f"{(size/(1024*1024*1024)):.2f} GB"

    def run_clean_process(self, selected_ids=None):
        if not isinstance(selected_ids, set):
            # Respeita seleções salvas; cai nos defaults se nunca configurou
            state = _load_clean_state()
            saved = state.get("user_selections") or {}
            if saved:
                selected_ids = {cid for cid, v in saved.items() if v}
            else:
                selected_ids = {c["id"] for c in _CLEAN_CATEGORIES if c["default"]}
        if self._clean_worker is not None:
            return
        self._clean_log_lines = []
        self.show_limpeza_progresso()
        self._clean_worker = CleanWorker(selected_ids)
        self._clean_worker.step_done.connect(self._on_clean_step)
        self._clean_worker.calculating.connect(self._on_clean_calculating)
        self._clean_worker.finished.connect(self._on_clean_done)
        self._clean_worker.start()

    def _is_widget_alive(self, widget) -> bool:
        """True se o widget existe e o objeto C++ subjacente ainda é válido.

        Usado pelos handlers de worker para evitar crash ao atualizar
        widgets já destruídos (ex.: usuário navegou de tela enquanto o
        worker ainda estava rodando).
        """
        if widget is None:
            return False
        try:
            return shiboken6.isValid(widget)
        except Exception:
            return False

    def _menu_icon(self, glyph: str, size: int = 18, color: str = "#ffffff") -> QIcon:
        """Renderiza um glifo Segoe MDL2 Assets como QIcon na cor especificada.

        Permite ícones reais (broom, lightning, wrench, cpu, gamepad) em
        vez de emojis coloridos do sistema. Funciona em Win10+ (MDL2)
        e Win11 (Fluent Icons herda os codepoints).
        """
        pix = QPixmap(size, size)
        pix.fill(Qt.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        f = QFont("Segoe Fluent Icons")
        if not f.exactMatch():
            f = QFont("Segoe MDL2 Assets")
        f.setPixelSize(size - 2)
        p.setFont(f)
        p.setPen(QColor(color))
        p.drawText(pix.rect(), Qt.AlignCenter, glyph)
        p.end()
        return QIcon(pix)

    def _build_logo_widget(self) -> QFrame:
        """Bloco da marca Tecnosup na sidebar — clicável → Home.

        Carrega `app/assets/tecnosup_logo.png` se existir; senão usa
        fallback tipográfico. Para usar o logo oficial, salvar a
        imagem como `app/assets/tecnosup_logo.png`.
        """
        frame = QFrame()
        frame.setObjectName("LogoBlock")
        frame.setCursor(QCursor(Qt.PointingHandCursor))
        frame.setStyleSheet(
            "QFrame#LogoBlock { background: transparent; border: none; border-radius: 8px; }"
            "QFrame#LogoBlock:hover { background: rgba(14, 179, 255, 0.06); }"
        )
        lyt = QVBoxLayout(frame)
        lyt.setContentsMargins(8, 6, 8, 6)
        lyt.setSpacing(0)
        lyt.setAlignment(Qt.AlignCenter)

        assets_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "assets"
        )
        # Aceita tanto "tecnosup_logo.png" quanto "logo.png" (qualquer um
        # que o usuário salvar nessa pasta).
        loaded_image = False
        for filename in ("tecnosup_logo.png", "logo.png", "tecnosup.png"):
            logo_path = os.path.join(assets_dir, filename)
            if os.path.exists(logo_path):
                pix = QPixmap(logo_path)
                if not pix.isNull():
                    scaled = pix.scaledToWidth(180, Qt.SmoothTransformation)
                    img_lbl = QLabel()
                    img_lbl.setPixmap(scaled)
                    img_lbl.setAlignment(Qt.AlignCenter)
                    img_lbl.setStyleSheet("background: transparent;")
                    lyt.addWidget(img_lbl)
                    loaded_image = True
                    break

        if not loaded_image:
            main = QLabel("Tecnosup")
            main.setFont(QFont("Segoe UI", 22, QFont.Bold))
            main.setAlignment(Qt.AlignCenter)
            main.setStyleSheet(f"color: {self.primary}; background: transparent;")
            self.add_neon(main, self.primary)
            lyt.addWidget(main)

            slogan = QLabel("SOLUÇÕES DIGITAIS")
            slogan.setFont(QFont("Segoe UI", 8, QFont.Bold))
            slogan.setAlignment(Qt.AlignCenter)
            slogan.setStyleSheet(
                f"color: {self.primary}; background: transparent; letter-spacing: 4px;"
            )
            lyt.addWidget(slogan)

        def _on_click(_event):
            self.show_home()
        frame.mousePressEvent = _on_click
        return frame

    def _stop_metrics_timer(self):
        """Para o QTimer ativo de métricas live (Home/Specs)."""
        timer = getattr(self, "_metrics_timer", None)
        if timer is not None:
            try:
                timer.stop()
            except Exception:
                pass
            self._metrics_timer = None

    def _set_status_bar(self, module: str, default: str) -> None:
        pending = self._pending_status.pop(module, None)
        if pending:
            self.add_status_bar(pending)
            self.status_lbl.setStyleSheet(
                "color: #ffbd2e; font-family: 'Consolas'; font-weight: bold;"
            )
            return
        stored = _get_module_status(module)
        if stored:
            self.add_status_bar(stored)
            self.status_lbl.setStyleSheet(
                "color: #ffbd2e; font-family: 'Consolas'; font-weight: bold;"
            )
        else:
            self.add_status_bar(default)

    def show_limpeza(self):
        self.clear_screen()
        self._set_active_menu("limpeza")
        self._stop_metrics_timer()

        panel = QWidget()
        panel.setStyleSheet("background: transparent;")
        panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        panel_lyt = QVBoxLayout(panel)
        panel_lyt.setContentsMargins(32, 24, 32, 24)
        panel_lyt.setSpacing(14)
        panel_lyt.setAlignment(Qt.AlignTop)

        title = QLabel("LIMPEZA")
        title.setFont(QFont("Segoe UI", 22, QFont.Bold))
        title.setStyleSheet(f"color: {Palette.FG_PRIMARY}; background: transparent;")
        panel_lyt.addWidget(title)

        sub = QLabel("Limpeza segura com ferramentas nativas do Windows")
        sub.setStyleSheet(
            f"color: {Palette.FG_MUTED}; font-family: 'Segoe UI'; "
            f"font-size: 12px; background: transparent;"
        )
        panel_lyt.addWidget(sub)
        panel_lyt.addSpacing(4)

        panel_lyt.addWidget(self._disk_usage_card())
        panel_lyt.addWidget(self._limpeza_hero())

        self.content_lyt.addWidget(panel, 1)
        self._set_status_bar("clean", "> Nenhuma limpeza realizada ainda.")

    def _disk_usage_card(self) -> Card:
        """Card com barra de uso do disco C:."""
        card = Card()
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        card.layout().setSpacing(8)

        free, total = self._get_disk_info()
        used_pct = int(((total - free) / total) * 100) if total > 0 else 0

        header_lyt = QHBoxLayout()
        header_lyt.setContentsMargins(0, 0, 0, 0)
        title = QLabel("DISCO C:")
        title.setStyleSheet(
            f"color: {Palette.ACCENT_CYAN}; font-family: 'Segoe UI'; font-size: 11px;"
            f" font-weight: bold; letter-spacing: 1px; background: transparent;"
        )
        header_lyt.addWidget(title)
        header_lyt.addStretch(1)
        pct = QLabel(f"{used_pct}%" if total > 0 else "—")
        pct.setStyleSheet(
            f"color: {Palette.FG_PRIMARY}; font-family: 'Consolas'; "
            f"font-size: 14px; font-weight: bold; background: transparent;"
        )
        header_lyt.addWidget(pct)
        card.layout().addLayout(header_lyt)

        bar = QProgressBar()
        bar.setFixedHeight(10)
        bar.setTextVisible(False)
        bar.setRange(0, 100)
        bar.setValue(used_pct)
        bar.setStyleSheet(
            f"QProgressBar {{"
            f"  background: #04060a; border: 1px solid {Palette.BORDER_SUBTLE};"
            f"  border-radius: 5px;"
            f"}}"
            f"QProgressBar::chunk {{"
            f"  background: {Palette.ACCENT_CYAN}; border-radius: 4px;"
            f"}}"
        )
        card.add(bar)

        if total > 0:
            stats = QLabel(
                f"{self.format_size(total - free)} usados  ·  "
                f"{self.format_size(free)} livres  ·  "
                f"{self.format_size(total)} total"
            )
        else:
            stats = QLabel("disco indisponível")
        stats.setAlignment(Qt.AlignCenter)
        stats.setStyleSheet(
            f"color: {Palette.FG_MUTED}; font-family: 'Consolas'; "
            f"font-size: 11px; background: transparent;"
        )
        card.add(stats)
        return card

    def _limpeza_hero(self) -> HeroCard:
        """Hero card com contador de categorias + CTA principal."""
        hero = HeroCard(accent_color=Palette.ACCENT_CYAN)
        hero.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        section = QLabel("LIMPEZA RÁPIDA")
        section.setAlignment(Qt.AlignCenter)
        section.setStyleSheet(
            f"color: {Palette.ACCENT_CYAN}; font-family: 'Segoe UI'; font-size: 11px;"
            f" font-weight: bold; letter-spacing: 1px; background: transparent;"
        )
        hero.add(section)

        state = _load_clean_state()
        saved = state.get("user_selections") or {}
        if saved:
            selected = sum(1 for v in saved.values() if v)
        else:
            selected = sum(1 for c in _CLEAN_CATEGORIES if c["default"])
        total_cats = len(_CLEAN_CATEGORIES)

        hero.add(MetricLabel(f"{selected} de {total_cats}"))
        noun = "categoria ativa" if selected == 1 else "categorias ativas"
        desc = QLabel(noun)
        desc.setAlignment(Qt.AlignCenter)
        desc.setStyleSheet(
            f"color: {Palette.FG_MUTED}; font-family: 'Segoe UI'; "
            f"font-size: 11px; background: transparent;"
        )
        hero.add(desc)
        hero.add_spacing(6)

        btn = QPushButton("INICIAR LIMPEZA")
        btn.setFixedWidth(400)
        btn.setCursor(QCursor(Qt.PointingHandCursor))
        btn.setStyleSheet(
            f"QPushButton {{"
            f"  background-color: {self.primary}; color: black; font-weight: bold;"
            f"  border-radius: 8px; padding: 12px; border: none; font-size: 14px;"
            f"}}"
            f"QPushButton:hover {{ background-color: white; }}"
        )
        btn.clicked.connect(lambda: self.run_clean_process())
        self.add_neon(btn, self.primary)
        hero.add(btn, alignment=Qt.AlignCenter)

        cfg = QPushButton("Configurar o que é limpo →")
        cfg.setFixedWidth(260)
        cfg.setCursor(QCursor(Qt.PointingHandCursor))
        cfg.setStyleSheet(
            f"background:transparent; color:{Palette.ACCENT_CYAN}; "
            f"border:1px solid {Palette.ACCENT_CYAN};"
            f"border-radius:6px; padding:6px; font-family:'Segoe UI'; font-size:11px;"
        )
        cfg.clicked.connect(self.show_limpeza_avancada)
        hero.add(cfg, alignment=Qt.AlignCenter)

        return hero

    def show_limpeza_avancada(self):
        self.clear_screen()
        self.add_title("CONFIGURAR LIMPEZA")
        sub = QLabel("Selecione o que deseja limpar. Os marcados por padrão são seguros para todos.")
        sub.setStyleSheet(f"color: {Palette.FG_MUTED}; font-size: 11px; margin-bottom: 8px;")
        sub.setWordWrap(True)
        sub.setAlignment(Qt.AlignCenter)
        self.content_lyt.addWidget(sub)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        inner = QWidget()
        inner.setStyleSheet("background: transparent;")
        inner_lyt = QVBoxLayout(inner)
        inner_lyt.setSpacing(6)
        inner_lyt.setContentsMargins(4, 4, 4, 4)

        self._clean_checkboxes = {}

        # Carrega seleções salvas; se item sem valor salvo, usa o default da categoria
        state = _load_clean_state()
        saved = state.get("user_selections") or {}

        safe_cats = [c for c in _CLEAN_CATEGORIES if c["default"]]
        opt_cats = [c for c in _CLEAN_CATEGORIES if not c["default"]]

        safe_hdr = QLabel("── SEGURO (sempre recomendado)")
        safe_hdr.setStyleSheet(f"color: {Palette.CYAN}; font-weight: bold; font-size: 11px; margin-top: 4px;")
        inner_lyt.addWidget(safe_hdr)

        for cat in safe_cats:
            checked = saved.get(cat["id"], cat["default"])
            inner_lyt.addWidget(self._build_clean_row(cat, checked=checked))

        opt_hdr = QLabel("── OPCIONAL (revise antes de ativar)")
        opt_hdr.setStyleSheet(f"color: {Palette.STATE_WARN}; font-weight: bold; font-size: 11px; margin-top: 10px;")
        inner_lyt.addWidget(opt_hdr)

        for cat in opt_cats:
            checked = saved.get(cat["id"], cat["default"])
            inner_lyt.addWidget(self._build_clean_row(cat, checked=checked))

        inner_lyt.addStretch()
        scroll.setWidget(inner)
        self.content_lyt.addWidget(scroll, 1)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)

        back = QPushButton("Voltar")
        back.setFixedWidth(100)
        back.setStyleSheet(
            f"background: transparent; border: 1px solid {Palette.STATE_OFF_BRD}; color: {Palette.FG_MUTED};"
            "font-weight: bold; border-radius: 6px; padding: 8px;"
        )
        back.clicked.connect(self.show_limpeza)

        save = QPushButton("Salvar alterações")
        save.setFixedWidth(200)
        save.setStyleSheet(
            f"background: {Palette.CYAN}; color: {Palette.BG_BASE}; border: none;"
            "border-radius: 6px; padding: 8px; font-family: 'Segoe UI'; font-weight: bold;"
        )
        save.clicked.connect(self._save_clean_and_return)

        btn_row.addWidget(back)
        btn_row.addSpacing(10)
        btn_row.addWidget(save)
        btn_row.addStretch(1)
        self.content_lyt.addLayout(btn_row)

        self.add_status_bar("> Configure aqui. Execução acontece na tela anterior em 'Limpeza Rápida'.")

    def _build_clean_row(self, cat, checked):
        row = QFrame()
        row.setStyleSheet(
            f"QFrame {{ background: {Palette.BG_CARD}; border: 1px solid {Palette.BORDER_SUBTLE}; border-radius: {Spacing.RADIUS_ROW}px; }}"
        )
        lyt = QVBoxLayout(row)
        lyt.setContentsMargins(10, 8, 10, 8)
        lyt.setSpacing(2)

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)

        cb = QCheckBox(cat["label"])
        cb.setChecked(checked)
        cb.setStyleSheet(
            f"QCheckBox {{ color: {Palette.FG_PRIMARY}; font-family: 'Segoe UI'; font-size: 12px; }}"
            "QCheckBox::indicator { width: 14px; height: 14px; }"
        )
        self._clean_checkboxes[cat["id"]] = cb
        cb.stateChanged.connect(self._on_clean_selection_changed)
        top.addWidget(cb, 1)

        impact = QLabel(cat["impact"])
        impact.setStyleSheet(f"color: {Palette.CYAN}; font-family: 'Consolas'; font-size: 10px;")
        top.addWidget(impact)
        lyt.addLayout(top)

        desc = QLabel(cat["desc"])
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {Palette.FG_MUTED}; font-family: 'Segoe UI'; font-size: 10px; padding-left: 22px;")
        lyt.addWidget(desc)

        if cat.get("warning"):
            warn = QLabel("⚠ " + cat["warning"])
            warn.setWordWrap(True)
            warn.setStyleSheet(f"color: {Palette.STATE_WARN}; font-family: 'Segoe UI'; font-size: 10px; padding-left: 22px;")
            lyt.addWidget(warn)

        return row

    def _on_clean_selection_changed(self, _state=None):
        self._save_clean_selections()

    def _save_clean_selections(self):
        state = _load_clean_state()
        state["user_selections"] = {
            cid: bool(cb.isChecked()) for cid, cb in self._clean_checkboxes.items()
        }
        _save_clean_state(state)

    def _save_clean_and_return(self):
        self._save_clean_selections()
        selected = sum(1 for cb in self._clean_checkboxes.values() if cb.isChecked())
        noun = "categoria selecionada" if selected == 1 else "categorias selecionadas"
        self._pending_status["clean"] = f"> ✓ Preferências salvas ({selected} {noun})"
        self.show_limpeza()

    def show_limpeza_progresso(self):
        self.clear_screen()
        self.add_title("LIMPEZA EM ANDAMENTO")

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            f"QScrollArea {{ border: 1px solid {Palette.BORDER_SUBTLE}; "
            f"background: {Palette.BG_CARD}; border-radius: 8px; }}"
        )
        log_inner = QWidget()
        log_inner.setStyleSheet("background: transparent;")
        log_lyt = QVBoxLayout(log_inner)
        log_lyt.setAlignment(Qt.AlignTop)
        log_lyt.setContentsMargins(14, 12, 14, 12)

        self._clean_log_label = QLabel("> Iniciando limpeza...")
        self._clean_log_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self._clean_log_label.setStyleSheet(
            f"color: {self.primary}; font-family: 'Consolas'; font-size: 12px; line-height: 180%;"
        )
        self._clean_log_label.setWordWrap(True)
        log_lyt.addWidget(self._clean_log_label)
        scroll.setWidget(log_inner)
        self.content_lyt.addWidget(scroll, 1)

        self._clean_total_label = QLabel("")
        self._clean_total_label.setFont(QFont("Segoe UI", 20, QFont.Bold))
        self._clean_total_label.setAlignment(Qt.AlignCenter)
        self._clean_total_label.setStyleSheet(f"color: {self.primary}; margin-top: 8px;")
        self._clean_total_label.hide()
        self.content_lyt.addWidget(self._clean_total_label)

        self._clean_btn_voltar = QPushButton("VOLTAR")
        self._clean_btn_voltar.setFixedWidth(200)
        self._clean_btn_voltar.setEnabled(False)
        self._clean_btn_voltar.setStyleSheet(
            f"background: transparent; border: 1px solid {Palette.STATE_OFF_BRD}; color: {Palette.FG_SUBTLE};"
            "font-weight: bold; border-radius: 8px; padding: 10px;"
        )
        self._clean_btn_voltar.clicked.connect(self.show_limpeza)
        self.content_lyt.addWidget(self._clean_btn_voltar, alignment=Qt.AlignCenter)

    def _on_clean_step(self, label: str, freed: int):
        log_label = getattr(self, "_clean_log_label", None)
        if not self._is_widget_alive(log_label):
            return
        size_str = f"   +{self.format_size(freed)}" if freed > 1024 else ""
        self._clean_log_lines.append(f"✓  {label}{size_str}")
        log_label.setText("\n".join(self._clean_log_lines))

    def _on_clean_calculating(self):
        log_label = getattr(self, "_clean_log_label", None)
        if not self._is_widget_alive(log_label):
            return
        self._clean_log_lines.append("")
        self._clean_log_lines.append("Calculando resultado·")
        log_label.setText("\n".join(self._clean_log_lines))
        self._clean_dots = 0
        self._clean_calc_timer = QTimer(self)
        self._clean_calc_timer.timeout.connect(self._animate_clean_dots)
        self._clean_calc_timer.start(180)

    def _animate_clean_dots(self):
        log_label = getattr(self, "_clean_log_label", None)
        if not self._is_widget_alive(log_label):
            # Widget sumiu (usuário navegou) — para o timer para não vazar.
            if self._clean_calc_timer is not None:
                try:
                    self._clean_calc_timer.stop()
                except Exception:
                    pass
                self._clean_calc_timer = None
            return
        try:
            self._clean_dots = (self._clean_dots + 1) % 3
            dots = "·" * (self._clean_dots + 1)
            self._clean_log_lines[-1] = f"Calculando resultado{dots}"
            log_label.setText("\n".join(self._clean_log_lines))
        except (RuntimeError, IndexError):
            pass

    def _on_clean_done(self, total: int):
        if self._clean_calc_timer is not None:
            try:
                self._clean_calc_timer.stop()
            except Exception:
                pass
            self._clean_calc_timer = None

        # Worker cleanup — independente de widgets estarem vivos.
        if self._clean_worker is not None:
            try:
                self._clean_worker.wait()
                self._clean_worker.deleteLater()
            except Exception:
                pass
            self._clean_worker = None

        if total > 102_400:
            msg = f"✓  {self.format_size(total)} liberados"
        else:
            msg = "✓  Sistema já estava limpo"
        _save_module_status("clean", msg)

        # Atualiza UI só se os widgets da tela de progresso ainda existem.
        log_label   = getattr(self, "_clean_log_label",   None)
        total_label = getattr(self, "_clean_total_label", None)
        btn_voltar  = getattr(self, "_clean_btn_voltar",  None)
        if self._is_widget_alive(log_label):
            while self._clean_log_lines and (
                self._clean_log_lines[-1].startswith("Calculando") or
                self._clean_log_lines[-1] == ""
            ):
                self._clean_log_lines.pop()
            log_label.setText("\n".join(self._clean_log_lines))
        if self._is_widget_alive(total_label):
            total_label.setText(msg)
            total_label.show()
            self.add_neon(total_label, self.primary)
        if self._is_widget_alive(btn_voltar):
            btn_voltar.setEnabled(True)
            btn_voltar.setStyleSheet(
                f"background: transparent; border: 1px solid {self.primary}; color: {self.primary};"
                "font-weight: bold; border-radius: 8px; padding: 10px;"
            )

    # ═══════════════════════════════════════════════════════════════════
    # HOME — Dashboard
    # ═══════════════════════════════════════════════════════════════════
    def show_home(self):
        self.clear_screen()
        self._set_active_menu("home")
        self._stop_metrics_timer()

        panel = QWidget()
        panel.setStyleSheet("background: transparent;")
        panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        panel_lyt = QVBoxLayout(panel)
        panel_lyt.setContentsMargins(32, 22, 32, 22)
        panel_lyt.setSpacing(12)
        panel_lyt.setAlignment(Qt.AlignTop)

        # Saudação contextual
        info = os_info()
        user = info.get("user", "")
        greeting_txt = f"Olá, {user}" if user and user != "—" else "Olá"
        greeting = QLabel(greeting_txt)
        greeting.setFont(QFont("Segoe UI", 22, QFont.Bold))
        greeting.setStyleSheet(f"color: {Palette.FG_PRIMARY}; background: transparent;")
        panel_lyt.addWidget(greeting)

        last_clean_ts = _load_module_statuses().get("clean", {}).get("timestamp")
        sub_parts = [
            info.get("system", "—"),
            f"uptime {format_uptime(uptime_seconds())}",
        ]
        if last_clean_ts:
            sub_parts.append(f"última limpeza {last_clean_ts}")
        sub = QLabel("  ·  ".join(sub_parts))
        sub.setStyleSheet(
            f"color: {Palette.FG_MUTED}; font-family: 'Segoe UI'; "
            f"font-size: 11px; background: transparent;"
        )
        panel_lyt.addWidget(sub)
        panel_lyt.addSpacing(4)

        # Linha de 3 cards LIVE (CPU / MEMÓRIA / DISCO C:)
        live_row = QHBoxLayout()
        live_row.setSpacing(12)

        cpu = cpu_static()
        cpu_card, self._home_cpu_metric, self._home_cpu_bar, self._home_cpu_sub = \
            self._build_live_card(
                "CPU", "0%",
                f"{cpu['threads']} threads · {cpu['freq']}",
            )
        live_row.addWidget(cpu_card)

        m = mem_live()
        ram_card, self._home_ram_metric, self._home_ram_bar, self._home_ram_sub = \
            self._build_live_card(
                "MEMÓRIA", f"{int(m['pct'])}%",
                f"{self.format_size(m['used'])} / {self.format_size(m['total'])}",
            )
        self._home_ram_bar.setValue(int(m["pct"]))
        live_row.addWidget(ram_card)

        d = disk_c_info()
        disk_card, self._home_disk_metric, self._home_disk_bar, self._home_disk_sub = \
            self._build_live_card(
                "DISCO C:", f"{int(d['pct'])}%",
                f"{self.format_size(d['used'])} / {self.format_size(d['total'])}",
            )
        self._home_disk_bar.setValue(int(d["pct"]))
        live_row.addWidget(disk_card)

        proc_n = processes_count()
        proc_card, self._home_proc_metric, _, self._home_proc_sub = \
            self._build_live_card(
                "PROCESSOS", str(proc_n), "em execução", show_bar=False,
            )
        live_row.addWidget(proc_card)

        panel_lyt.addLayout(live_row)

        # Linha de cards de AÇÃO — responsiva: 1×4 quando largo, 2×2 quando estreito
        action_cards = [
            self._home_card_limpeza(),
            self._home_card_otimizacao(),
            self._home_card_reparos(),
            self._home_card_gamer(),
        ]
        actions_row = ResponsiveCardRow(action_cards, breakpoint_px=900, spacing=12)
        panel_lyt.addWidget(actions_row)

        # Card SISTEMA — grid 2×2 com info estática
        sistema_card = Card()
        sistema_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        sistema_card.layout().setSpacing(6)

        sistema_title = QLabel("SISTEMA")
        sistema_title.setStyleSheet(
            f"color: {Palette.ACCENT_CYAN}; font-family: 'Segoe UI'; "
            f"font-size: 11px; font-weight: bold; letter-spacing: 1px;"
            f" background: transparent;"
        )
        sistema_card.add(sistema_title)

        sistema_grid = QGridLayout()
        sistema_grid.setHorizontalSpacing(24)
        sistema_grid.setVerticalSpacing(4)
        sistema_grid.setContentsMargins(0, 6, 0, 0)
        cpu_static_info = cpu_static()
        mem_total = mem_live().get("total", 0)
        rows = [
            ("Processador", cpu_static_info.get("name") or "—"),
            ("Memória RAM", self.format_size(mem_total) if mem_total else "—"),
            ("Sistema", info.get("system", "—")),
            ("Uptime", format_uptime(uptime_seconds())),
        ]
        for i, (k, v) in enumerate(rows):
            r, c = divmod(i, 2)
            cell = QWidget()
            cell.setStyleSheet(
                f"QWidget {{ border-bottom: 1px solid {Palette.BORDER_SUBTLE};"
                f" background: transparent; }}"
            )
            cell_lyt = QHBoxLayout(cell)
            cell_lyt.setContentsMargins(0, 4, 0, 4)
            cell_lyt.setSpacing(8)
            k_lbl = QLabel(k)
            k_lbl.setStyleSheet(
                f"color: {Palette.FG_MUTED}; font-family: 'Consolas';"
                f" font-size: 10px; background: transparent; border: none;"
            )
            k_lbl.setMinimumWidth(100)
            v_lbl = QLabel(v)
            v_lbl.setStyleSheet(
                f"color: {Palette.FG_PRIMARY}; font-family: 'Consolas';"
                f" font-size: 10px; background: transparent; border: none;"
            )
            v_lbl.setWordWrap(True)
            cell_lyt.addWidget(k_lbl)
            cell_lyt.addWidget(v_lbl, 1)
            sistema_grid.addWidget(cell, r, c)
        sistema_grid.setColumnStretch(0, 1)
        sistema_grid.setColumnStretch(1, 1)
        sistema_card.layout().addLayout(sistema_grid)
        panel_lyt.addWidget(sistema_card)

        # Status bar inferior (cyan mono)
        status_lbl = QLabel("> Sistema verificado — nenhuma ação pendente.")
        status_lbl.setStyleSheet(
            f"color: {Palette.ACCENT_CYAN}; font-family: 'Consolas';"
            f" font-size: 10px; background: transparent; padding-top: 4px;"
        )
        panel_lyt.addWidget(status_lbl)

        panel_lyt.addStretch(1)

        self.content_lyt.addWidget(panel, 1)

        # Inicia o timer de métricas live
        self._metrics_timer = QTimer(self)
        self._metrics_timer.timeout.connect(self._update_home_live_metrics)
        self._metrics_timer.start(1000)
        self._update_home_live_metrics()

    def _build_live_card(self, title: str, initial_pct: str, initial_sub: str,
                         show_bar: bool = True, accent: str | None = None):
        """Card com título, % grande, barra de progresso e sublabel.

        Retorna (card, metric_label, progress_bar|None, sub_label) — refs
        para atualização via timer. Quando show_bar=False, a barra é None
        (usado p.ex. no card PROCESSOS, que mostra só uma contagem).
        """
        card = HeroCard(accent_color=accent or Palette.ACCENT_CYAN)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        card.layout().setSpacing(8)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(
            f"color: {Palette.ACCENT_CYAN}; font-family: 'Segoe UI'; "
            f"font-size: 11px; font-weight: bold; letter-spacing: 1px;"
            f" background: transparent;"
        )
        card.add(title_lbl)

        metric = QLabel(initial_pct)
        metric.setFont(QFont("Segoe UI", 26, QFont.Bold))
        metric.setAlignment(Qt.AlignCenter)
        metric.setStyleSheet(f"color: {Palette.FG_PRIMARY}; background: transparent;")
        card.add(metric)

        bar = None
        if show_bar:
            bar = QProgressBar()
            bar.setFixedHeight(8)
            bar.setTextVisible(False)
            bar.setRange(0, 100)
            bar.setValue(0)
            bar.setStyleSheet(
                f"QProgressBar {{"
                f"  background: #04060a; border: 1px solid {Palette.BORDER_SUBTLE};"
                f"  border-radius: 4px;"
                f"}}"
                f"QProgressBar::chunk {{"
                f"  background: {Palette.ACCENT_CYAN}; border-radius: 3px;"
                f"}}"
            )
            card.add(bar)

        sub_lbl = QLabel(initial_sub)
        sub_lbl.setStyleSheet(
            f"color: {Palette.FG_MUTED}; font-family: 'Consolas'; "
            f"font-size: 10px; background: transparent;"
        )
        sub_lbl.setWordWrap(True)
        sub_lbl.setAlignment(Qt.AlignCenter)
        card.add(sub_lbl)

        return card, metric, bar, sub_lbl

    def _update_home_live_metrics(self):
        if not self._is_widget_alive(getattr(self, "_home_cpu_bar", None)):
            return

        cpu = cpu_pct()
        if self._is_widget_alive(self._home_cpu_metric):
            self._home_cpu_metric.setText(f"{cpu:.0f}%")
        self._home_cpu_bar.setValue(int(cpu))

        m = mem_live()
        if self._is_widget_alive(self._home_ram_metric):
            self._home_ram_metric.setText(f"{int(m['pct'])}%")
        if self._is_widget_alive(self._home_ram_bar):
            self._home_ram_bar.setValue(int(m["pct"]))
        if self._is_widget_alive(self._home_ram_sub):
            self._home_ram_sub.setText(
                f"{self.format_size(m['used'])} / {self.format_size(m['total'])}"
            )

        d = disk_c_info()
        if self._is_widget_alive(self._home_disk_metric):
            self._home_disk_metric.setText(f"{int(d['pct'])}%")
        if self._is_widget_alive(self._home_disk_bar):
            self._home_disk_bar.setValue(int(d["pct"]))
        if self._is_widget_alive(self._home_disk_sub):
            self._home_disk_sub.setText(
                f"{self.format_size(d['used'])} / {self.format_size(d['total'])}"
            )

        if self._is_widget_alive(getattr(self, "_home_proc_metric", None)):
            self._home_proc_metric.setText(str(processes_count()))

    def _get_disk_info(self) -> tuple[int, int]:
        """Retorna (free_bytes, total_bytes) do disco C:. (0, 0) em falha."""
        total = ctypes.c_ulonglong(0)
        free = ctypes.c_ulonglong(0)
        try:
            ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                ctypes.c_wchar_p("C:\\"),
                None,
                ctypes.pointer(total),
                ctypes.pointer(free),
            )
            return (free.value, total.value)
        except Exception:
            return (0, 0)

    def _home_section_title(self, text: str, color: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"color: {color}; font-family: 'Segoe UI'; font-size: 11px;"
            f" font-weight: bold; letter-spacing: 1px; background: transparent;"
        )
        return lbl

    def _home_desc(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"color: {Palette.FG_MUTED}; font-family: 'Segoe UI'; "
            f"font-size: 11px; background: transparent;"
        )
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setWordWrap(True)
        return lbl

    def _home_cta(self, text: str, color: str, handler) -> QPushButton:
        btn = QPushButton(text)
        btn.setCursor(QCursor(Qt.PointingHandCursor))
        btn.setFixedHeight(38)
        is_purple = color == Palette.ACCENT_PURPLE
        hover_color = "#8a2bff" if is_purple else "#2dc3ff"
        text_color = "#ffffff" if is_purple else "#030407"
        btn.setStyleSheet(
            f"QPushButton {{"
            f"  background: {color}; color: {text_color}; border: none;"
            f"  border-radius: 8px; padding: 0 16px;"
            f"  font-family: 'Segoe UI'; font-size: 12px;"
            f"  font-weight: bold; letter-spacing: 1px;"
            f"}}"
            f"QPushButton:hover {{ background: {hover_color}; }}"
            f"QPushButton:pressed {{ background: {color}; }}"
        )
        btn.clicked.connect(handler)
        return btn

    def _home_card_limpeza(self) -> HeroCard:
        card = HeroCard(accent_color=Palette.ACCENT_CYAN)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        card.add(self._home_section_title("LIMPEZA", Palette.ACCENT_CYAN))
        card.add_stretch(1)

        free, total = self._get_disk_info()
        if total > 0:
            used_str = self.format_size(total - free)
            value, unit = used_str.rsplit(" ", 1)
            card.add(MetricLabel(value, unit))
            card.add(self._home_desc(f"usados de {self.format_size(total)}"))
        else:
            card.add(MetricLabel("—"))
            card.add(self._home_desc("disco indisponível"))

        card.add_stretch(1)
        card.add(self._home_cta("Limpar", Palette.ACCENT_CYAN, self.show_limpeza))
        return card

    def _home_card_otimizacao(self) -> HeroCard:
        card = HeroCard(accent_color=Palette.ACCENT_CYAN)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        card.add(self._home_section_title("OTIMIZAÇÃO", Palette.ACCENT_CYAN))
        card.add_stretch(1)

        state = _load_optimize_state()
        saved = state.get("user_selections") or {}
        if saved:
            selected = sum(1 for v in saved.values() if v)
        else:
            selected = sum(1 for c in _OPTIMIZE_CATEGORIES if c["default"])
        total = len(_OPTIMIZE_CATEGORIES)

        card.add(MetricLabel(f"{selected} de {total}"))
        label = "otimização selecionada" if selected == 1 else "otimizações selecionadas"
        card.add(self._home_desc(label))

        card.add_stretch(1)
        card.add(self._home_cta("Otimizar", Palette.ACCENT_CYAN, self.show_otimizacao))
        return card

    def _home_card_reparos(self) -> HeroCard:
        card = HeroCard(accent_color=Palette.ACCENT_CYAN)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        card.add(self._home_section_title("REPAROS", Palette.ACCENT_CYAN))
        card.add_stretch(1)

        n = len(_REPAIR_TOOLS)
        card.add(MetricLabel(str(n)))
        noun = "ferramenta disponível" if n == 1 else "ferramentas disponíveis"
        card.add(self._home_desc(noun))

        card.add_stretch(1)
        card.add(self._home_cta("Abrir", Palette.ACCENT_CYAN, self.show_reparos))
        return card

    def _home_card_gamer(self) -> HeroCard:
        card = HeroCard(accent_color=Palette.ACCENT_PURPLE)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        card.add(self._home_section_title("MODO GAMER", Palette.ACCENT_PURPLE))
        card.add_stretch(1)

        active = self.gamer_engine.is_active()
        metric = MetricLabel("● ATIVO" if active else "● INATIVO")
        metric.setStyleSheet(
            f"color: {Palette.STATE_ON if active else Palette.FG_MUTED};"
            f" background: transparent;"
        )
        card.add(metric)
        card.add(self._home_desc(
            "otimizações para jogos aplicadas" if active else "pronto para ativar"
        ))

        card.add_stretch(1)
        card.add(self._home_cta("Abrir", Palette.ACCENT_PURPLE, self.show_gamer))
        return card

    # ═══════════════════════════════════════════════════════════════════
    # ESPECIFICAÇÕES
    # ═══════════════════════════════════════════════════════════════════
    def show_specs(self):
        self.clear_screen()
        self._set_active_menu("specs")
        self._stop_metrics_timer()

        panel = QWidget()
        panel.setStyleSheet("background: transparent;")
        panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        panel_lyt = QVBoxLayout(panel)
        panel_lyt.setContentsMargins(32, 22, 32, 22)
        panel_lyt.setSpacing(10)
        panel_lyt.setAlignment(Qt.AlignTop)

        title = QLabel("ESPECIFICAÇÕES")
        title.setFont(QFont("Segoe UI", 22, QFont.Bold))
        title.setStyleSheet(f"color: {Palette.FG_PRIMARY}; background: transparent;")
        panel_lyt.addWidget(title)

        sub = QLabel("Visão completa do sistema · atualizada em tempo real")
        sub.setStyleSheet(
            f"color: {Palette.FG_MUTED}; font-family: 'Segoe UI'; "
            f"font-size: 12px; background: transparent;"
        )
        panel_lyt.addWidget(sub)
        panel_lyt.addSpacing(4)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            f"QScrollArea {{ border: none; background: transparent; }}"
            f"QScrollBar:vertical {{ width: 6px; background: {Palette.BG_BASE}; border-radius: 3px; }}"
            f"QScrollBar::handle:vertical {{ background: {Palette.CYAN}; border-radius: 3px; }}"
        )
        inner = QWidget()
        inner.setStyleSheet("background: transparent;")
        inner_lyt = QVBoxLayout(inner)
        inner_lyt.setSpacing(12)
        inner_lyt.setContentsMargins(0, 0, 8, 0)

        grid = QGridLayout()
        grid.setSpacing(12)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.addWidget(self._spec_card_os(),        0, 0)
        grid.addWidget(self._spec_card_mobo(),      0, 1)
        grid.addWidget(self._spec_card_cpu(),       1, 0)
        grid.addWidget(self._spec_card_gpu(),       1, 1)
        grid.addWidget(self._spec_card_ram(),       2, 0)
        grid.addWidget(self._spec_card_disks(),     2, 1)
        grid.addWidget(self._spec_card_processes(), 3, 0, 1, 2)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        inner_lyt.addLayout(grid)
        inner_lyt.addStretch(1)
        scroll.setWidget(inner)
        panel_lyt.addWidget(scroll, 1)

        self.content_lyt.addWidget(panel, 1)

        # Hardware lento via WMI (cacheado depois da primeira chamada)
        self._start_hardware_worker()

        # Live metrics: CPU live + RAM live
        self._metrics_timer = QTimer(self)
        self._metrics_timer.timeout.connect(self._update_specs_live_metrics)
        self._metrics_timer.start(1500)
        self._update_specs_live_metrics()

    def _spec_title(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"color: {Palette.ACCENT_CYAN}; font-family: 'Segoe UI'; "
            f"font-size: 11px; font-weight: bold; letter-spacing: 1px;"
            f" background: transparent;"
        )
        return lbl

    def _kv_html(self, key: str, value: str) -> str:
        return f"<span style='color:{Palette.FG_MUTED};'>{key}</span>&nbsp;&nbsp;{value}"

    def _spec_kv(self, key: str, value: str) -> QLabel:
        lbl = QLabel(self._kv_html(key, value))
        lbl.setTextFormat(Qt.RichText)
        lbl.setWordWrap(True)
        lbl.setStyleSheet(
            f"color: {Palette.FG_BODY}; font-family: 'Segoe UI'; "
            f"font-size: 11px; background: transparent;"
        )
        return lbl

    def _spec_bar_style(self) -> str:
        return (
            f"QProgressBar {{"
            f"  background: #04060a; border: 1px solid {Palette.BORDER_SUBTLE};"
            f"  border-radius: 4px;"
            f"}}"
            f"QProgressBar::chunk {{"
            f"  background: {Palette.ACCENT_CYAN}; border-radius: 3px;"
            f"}}"
        )

    def _spec_card_os(self) -> Card:
        card = Card()
        card.layout().setSpacing(4)
        card.add(self._spec_title("SISTEMA OPERACIONAL"))
        info = os_info()
        card.add(self._spec_kv("Sistema",     info["system"]))
        card.add(self._spec_kv("Build",       info["version"]))
        card.add(self._spec_kv("Arquitetura", info["arch"]))
        card.add(self._spec_kv("Usuário",     info["user"]))
        card.add(self._spec_kv("Máquina",     info["machine"]))
        return card

    def _spec_card_mobo(self) -> Card:
        card = Card()
        card.layout().setSpacing(4)
        card.add(self._spec_title("PLACA-MÃE"))
        self._specs_mobo_man   = self._spec_kv("Fabricante", "detectando…")
        self._specs_mobo_model = self._spec_kv("Modelo",     "detectando…")
        self._specs_bios       = self._spec_kv("BIOS",       "detectando…")
        card.add(self._specs_mobo_man)
        card.add(self._specs_mobo_model)
        card.add(self._specs_bios)
        return card

    def _spec_card_cpu(self) -> Card:
        card = Card()
        card.layout().setSpacing(4)
        card.add(self._spec_title("PROCESSADOR"))
        cpu = cpu_static()
        card.add(self._spec_kv("Modelo",     cpu["name"]))
        card.add(self._spec_kv("Frequência", cpu["freq"]))
        card.add(self._spec_kv("Núcleos",    str(cpu["cores"])))
        card.add(self._spec_kv("Threads",    str(cpu["threads"])))

        self._specs_cpu_pct_label = QLabel("Uso atual · 0%")
        self._specs_cpu_pct_label.setStyleSheet(
            f"color: {Palette.FG_MUTED}; font-family: 'Consolas'; "
            f"font-size: 11px; background: transparent;"
        )
        card.add_spacing(2)
        card.add(self._specs_cpu_pct_label)

        self._specs_cpu_bar = QProgressBar()
        self._specs_cpu_bar.setFixedHeight(8)
        self._specs_cpu_bar.setTextVisible(False)
        self._specs_cpu_bar.setRange(0, 100)
        self._specs_cpu_bar.setStyleSheet(self._spec_bar_style())
        card.add(self._specs_cpu_bar)
        return card

    def _spec_card_gpu(self) -> Card:
        card = Card()
        card.layout().setSpacing(4)
        card.add(self._spec_title("PLACA DE VÍDEO"))
        self._specs_gpu_name   = self._spec_kv("Modelo",  "detectando…")
        self._specs_gpu_vram   = self._spec_kv("Memória", "detectando…")
        self._specs_gpu_driver = self._spec_kv("Driver",  "detectando…")
        card.add(self._specs_gpu_name)
        card.add(self._specs_gpu_vram)
        card.add(self._specs_gpu_driver)
        return card

    def _spec_card_ram(self) -> Card:
        card = Card()
        card.layout().setSpacing(4)
        card.add(self._spec_title("MEMÓRIA RAM"))
        m = mem_live()
        card.add(self._spec_kv("Total", self.format_size(m["total"])))
        self._specs_ram_used = self._spec_kv(
            "Usado", f"{self.format_size(m['used'])} ({m['pct']:.0f}%)"
        )
        card.add(self._specs_ram_used)

        card.add_spacing(2)
        self._specs_ram_bar = QProgressBar()
        self._specs_ram_bar.setFixedHeight(8)
        self._specs_ram_bar.setTextVisible(False)
        self._specs_ram_bar.setRange(0, 100)
        self._specs_ram_bar.setValue(int(m["pct"]))
        self._specs_ram_bar.setStyleSheet(self._spec_bar_style())
        card.add(self._specs_ram_bar)
        return card

    def _spec_card_disks(self) -> Card:
        card = Card()
        card.layout().setSpacing(4)
        card.add(self._spec_title("DISCOS"))
        for d in disks_info():
            line = QLabel(
                f"<span style='color:{Palette.ACCENT_CYAN}; font-weight:bold;'>{d['drive']}</span>"
                f"&nbsp;&nbsp;<span style='color:{Palette.FG_MUTED};'>{d['fs']}</span>"
                f"&nbsp;&nbsp;{self.format_size(d['used'])} usados / "
                f"{self.format_size(d['total'])}&nbsp;&nbsp;"
                f"<span style='color:{Palette.FG_MUTED};'>({d['pct']:.0f}%)</span>"
            )
            line.setTextFormat(Qt.RichText)
            line.setStyleSheet(
                f"color: {Palette.FG_BODY}; font-family: 'Consolas'; "
                f"font-size: 10px; background: transparent;"
            )
            card.add(line)
        return card

    def _spec_card_processes(self) -> Card:
        card = Card()
        card.layout().setSpacing(4)
        card.add(self._spec_title("PROCESSOS EM USO"))
        card.add(self._spec_kv("Total em execução", str(processes_count())))

        top_label = QLabel("Top 5 por consumo de memória")
        top_label.setStyleSheet(
            f"color: {Palette.FG_MUTED}; font-family: 'Segoe UI'; "
            f"font-size: 10px; background: transparent;"
        )
        card.add_spacing(2)
        card.add(top_label)

        for p in top_processes(5):
            mb = p["mem"] // (1024 * 1024)
            line = QLabel(
                f"<span style='color:{Palette.ACCENT_CYAN};'>{p['name']}</span>"
                f"&nbsp;&nbsp;<span style='color:{Palette.FG_MUTED};'>{mb} MB</span>"
            )
            line.setTextFormat(Qt.RichText)
            line.setStyleSheet(
                f"color: {Palette.FG_BODY}; font-family: 'Consolas'; "
                f"font-size: 10px; background: transparent;"
            )
            card.add(line)
        return card

    def _start_hardware_worker(self):
        cache = getattr(self, "_hardware_cache", None)
        if cache is not None:
            self._on_hardware_info(cache)
            return
        if getattr(self, "_hardware_worker", None) is not None:
            return
        self._hardware_worker = HardwareInfoWorker()
        self._hardware_worker.finished_info.connect(self._on_hardware_info)
        self._hardware_worker.start()

    def _on_hardware_info(self, info: dict):
        self._hardware_cache = info
        worker = getattr(self, "_hardware_worker", None)
        if worker is not None:
            try:
                worker.wait()
                worker.deleteLater()
            except Exception:
                pass
            self._hardware_worker = None

        if self._is_widget_alive(getattr(self, "_specs_gpu_name", None)):
            self._specs_gpu_name.setText(self._kv_html("Modelo", info["gpu_name"]))
        if self._is_widget_alive(getattr(self, "_specs_gpu_vram", None)):
            vram = info["gpu_vram"]
            vram_str = self.format_size(vram) if vram > 0 else "—"
            self._specs_gpu_vram.setText(self._kv_html("Memória", vram_str))
        if self._is_widget_alive(getattr(self, "_specs_gpu_driver", None)):
            self._specs_gpu_driver.setText(self._kv_html("Driver", info["gpu_driver"]))
        if self._is_widget_alive(getattr(self, "_specs_mobo_man", None)):
            self._specs_mobo_man.setText(self._kv_html("Fabricante", info["mobo_manufacturer"]))
        if self._is_widget_alive(getattr(self, "_specs_mobo_model", None)):
            self._specs_mobo_model.setText(self._kv_html("Modelo", info["mobo_model"]))
        if self._is_widget_alive(getattr(self, "_specs_bios", None)):
            self._specs_bios.setText(self._kv_html("BIOS", info["bios_version"]))

    def _update_specs_live_metrics(self):
        if not self._is_widget_alive(getattr(self, "_specs_cpu_bar", None)):
            return
        cpu = cpu_pct()
        self._specs_cpu_bar.setValue(int(cpu))
        if self._is_widget_alive(getattr(self, "_specs_cpu_pct_label", None)):
            self._specs_cpu_pct_label.setText(f"Uso atual · {cpu:.0f}%")

        m = mem_live()
        if self._is_widget_alive(getattr(self, "_specs_ram_bar", None)):
            self._specs_ram_bar.setValue(int(m["pct"]))
        if self._is_widget_alive(getattr(self, "_specs_ram_used", None)):
            self._specs_ram_used.setText(
                self._kv_html("Usado", f"{self.format_size(m['used'])} ({m['pct']:.0f}%)")
            )

    # ═══════════════════════════════════════════════════════════════════
    # OTIMIZAÇÃO
    # ═══════════════════════════════════════════════════════════════════
    def show_otimizacao(self):
        self.clear_screen()
        self._set_active_menu("otimizacao")
        self._stop_metrics_timer()

        panel = QWidget()
        panel.setStyleSheet("background: transparent;")
        panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        panel_lyt = QVBoxLayout(panel)
        panel_lyt.setContentsMargins(32, 24, 32, 24)
        panel_lyt.setSpacing(14)
        panel_lyt.setAlignment(Qt.AlignTop)

        title = QLabel("OTIMIZAÇÃO")
        title.setFont(QFont("Segoe UI", 22, QFont.Bold))
        title.setStyleSheet(f"color: {Palette.FG_PRIMARY}; background: transparent;")
        panel_lyt.addWidget(title)

        sub = QLabel("Ajustes persistentes de performance · totalmente reversíveis")
        sub.setStyleSheet(
            f"color: {Palette.FG_MUTED}; font-family: 'Segoe UI'; "
            f"font-size: 12px; background: transparent;"
        )
        panel_lyt.addWidget(sub)
        panel_lyt.addSpacing(4)

        panel_lyt.addWidget(self._otimizacao_hero())
        panel_lyt.addLayout(self._otimizacao_chips_row())

        self.content_lyt.addWidget(panel, 1)
        self._set_status_bar("optimize", "> Nenhuma otimização realizada ainda.")

    def _otimizacao_hero(self) -> HeroCard:
        """Hero card com contador de otimizações selecionadas + CTAs."""
        hero = HeroCard(accent_color=Palette.ACCENT_CYAN)
        hero.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        section = QLabel("OTIMIZAR SISTEMA")
        section.setAlignment(Qt.AlignCenter)
        section.setStyleSheet(
            f"color: {Palette.ACCENT_CYAN}; font-family: 'Segoe UI'; font-size: 11px;"
            f" font-weight: bold; letter-spacing: 1px; background: transparent;"
        )
        hero.add(section)

        state = _load_optimize_state()
        saved = state.get("user_selections") or {}
        if saved:
            selected = sum(1 for v in saved.values() if v)
        else:
            selected = sum(1 for c in _OPTIMIZE_CATEGORIES if c["default"])
        total_cats = len(_OPTIMIZE_CATEGORIES)

        hero.add(MetricLabel(f"{selected} de {total_cats}"))
        noun = "otimização selecionada" if selected == 1 else "otimizações selecionadas"
        desc = QLabel(noun)
        desc.setAlignment(Qt.AlignCenter)
        desc.setStyleSheet(
            f"color: {Palette.FG_MUTED}; font-family: 'Segoe UI'; "
            f"font-size: 11px; background: transparent;"
        )
        hero.add(desc)
        hero.add_spacing(6)

        btn = QPushButton("OTIMIZAR SISTEMA")
        btn.setFixedWidth(400)
        btn.setCursor(QCursor(Qt.PointingHandCursor))
        btn.setStyleSheet(
            f"QPushButton {{"
            f"  background-color: {self.primary}; color: black; font-weight: bold;"
            f"  border-radius: 8px; padding: 12px; border: none; font-size: 14px;"
            f"}}"
            f"QPushButton:hover {{ background-color: white; }}"
        )
        btn.clicked.connect(lambda: self.run_optimize_process())
        self.add_neon(btn, self.primary)
        hero.add(btn, alignment=Qt.AlignCenter)

        cfg = QPushButton("Configurar ajustes →")
        cfg.setFixedWidth(260)
        cfg.setCursor(QCursor(Qt.PointingHandCursor))
        cfg.setStyleSheet(
            f"background:transparent; color:{Palette.ACCENT_CYAN}; "
            f"border:1px solid {Palette.ACCENT_CYAN};"
            f"border-radius:6px; padding:6px; font-family:'Segoe UI'; font-size:11px;"
        )
        cfg.clicked.connect(self.show_otimizacao_avancada)
        hero.add(cfg, alignment=Qt.AlignCenter)

        revert = QPushButton("Restaurar padrões do Windows")
        revert.setFixedWidth(260)
        revert.setCursor(QCursor(Qt.PointingHandCursor))
        revert.setStyleSheet(
            "background: transparent; border: 1px solid #666; color: #888;"
            "font-weight: bold; border-radius: 6px; font-size: 11px; padding: 6px;"
        )
        revert.clicked.connect(self._confirm_revert_optimize)
        hero.add(revert, alignment=Qt.AlignCenter)

        return hero

    _OPTIMIZE_CHIP_LABELS = {
        "power_ultimate":    "Desempenho Máximo",
        "disk_optimize":     "Otimização de Disco",
        "hibernate_off":     "Hibernação",
        "telemetry_disable": "Telemetria",
    }

    def _otimizacao_chips_row(self) -> QHBoxLayout:
        """Linha de chips mostrando o estado selecionado de cada ajuste."""
        state = _load_optimize_state()
        saved = state.get("user_selections") or {}

        row = QHBoxLayout()
        row.setSpacing(8)
        row.addStretch(1)
        for cat in _OPTIMIZE_CATEGORIES:
            cid = cat["id"]
            label = self._OPTIMIZE_CHIP_LABELS.get(cid, cat["label"])
            if saved:
                is_on = bool(saved.get(cid, False))
            else:
                is_on = bool(cat["default"])
            row.addWidget(Chip(label, state=("on" if is_on else "off")))
        row.addStretch(1)
        return row

    def show_otimizacao_avancada(self):
        self.clear_screen()
        self.add_title("CONFIGURAR OTIMIZAÇÃO")
        sub = QLabel("Selecione os ajustes desejados. Os marcados por padrão são seguros para todos.")
        sub.setStyleSheet(f"color: {Palette.FG_MUTED}; font-size: 11px; margin-bottom: 8px;")
        sub.setWordWrap(True)
        sub.setAlignment(Qt.AlignCenter)
        self.content_lyt.addWidget(sub)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        inner = QWidget()
        inner.setStyleSheet("background: transparent;")
        inner_lyt = QVBoxLayout(inner)
        inner_lyt.setSpacing(6)
        inner_lyt.setContentsMargins(4, 4, 4, 4)

        self._optimize_checkboxes = {}

        # Carrega seleções salvas; se item não tem valor salvo, usa o default da categoria
        state = _load_optimize_state()
        saved = state.get("user_selections") or {}

        safe_cats = [c for c in _OPTIMIZE_CATEGORIES if c["default"]]
        opt_cats  = [c for c in _OPTIMIZE_CATEGORIES if not c["default"]]

        safe_hdr = QLabel("── RECOMENDADO (seguro)")
        safe_hdr.setStyleSheet(f"color: {Palette.CYAN}; font-weight: bold; font-size: 11px; margin-top: 4px;")
        inner_lyt.addWidget(safe_hdr)
        for cat in safe_cats:
            checked = saved.get(cat["id"], cat["default"])
            use_toggle = (cat["id"] == "hibernate_off")
            inner_lyt.addWidget(self._build_optimize_row(cat, checked=checked, use_toggle=use_toggle))

        opt_hdr = QLabel("── OPCIONAL (revise antes de ativar)")
        opt_hdr.setStyleSheet(f"color: {Palette.STATE_WARN}; font-weight: bold; font-size: 11px; margin-top: 10px;")
        inner_lyt.addWidget(opt_hdr)
        for cat in opt_cats:
            checked = saved.get(cat["id"], cat["default"])
            use_toggle = (cat["id"] == "hibernate_off")
            inner_lyt.addWidget(self._build_optimize_row(cat, checked=checked, use_toggle=use_toggle))

        inner_lyt.addStretch()
        scroll.setWidget(inner)
        self.content_lyt.addWidget(scroll, 1)

        # Contador dinâmico de seleções
        self._optimize_counter_label = QLabel("")
        self._optimize_counter_label.setAlignment(Qt.AlignCenter)
        self._optimize_counter_label.setStyleSheet(
            f"color: {Palette.FG_MUTED}; font-family: 'Consolas'; font-size: 11px; margin-top: 6px;"
        )
        self.content_lyt.addWidget(self._optimize_counter_label)
        self._update_optimize_counter()

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        back = QPushButton("Voltar")
        back.setFixedWidth(100)
        back.setStyleSheet(
            f"background: transparent; border: 1px solid {Palette.STATE_OFF_BRD}; color: {Palette.FG_MUTED};"
            "font-weight: bold; border-radius: 6px; padding: 8px;"
        )
        back.clicked.connect(self.show_otimizacao)
        save = QPushButton("Salvar alterações")
        save.setFixedWidth(200)
        save.setStyleSheet(
            f"background: {Palette.CYAN}; color: {Palette.BG_BASE}; border: none;"
            "border-radius: 6px; padding: 8px; font-family: 'Segoe UI'; font-weight: bold;"
        )
        save.clicked.connect(self._save_optimize_and_return)
        btn_row.addWidget(back)
        btn_row.addSpacing(10)
        btn_row.addWidget(save)
        btn_row.addStretch(1)
        self.content_lyt.addLayout(btn_row)

        self.add_status_bar("> Configure aqui. Execução acontece na tela anterior em 'Otimizar Sistema'.")

    def _build_optimize_row(self, cat, checked, use_toggle=False):
        row = QFrame()
        row.setStyleSheet(
            f"QFrame {{ background: {Palette.BG_CARD}; border: 1px solid {Palette.BORDER_SUBTLE}; border-radius: {Spacing.RADIUS_ROW}px; }}"
        )
        lyt = QVBoxLayout(row)
        lyt.setContentsMargins(10, 8, 10, 8)
        lyt.setSpacing(2)

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)

        if use_toggle:
            cb = ToggleSwitch()
            cb.setChecked(checked)
            top.addWidget(cb)
            top.addSpacing(8)

            lbl = QLabel(cat["label"])
            lbl.setStyleSheet(f"color: {Palette.FG_PRIMARY}; font-family: 'Segoe UI'; font-size: 12px;")
            top.addWidget(lbl, 1)
        else:
            cb = QCheckBox(cat["label"])
            cb.setChecked(checked)
            cb.setStyleSheet(
                f"QCheckBox {{ color: {Palette.FG_PRIMARY}; font-family: 'Segoe UI'; font-size: 12px; }}"
                "QCheckBox::indicator { width: 14px; height: 14px; }"
            )
            top.addWidget(cb, 1)

        impact = QLabel(cat["impact"])
        impact.setStyleSheet(f"color: {Palette.CYAN}; font-family: 'Consolas'; font-size: 10px;")
        top.addWidget(impact)

        self._optimize_checkboxes[cat["id"]] = cb
        cb.stateChanged.connect(self._on_optimize_selection_changed)
        lyt.addLayout(top)

        desc = QLabel(cat["desc"])
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {Palette.FG_MUTED}; font-family: 'Segoe UI'; font-size: 10px; padding-left: 22px;")
        lyt.addWidget(desc)

        if cat.get("warning"):
            warn = QLabel("⚠ " + cat["warning"])
            warn.setWordWrap(True)
            warn.setStyleSheet(f"color: {Palette.STATE_WARN}; font-family: 'Segoe UI'; font-size: 10px; padding-left: 22px;")
            lyt.addWidget(warn)

        return row

    def _on_optimize_selection_changed(self, _state=None):
        """Chamado sempre que qualquer checkbox/toggle muda — salva e atualiza contador."""
        self._save_optimize_selections()
        self._update_optimize_counter()

    def _save_optimize_selections(self):
        state = _load_optimize_state()
        state["user_selections"] = {
            cid: bool(cb.isChecked()) for cid, cb in self._optimize_checkboxes.items()
        }
        _save_optimize_state(state)

    def _update_optimize_counter(self):
        if not hasattr(self, "_optimize_counter_label") or self._optimize_counter_label is None:
            return
        try:
            selected = sum(1 for cb in self._optimize_checkboxes.values() if cb.isChecked())
            total = len(self._optimize_checkboxes)
            self._optimize_counter_label.setText(f"{selected} de {total} otimizações selecionadas")
        except RuntimeError:
            # Widget já foi destruído (tela trocou) — ignora
            pass

    def _save_optimize_and_return(self):
        self._save_optimize_selections()
        selected = sum(1 for cb in self._optimize_checkboxes.values() if cb.isChecked())
        noun = "otimização selecionada" if selected == 1 else "otimizações selecionadas"
        self._pending_status["optimize"] = f"> ✓ Preferências salvas ({selected} {noun})"
        self.show_otimizacao()

    def run_optimize_process(self, selected_ids=None, mode: str = "apply"):
        if not isinstance(selected_ids, set):
            # Respeita as seleções salvas pelo usuário; cai nos defaults se nunca configurou
            state = _load_optimize_state()
            saved = state.get("user_selections") or {}
            if saved:
                selected_ids = {cid for cid, v in saved.items() if v}
            else:
                selected_ids = {c["id"] for c in _OPTIMIZE_CATEGORIES if c["default"]}
        if self._optimize_worker is not None:
            return
        self._optimize_log_lines = []
        self.show_otimizacao_progresso(mode=mode)
        self._optimize_worker = OptimizeWorker(selected_ids, mode=mode)
        self._optimize_worker.step_done.connect(self._on_optimize_step)
        self._optimize_worker.finished.connect(self._on_optimize_done)
        self._optimize_worker.start()

    def _confirm_revert_optimize(self):
        m = QMessageBox(self)
        m.setWindowTitle("Restaurar padrões")
        m.setText("Deseja restaurar as otimizações aos padrões do Windows?")
        m.setInformativeText(
            "Reverterá: plano de energia para 'Balanceado', reativará hibernação "
            "e reativará a telemetria do Windows.\n\n"
            "A otimização de disco não é revertida (é uma operação de manutenção)."
        )
        m.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        m.setStyleSheet(
            "QLabel{color:white; font-family:'Segoe UI';} "
            "QMessageBox{background:#030407; border:1px solid #0eb3ff;} "
            "QPushButton{color:white; border:1px solid #0eb3ff; padding:5px; min-width:80px;}"
        )
        if m.exec() == QMessageBox.Yes:
            all_ids = {c["id"] for c in _OPTIMIZE_CATEGORIES}
            self.run_optimize_process(selected_ids=all_ids, mode="revert")

    def show_otimizacao_progresso(self, mode: str = "apply"):
        self.clear_screen()
        title = "OTIMIZAÇÃO EM ANDAMENTO" if mode == "apply" else "RESTAURANDO PADRÕES"
        self.add_title(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            f"QScrollArea {{ border: 1px solid {Palette.BORDER_SUBTLE}; "
            f"background: {Palette.BG_CARD}; border-radius: 8px; }}"
        )
        log_inner = QWidget()
        log_inner.setStyleSheet("background: transparent;")
        log_lyt = QVBoxLayout(log_inner)
        log_lyt.setAlignment(Qt.AlignTop)
        log_lyt.setContentsMargins(14, 12, 14, 12)

        self._optimize_log_label = QLabel("> Iniciando...")
        self._optimize_log_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self._optimize_log_label.setStyleSheet(
            f"color: {self.primary}; font-family: 'Consolas'; font-size: 12px; line-height: 180%;"
        )
        self._optimize_log_label.setWordWrap(True)
        log_lyt.addWidget(self._optimize_log_label)
        scroll.setWidget(log_inner)
        self.content_lyt.addWidget(scroll, 1)

        self._optimize_total_label = QLabel("")
        self._optimize_total_label.setFont(QFont("Segoe UI", 16, QFont.Bold))
        self._optimize_total_label.setAlignment(Qt.AlignCenter)
        self._optimize_total_label.setStyleSheet(f"color: {self.primary}; margin-top: 8px;")
        self._optimize_total_label.hide()
        self.content_lyt.addWidget(self._optimize_total_label)

        self._optimize_btn_voltar = QPushButton("VOLTAR")
        self._optimize_btn_voltar.setFixedWidth(200)
        self._optimize_btn_voltar.setEnabled(False)
        self._optimize_btn_voltar.setStyleSheet(
            f"background: transparent; border: 1px solid {Palette.STATE_OFF_BRD}; color: {Palette.FG_SUBTLE};"
            "font-weight: bold; border-radius: 8px; padding: 10px;"
        )
        self._optimize_btn_voltar.clicked.connect(self.show_otimizacao)
        self.content_lyt.addWidget(self._optimize_btn_voltar, alignment=Qt.AlignCenter)

    def _on_optimize_step(self, label: str, ok: bool, detail: str):
        log_label = getattr(self, "_optimize_log_label", None)
        if not self._is_widget_alive(log_label):
            return
        mark = "✓" if ok else "✗"
        extra = f"   ({detail})" if detail else ""
        self._optimize_log_lines.append(f"{mark}  {label}{extra}")
        log_label.setText("\n".join(self._optimize_log_lines))

    def _on_optimize_done(self, applied: int, failed: int):
        if self._optimize_worker is not None:
            try:
                self._optimize_worker.wait()
                self._optimize_worker.deleteLater()
            except Exception:
                pass
            self._optimize_worker = None

        if applied > 0 and failed == 0:
            noun = "otimização aplicada" if applied == 1 else "otimizações aplicadas"
            msg = f"✓  {applied} {noun}"
        elif applied > 0 and failed > 0:
            a_word = "aplicada" if applied == 1 else "aplicadas"
            f_word = "falha" if failed == 1 else "falhas"
            msg = f"⚠  {applied} {a_word}, {failed} com {f_word}"
        elif failed > 0:
            noun = "otimização" if failed == 1 else "otimizações"
            msg = f"✗  Falha em {failed} {noun}"
        else:
            msg = "Nenhuma otimização selecionada"
        _save_module_status("optimize", msg)

        total_label = getattr(self, "_optimize_total_label", None)
        btn_voltar  = getattr(self, "_optimize_btn_voltar",  None)
        if self._is_widget_alive(total_label):
            total_label.setText(msg)
            total_label.show()
            self.add_neon(total_label, self.primary)
        if self._is_widget_alive(btn_voltar):
            btn_voltar.setEnabled(True)
            btn_voltar.setStyleSheet(
                f"background: transparent; border: 1px solid {self.primary}; color: {self.primary};"
                "font-weight: bold; border-radius: 8px; padding: 10px;"
            )

    # ═══════════════════════════════════════════════════════════════════
    # REPAROS
    # ═══════════════════════════════════════════════════════════════════
    def show_reparos(self):
        self.clear_screen()
        self._set_active_menu("reparos")
        self._stop_metrics_timer()

        panel = QWidget()
        panel.setStyleSheet("background: transparent;")
        panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        panel_lyt = QVBoxLayout(panel)
        panel_lyt.setContentsMargins(32, 24, 32, 24)
        panel_lyt.setSpacing(10)
        panel_lyt.setAlignment(Qt.AlignTop)

        title = QLabel("REPAROS")
        title.setFont(QFont("Segoe UI", 22, QFont.Bold))
        title.setStyleSheet(f"color: {Palette.FG_PRIMARY}; background: transparent;")
        panel_lyt.addWidget(title)

        sub = QLabel("Cada reparo é independente · escolha conforme o problema")
        sub.setStyleSheet(
            f"color: {Palette.FG_MUTED}; font-family: 'Segoe UI'; "
            f"font-size: 12px; background: transparent;"
        )
        panel_lyt.addWidget(sub)
        panel_lyt.addSpacing(4)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        inner = QWidget()
        inner.setStyleSheet("background: transparent;")
        inner_lyt = QVBoxLayout(inner)
        inner_lyt.setSpacing(8)
        inner_lyt.setContentsMargins(0, 0, 8, 0)

        essentials = [t for t in _REPAIR_TOOLS if t["category"] == "essential"]
        advanced   = [t for t in _REPAIR_TOOLS if t["category"] == "advanced"]

        hdr1 = QLabel("── ESSENCIAIS")
        hdr1.setStyleSheet(
            f"color: {Palette.ACCENT_CYAN}; font-family: 'Segoe UI'; font-size: 11px;"
            f" font-weight: bold; letter-spacing: 1px; background: transparent;"
        )
        inner_lyt.addWidget(hdr1)
        inner_lyt.addLayout(self._repair_grid(essentials))

        inner_lyt.addSpacing(8)

        hdr2 = QLabel("── AVANÇADOS")
        hdr2.setStyleSheet(
            f"color: {Palette.STATE_WARN}; font-family: 'Segoe UI'; font-size: 11px;"
            f" font-weight: bold; letter-spacing: 1px; background: transparent;"
        )
        inner_lyt.addWidget(hdr2)
        inner_lyt.addLayout(self._repair_grid(advanced))

        inner_lyt.addStretch(1)
        scroll.setWidget(inner)
        panel_lyt.addWidget(scroll, 1)

        self.content_lyt.addWidget(panel, 1)
        self._set_status_bar("repair", "> Nenhum reparo executado ainda.")

    def _repair_grid(self, tools: list) -> QGridLayout:
        """Grid 2-colunas com cards dos reparos fornecidos."""
        grid = QGridLayout()
        grid.setSpacing(10)
        grid.setContentsMargins(0, 0, 0, 0)
        for i, tool in enumerate(tools):
            r, c = divmod(i, 2)
            grid.addWidget(self._build_repair_card(tool), r, c)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        return grid

    def _build_repair_card(self, tool) -> Card:
        """Card individual de uma ferramenta de reparo."""
        card = Card()
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        card.layout().setContentsMargins(14, 12, 14, 12)
        card.layout().setSpacing(6)

        title = QLabel(tool["label"])
        title.setWordWrap(True)
        title.setStyleSheet(
            f"color: {Palette.FG_PRIMARY}; font-family: 'Segoe UI'; "
            f"font-size: 12px; font-weight: bold; background: transparent;"
        )
        card.add(title)

        tags = [tool["duration"]]
        if tool["reboot"]:
            tags.append("REBOOT")
        tag = QLabel(" · ".join(tags))
        tag.setStyleSheet(
            f"color: {Palette.ACCENT_CYAN}; font-family: 'Consolas'; "
            f"font-size: 10px; background: transparent;"
        )
        card.add(tag)

        desc = QLabel(tool["desc"])
        desc.setWordWrap(True)
        desc.setStyleSheet(
            f"color: {Palette.FG_MUTED}; font-family: 'Segoe UI'; "
            f"font-size: 10px; background: transparent;"
        )
        card.add(desc)

        if tool.get("warning"):
            warn = QLabel("⚠ " + tool["warning"])
            warn.setWordWrap(True)
            warn.setStyleSheet(
                f"color: {Palette.STATE_WARN}; font-family: 'Segoe UI'; "
                f"font-size: 10px; background: transparent;"
            )
            card.add(warn)

        card.add_stretch(1)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        btn = QPushButton("Executar")
        btn.setFixedWidth(110)
        btn.setCursor(QCursor(Qt.PointingHandCursor))
        btn.setStyleSheet(
            f"QPushButton {{"
            f"  background: {self.primary}; color: #030407; border: none;"
            f"  border-radius: 5px; padding: 6px; font-family: 'Segoe UI'; "
            f"  font-weight: bold; font-size: 11px;"
            f"}}"
            f"QPushButton:hover {{ background: white; }}"
        )
        tid = tool["id"]
        btn.clicked.connect(lambda _=False, t=tid: self._confirm_repair(t))
        btn_row.addWidget(btn)
        card.layout().addLayout(btn_row)

        return card

    def _confirm_repair(self, tool_id: str):
        tool = next((t for t in _REPAIR_TOOLS if t["id"] == tool_id), None)
        if tool is None:
            return
        m = QMessageBox(self)
        m.setWindowTitle("Confirmar reparo")
        m.setText(f"Executar: {tool['label']}?")
        info = f"Duração estimada: {tool['duration']}"
        if tool["reboot"]:
            info += "\n\n⚠ Reinicialização necessária após a execução."
        if tool.get("warning"):
            info += f"\n\n{tool['warning']}"
        m.setInformativeText(info)
        m.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        m.setStyleSheet(
            "QLabel{color:white; font-family:'Segoe UI';} "
            "QMessageBox{background:#030407; border:1px solid #0eb3ff;} "
            "QPushButton{color:white; border:1px solid #0eb3ff; padding:5px; min-width:80px;}"
        )
        if m.exec() == QMessageBox.Yes:
            self.run_repair_process(tool_id)

    def run_repair_process(self, tool_id: str):
        if self._repair_worker is not None:
            return
        self._repair_log_lines = []
        self._repair_current_tool = tool_id
        self.show_reparos_progresso(tool_id)
        self._repair_worker = RepairWorker(tool_id)
        self._repair_worker.step_done.connect(self._on_repair_step)
        self._repair_worker.finished.connect(self._on_repair_done)
        self._repair_worker.start()

    def show_reparos_progresso(self, tool_id: str):
        self.clear_screen()
        tool = next((t for t in _REPAIR_TOOLS if t["id"] == tool_id), None)
        title = tool["label"].upper() if tool else "REPARO EM ANDAMENTO"
        self.add_title(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            f"QScrollArea {{ border: 1px solid {Palette.BORDER_SUBTLE}; background: {Palette.BG_CARD}; border-radius: 8px; }}"
            f"QScrollBar:vertical {{ width: 6px; background: {Palette.BG_BASE}; border-radius: 3px; }}"
            f"QScrollBar::handle:vertical {{ background: {Palette.CYAN}; border-radius: 3px; }}"
        )
        log_inner = QWidget()
        log_inner.setStyleSheet("background: transparent;")
        log_lyt = QVBoxLayout(log_inner)
        log_lyt.setAlignment(Qt.AlignTop)
        log_lyt.setContentsMargins(14, 12, 14, 12)

        self._repair_log_label = QLabel("> Iniciando reparo...")
        self._repair_log_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self._repair_log_label.setStyleSheet(
            f"color: {self.primary}; font-family: 'Consolas'; font-size: 12px; line-height: 180%;"
        )
        self._repair_log_label.setWordWrap(True)
        log_lyt.addWidget(self._repair_log_label)
        scroll.setWidget(log_inner)
        self.content_lyt.addWidget(scroll, 1)

        self._repair_summary_label = QLabel("")
        self._repair_summary_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self._repair_summary_label.setAlignment(Qt.AlignCenter)
        self._repair_summary_label.setWordWrap(True)
        self._repair_summary_label.setStyleSheet(f"color: {self.primary}; margin-top: 8px;")
        self._repair_summary_label.hide()
        self.content_lyt.addWidget(self._repair_summary_label)

        self._repair_btn_voltar = QPushButton("VOLTAR")
        self._repair_btn_voltar.setFixedWidth(200)
        self._repair_btn_voltar.setEnabled(False)
        self._repair_btn_voltar.setStyleSheet(
            f"background: transparent; border: 1px solid {Palette.BORDER_SUBTLE}; color: {Palette.FG_MUTED};"
            "font-weight: bold; border-radius: 8px; padding: 10px;"
        )
        self._repair_btn_voltar.clicked.connect(self.show_reparos)
        self.content_lyt.addWidget(self._repair_btn_voltar, alignment=Qt.AlignCenter)

    def _on_repair_step(self, label: str, ok: bool, detail: str):
        log_label = getattr(self, "_repair_log_label", None)
        if not self._is_widget_alive(log_label):
            return
        mark = "✓" if ok else "✗"
        extra = f"   ({detail})" if detail else ""
        self._repair_log_lines.append(f"{mark}  {label}{extra}")
        log_label.setText("\n".join(self._repair_log_lines))

    def _on_repair_done(self, overall_ok: bool, summary: str):
        if self._repair_worker is not None:
            try:
                self._repair_worker.wait()
                self._repair_worker.deleteLater()
            except Exception:
                pass
            self._repair_worker = None

        _save_module_status("repair", summary)
        color = self.primary if overall_ok else Palette.STATE_WARN

        summary_label = getattr(self, "_repair_summary_label", None)
        btn_voltar    = getattr(self, "_repair_btn_voltar",    None)
        if self._is_widget_alive(summary_label):
            summary_label.setText(summary)
            summary_label.setStyleSheet(f"color: {color}; margin-top: 8px;")
            summary_label.show()
            self.add_neon(summary_label, color)
        if self._is_widget_alive(btn_voltar):
            btn_voltar.setEnabled(True)
            btn_voltar.setStyleSheet(
                f"background: transparent; border: 1px solid {self.primary}; color: {self.primary};"
                "font-weight: bold; border-radius: 8px; padding: 10px;"
            )
    def show_gamer(self):
        self.clear_screen()
        self._set_active_menu("gamer")
        self._stop_metrics_timer()

        active = self.gamer_engine.is_active()
        snapshot = self.gamer_engine.active_snapshot() if active else None

        panel = QWidget()
        panel.setStyleSheet("background: transparent;")
        panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        panel_lyt = QVBoxLayout(panel)
        panel_lyt.setContentsMargins(32, 24, 32, 24)
        panel_lyt.setSpacing(14)
        panel_lyt.setAlignment(Qt.AlignTop)

        title = QLabel("MODO GAMER")
        title.setFont(QFont("Segoe UI", 22, QFont.Bold))
        title.setStyleSheet(f"color: {Palette.FG_PRIMARY}; background: transparent;")
        panel_lyt.addWidget(title)

        gamer_sub = QLabel("18 tweaks reversíveis de CPU, GPU, sistema e rede")
        gamer_sub.setStyleSheet(
            f"color: {Palette.FG_MUTED}; font-family: 'Segoe UI'; "
            f"font-size: 12px; background: transparent;"
        )
        panel_lyt.addWidget(gamer_sub)
        panel_lyt.addSpacing(4)

        hero = HeroCard(accent_color=Palette.ACCENT_PURPLE)
        hero.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        metric = MetricLabel("● ATIVO" if active else "● INATIVO")
        metric.setStyleSheet(
            f"color: {Palette.STATE_ON if active else Palette.FG_MUTED};"
            f" background: transparent;"
        )
        hero.add(metric)

        if active and snapshot:
            sub_text = f"desde {snapshot.created_at}"
        else:
            sub_text = "pronto para ativar otimizações para jogos"
        sub = QLabel(sub_text)
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet(
            f"color: {Palette.FG_MUTED}; font-family: 'Segoe UI'; "
            f"font-size: 11px; background: transparent;"
        )
        hero.add(sub)
        panel_lyt.addWidget(hero)

        if active:
            btn = QPushButton("DESATIVAR MODO GAMER")
            btn.setStyleSheet(
                f"QPushButton {{"
                f"  background-color: {self.danger}; color: white; font-weight: bold;"
                f"  border-radius: 8px; padding: 12px; border: none; font-size: 14px;"
                f"}}"
                f"QPushButton:hover {{ background-color: #ff6b6b; }}"
            )
            btn.clicked.connect(self.run_gamer_deactivate)
            self.add_neon(btn, self.danger)
        else:
            btn = QPushButton("ATIVAR MODO GAMER")
            btn.setStyleSheet(
                f"QPushButton {{"
                f"  background: qlineargradient(x1:0, y1:0, x2:1, y2:0,"
                f"    stop:0 {Palette.ACCENT_CYAN}, stop:1 {Palette.ACCENT_PURPLE});"
                f"  color: white; font-weight: bold;"
                f"  border-radius: 8px; padding: 12px; border: none; font-size: 14px;"
                f"  letter-spacing: 1px;"
                f"}}"
                f"QPushButton:hover {{"
                f"  background: qlineargradient(x1:0, y1:0, x2:1, y2:0,"
                f"    stop:0 #2dc3ff, stop:1 #8a2bff);"
                f"}}"
            )
            btn.clicked.connect(self.run_gamer_activate)
            self.add_neon(btn, Palette.ACCENT_PURPLE)
        btn.setCursor(QCursor(Qt.PointingHandCursor))
        btn.setFixedWidth(400)
        panel_lyt.addWidget(btn, alignment=Qt.AlignCenter)

        adv = QPushButton("Avançado (granular) →")
        adv.setFixedWidth(260)
        adv.setCursor(QCursor(Qt.PointingHandCursor))
        adv.setStyleSheet(
            f"background:transparent; color:{Palette.ACCENT_PURPLE}; "
            f"border:1px solid {Palette.ACCENT_PURPLE};"
            f"border-radius:6px; padding:6px; font-family:'Segoe UI'; font-size:11px;"
        )
        adv.clicked.connect(self.show_gamer_advanced)
        panel_lyt.addWidget(adv, alignment=Qt.AlignCenter)

        panel_lyt.addSpacing(4)

        grouped = self.gamer_engine.tweaks_by_category()
        cat_row = QHBoxLayout()
        cat_row.setSpacing(12)
        cat_row.addWidget(self._gamer_category_card("CPU",     len(grouped[Category.CPU])))
        cat_row.addWidget(self._gamer_category_card("GPU",     len(grouped[Category.GPU])))
        cat_row.addWidget(self._gamer_category_card("SISTEMA", len(grouped[Category.SYSTEM])))
        cat_row.addWidget(self._gamer_category_card("REDE",    len(grouped[Category.NETWORK])))
        panel_lyt.addLayout(cat_row)

        enabled = load_enabled_optins()
        if enabled:
            n = len(enabled)
            noun = "tweak opt-in ativo" if n == 1 else "tweaks opt-in ativos"
            opt_lbl = QLabel(f"{n} {noun}: {', '.join(sorted(enabled))}")
            opt_lbl.setAlignment(Qt.AlignCenter)
            opt_lbl.setWordWrap(True)
            opt_lbl.setStyleSheet(
                f"color: {Palette.ACCENT_PURPLE}; font-family: 'Consolas'; "
                f"font-size: 10px; background: transparent;"
            )
            panel_lyt.addWidget(opt_lbl)

        self.content_lyt.addWidget(panel, 1)
        self._set_status_bar("gamer", "> Modo Gamer nunca foi ativado.")

    def _gamer_category_card(self, name: str, count: int) -> Card:
        """Mini card: número da contagem + label da categoria."""
        card = Card()
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        card.layout().setContentsMargins(12, 12, 12, 12)
        card.layout().setSpacing(2)

        metric = QLabel(str(count))
        metric.setFont(QFont("Segoe UI", 24, QFont.Bold))
        metric.setAlignment(Qt.AlignCenter)
        metric.setStyleSheet(f"color: {Palette.FG_PRIMARY}; background: transparent;")
        card.add(metric)

        label = QLabel(name)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet(
            f"color: {Palette.ACCENT_PURPLE}; font-family: 'Segoe UI'; "
            f"font-size: 10px; font-weight: bold; letter-spacing: 1px; background: transparent;"
        )
        card.add(label)
        return card

    def show_gamer_advanced(self):
        self.clear_screen()
        self.add_title("MODO GAMER — AVANÇADO", self.secondary)

        intro = QLabel(
            "Escolha quais tweaks rodam no one-click.\n"
            "Os essenciais sempre rodam. Os marcados como opt-in só rodam se você habilitar aqui."
        )
        intro.setAlignment(Qt.AlignCenter)
        intro.setWordWrap(True)
        intro.setStyleSheet(f"color:{Palette.FG_MUTED}; font-family:'Segoe UI'; font-size:12px;")
        self.content_lyt.addWidget(intro)
        self.content_lyt.addSpacing(10)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            f"QScrollArea {{ border: none; background: transparent; }}"
            f"QScrollBar:vertical {{ width: 6px; background: {Palette.BG_BASE}; border-radius: 3px; }}"
            f"QScrollBar::handle:vertical {{ background: {Palette.CYAN}; border-radius: 3px; }}"
        )
        inner = QWidget()
        inner_lyt = QVBoxLayout(inner)
        inner_lyt.setContentsMargins(10, 0, 10, 0)
        inner_lyt.setSpacing(8)

        enabled = load_enabled_optins()
        self._advanced_checks = {}

        grouped = self.gamer_engine.tweaks_by_category()
        cat_labels = {
            Category.CPU: "CPU",
            Category.GPU: "GPU",
            Category.SYSTEM: "Sistema",
            Category.NETWORK: "Rede",
        }
        for cat, tweaks in grouped.items():
            if not tweaks:
                continue
            header = QLabel(cat_labels[cat])
            header.setStyleSheet(
                f"color:{self.primary}; font-family:'Consolas'; font-weight:bold; font-size:12px;"
            )
            inner_lyt.addWidget(header)
            for tw in tweaks:
                row = self._build_advanced_row(tw, tw.id in enabled)
                inner_lyt.addWidget(row)
            inner_lyt.addSpacing(6)

        inner_lyt.addStretch(1)
        scroll.setWidget(inner)
        self.content_lyt.addWidget(scroll, stretch=1)

        btn_row = QHBoxLayout()
        back = QPushButton("← Voltar")
        back.setFixedWidth(120)
        back.setStyleSheet(
            f"background: transparent; color: {Palette.FG_MUTED}; border: 1px solid {Palette.BORDER_SUBTLE};"
            "border-radius: 6px; padding: 8px; font-family: 'Segoe UI';"
        )
        back.clicked.connect(self.show_gamer)
        save = QPushButton("Salvar preferências")
        save.setFixedWidth(200)
        save.setStyleSheet(
            f"background:{self.primary}; color:#030407; border:none; border-radius:6px;"
            "padding:8px; font-family:'Segoe UI'; font-weight:bold;"
        )
        save.clicked.connect(self._save_advanced_prefs)
        btn_row.addStretch(1)
        btn_row.addWidget(back)
        btn_row.addSpacing(10)
        btn_row.addWidget(save)
        btn_row.addStretch(1)
        self.content_lyt.addLayout(btn_row)

        self.add_status_bar("> Ajustes não aplicam imediatamente — salvar e ativar o Modo Gamer.")

    def _build_advanced_row(self, tweak, checked):
        row = QFrame()
        row.setStyleSheet(
            f"QFrame{{background:{Palette.BG_CARD}; border:1px solid {Palette.BORDER_SUBTLE}; border-radius:6px;}}"
        )
        lyt = QVBoxLayout(row)
        lyt.setContentsMargins(10, 8, 10, 8)
        lyt.setSpacing(2)

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        cb = QCheckBox(tweak.label)
        cb.setStyleSheet(
            f"QCheckBox{{color:{Palette.FG_PRIMARY}; font-family:'Segoe UI'; font-size:12px;}}"
            "QCheckBox::indicator{width:14px; height:14px;}"
        )
        if tweak.opt_in:
            cb.setChecked(checked)
            cb.setEnabled(True)
            self._advanced_checks[tweak.id] = cb
        else:
            cb.setChecked(True)
            cb.setEnabled(False)
            cb.setToolTip("Tweak essencial — sempre ativo no one-click")
        top.addWidget(cb)
        top.addStretch(1)

        tag_parts = [tweak.risk.value.upper()]
        if tweak.requires_reboot:
            tag_parts.append("REBOOT")
        if tweak.opt_in:
            tag_parts.append("OPT-IN")
        tag = QLabel(" · ".join(tag_parts))
        color = {"low": Palette.STATE_ON, "medium": Palette.STATE_WARN, "high": Palette.STATE_DANGER}.get(tweak.risk.value, Palette.FG_MUTED)
        tag.setStyleSheet(f"color:{color}; font-family:'Consolas'; font-size:10px;")
        top.addWidget(tag)
        lyt.addLayout(top)

        if tweak.description:
            desc = QLabel(tweak.description)
            desc.setWordWrap(True)
            desc.setStyleSheet(f"color:{Palette.FG_MUTED}; font-family:'Segoe UI'; font-size:10px;")
            lyt.addWidget(desc)

        if tweak.warning:
            warn = QLabel("⚠ " + tweak.warning)
            warn.setWordWrap(True)
            warn.setStyleSheet(f"color:{Palette.STATE_WARN}; font-family:'Segoe UI'; font-size:10px;")
            lyt.addWidget(warn)

        return row

    def _save_advanced_prefs(self):
        selected = {tid for tid, cb in self._advanced_checks.items() if cb.isChecked()}
        save_enabled_optins(selected)
        n = len(selected)
        noun = "tweak ativo" if n == 1 else "tweaks ativos"
        self._pending_status["gamer"] = f"> ✓ Preferências salvas ({n} {noun})"
        self.show_gamer()

    def add_danger_btn(self, text, func):
        b = QPushButton(text); b.setFixedWidth(400)
        b.setStyleSheet(f"""
            background-color: {self.danger}; color: white; font-weight: bold;
            border-radius: 8px; padding: 12px; border: none; font-size: 14px;
        """)
        b.clicked.connect(func)
        self.content_lyt.addWidget(b, alignment=Qt.AlignCenter)
        self.add_neon(b, self.danger)

    def run_gamer_activate(self):
        self._run_gamer_task("activate")

    def run_gamer_deactivate(self):
        self._run_gamer_task("deactivate")

    def _run_gamer_task(self, action):
        # Defesa: se um worker antigo ficou referenciado mas já não está
        # rodando (ex.: cleanup falhou silenciosamente), descarta antes
        # de bloquear nova execução.
        worker = self._gamer_worker
        if worker is not None:
            try:
                still_running = worker.isRunning()
            except Exception:
                still_running = False
            if still_running:
                return
            try:
                worker.deleteLater()
            except Exception:
                pass
            self._gamer_worker = None

        web = getattr(self, "_web_view", None)
        if web is not None:
            msg = "Aplicando Modo Gamer... aguarde." if action == "activate" else "Desativando Modo Gamer..."
            web.page().runJavaScript(f"window.setStatus('{msg}');")
            web.page().runJavaScript("document.getElementById('gamer-terminal').style.display='block'; window.clearTerminal();")
            web.page().runJavaScript("window.appendTerminalLine('> Iniciando...');")
        else:
            status_lbl = getattr(self, "status_lbl", None)
            if self._is_widget_alive(status_lbl):
                status_lbl.setText(
                    "> Aplicando Modo Gamer... aguarde."
                    if action == "activate"
                    else "> Desativando Modo Gamer..."
                )
        QApplication.processEvents()

        try:
            optins = load_enabled_optins() if action == "activate" else set()
            self._gamer_worker = GamerWorker(self.gamer_engine, action, enabled_optins=optins)
            self._gamer_worker.finished.connect(self._on_gamer_done)
            self._gamer_worker.start()
        except Exception as e:
            self._gamer_worker = None
            try:
                m = QMessageBox(self)
                m.setWindowTitle("Modo Gamer")
                m.setIcon(QMessageBox.Critical)
                m.setText("Falha ao iniciar Modo Gamer.")
                m.setInformativeText(str(e))
                m.exec()
            except Exception:
                pass

    def _on_gamer_done(self, report, action):
        self._gamer_worker = None
        if action == "activate":
            n = len(report.applied)
            noun = "tweak aplicado" if n == 1 else "tweaks aplicados"
            short_msg = f"Modo Gamer ativado · {n} {noun}"
            if report.failed:
                f = len(report.failed)
                f_word = "falha" if f == 1 else "falhas"
                short_msg += f" · {f} {f_word}"
        else:
            short_msg = "Modo Gamer desativado"
        _save_module_status("gamer", short_msg)
        self._pending_status["gamer"] = f"> {short_msg}"

        active = (action == "activate")
        web = getattr(self, "_web_view", None)
        if web is not None:
            js_active = "true" if active else "false"
            status_escaped = short_msg.replace("'", "\\'")
            web.page().runJavaScript(f"window.setGamerMode({js_active});")
            web.page().runJavaScript(f"window.setStatus('{status_escaped}');")
            # mostra log de tweaks aplicados no terminal
            if active and report.applied:
                web.page().runJavaScript("document.getElementById('gamer-terminal').style.display='block';")
                web.page().runJavaScript("window.clearTerminal();")
                # report.applied traz TweakResult, que nao tem .label — o
                # getattr caia no str() e imprimia o repr inteiro do objeto.
                # O rotulo legivel esta no tweak registrado no engine.
                def _rotulo(r):
                    tw = self.gamer_engine._tweaks.get(getattr(r, "tweak_id", ""))
                    if tw is not None:
                        return getattr(tw, "label", None) or getattr(r, "tweak_id", "?")
                    return getattr(r, "tweak_id", "?")

                for r in report.applied:
                    txt = _rotulo(r)
                    msg = getattr(r, "message", "")
                    if msg:
                        txt = f"{txt} — {msg}"
                    web.page().runJavaScript(
                        "window.appendTerminalLine(" + json.dumps("✓ " + txt) + ", 'success');")
                for r in (report.failed or []):
                    txt = _rotulo(r)
                    err = getattr(r, "error", None) or getattr(r, "message", "")
                    if err:
                        txt = f"{txt} — {err}"
                    web.page().runJavaScript(
                        "window.appendTerminalLine(" + json.dumps("✗ " + txt) + ", 'warn');")
        else:
            self.show_gamer()

        if action == "activate" and report.reboot_required:
            # So pede reboot se ainda nao foi feito para estes tweaks.
            # Sem essa checagem o modal reaparecia a cada ativacao, mesmo
            # o usuario tendo acabado de reiniciar.
            try:
                from reboot import reboot_already_done
                pendente = not reboot_already_done()
            except Exception:
                pendente = True
            if pendente:
                self.show_reboot_modal(report)

        # Desativar zera a marca: a proxima ativacao precisa de reboot de novo
        if action == "deactivate":
            try:
                from reboot import clear_reboot_done
                clear_reboot_done()
            except Exception:
                pass

    def show_reboot_modal(self, report):
        """
        Pede o reboot pelo modal do proprio app.

        O QMessageBox nativo abria uma janela do Windows por cima do
        WebEngine — mesma quebra visual das outras janelas ja eliminadas.
        """
        reboot_tweaks = []
        for r in report.applied:
            tw = self.gamer_engine._tweaks.get(r.tweak_id)
            if tw and tw.requires_reboot:
                reboot_tweaks.append(getattr(tw, "label", None) or r.tweak_id)

        web = getattr(self, "_web_view", None)
        if web is not None and hasattr(web, "bridge"):
            web.bridge.ask_reboot(reboot_tweaks)
    def criar_ponto_restauracao(self):
        """Aciona o serviço de pontos de restauração do Windows e cria
        um snapshot rotulado pelo TecnoApp. É a mesma operação que o
        botão "Criar Ponto de Restauração" do design representa.

        Lógica:
          • garante que o serviço esteja habilitado em C:          • chama Checkpoint-Computer (PowerShell) com descrição padrão
          • exibe feedback ao usuário
        """
        import subprocess as _sp
        ps = (
            "$ErrorActionPreference='Stop';"
            " try {"
            "   Enable-ComputerRestore -Drive 'C:\' -ErrorAction SilentlyContinue;"
            "   Checkpoint-Computer -Description 'TecnoApp' -RestorePointType MODIFY_SETTINGS;"
            "   Write-Output 'OK'"
            " } catch { Write-Error $_.Exception.Message; exit 1 }"
        )
        try:
            self.btn_restore.setEnabled(False)
            r = _sp.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
                capture_output=True, text=True, timeout=120,
                creationflags=getattr(_sp, "CREATE_NO_WINDOW", 0),
            )
            ok = (r.returncode == 0)
        except Exception as e:
            ok = False
            r = type("R", (), {"stderr": str(e), "stdout": ""})()
        finally:
            self.btn_restore.setEnabled(True)

        m = QMessageBox(self)
        m.setWindowTitle("Ponto de Restauração")
        if ok:
            m.setIcon(QMessageBox.Information)
            m.setText("Ponto de restauração criado com sucesso.")
            m.setInformativeText(
                "O Windows pode limitar a frequência (1 a cada 24h por padrão). "
                "Use Painel de Controle > Recuperação para revisar."
            )
        else:
            m.setIcon(QMessageBox.Warning)
            m.setText("Não foi possível criar o ponto de restauração.")
            err = (getattr(r, "stderr", "") or getattr(r, "stdout", "") or "").strip()
            m.setInformativeText(
                err or "Verifique se a Proteção do Sistema está ativa em C:\\."
            )
        m.setStyleSheet(
            "QMessageBox{background:#030407; border:1px solid #0eb3ff;} "
            "QLabel{color:#ffffff; font-family:'Segoe UI';} "
            "QPushButton{color:white; border:1px solid #0eb3ff; padding:6px 12px; min-width:80px;}"
        )
        m.exec()

    def add_title(self, text, color=None): t = QLabel(text); t.setFont(QFont("Segoe UI", 24, QFont.Bold)); t.setStyleSheet(f"color: {color};") if color else None; self.content_lyt.addWidget(t, alignment=Qt.AlignCenter); self.content_lyt.addSpacing(10)
    def add_status_bar(self, msg): self.content_lyt.addSpacing(25); self.status_lbl = QLabel(msg); self.status_lbl.setStyleSheet(f"color: {Palette.ACCENT_CYAN}; font-family: 'Consolas'; font-size: 10px;"); self.content_lyt.addWidget(self.status_lbl, alignment=Qt.AlignCenter)
    def add_action_btn(self, text, func): b = QPushButton(text); b.setObjectName("ActionBtn"); b.setFixedWidth(400); b.clicked.connect(func); self.content_lyt.addWidget(b, alignment=Qt.AlignCenter); self.add_neon(b, self.primary)
    def paint_grid(self, event):
        p = QPainter(self.content_container); p.setPen(QPen(QColor(14, 179, 255, 12)))
        for x in range(0, self.content_container.width(), 40): p.drawLine(x, 0, x, self.content_container.height())
        for y in range(0, self.content_container.height(), 40): p.drawLine(0, y, self.content_container.width(), y)
    def add_neon(self, w, c): g = QGraphicsDropShadowEffect(); g.setBlurRadius(20); g.setColor(QColor(c)); g.setOffset(0); w.setGraphicsEffect(g)
    def create_menu_btn(self, t, f, glyph: str = ""):
        b = QPushButton(t)
        b.setObjectName("MenuBtn")
        b.setFixedSize(190, 40)
        b.setCursor(QCursor(Qt.PointingHandCursor))
        if glyph:
            b.setIcon(self._menu_icon(glyph, size=18))
            b.setIconSize(QSize(18, 18))
        b.clicked.connect(f)
        return b

    def _set_active_menu(self, key):
        """Marca visualmente o item ativo da sidebar.

        Não altera lógica de navegação — apenas estado visual.
        """
        for k, btn in getattr(self, "_menu_buttons", {}).items():
            if hasattr(btn, "set_active"):
                btn.set_active(k == key)
        gamer = getattr(self, "btn_gamer_nav", None)
        if gamer is not None and hasattr(gamer, "set_active"):
            gamer.set_active(key == "gamer")

    def clear_screen(self):
        while self.content_lyt.count():
            i = self.content_lyt.takeAt(0)
            if i.widget(): i.widget().deleteLater()
            elif i.layout():
                while i.layout().count():
                    c = i.layout().takeAt(0); c.widget().deleteLater() if c.widget() else None
    def finalizar_app(self): self.clear_screen(); l = QLabel("TECNOAPP ENCERRADO"); l.setFont(QFont("Segoe UI", 18, QFont.Bold)); self.add_neon(l, "#ff4b4b"); self.content_lyt.addWidget(l, alignment=Qt.AlignCenter); QTimer.singleShot(1000, self.close)

# ═══════════════════════════════════════════════════════════════════════
# Entrypoint — proteção contra crash silencioso na inicialização
# ═══════════════════════════════════════════════════════════════════════

def _fatal_log_path() -> str:
    log_dir = os.path.join(
        os.environ.get("LOCALAPPDATA", os.environ.get("TEMP", ".")),
        "TecnoApp",
    )
    try:
        os.makedirs(log_dir, exist_ok=True)
    except Exception:
        log_dir = "."
    return os.path.join(log_dir, "tecnoapp_error.log")


def _write_fatal_log(exc: BaseException) -> str:
    """Escreve traceback completo e contexto ambiental. Retorna o path."""
    import traceback
    path = _fatal_log_path()
    try:
        import PySide6
        pyside_ver = getattr(PySide6, "__version__", "desconhecida")
    except Exception:
        pyside_ver = "desconhecida"
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write("=" * 70 + "\n")
            f.write(f"TecnoApp — erro fatal · {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
            f.write(f"Python     : {sys.version.splitlines()[0]}\n")
            f.write(f"PySide6    : {pyside_ver}\n")
            f.write(f"Diretório  : {os.getcwd()}\n")
            f.write(f"Argumentos : {sys.argv}\n")
            f.write("-" * 70 + "\n")
            f.write("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))
            f.write("\n")
    except Exception:
        pass
    return path


def _show_fatal_dialog(log_path: str):
    """Exibe QMessageBox sobre o erro. Silencioso se Qt falhar também."""
    try:
        app = QApplication.instance() or QApplication(sys.argv)
        m = QMessageBox()
        m.setWindowTitle("TecnoApp — erro ao iniciar")
        m.setIcon(QMessageBox.Critical)
        m.setText("O TECNOAPP encontrou um erro ao iniciar.")
        m.setInformativeText(f"O log foi salvo em:\n{log_path}")
        m.exec()
    except Exception:
        pass


if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        app.setStyleSheet(GLOBAL_STYLESHEET)

        # Instancia unica: duas copias mexendo nos mesmos tweaks e no mesmo
        # snapshot em %APPDATA% corrompem o estado do Modo Gamer.
        #
        # Aqui so CHECA, sem tomar posse: este processo pode ser o
        # nao-elevado, que morre logo apos disparar o ShellExecuteW. Quem
        # toma posse de fato e o processo elevado, no __init__ de TecnoApp.
        import singleton
        if singleton.is_running():
            if not singleton.focus_existing():
                m = QMessageBox()
                m.setWindowTitle("TecnoApp")
                m.setIcon(QMessageBox.Information)
                m.setText("O TecnoApp ja esta aberto.")
                m.setInformativeText(
                    "Procure a janela na barra de tarefas. "
                    "Manter duas copias abertas pode corromper o estado dos tweaks."
                )
                m.exec()
            sys.exit(0)

        window = TecnoApp()
        window.show()
        sys.exit(app.exec())
    except SystemExit:
        raise
    except BaseException as _fatal_exc:
        _path = _write_fatal_log(_fatal_exc)
        try:
            print(f"\n[TecnoApp] Erro fatal. Log salvo em: {_path}", file=sys.stderr)
        except Exception:
            pass
        _show_fatal_dialog(_path)
        try:
            input("\nPressione Enter para sair...")
        except (EOFError, KeyboardInterrupt):
            pass
        sys.exit(1)
