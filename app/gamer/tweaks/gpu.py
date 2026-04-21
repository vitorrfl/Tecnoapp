from __future__ import annotations

import sys
import winreg
from typing import Any

from ..utils import registry
from .base import Category, RiskLevel, Tweak, TweakResult, TweakStatus


def _apply_registry_values(
    tweak_id: str,
    values: list[tuple[str, str, str, Any, int]],
    success_msg: str,
) -> TweakResult:
    try:
        registry.write_many(values)
    except OSError as exc:
        return TweakResult(
            tweak_id=tweak_id,
            status=TweakStatus.FAILED,
            message="falha ao escrever registro",
            error=str(exc),
        )
    return TweakResult(tweak_id=tweak_id, status=TweakStatus.APPLIED, message=success_msg)


def _revert_registry_snapshots(tweak_id: str, snapshots: list[dict], success_msg: str) -> TweakResult:
    errors = registry.restore_many(snapshots)
    if errors:
        return TweakResult(
            tweak_id=tweak_id,
            status=TweakStatus.REVERT_FAILED,
            message="alguns valores não restauraram",
            error="; ".join(errors),
        )
    return TweakResult(tweak_id=tweak_id, status=TweakStatus.REVERTED, message=success_msg)


# --- G1: HAGS --------------------------------------------------------------

_HAGS_PATH = r"SYSTEM\CurrentControlSet\Control\GraphicsDrivers"


class HardwareAcceleratedGpuScheduling(Tweak):
    id = "gpu.hags"
    category = Category.GPU
    label = "HAGS — Hardware Accelerated GPU Scheduling"
    description = (
        "Ativa o escalonamento de GPU por hardware. Reduz latência em GPUs modernas "
        "(NVIDIA Turing+/AMD RDNA2+). Requer reinicialização para entrar em efeito."
    )
    risk = RiskLevel.MEDIUM
    requires_reboot = True

    def is_supported(self) -> bool:
        if sys.platform != "win32":
            return False
        # HAGS registry key exists on Windows 10 2004 (build 19041) and later
        return sys.getwindowsversion().build >= 19041

    def read_current(self) -> dict[str, Any]:
        return {"snapshots": registry.snapshot_many([("HKLM", _HAGS_PATH, "HwSchMode")])}

    def apply(self) -> TweakResult:
        return _apply_registry_values(
            self.id,
            [("HKLM", _HAGS_PATH, "HwSchMode", 2, winreg.REG_DWORD)],
            "HAGS ativado (requer reboot)",
        )

    def revert(self, previous_state: dict[str, Any]) -> TweakResult:
        return _revert_registry_snapshots(
            self.id, previous_state.get("snapshots", []), "HAGS restaurado"
        )


# --- G2: Fullscreen Optimizations OFF -------------------------------------

_GAMECONFIG_PATH = r"System\GameConfigStore"

_FSO_OFF_VALUES: list[tuple[str, str, str, Any, int]] = [
    ("HKCU", _GAMECONFIG_PATH, "GameDVR_FSEBehaviorMode", 2, winreg.REG_DWORD),
    ("HKCU", _GAMECONFIG_PATH, "GameDVR_HonorUserFSEBehaviorMode", 1, winreg.REG_DWORD),
    ("HKCU", _GAMECONFIG_PATH, "GameDVR_DXGIHonorFSEWindowsCompatible", 1, winreg.REG_DWORD),
    ("HKCU", _GAMECONFIG_PATH, "GameDVR_EFSEFeatureFlags", 0, winreg.REG_DWORD),
]


class FullscreenOptimizationsOff(Tweak):
    id = "gpu.fso_off"
    category = Category.GPU
    label = "Desativar Fullscreen Optimizations (global)"
    description = (
        "Força fullscreen exclusivo em jogos DX11/DX12, eliminando o composer do DWM "
        "no caminho de renderização. Ganho direto de FPS e input lag."
    )
    risk = RiskLevel.LOW

    def is_supported(self) -> bool:
        return sys.platform == "win32"

    def read_current(self) -> dict[str, Any]:
        entries = [(h, p, n) for (h, p, n, _v, _t) in _FSO_OFF_VALUES]
        return {"snapshots": registry.snapshot_many(entries)}

    def apply(self) -> TweakResult:
        return _apply_registry_values(self.id, _FSO_OFF_VALUES, "Fullscreen Optimizations desativado")

    def revert(self, previous_state: dict[str, Any]) -> TweakResult:
        return _revert_registry_snapshots(
            self.id, previous_state.get("snapshots", []), "Fullscreen Optimizations restaurado"
        )


# --- G3: Game DVR / Xbox Capture OFF --------------------------------------

_GAMEDVR_PATH = r"Software\Microsoft\Windows\CurrentVersion\GameDVR"

_GAMEDVR_OFF_VALUES: list[tuple[str, str, str, Any, int]] = [
    ("HKCU", _GAMECONFIG_PATH, "GameDVR_Enabled", 0, winreg.REG_DWORD),
    ("HKCU", _GAMEDVR_PATH, "AppCaptureEnabled", 0, winreg.REG_DWORD),
]


class GameDvrOff(Tweak):
    id = "gpu.gamedvr_off"
    category = Category.GPU
    label = "Desativar Game DVR / Xbox Capture"
    description = (
        "Encerra a captura em background do Xbox Game Bar. Libera overhead de GPU "
        "(2-5%) especialmente em notebooks."
    )
    risk = RiskLevel.LOW

    def is_supported(self) -> bool:
        return sys.platform == "win32"

    def read_current(self) -> dict[str, Any]:
        entries = [(h, p, n) for (h, p, n, _v, _t) in _GAMEDVR_OFF_VALUES]
        return {"snapshots": registry.snapshot_many(entries)}

    def apply(self) -> TweakResult:
        return _apply_registry_values(self.id, _GAMEDVR_OFF_VALUES, "Game DVR desativado")

    def revert(self, previous_state: dict[str, Any]) -> TweakResult:
        return _revert_registry_snapshots(
            self.id, previous_state.get("snapshots", []), "Game DVR restaurado"
        )


# --- G4: Game Mode ON ------------------------------------------------------

_GAMEBAR_PATH = r"Software\Microsoft\GameBar"

_GAMEMODE_ON_VALUES: list[tuple[str, str, str, Any, int]] = [
    ("HKCU", _GAMEBAR_PATH, "AllowAutoGameMode", 1, winreg.REG_DWORD),
    ("HKCU", _GAMEBAR_PATH, "AutoGameModeEnabled", 1, winreg.REG_DWORD),
]


class GameModeOn(Tweak):
    id = "gpu.game_mode_on"
    category = Category.GPU
    label = "Garantir Game Mode ativo"
    description = (
        "Força o Game Mode do Windows a ficar ativo automaticamente. "
        "Reduz interrupções de background durante jogos."
    )
    risk = RiskLevel.LOW

    def is_supported(self) -> bool:
        return sys.platform == "win32"

    def read_current(self) -> dict[str, Any]:
        entries = [(h, p, n) for (h, p, n, _v, _t) in _GAMEMODE_ON_VALUES]
        return {"snapshots": registry.snapshot_many(entries)}

    def apply(self) -> TweakResult:
        return _apply_registry_values(self.id, _GAMEMODE_ON_VALUES, "Game Mode garantido")

    def revert(self, previous_state: dict[str, Any]) -> TweakResult:
        return _revert_registry_snapshots(
            self.id, previous_state.get("snapshots", []), "Game Mode restaurado"
        )


# --- G5: TDR delay --------------------------------------------------------

_TDR_VALUES: list[tuple[str, str, str, Any, int]] = [
    ("HKLM", _HAGS_PATH, "TdrDelay", 10, winreg.REG_DWORD),
]


class TdrDelayExtended(Tweak):
    id = "gpu.tdr_delay"
    category = Category.GPU
    label = "Estender timeout TDR da GPU"
    description = (
        "Aumenta o Timeout Detection and Recovery da GPU para 10s. "
        "Evita crashes em jogos pesados ou com overclock. Requer reboot."
    )
    risk = RiskLevel.MEDIUM
    requires_reboot = True

    def is_supported(self) -> bool:
        return sys.platform == "win32"

    def read_current(self) -> dict[str, Any]:
        entries = [(h, p, n) for (h, p, n, _v, _t) in _TDR_VALUES]
        return {"snapshots": registry.snapshot_many(entries)}

    def apply(self) -> TweakResult:
        return _apply_registry_values(self.id, _TDR_VALUES, "TDR delay estendido para 10s")

    def revert(self, previous_state: dict[str, Any]) -> TweakResult:
        return _revert_registry_snapshots(
            self.id, previous_state.get("snapshots", []), "TDR delay restaurado"
        )


def register_all(engine) -> None:
    engine.register(HardwareAcceleratedGpuScheduling())
    engine.register(FullscreenOptimizationsOff())
    engine.register(GameDvrOff())
    engine.register(GameModeOn())
    engine.register(TdrDelayExtended())
