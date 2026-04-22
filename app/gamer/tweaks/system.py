from __future__ import annotations

import ctypes
import subprocess
import sys
import winreg
from typing import Any

from ..utils import registry, services
from .base import Category, RiskLevel, Tweak, TweakResult, TweakStatus

_CREATE_NO_WINDOW = 0x08000000


# --- S1: Bloatware killer -------------------------------------------------
#
# Whitelist-only. Discord and Steam are intentionally NOT in this list —
# user rule: never close communication/game-launcher apps.

_BLOAT_PROCESSES: list[str] = [
    "OneDrive.exe",
    "Teams.exe",
    "ms-teams.exe",
    "Spotify.exe",
    "SearchApp.exe",
    "YourPhone.exe",
    "PhoneExperienceHost.exe",
    "GameBar.exe",
    "GameBarFTServer.exe",
]


class BloatwareKiller(Tweak):
    id = "system.kill_bloat"
    category = Category.SYSTEM
    label = "Encerrar processos em background"
    description = (
        "Encerra apps não essenciais rodando em background (OneDrive, Teams, Spotify, "
        "Your Phone, Game Bar, etc). Discord e Steam são preservados. "
        "Processos reiniciam no próximo login."
    )
    risk = RiskLevel.LOW

    def is_supported(self) -> bool:
        return sys.platform == "win32"

    def read_current(self) -> dict[str, Any]:
        return {"targets": list(_BLOAT_PROCESSES)}

    def apply(self) -> TweakResult:
        killed: list[str] = []
        for proc in _BLOAT_PROCESSES:
            result = subprocess.run(
                ["taskkill", "/F", "/IM", proc],
                capture_output=True,
                text=True,
                creationflags=_CREATE_NO_WINDOW,
                check=False,
            )
            if result.returncode == 0:
                killed.append(proc)
        return TweakResult(
            tweak_id=self.id,
            status=TweakStatus.APPLIED,
            message=f"{len(killed)} processo(s) encerrados",
            state_update={"killed": killed},
        )

    def revert(self, previous_state: dict[str, Any]) -> TweakResult:
        return TweakResult(
            tweak_id=self.id,
            status=TweakStatus.REVERTED,
            message="processos reiniciam normalmente no próximo login",
        )


# --- S2: Empty standby memory ---------------------------------------------


class EmptyStandbyMemory(Tweak):
    id = "system.empty_standby"
    category = Category.SYSTEM
    label = "Liberar memória em standby"
    description = (
        "Libera páginas na lista de standby via NtSetSystemInformation. "
        "Ação pontual — sem estado a reverter."
    )
    risk = RiskLevel.HIGH
    opt_in = True
    warning = (
        "API semi-documentada do kernel (ntdll). Em alguns sistemas pode colidir "
        "com drivers (GPU/AV) e causar BSOD (MEMORY_MANAGEMENT). Ative por sua conta e risco."
    )

    def is_supported(self) -> bool:
        return sys.platform == "win32"

    def read_current(self) -> dict[str, Any]:
        return {}

    def apply(self) -> TweakResult:
        try:
            ntdll = ctypes.WinDLL("ntdll", use_last_error=True)
            # SeProfileSingleProcessPrivilege = 13
            previous = ctypes.c_byte()
            status = ntdll.RtlAdjustPrivilege(13, 1, 0, ctypes.byref(previous))
            if status != 0:
                return TweakResult(
                    tweak_id=self.id,
                    status=TweakStatus.FAILED,
                    message="sem privilégio para purgar standby (execute como admin)",
                )
            SystemMemoryListInformation = 80
            MemoryPurgeStandbyList = 4
            cmd = ctypes.c_int(MemoryPurgeStandbyList)
            status = ntdll.NtSetSystemInformation(
                SystemMemoryListInformation, ctypes.byref(cmd), ctypes.sizeof(cmd)
            )
            if status != 0:
                return TweakResult(
                    tweak_id=self.id,
                    status=TweakStatus.FAILED,
                    message=f"NtSetSystemInformation retornou {status:#x}",
                )
        except OSError as exc:
            return TweakResult(
                tweak_id=self.id,
                status=TweakStatus.FAILED,
                message="falha ao carregar ntdll",
                error=str(exc),
            )
        return TweakResult(
            tweak_id=self.id, status=TweakStatus.APPLIED, message="standby memory liberada"
        )

    def revert(self, previous_state: dict[str, Any]) -> TweakResult:
        return TweakResult(
            tweak_id=self.id,
            status=TweakStatus.REVERTED,
            message="nada a reverter (ação pontual)",
        )


# --- S3: Visual effects performance ---------------------------------------

_VFX_PATH = r"Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects"
_VFX_VALUES: list[tuple[str, str, str, Any, int]] = [
    ("HKCU", _VFX_PATH, "VisualFXSetting", 2, winreg.REG_DWORD),
]


class VisualEffectsPerformance(Tweak):
    id = "system.visual_effects_perf"
    category = Category.SYSTEM
    label = "Efeitos visuais: modo desempenho"
    description = (
        "Seta VisualFXSetting=2 (ajustar para melhor desempenho). "
        "Ganho perceptível em PCs mais fracos — GPU e CPU liberados de animações."
    )
    risk = RiskLevel.LOW

    def is_supported(self) -> bool:
        return sys.platform == "win32"

    def read_current(self) -> dict[str, Any]:
        entries = [(h, p, n) for (h, p, n, _v, _t) in _VFX_VALUES]
        return {"snapshots": registry.snapshot_many(entries)}

    def apply(self) -> TweakResult:
        try:
            registry.write_many(_VFX_VALUES)
        except OSError as exc:
            return TweakResult(
                tweak_id=self.id, status=TweakStatus.FAILED, message="falha registro", error=str(exc)
            )
        return TweakResult(
            tweak_id=self.id, status=TweakStatus.APPLIED, message="modo desempenho ativado"
        )

    def revert(self, previous_state: dict[str, Any]) -> TweakResult:
        errors = registry.restore_many(previous_state.get("snapshots", []))
        if errors:
            return TweakResult(
                tweak_id=self.id,
                status=TweakStatus.REVERT_FAILED,
                message="alguns valores não restauraram",
                error="; ".join(errors),
            )
        return TweakResult(
            tweak_id=self.id, status=TweakStatus.REVERTED, message="efeitos visuais restaurados"
        )


# --- S4: Notifications / Toast off ----------------------------------------

_TOAST_PATH = r"Software\Microsoft\Windows\CurrentVersion\PushNotifications"
_TOAST_VALUES: list[tuple[str, str, str, Any, int]] = [
    ("HKCU", _TOAST_PATH, "ToastEnabled", 0, winreg.REG_DWORD),
]


class NotificationsOff(Tweak):
    id = "system.toasts_off"
    category = Category.SYSTEM
    label = "Desativar notificações (toasts)"
    description = (
        "Desliga notificações em toast. Evita tirar o jogo do fullscreen e "
        "interromper o foco."
    )
    risk = RiskLevel.LOW

    def is_supported(self) -> bool:
        return sys.platform == "win32"

    def read_current(self) -> dict[str, Any]:
        entries = [(h, p, n) for (h, p, n, _v, _t) in _TOAST_VALUES]
        return {"snapshots": registry.snapshot_many(entries)}

    def apply(self) -> TweakResult:
        try:
            registry.write_many(_TOAST_VALUES)
        except OSError as exc:
            return TweakResult(
                tweak_id=self.id, status=TweakStatus.FAILED, message="falha registro", error=str(exc)
            )
        return TweakResult(
            tweak_id=self.id, status=TweakStatus.APPLIED, message="notificações desativadas"
        )

    def revert(self, previous_state: dict[str, Any]) -> TweakResult:
        errors = registry.restore_many(previous_state.get("snapshots", []))
        if errors:
            return TweakResult(
                tweak_id=self.id,
                status=TweakStatus.REVERT_FAILED,
                message="alguns valores não restauraram",
                error="; ".join(errors),
            )
        return TweakResult(
            tweak_id=self.id, status=TweakStatus.REVERTED, message="notificações restauradas"
        )


# --- S5: Non-essential services on demand ---------------------------------
#
# Whitelist. Critical services (Audiosrv, RpcSs, CryptSvc, WinDefend,
# BITS) are NEVER touched.

_SERVICES_TO_DEMAND: list[str] = [
    "SysMain",   # Superfetch — inútil em SSD, overhead em HDD mínimo
    "DiagTrack", # Telemetria do Windows
    "WSearch",   # Indexação — Windows Search fica mais lento mas libera I/O
]


class NonEssentialServicesOnDemand(Tweak):
    id = "system.services_demand"
    category = Category.SYSTEM
    label = "Serviços não essenciais sob demanda"
    description = (
        "Coloca SysMain (Superfetch), DiagTrack (telemetria) e WSearch (indexação) "
        "em modo 'demand start'. Libera I/O e CPU durante sessões de jogo."
    )
    risk = RiskLevel.MEDIUM

    def is_supported(self) -> bool:
        return sys.platform == "win32"

    def read_current(self) -> dict[str, Any]:
        state: dict[str, str | None] = {}
        for svc in _SERVICES_TO_DEMAND:
            state[svc] = services.query_start_type(svc)
        return {"services": state}

    def apply(self) -> TweakResult:
        changed: list[str] = []
        failed: list[str] = []
        for svc in _SERVICES_TO_DEMAND:
            if services.set_start_type(svc, "demand"):
                changed.append(svc)
            else:
                failed.append(svc)
        if failed and not changed:
            return TweakResult(
                tweak_id=self.id,
                status=TweakStatus.FAILED,
                message=f"nenhum serviço alterado ({', '.join(failed)})",
            )
        return TweakResult(
            tweak_id=self.id,
            status=TweakStatus.APPLIED,
            message=f"{len(changed)} serviço(s) em demand" + (f" | falhas: {', '.join(failed)}" if failed else ""),
        )

    def revert(self, previous_state: dict[str, Any]) -> TweakResult:
        errors: list[str] = []
        for svc, start_type in (previous_state.get("services") or {}).items():
            if not start_type:
                continue
            if not services.set_start_type(svc, start_type):
                errors.append(svc)
        if errors:
            return TweakResult(
                tweak_id=self.id,
                status=TweakStatus.REVERT_FAILED,
                message=f"falha ao restaurar: {', '.join(errors)}",
            )
        return TweakResult(
            tweak_id=self.id, status=TweakStatus.REVERTED, message="serviços restaurados"
        )


def register_all(engine) -> None:
    engine.register(BloatwareKiller())
    engine.register(EmptyStandbyMemory())
    engine.register(VisualEffectsPerformance())
    engine.register(NotificationsOff())
    engine.register(NonEssentialServicesOnDemand())
