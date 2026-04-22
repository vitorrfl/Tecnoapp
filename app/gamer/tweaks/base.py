from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Category(str, Enum):
    CPU = "cpu"
    GPU = "gpu"
    SYSTEM = "system"
    NETWORK = "network"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TweakStatus(str, Enum):
    APPLIED = "applied"
    SKIPPED_UNSUPPORTED = "skipped_unsupported"
    SKIPPED_ALREADY = "skipped_already_applied"
    FAILED = "failed"
    REVERTED = "reverted"
    REVERT_FAILED = "revert_failed"


@dataclass
class TweakResult:
    tweak_id: str
    status: TweakStatus
    message: str = ""
    error: str | None = None
    previous_state: dict[str, Any] = field(default_factory=dict)
    state_update: dict[str, Any] = field(default_factory=dict)
    """Extra state produced by apply() that must be persisted for revert().

    Example: a tweak that creates a new power plan stores the new GUID here
    so the snapshot knows what to delete on revert.
    """


class Tweak(ABC):
    """Base contract for every reversible optimization.

    Subclasses must be idempotent: calling apply() twice must not corrupt state,
    and revert() must work whether or not apply() ran earlier.
    """

    id: str
    category: Category
    label: str
    description: str = ""
    risk: RiskLevel = RiskLevel.LOW
    requires_reboot: bool = False
    opt_in: bool = False
    """If True, skipped by default in activate() — only runs when the user
    explicitly enables it via the Advanced screen. Use for tweaks with
    non-trivial failure modes (e.g. kernel-level APIs)."""
    warning: str = ""
    """User-facing warning shown next to opt-in tweaks in the Advanced screen."""

    @abstractmethod
    def is_supported(self) -> bool:
        ...

    @abstractmethod
    def read_current(self) -> dict[str, Any]:
        ...

    @abstractmethod
    def apply(self) -> TweakResult:
        ...

    @abstractmethod
    def revert(self, previous_state: dict[str, Any]) -> TweakResult:
        ...

    def __repr__(self) -> str:
        return f"<Tweak {self.id} ({self.category.value})>"
