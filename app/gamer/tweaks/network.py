from __future__ import annotations

import sys
import winreg
from typing import Any

from ..utils import netsh, registry
from .base import Category, RiskLevel, Tweak, TweakResult, TweakStatus


# --- N1: TCP autotuning ---------------------------------------------------


class TcpAutotuningNormal(Tweak):
    id = "network.tcp_autotuning"
    category = Category.NETWORK
    label = "TCP autotuning: normal"
    description = (
        "Garante TCP Receive Window Auto-Tuning em 'normal'. "
        "Melhora vazão em conexões de alta latência."
    )
    risk = RiskLevel.LOW

    def is_supported(self) -> bool:
        return sys.platform == "win32"

    def read_current(self) -> dict[str, Any]:
        return {"level": netsh.get_autotuninglevel()}

    def apply(self) -> TweakResult:
        if not netsh.set_autotuninglevel("normal"):
            return TweakResult(
                tweak_id=self.id,
                status=TweakStatus.FAILED,
                message="netsh set global falhou",
            )
        return TweakResult(
            tweak_id=self.id, status=TweakStatus.APPLIED, message="autotuning=normal"
        )

    def revert(self, previous_state: dict[str, Any]) -> TweakResult:
        level = previous_state.get("level") or "normal"
        netsh.set_autotuninglevel(level)
        return TweakResult(
            tweak_id=self.id, status=TweakStatus.REVERTED, message=f"autotuning={level}"
        )


# --- N2: Disable Nagle per interface --------------------------------------

_INTERFACES_PATH = r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces"
_NAGLE_VALUES = [
    ("TcpAckFrequency", 1, winreg.REG_DWORD),
    ("TCPNoDelay", 1, winreg.REG_DWORD),
    ("TcpDelAckTicks", 0, winreg.REG_DWORD),
]


def _active_interface_guids() -> list[str]:
    """Interfaces that have an IP configured (static or DHCP)."""
    guids: list[str] = []
    for guid in registry.enum_subkeys("HKLM", _INTERFACES_PATH):
        path = f"{_INTERFACES_PATH}\\{guid}"
        ip = registry.read_value("HKLM", path, "IPAddress")
        dhcp_ip = registry.read_value("HKLM", path, "DhcpIPAddress")
        if _has_valid_ip(ip) or _has_valid_ip(dhcp_ip):
            guids.append(guid)
    return guids


def _has_valid_ip(entry: tuple[Any, int] | None) -> bool:
    if entry is None:
        return False
    value = entry[0]
    if isinstance(value, list):
        return any(v and v != "0.0.0.0" for v in value)
    return bool(value) and value != "0.0.0.0"


class NagleDisabled(Tweak):
    id = "network.nagle_off"
    category = Category.NETWORK
    label = "Desabilitar Nagle (baixa latência)"
    description = (
        "Desativa o Nagle Algorithm nas interfaces ativas. "
        "Reduz latência em jogos online competitivos."
    )
    risk = RiskLevel.MEDIUM

    def is_supported(self) -> bool:
        return sys.platform == "win32"

    def read_current(self) -> dict[str, Any]:
        guids = _active_interface_guids()
        snapshots: list[dict] = []
        for guid in guids:
            path = f"{_INTERFACES_PATH}\\{guid}"
            for name, _v, _t in _NAGLE_VALUES:
                snapshots.append(registry.snapshot_value("HKLM", path, name))
        return {"interfaces": guids, "snapshots": snapshots}

    def apply(self) -> TweakResult:
        guids = _active_interface_guids()
        if not guids:
            return TweakResult(
                tweak_id=self.id,
                status=TweakStatus.SKIPPED_UNSUPPORTED,
                message="nenhuma interface com IP detectada",
            )
        try:
            for guid in guids:
                path = f"{_INTERFACES_PATH}\\{guid}"
                for name, value, reg_type in _NAGLE_VALUES:
                    registry.write_value("HKLM", path, name, value, reg_type)
        except OSError as exc:
            return TweakResult(
                tweak_id=self.id,
                status=TweakStatus.FAILED,
                message="falha ao gravar no registro de interface",
                error=str(exc),
            )
        return TweakResult(
            tweak_id=self.id,
            status=TweakStatus.APPLIED,
            message=f"Nagle desativado em {len(guids)} interface(s)",
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
            tweak_id=self.id, status=TweakStatus.REVERTED, message="Nagle restaurado"
        )


# --- N3: Network throttling off -------------------------------------------

_MM_PROFILE_PATH = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile"
_THROTTLING_VALUES: list[tuple[str, str, str, Any, int]] = [
    ("HKLM", _MM_PROFILE_PATH, "NetworkThrottlingIndex", 0xFFFFFFFF, winreg.REG_DWORD),
]


class NetworkThrottlingOff(Tweak):
    id = "network.throttling_off"
    category = Category.NETWORK
    label = "Desativar network throttling"
    description = (
        "Seta NetworkThrottlingIndex=0xFFFFFFFF para remover o limite de pacotes "
        "por segundo imposto ao tráfego de rede em apps não-multimedia."
    )
    risk = RiskLevel.LOW

    def is_supported(self) -> bool:
        return sys.platform == "win32"

    def read_current(self) -> dict[str, Any]:
        entries = [(h, p, n) for (h, p, n, _v, _t) in _THROTTLING_VALUES]
        return {"snapshots": registry.snapshot_many(entries)}

    def apply(self) -> TweakResult:
        try:
            registry.write_many(_THROTTLING_VALUES)
        except OSError as exc:
            return TweakResult(
                tweak_id=self.id, status=TweakStatus.FAILED, message="falha registro", error=str(exc)
            )
        return TweakResult(
            tweak_id=self.id, status=TweakStatus.APPLIED, message="network throttling desativado"
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
            tweak_id=self.id, status=TweakStatus.REVERTED, message="throttling restaurado"
        )


# --- N4: Flush DNS (one-shot) ---------------------------------------------


class FlushDns(Tweak):
    id = "network.flush_dns"
    category = Category.NETWORK
    label = "Limpar cache DNS"
    description = "Executa ipconfig /flushdns. Ação pontual, sem estado a reverter."
    risk = RiskLevel.LOW

    def is_supported(self) -> bool:
        return sys.platform == "win32"

    def read_current(self) -> dict[str, Any]:
        return {}

    def apply(self) -> TweakResult:
        if not netsh.flush_dns():
            return TweakResult(
                tweak_id=self.id, status=TweakStatus.FAILED, message="ipconfig /flushdns falhou"
            )
        return TweakResult(
            tweak_id=self.id, status=TweakStatus.APPLIED, message="cache DNS limpo"
        )

    def revert(self, previous_state: dict[str, Any]) -> TweakResult:
        return TweakResult(
            tweak_id=self.id,
            status=TweakStatus.REVERTED,
            message="nada a reverter (ação pontual)",
        )


def register_all(engine) -> None:
    engine.register(TcpAutotuningNormal())
    engine.register(NagleDisabled())
    engine.register(NetworkThrottlingOff())
    engine.register(FlushDns())
