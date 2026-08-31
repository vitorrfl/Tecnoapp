"""
Prioridade de processo do jogo.

Complementa o MMCSS, que e generico: pede ao Windows para favorecer
"jogos" de forma abstrata. Aqui o alvo e o processo concreto que o usuario
apontou, e o efeito e verificavel no Gerenciador de Tarefas.

O alvo e escolhido na tela do Modo Gamer e guardado em prefs. Sem alvo
escolhido, o tweak e pulado — nao ha adivinhacao.
"""

from __future__ import annotations

from typing import Any

from ..gamedetect import (
    PRIORITY_HIGH,
    PRIORITY_NORMAL,
    find_by_names,
    set_priority,
)
from .base import Category, RiskLevel, Tweak, TweakResult, TweakStatus

def _load_targets() -> list[str]:
    """Nomes de processo que o usuario escolheu priorizar."""
    try:
        from ..prefs import load_priority_targets
        return load_priority_targets()
    except Exception:
        return []


def save_targets(nomes: list[str]) -> bool:
    try:
        from ..prefs import save_priority_targets
        return save_priority_targets(nomes)
    except Exception:
        return False


class GameProcessPriority(Tweak):
    id = "cpu.game_priority"
    category = Category.CPU
    label = "Prioridade alta para o jogo"
    description = (
        "Coloca o processo do jogo escolhido em prioridade Alta, para que o "
        "Windows lhe de CPU antes dos outros programas. Diferente do MMCSS, "
        "que e generico, aqui o alvo e o processo real em execucao."
    )
    risk = RiskLevel.LOW
    requires_reboot = False

    def is_supported(self) -> bool:
        # Depende so de psutil, disponivel em qualquer Windows suportado
        return True

    def read_current(self) -> dict[str, Any]:
        """
        Guarda a prioridade atual de cada alvo, para o revert devolver
        exatamente o que era antes.
        """
        estado: dict[str, Any] = {}
        alvos = _load_targets()
        if not alvos:
            return estado
        for c in find_by_names(alvos):
            estado[c["name"]] = c["priority"]
        return estado

    def apply(self) -> TweakResult:
        alvos = _load_targets()
        if not alvos:
            return TweakResult(
                tweak_id=self.id,
                status=TweakStatus.SKIPPED_UNSUPPORTED,
                message="nenhum jogo escolhido na tela do Modo Gamer",
            )

        anterior: dict[str, Any] = {}
        aplicados: list[str] = []
        falhas: list[str] = []

        for c in find_by_names(alvos):
            anterior[c["name"]] = c["priority"]
            ok, msg = set_priority(c["pid"], PRIORITY_HIGH)
            if ok:
                aplicados.append(c["name"])
            else:
                falhas.append(f"{c['name']} ({msg})")

        if not aplicados and not falhas:
            return TweakResult(
                tweak_id=self.id,
                status=TweakStatus.SKIPPED_UNSUPPORTED,
                message="o jogo escolhido nao esta em execucao",
                previous_state=anterior,
            )

        partes = []
        if aplicados:
            partes.append(f"{len(aplicados)} processo(s) em prioridade alta")
        if falhas:
            partes.append(f"{len(falhas)} falhou: " + ", ".join(falhas[:2]))

        return TweakResult(
            tweak_id=self.id,
            status=TweakStatus.APPLIED if aplicados else TweakStatus.FAILED,
            message=" · ".join(partes),
            previous_state=anterior,
            state_update={"targets": aplicados},
        )

    def revert(self, previous_state: dict[str, Any]) -> TweakResult:
        """
        Devolve os processos a prioridade Normal.

        Se o jogo ja foi fechado, nao ha o que reverter — a prioridade
        morre com o processo.
        """
        alvos = set(_load_targets()) | set((previous_state or {}).keys())
        if not alvos:
            return TweakResult(
                tweak_id=self.id,
                status=TweakStatus.REVERTED,
                message="nada para reverter",
            )

        revertidos = 0
        for c in find_by_names(sorted(alvos)):
            if c["is_boosted"]:
                ok, _ = set_priority(c["pid"], PRIORITY_NORMAL)
                if ok:
                    revertidos += 1

        return TweakResult(
            tweak_id=self.id,
            status=TweakStatus.REVERTED,
            message=(f"{revertidos} processo(s) de volta ao normal"
                     if revertidos else "processos ja nao estavam priorizados"),
        )


def register_all(engine) -> None:
    engine.register(GameProcessPriority())
