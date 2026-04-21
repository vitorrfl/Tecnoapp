from __future__ import annotations

import sys
import winreg
from typing import Any

from ..utils import powercfg, registry
from .base import Category, RiskLevel, Tweak, TweakResult, TweakStatus

SCHEME_CURRENT = "SCHEME_CURRENT"


class UltimatePerformancePlan(Tweak):
    id = "cpu.ultimate_performance"
    category = Category.CPU
    label = "Plano de Energia: Ultimate Performance"
    description = (
        "Duplica o plano Ultimate Performance da Microsoft e o define como ativo. "
        "Elimina throttling agressivo da CPU. Pulado em notebooks na bateria."
    )
    risk = RiskLevel.LOW

    def is_supported(self) -> bool:
        if sys.platform != "win32":
            return False
        return powercfg.is_on_ac_power()

    def read_current(self) -> dict[str, Any]:
        return {"previous_active_guid": powercfg.get_active_scheme_guid()}

    def apply(self) -> TweakResult:
        new_guid = powercfg.duplicate_scheme(powercfg.ULTIMATE_PERFORMANCE_TEMPLATE)
        if not new_guid:
            return TweakResult(
                tweak_id=self.id,
                status=TweakStatus.FAILED,
                message="powercfg -duplicatescheme falhou (edição do Windows pode não suportar)",
            )
        if not powercfg.set_active(new_guid):
            powercfg.delete_scheme(new_guid)
            return TweakResult(
                tweak_id=self.id,
                status=TweakStatus.FAILED,
                message="não foi possível ativar o plano criado",
            )
        return TweakResult(
            tweak_id=self.id,
            status=TweakStatus.APPLIED,
            message="Ultimate Performance ativo",
            state_update={"created_guid": new_guid},
        )

    def revert(self, previous_state: dict[str, Any]) -> TweakResult:
        previous_guid = previous_state.get("previous_active_guid")
        created_guid = previous_state.get("created_guid")

        if previous_guid:
            powercfg.set_active(previous_guid)
        if created_guid and powercfg.scheme_exists(created_guid):
            powercfg.delete_scheme(created_guid)

        return TweakResult(
            tweak_id=self.id,
            status=TweakStatus.REVERTED,
            message="plano anterior restaurado",
        )


class CoreParkingDisabled(Tweak):
    id = "cpu.core_parking_off"
    category = Category.CPU
    label = "Desabilitar Core Parking"
    description = (
        "Força o Windows a manter 100% dos núcleos ativos no plano atual. "
        "Reduz latência de escalonamento em CPUs multi-core."
    )
    risk = RiskLevel.LOW

    def is_supported(self) -> bool:
        return sys.platform == "win32"

    def read_current(self) -> dict[str, Any]:
        powercfg.unhide_attribute(powercfg.SUB_PROCESSOR, powercfg.SETTING_CPMINCORES)
        ac, dc = powercfg.query_setting_index(
            SCHEME_CURRENT, powercfg.SUB_PROCESSOR, powercfg.SETTING_CPMINCORES
        )
        return {"ac": ac, "dc": dc}

    def apply(self) -> TweakResult:
        ok_ac = powercfg.set_ac_value_index(
            SCHEME_CURRENT, powercfg.SUB_PROCESSOR, powercfg.SETTING_CPMINCORES, 100
        )
        ok_dc = powercfg.set_dc_value_index(
            SCHEME_CURRENT, powercfg.SUB_PROCESSOR, powercfg.SETTING_CPMINCORES, 100
        )
        active = powercfg.get_active_scheme_guid()
        if active:
            powercfg.set_active(active)
        if not (ok_ac and ok_dc):
            return TweakResult(
                tweak_id=self.id,
                status=TweakStatus.FAILED,
                message="falha ao definir CPMINCORES via powercfg",
            )
        return TweakResult(
            tweak_id=self.id,
            status=TweakStatus.APPLIED,
            message="core parking desativado (100% núcleos ativos)",
        )

    def revert(self, previous_state: dict[str, Any]) -> TweakResult:
        ac = previous_state.get("ac")
        dc = previous_state.get("dc")
        if ac is not None:
            powercfg.set_ac_value_index(
                SCHEME_CURRENT, powercfg.SUB_PROCESSOR, powercfg.SETTING_CPMINCORES, int(ac)
            )
        if dc is not None:
            powercfg.set_dc_value_index(
                SCHEME_CURRENT, powercfg.SUB_PROCESSOR, powercfg.SETTING_CPMINCORES, int(dc)
            )
        active = powercfg.get_active_scheme_guid()
        if active:
            powercfg.set_active(active)
        return TweakResult(
            tweak_id=self.id,
            status=TweakStatus.REVERTED,
            message="core parking restaurado ao valor anterior",
        )


_MMCSS_PATH = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Games"
_MMCSS_VALUES = [
    ("GPU Priority", 8, winreg.REG_DWORD),
    ("Priority", 6, winreg.REG_DWORD),
    ("Scheduling Category", "High", winreg.REG_SZ),
    ("SFIO Priority", "High", winreg.REG_SZ),
]


class MMCSSGamesPriority(Tweak):
    id = "cpu.mmcss_games"
    category = Category.CPU
    label = "MMCSS: prioridade alta para Jogos"
    description = (
        "Ajusta o perfil Games do Multimedia Class Scheduler (MMCSS) para prioridade máxima. "
        "Melhora escalonamento de threads de jogos competindo com background."
    )
    risk = RiskLevel.LOW

    def is_supported(self) -> bool:
        return sys.platform == "win32"

    def read_current(self) -> dict[str, Any]:
        snapshots = []
        for name, _target, _reg_type in _MMCSS_VALUES:
            snapshots.append(registry.snapshot_value("HKLM", _MMCSS_PATH, name))
        return {"values": snapshots}

    def apply(self) -> TweakResult:
        try:
            for name, value, reg_type in _MMCSS_VALUES:
                registry.write_value("HKLM", _MMCSS_PATH, name, value, reg_type)
        except OSError as exc:
            return TweakResult(
                tweak_id=self.id,
                status=TweakStatus.FAILED,
                message="falha ao escrever chave MMCSS",
                error=str(exc),
            )
        return TweakResult(
            tweak_id=self.id,
            status=TweakStatus.APPLIED,
            message="perfil MMCSS Games ajustado",
        )

    def revert(self, previous_state: dict[str, Any]) -> TweakResult:
        values = previous_state.get("values") or []
        errors = []
        for snap in values:
            try:
                registry.restore_value(snap)
            except OSError as exc:
                errors.append(f"{snap.get('name')}: {exc}")
        if errors:
            return TweakResult(
                tweak_id=self.id,
                status=TweakStatus.REVERT_FAILED,
                message="alguns valores não restauraram",
                error="; ".join(errors),
            )
        return TweakResult(
            tweak_id=self.id,
            status=TweakStatus.REVERTED,
            message="perfil MMCSS Games restaurado",
        )


def register_all(engine) -> None:
    engine.register(UltimatePerformancePlan())
    engine.register(CoreParkingDisabled())
    engine.register(MMCSSGamesPriority())
