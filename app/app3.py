import sys
import os
import re
import json
import subprocess
import ctypes
from datetime import datetime
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QMessageBox,
                             QHBoxLayout, QPushButton, QLabel, QFrame, QGraphicsDropShadowEffect,
                             QCheckBox, QScrollArea)
from PySide6.QtGui import QFont, QColor, QCursor, QPainter, QPen, QBrush
from PySide6.QtCore import Qt, QTimer, QThread, Signal

from gamer import build_engine, load_enabled_optins, save_enabled_optins
from gamer.tweaks import Category

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
            return json.load(f) or {}
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
            return json.load(f) or {}
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
            return json.load(f) or {}
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
    entry = _load_module_statuses().get(module) or {}
    if entry.get("message") and entry.get("timestamp"):
        label = _MODULE_LABELS.get(module, module)
        return f"> Última {label}: {entry['timestamp']} — {entry['message']}"
    return ""


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
            bg_color    = QColor("#0eb3ff")
            border_col  = QColor("#0eb3ff")
            knob_color  = QColor("white")
            knob_x      = w - 18
        else:
            bg_color    = QColor("#1a1f2b")
            border_col  = QColor("#333333")
            knob_color  = QColor("#888888")
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

        self.setWindowTitle("TECNOAPP OTIMIZAÇÃO - Pro Edition")
        self.setFixedSize(850, 600)

        # Cores da Identidade Visual
        self.primary = "#0eb3ff"    
        self.secondary = "#7000ff"  
        self.danger = "#ff4b4b"
        self.bg_dark = "#030407"    
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
            QMainWindow {{ background-color: {self.bg_dark}; }}
            #Sidebar {{ background-color: rgba(3, 4, 7, 245); border-right: 1px solid rgba(14, 179, 255, 0.1); }}
            QLabel {{ color: #ffffff; background: transparent; }}
            
            QPushButton#MenuBtn {{
                background: transparent; border: 2px solid {self.primary};
                color: {self.primary}; font-family: 'Segoe UI'; font-size: 11px;
                font-weight: bold; border-radius: 10px; padding: 8px;
            }}
            QPushButton#MenuBtn:hover {{ background: {self.primary}; color: black; }}
            
            QPushButton#ActionBtn {{
                background-color: {self.primary}; color: black; font-weight: bold;
                border-radius: 8px; padding: 12px; border: none; font-size: 14px;
            }}
            QPushButton#ActionBtn:hover {{ background-color: white; }}

            QPushButton#InfoBtn {{
                background: rgba(14, 179, 255, 0.1); border: 1px solid {self.primary}; 
                color: {self.primary}; font-size: 14px; border-radius: 15px; font-weight: bold;
            }}
            QPushButton#InfoBtn:hover {{ background: {self.primary}; color: black; }}

            QPushButton#GamerNav {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {self.primary}, stop:1 {self.secondary});
                color: white; font-weight: bold; border-radius: 15px; padding: 10px; border: 1px solid transparent;
            }}
            QPushButton#ExitBtn {{
                background: transparent; border: 1px solid #ff4b4b; color: #ff4b4b; border-radius: 8px; font-weight: bold;
            }}
            QPushButton#ExitBtn:hover {{ background: #ff4b4b; color: white; }}
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        sidebar = QFrame(); sidebar.setObjectName("Sidebar"); sidebar.setFixedWidth(220)
        side_lyt = QVBoxLayout(sidebar); side_lyt.setContentsMargins(15, 30, 15, 30); side_lyt.setSpacing(10)
        
        logo = QLabel("TECNOSUP"); logo.setFont(QFont("Segoe UI", 22, QFont.Bold))
        self.add_neon(logo, self.primary); side_lyt.addWidget(logo, alignment=Qt.AlignCenter)
        side_lyt.addSpacing(20)
        
        side_lyt.addWidget(self.create_menu_btn("🧹 LIMPEZA", self.show_limpeza))
        side_lyt.addWidget(self.create_menu_btn("⚡ OTIMIZAÇÃO", self.show_otimizacao))
        side_lyt.addWidget(self.create_menu_btn("🔧 REPAROS", self.show_reparos))
        
        self.btn_gamer_nav = QPushButton("🎮 MODO GAMER")
        self.btn_gamer_nav.setObjectName("GamerNav")
        self.btn_gamer_nav.clicked.connect(self.show_gamer)
        self.add_neon(self.btn_gamer_nav, self.secondary)
        side_lyt.addWidget(self.btn_gamer_nav)

        side_lyt.addStretch()
        btn_sair = QPushButton("SAIR"); btn_sair.setObjectName("ExitBtn"); btn_sair.setFixedSize(180, 35)
        btn_sair.clicked.connect(self.finalizar_app); side_lyt.addWidget(btn_sair, alignment=Qt.AlignCenter)

        main_layout.addWidget(sidebar)

        self.content_container = QWidget()
        self.content_container.paintEvent = self.paint_grid 
        self.content_lyt = QVBoxLayout(self.content_container)
        self.content_lyt.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.content_container)

        self.show_home()

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
        self.add_title("MÓDULO DE LIMPEZA")
        desc = QLabel("Limpeza segura com ferramentas nativas do Windows.")
        desc.setStyleSheet("color: #444; margin-bottom: 25px;")
        self.content_lyt.addWidget(desc, alignment=Qt.AlignCenter)

        self.add_action_btn("LIMPEZA RÁPIDA", lambda: self.run_clean_process())

        btn_adv = QPushButton("CONFIGURAR LIMPEZA")
        btn_adv.setFixedWidth(400)
        btn_adv.setFixedHeight(42)
        btn_adv.setStyleSheet(
            f"background: transparent; border: 1px solid {self.primary}; color: {self.primary};"
            "font-weight: bold; border-radius: 8px; font-size: 13px;"
        )
        btn_adv.clicked.connect(self.show_limpeza_avancada)
        self.content_lyt.addWidget(btn_adv, alignment=Qt.AlignCenter)

        self._set_status_bar("clean", "> Nenhuma limpeza realizada ainda.")

    def show_limpeza_avancada(self):
        self.clear_screen()
        self.add_title("CONFIGURAR LIMPEZA")
        sub = QLabel("Selecione o que deseja limpar. Os marcados por padrão são seguros para todos.")
        sub.setStyleSheet("color: #555; font-size: 11px; margin-bottom: 8px;")
        sub.setWordWrap(True)
        sub.setAlignment(Qt.AlignCenter)
        self.content_lyt.addWidget(sub)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            "QScrollArea { border: none; background: transparent; }"
            "QScrollBar:vertical { width: 6px; background: #111; border-radius: 3px; }"
            "QScrollBar::handle:vertical { background: #0eb3ff; border-radius: 3px; }"
        )
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
        safe_hdr.setStyleSheet(f"color: {self.primary}; font-weight: bold; font-size: 11px; margin-top: 4px;")
        inner_lyt.addWidget(safe_hdr)

        for cat in safe_cats:
            checked = saved.get(cat["id"], cat["default"])
            inner_lyt.addWidget(self._build_clean_row(cat, checked=checked))

        opt_hdr = QLabel("── OPCIONAL (revise antes de ativar)")
        opt_hdr.setStyleSheet("color: #ffbd2e; font-weight: bold; font-size: 11px; margin-top: 10px;")
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
            "background: transparent; border: 1px solid #333; color: #666;"
            "font-weight: bold; border-radius: 6px; padding: 8px;"
        )
        back.clicked.connect(self.show_limpeza)

        save = QPushButton("Salvar alterações")
        save.setFixedWidth(200)
        save.setStyleSheet(
            f"background: {self.primary}; color: #030407; border: none;"
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
            "QFrame { background: #0a0d14; border: 1px solid #1a1f2b; border-radius: 6px; }"
        )
        lyt = QVBoxLayout(row)
        lyt.setContentsMargins(10, 8, 10, 8)
        lyt.setSpacing(2)

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)

        cb = QCheckBox(cat["label"])
        cb.setChecked(checked)
        cb.setStyleSheet(
            "QCheckBox { color: white; font-family: 'Segoe UI'; font-size: 12px; }"
            "QCheckBox::indicator { width: 14px; height: 14px; }"
        )
        self._clean_checkboxes[cat["id"]] = cb
        cb.stateChanged.connect(self._on_clean_selection_changed)
        top.addWidget(cb, 1)

        impact = QLabel(cat["impact"])
        impact.setStyleSheet("color: #0eb3ff; font-family: 'Consolas'; font-size: 10px;")
        top.addWidget(impact)
        lyt.addLayout(top)

        desc = QLabel(cat["desc"])
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #888; font-family: 'Segoe UI'; font-size: 10px; padding-left: 22px;")
        lyt.addWidget(desc)

        if cat.get("warning"):
            warn = QLabel("⚠ " + cat["warning"])
            warn.setWordWrap(True)
            warn.setStyleSheet("color: #ff8a4b; font-family: 'Segoe UI'; font-size: 10px; padding-left: 22px;")
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
        self._pending_status["clean"] = f"> ✓ Preferências salvas ({selected} itens selecionados)"
        self.show_limpeza()

    def show_limpeza_progresso(self):
        self.clear_screen()
        self.add_title("LIMPEZA EM ANDAMENTO")

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            "QScrollArea { border: 1px solid #1a1f2b; background: #0a0d14; border-radius: 8px; }"
            "QScrollBar:vertical { width: 6px; background: #111; border-radius: 3px; }"
            "QScrollBar::handle:vertical { background: #0eb3ff; border-radius: 3px; }"
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
            "background: transparent; border: 1px solid #333; color: #444;"
            "font-weight: bold; border-radius: 8px; padding: 10px;"
        )
        self._clean_btn_voltar.clicked.connect(self.show_limpeza)
        self.content_lyt.addWidget(self._clean_btn_voltar, alignment=Qt.AlignCenter)

    def _on_clean_step(self, label: str, freed: int):
        size_str = f"   +{self.format_size(freed)}" if freed > 1024 else ""
        self._clean_log_lines.append(f"✓  {label}{size_str}")
        self._clean_log_label.setText("\n".join(self._clean_log_lines))

    def _on_clean_calculating(self):
        self._clean_log_lines.append("")
        self._clean_log_lines.append("Calculando resultado·")
        self._clean_log_label.setText("\n".join(self._clean_log_lines))
        self._clean_dots = 0
        self._clean_calc_timer = QTimer(self)
        self._clean_calc_timer.timeout.connect(self._animate_clean_dots)
        self._clean_calc_timer.start(180)

    def _animate_clean_dots(self):
        try:
            self._clean_dots = (self._clean_dots + 1) % 3
            dots = "·" * (self._clean_dots + 1)
            self._clean_log_lines[-1] = f"Calculando resultado{dots}"
            self._clean_log_label.setText("\n".join(self._clean_log_lines))
        except (RuntimeError, IndexError):
            pass

    def _on_clean_done(self, total: int):
        if self._clean_calc_timer is not None:
            self._clean_calc_timer.stop()
            self._clean_calc_timer = None
        # Remove a linha de animação e a linha em branco antes dela
        while self._clean_log_lines and (
            self._clean_log_lines[-1].startswith("Calculando") or
            self._clean_log_lines[-1] == ""
        ):
            self._clean_log_lines.pop()
        self._clean_log_label.setText("\n".join(self._clean_log_lines))

        if self._clean_worker is not None:
            self._clean_worker.wait()
            self._clean_worker.deleteLater()
            self._clean_worker = None
        if total > 102_400:
            msg = f"✓  {self.format_size(total)} liberados"
        else:
            msg = "✓  Sistema já estava otimizado"
        self._clean_total_label.setText(msg)
        self._clean_total_label.show()
        self.add_neon(self._clean_total_label, self.primary)
        self._clean_btn_voltar.setEnabled(True)
        self._clean_btn_voltar.setStyleSheet(
            f"background: transparent; border: 1px solid {self.primary}; color: {self.primary};"
            "font-weight: bold; border-radius: 8px; padding: 10px;"
        )
        _save_module_status("clean", msg)

    def show_home(self): self.clear_screen(); lbl = QLabel("SISTEMA PRONTO"); lbl.setFont(QFont("Segoe UI", 28, QFont.Bold)); self.add_neon(lbl, self.primary); self.content_lyt.addWidget(lbl, alignment=Qt.AlignCenter)

    # ═══════════════════════════════════════════════════════════════════
    # OTIMIZAÇÃO
    # ═══════════════════════════════════════════════════════════════════
    def show_otimizacao(self):
        self.clear_screen()
        self.add_title("MÓDULO DE OTIMIZAÇÃO")
        desc = QLabel("Ajustes persistentes de performance. Totalmente reversíveis.")
        desc.setStyleSheet("color: #444; margin-bottom: 25px;")
        self.content_lyt.addWidget(desc, alignment=Qt.AlignCenter)

        self.add_action_btn("OTIMIZAR SISTEMA", lambda: self.run_optimize_process())

        btn_adv = QPushButton("CONFIGURAR OTIMIZAÇÃO")
        btn_adv.setFixedWidth(400)
        btn_adv.setFixedHeight(42)
        btn_adv.setStyleSheet(
            f"background: transparent; border: 1px solid {self.primary}; color: {self.primary};"
            "font-weight: bold; border-radius: 8px; font-size: 13px;"
        )
        btn_adv.clicked.connect(self.show_otimizacao_avancada)
        self.content_lyt.addWidget(btn_adv, alignment=Qt.AlignCenter)

        self.content_lyt.addSpacing(6)

        btn_revert = QPushButton("Restaurar padrões do Windows")
        btn_revert.setFixedWidth(280)
        btn_revert.setStyleSheet(
            "background: transparent; border: 1px solid #666; color: #888;"
            "font-weight: bold; border-radius: 6px; font-size: 11px; padding: 6px;"
        )
        btn_revert.clicked.connect(self._confirm_revert_optimize)
        self.content_lyt.addWidget(btn_revert, alignment=Qt.AlignCenter)

        self._set_status_bar("optimize", "> Nenhuma otimização realizada ainda.")

    def show_otimizacao_avancada(self):
        self.clear_screen()
        self.add_title("CONFIGURAR OTIMIZAÇÃO")
        sub = QLabel("Selecione os ajustes desejados. Os marcados por padrão são seguros para todos.")
        sub.setStyleSheet("color: #555; font-size: 11px; margin-bottom: 8px;")
        sub.setWordWrap(True)
        sub.setAlignment(Qt.AlignCenter)
        self.content_lyt.addWidget(sub)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            "QScrollArea { border: none; background: transparent; }"
            "QScrollBar:vertical { width: 6px; background: #111; border-radius: 3px; }"
            "QScrollBar::handle:vertical { background: #0eb3ff; border-radius: 3px; }"
        )
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
        safe_hdr.setStyleSheet(f"color: {self.primary}; font-weight: bold; font-size: 11px; margin-top: 4px;")
        inner_lyt.addWidget(safe_hdr)
        for cat in safe_cats:
            checked = saved.get(cat["id"], cat["default"])
            use_toggle = (cat["id"] == "hibernate_off")
            inner_lyt.addWidget(self._build_optimize_row(cat, checked=checked, use_toggle=use_toggle))

        opt_hdr = QLabel("── OPCIONAL (revise antes de ativar)")
        opt_hdr.setStyleSheet("color: #ffbd2e; font-weight: bold; font-size: 11px; margin-top: 10px;")
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
            "color: #888; font-family: 'Consolas'; font-size: 11px; margin-top: 6px;"
        )
        self.content_lyt.addWidget(self._optimize_counter_label)
        self._update_optimize_counter()

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        back = QPushButton("Voltar")
        back.setFixedWidth(100)
        back.setStyleSheet(
            "background: transparent; border: 1px solid #333; color: #666;"
            "font-weight: bold; border-radius: 6px; padding: 8px;"
        )
        back.clicked.connect(self.show_otimizacao)
        save = QPushButton("Salvar alterações")
        save.setFixedWidth(200)
        save.setStyleSheet(
            f"background: {self.primary}; color: #030407; border: none;"
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
            "QFrame { background: #0a0d14; border: 1px solid #1a1f2b; border-radius: 6px; }"
        )
        lyt = QVBoxLayout(row)
        lyt.setContentsMargins(10, 8, 10, 8)
        lyt.setSpacing(2)

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)

        if use_toggle:
            # Toggle à esquerda + label ao lado (alinhado com padrão dos checkboxes)
            cb = ToggleSwitch()
            cb.setChecked(checked)
            top.addWidget(cb)
            top.addSpacing(8)

            lbl = QLabel(cat["label"])
            lbl.setStyleSheet("color: white; font-family: 'Segoe UI'; font-size: 12px;")
            top.addWidget(lbl, 1)
        else:
            cb = QCheckBox(cat["label"])
            cb.setChecked(checked)
            cb.setStyleSheet(
                "QCheckBox { color: white; font-family: 'Segoe UI'; font-size: 12px; }"
                "QCheckBox::indicator { width: 14px; height: 14px; }"
            )
            top.addWidget(cb, 1)

        impact = QLabel(cat["impact"])
        impact.setStyleSheet("color: #0eb3ff; font-family: 'Consolas'; font-size: 10px;")
        top.addWidget(impact)

        self._optimize_checkboxes[cat["id"]] = cb
        cb.stateChanged.connect(self._on_optimize_selection_changed)
        lyt.addLayout(top)

        desc = QLabel(cat["desc"])
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #888; font-family: 'Segoe UI'; font-size: 10px; padding-left: 22px;")
        lyt.addWidget(desc)

        if cat.get("warning"):
            warn = QLabel("⚠ " + cat["warning"])
            warn.setWordWrap(True)
            warn.setStyleSheet("color: #ff8a4b; font-family: 'Segoe UI'; font-size: 10px; padding-left: 22px;")
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
        self._pending_status["optimize"] = f"> ✓ Preferências salvas ({selected} otimizações)"
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
            "QScrollArea { border: 1px solid #1a1f2b; background: #0a0d14; border-radius: 8px; }"
            "QScrollBar:vertical { width: 6px; background: #111; border-radius: 3px; }"
            "QScrollBar::handle:vertical { background: #0eb3ff; border-radius: 3px; }"
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
            "background: transparent; border: 1px solid #333; color: #444;"
            "font-weight: bold; border-radius: 8px; padding: 10px;"
        )
        self._optimize_btn_voltar.clicked.connect(self.show_otimizacao)
        self.content_lyt.addWidget(self._optimize_btn_voltar, alignment=Qt.AlignCenter)

    def _on_optimize_step(self, label: str, ok: bool, detail: str):
        mark = "✓" if ok else "✗"
        extra = f"   ({detail})" if detail else ""
        self._optimize_log_lines.append(f"{mark}  {label}{extra}")
        self._optimize_log_label.setText("\n".join(self._optimize_log_lines))

    def _on_optimize_done(self, applied: int, failed: int):
        if self._optimize_worker is not None:
            self._optimize_worker.wait()
            self._optimize_worker.deleteLater()
            self._optimize_worker = None
        if failed == 0 and applied > 0:
            msg = f"✓  {applied} ajuste(s) aplicado(s) com sucesso"
        elif applied == 0:
            msg = "Nenhum ajuste foi aplicado"
        else:
            msg = f"{applied} aplicado(s) · {failed} falha(s)"
        self._optimize_total_label.setText(msg)
        self._optimize_total_label.show()
        self.add_neon(self._optimize_total_label, self.primary)
        self._optimize_btn_voltar.setEnabled(True)
        self._optimize_btn_voltar.setStyleSheet(
            f"background: transparent; border: 1px solid {self.primary}; color: {self.primary};"
            "font-weight: bold; border-radius: 8px; padding: 10px;"
        )
        _save_module_status("optimize", msg)

    # ═══════════════════════════════════════════════════════════════════
    # REPAROS
    # ═══════════════════════════════════════════════════════════════════
    def show_reparos(self):
        self.clear_screen()
        self.add_title("CENTRAL DE REPAROS")
        desc = QLabel("Cada reparo é independente. Escolha conforme o problema.")
        desc.setStyleSheet("color: #444; margin-bottom: 15px;")
        self.content_lyt.addWidget(desc, alignment=Qt.AlignCenter)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            "QScrollArea { border: none; background: transparent; }"
            "QScrollBar:vertical { width: 6px; background: #111; border-radius: 3px; }"
            "QScrollBar::handle:vertical { background: #0eb3ff; border-radius: 3px; }"
        )
        inner = QWidget()
        inner.setStyleSheet("background: transparent;")
        inner_lyt = QVBoxLayout(inner)
        inner_lyt.setSpacing(6)
        inner_lyt.setContentsMargins(4, 4, 4, 4)

        essentials = [t for t in _REPAIR_TOOLS if t["category"] == "essential"]
        advanced   = [t for t in _REPAIR_TOOLS if t["category"] == "advanced"]

        hdr1 = QLabel("── ESSENCIAIS")
        hdr1.setStyleSheet(f"color: {self.primary}; font-weight: bold; font-size: 11px; margin-top: 4px;")
        inner_lyt.addWidget(hdr1)
        for tool in essentials:
            inner_lyt.addWidget(self._build_repair_row(tool))

        hdr2 = QLabel("── AVANÇADOS")
        hdr2.setStyleSheet("color: #ffbd2e; font-weight: bold; font-size: 11px; margin-top: 10px;")
        inner_lyt.addWidget(hdr2)
        for tool in advanced:
            inner_lyt.addWidget(self._build_repair_row(tool))

        inner_lyt.addStretch()
        scroll.setWidget(inner)
        self.content_lyt.addWidget(scroll, 1)

        self._set_status_bar("repair", "> Escolha um reparo.")

    def _build_repair_row(self, tool):
        row = QFrame()
        row.setStyleSheet(
            "QFrame { background: #0a0d14; border: 1px solid #1a1f2b; border-radius: 6px; }"
        )
        lyt = QVBoxLayout(row)
        lyt.setContentsMargins(10, 8, 10, 8)
        lyt.setSpacing(2)

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        title = QLabel(tool["label"])
        title.setStyleSheet("color: white; font-family: 'Segoe UI'; font-size: 12px; font-weight: bold;")
        top.addWidget(title, 1)

        tags = [tool["duration"]]
        if tool["reboot"]:
            tags.append("REBOOT")
        tag = QLabel(" · ".join(tags))
        tag.setStyleSheet("color: #0eb3ff; font-family: 'Consolas'; font-size: 10px;")
        top.addWidget(tag)
        lyt.addLayout(top)

        desc = QLabel(tool["desc"])
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #888; font-family: 'Segoe UI'; font-size: 10px;")
        lyt.addWidget(desc)

        if tool.get("warning"):
            warn = QLabel("⚠ " + tool["warning"])
            warn.setWordWrap(True)
            warn.setStyleSheet("color: #ff8a4b; font-family: 'Segoe UI'; font-size: 10px;")
            lyt.addWidget(warn)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        btn = QPushButton("Executar")
        btn.setFixedWidth(110)
        btn.setStyleSheet(
            f"background: {self.primary}; color: #030407; border: none;"
            "border-radius: 5px; padding: 6px; font-family: 'Segoe UI'; font-weight: bold; font-size: 11px;"
        )
        tid = tool["id"]
        btn.clicked.connect(lambda _=False, t=tid: self._confirm_repair(t))
        btn_row.addWidget(btn)
        lyt.addLayout(btn_row)

        return row

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
            "QScrollArea { border: 1px solid #1a1f2b; background: #0a0d14; border-radius: 8px; }"
            "QScrollBar:vertical { width: 6px; background: #111; border-radius: 3px; }"
            "QScrollBar::handle:vertical { background: #0eb3ff; border-radius: 3px; }"
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
            "background: transparent; border: 1px solid #333; color: #444;"
            "font-weight: bold; border-radius: 8px; padding: 10px;"
        )
        self._repair_btn_voltar.clicked.connect(self.show_reparos)
        self.content_lyt.addWidget(self._repair_btn_voltar, alignment=Qt.AlignCenter)

    def _on_repair_step(self, label: str, ok: bool, detail: str):
        mark = "✓" if ok else "✗"
        extra = f"   ({detail})" if detail else ""
        self._repair_log_lines.append(f"{mark}  {label}{extra}")
        self._repair_log_label.setText("\n".join(self._repair_log_lines))

    def _on_repair_done(self, overall_ok: bool, summary: str):
        if self._repair_worker is not None:
            self._repair_worker.wait()
            self._repair_worker.deleteLater()
            self._repair_worker = None
        self._repair_summary_label.setText(summary)
        color = self.primary if overall_ok else "#ff8a4b"
        self._repair_summary_label.setStyleSheet(f"color: {color}; margin-top: 8px;")
        self._repair_summary_label.show()
        self.add_neon(self._repair_summary_label, color)
        self._repair_btn_voltar.setEnabled(True)
        self._repair_btn_voltar.setStyleSheet(
            f"background: transparent; border: 1px solid {self.primary}; color: {self.primary};"
            "font-weight: bold; border-radius: 8px; padding: 10px;"
        )
        _save_module_status("repair", summary)
    def show_gamer(self):
        self.clear_screen()
        self.add_title("MODO GAMER", self.secondary)

        active = self.gamer_engine.is_active()
        snapshot = self.gamer_engine.active_snapshot() if active else None

        if active and snapshot:
            status_txt = f"● ATIVO desde {snapshot.created_at}"
            status_color = self.primary
        else:
            status_txt = "● INATIVO"
            status_color = "#666"

        self.gamer_status = QLabel(status_txt)
        self.gamer_status.setStyleSheet(
            f"color: {status_color}; font-family: 'Consolas'; font-size: 13px; font-weight: bold;"
        )
        self.content_lyt.addWidget(self.gamer_status, alignment=Qt.AlignCenter)
        self.content_lyt.addSpacing(15)

        if active:
            self.add_danger_btn("DESATIVAR MODO GAMER", self.run_gamer_deactivate)
        else:
            self.add_action_btn("ATIVAR MODO GAMER", self.run_gamer_activate)

        self.content_lyt.addSpacing(10)

        adv = QPushButton("Avançado (granular)")
        adv.setFixedWidth(260)
        adv.setCursor(QCursor(Qt.PointingHandCursor))
        adv.setStyleSheet(
            "background:transparent; color:#7000ff; border:1px solid #7000ff;"
            "border-radius:6px; padding:6px; font-family:'Segoe UI'; font-size:11px;"
        )
        adv.clicked.connect(self.show_gamer_advanced)
        self.content_lyt.addWidget(adv, alignment=Qt.AlignCenter)

        self.content_lyt.addSpacing(15)
        grouped = self.gamer_engine.tweaks_by_category()
        counts = (
            f"CPU: {len(grouped[Category.CPU])}    "
            f"GPU: {len(grouped[Category.GPU])}    "
            f"Sistema: {len(grouped[Category.SYSTEM])}    "
            f"Rede: {len(grouped[Category.NETWORK])}"
        )
        detail = QLabel(counts)
        detail.setStyleSheet("color: #555; font-family: 'Segoe UI'; font-size: 11px;")
        self.content_lyt.addWidget(detail, alignment=Qt.AlignCenter)

        enabled = load_enabled_optins()
        if enabled:
            opt_lbl = QLabel(f"opt-in ativos: {', '.join(sorted(enabled))}")
            opt_lbl.setStyleSheet("color: #7000ff; font-family: 'Consolas'; font-size: 10px;")
            self.content_lyt.addWidget(opt_lbl, alignment=Qt.AlignCenter)

        self._set_status_bar("gamer", "> Pronto.")

    def show_gamer_advanced(self):
        self.clear_screen()
        self.add_title("MODO GAMER — AVANÇADO", self.secondary)

        intro = QLabel(
            "Escolha quais tweaks rodam no one-click.\n"
            "Os essenciais sempre rodam. Os marcados como opt-in só rodam se você habilitar aqui."
        )
        intro.setAlignment(Qt.AlignCenter)
        intro.setWordWrap(True)
        intro.setStyleSheet("color:#aaa; font-family:'Segoe UI'; font-size:12px;")
        self.content_lyt.addWidget(intro)
        self.content_lyt.addSpacing(10)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{border:none; background:transparent;}")
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
            "background:transparent; color:#888; border:1px solid #444;"
            "border-radius:6px; padding:8px; font-family:'Segoe UI';"
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
            "QFrame{background:#0a0d14; border:1px solid #1a1f2b; border-radius:6px;}"
        )
        lyt = QVBoxLayout(row)
        lyt.setContentsMargins(10, 8, 10, 8)
        lyt.setSpacing(2)

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        cb = QCheckBox(tweak.label)
        cb.setStyleSheet(
            "QCheckBox{color:white; font-family:'Segoe UI'; font-size:12px;}"
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
        color = {"low": "#4caf50", "medium": "#ffb300", "high": "#ff4b4b"}.get(tweak.risk.value, "#888")
        tag.setStyleSheet(f"color:{color}; font-family:'Consolas'; font-size:10px;")
        top.addWidget(tag)
        lyt.addLayout(top)

        if tweak.description:
            desc = QLabel(tweak.description)
            desc.setWordWrap(True)
            desc.setStyleSheet("color:#888; font-family:'Segoe UI'; font-size:10px;")
            lyt.addWidget(desc)

        if tweak.warning:
            warn = QLabel("⚠ " + tweak.warning)
            warn.setWordWrap(True)
            warn.setStyleSheet("color:#ff8a4b; font-family:'Segoe UI'; font-size:10px;")
            lyt.addWidget(warn)

        return row

    def _save_advanced_prefs(self):
        selected = {tid for tid, cb in self._advanced_checks.items() if cb.isChecked()}
        save_enabled_optins(selected)
        self._pending_status["gamer"] = f"> Preferências salvas ({len(selected)} opt-in ativos)."
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
        if self._gamer_worker is not None:
            return
        self.status_lbl.setText("> Aplicando Modo Gamer... aguarde." if action == "activate" else "> Desativando Modo Gamer...")
        self.status_lbl.setStyleSheet(f"color: {self.primary}; font-family: 'Consolas'; font-weight: bold;")
        QApplication.processEvents()

        optins = load_enabled_optins() if action == "activate" else set()
        self._gamer_worker = GamerWorker(self.gamer_engine, action, enabled_optins=optins)
        self._gamer_worker.finished.connect(self._on_gamer_done)
        self._gamer_worker.start()

    def _on_gamer_done(self, report, action):
        self._gamer_worker = None
        verb = "aplicado" if action == "activate" else "desativado"
        short_msg = (
            f"Modo Gamer {verb}. "
            f"Aplicados: {len(report.applied)} · Pulados: {len(report.skipped)} · Falhas: {len(report.failed)}"
        )
        _save_module_status("gamer", short_msg)
        self._pending_status["gamer"] = f"> {short_msg}"
        self.show_gamer()
        if action == "activate" and report.reboot_required:
            self.show_reboot_modal(report)

    def show_reboot_modal(self, report):
        reboot_tweaks = [r.tweak_id for r in report.applied
                         if self.gamer_engine._tweaks.get(r.tweak_id) and self.gamer_engine._tweaks[r.tweak_id].requires_reboot]
        m = QMessageBox(self)
        m.setWindowTitle("Reinicialização recomendada")
        m.setText("Alguns tweaks exigem reboot para entrar em efeito.")
        m.setInformativeText(
            "Para ter ganho completo, reinicie o PC quando for conveniente.\n"
            "Os tweaks já estão salvos e sobrevivem ao reboot.\n\n"
            f"Tweaks afetados:\n• " + "\n• ".join(reboot_tweaks)
        )
        m.setStandardButtons(QMessageBox.Ok)
        m.setStyleSheet(
            "QLabel{color:white; font-family:'Segoe UI';} "
            "QMessageBox{background:#030407; border:1px solid #0eb3ff;} "
            "QPushButton{color:white; border:1px solid #0eb3ff; padding:5px; min-width:80px;}"
        )
        m.exec()
    def add_title(self, text, color=None): t = QLabel(text); t.setFont(QFont("Segoe UI", 24, QFont.Bold)); t.setStyleSheet(f"color: {color};") if color else None; self.content_lyt.addWidget(t, alignment=Qt.AlignCenter); self.content_lyt.addSpacing(10)
    def add_status_bar(self, msg): self.content_lyt.addSpacing(25); self.status_lbl = QLabel(msg); self.status_lbl.setStyleSheet("color: #444; font-family: 'Consolas';"); self.content_lyt.addWidget(self.status_lbl, alignment=Qt.AlignCenter)
    def add_action_btn(self, text, func): b = QPushButton(text); b.setObjectName("ActionBtn"); b.setFixedWidth(400); b.clicked.connect(func); self.content_lyt.addWidget(b, alignment=Qt.AlignCenter); self.add_neon(b, self.primary)
    def paint_grid(self, event):
        p = QPainter(self.content_container); p.setPen(QPen(QColor(14, 179, 255, 12)))
        for x in range(0, self.content_container.width(), 40): p.drawLine(x, 0, x, self.content_container.height())
        for y in range(0, self.content_container.height(), 40): p.drawLine(0, y, self.content_container.width(), y)
    def add_neon(self, w, c): g = QGraphicsDropShadowEffect(); g.setBlurRadius(20); g.setColor(QColor(c)); g.setOffset(0); w.setGraphicsEffect(g)
    def create_menu_btn(self, t, f): b = QPushButton(t); b.setObjectName("MenuBtn"); b.setFixedSize(190, 40); b.clicked.connect(f); return b
    def clear_screen(self):
        while self.content_lyt.count():
            i = self.content_lyt.takeAt(0)
            if i.widget(): i.widget().deleteLater()
            elif i.layout():
                while i.layout().count():
                    c = i.layout().takeAt(0); c.widget().deleteLater() if c.widget() else None
    def finalizar_app(self): self.clear_screen(); l = QLabel("TECNOAPP ENCERRADO"); l.setFont(QFont("Segoe UI", 18, QFont.Bold)); self.add_neon(l, "#ff4b4b"); self.content_lyt.addWidget(l, alignment=Qt.AlignCenter); QTimer.singleShot(1000, self.close)

if __name__ == "__main__":
    app = QApplication(sys.argv); window = TecnoApp(); window.show(); sys.exit(app.exec())
