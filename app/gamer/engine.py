from __future__ import annotations

import logging
import sys
from dataclasses import dataclass, field
from logging.handlers import RotatingFileHandler
from pathlib import Path

from .snapshot import Snapshot, SnapshotStore, TweakSnapshot, appdata_dir
from .tweaks import Category, Tweak, TweakResult, TweakStatus


def _setup_logger() -> logging.Logger:
    logger = logging.getLogger("tecnoapp.gamer")
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    log_path: Path = appdata_dir() / "gamer.log"
    handler = RotatingFileHandler(log_path, maxBytes=512_000, backupCount=3, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(handler)
    return logger


@dataclass
class RunReport:
    run_id: str
    applied: list[TweakResult] = field(default_factory=list)
    skipped: list[TweakResult] = field(default_factory=list)
    failed: list[TweakResult] = field(default_factory=list)
    reboot_required: bool = False

    @property
    def total(self) -> int:
        return len(self.applied) + len(self.skipped) + len(self.failed)

    def summary(self) -> str:
        return (
            f"aplicados={len(self.applied)} "
            f"pulados={len(self.skipped)} "
            f"falhas={len(self.failed)}"
            + (" | REINICIAR" if self.reboot_required else "")
        )


class GamerEngine:
    """Orchestrates activation and reversal of gaming tweaks.

    Register Tweak instances via register(); call activate() to snapshot-then-apply
    and deactivate() to revert using the last saved snapshot. Partial failures
    during activate() do NOT trigger automatic rollback — the user is expected to
    click Deactivate for a clean revert (see planning doc).
    """

    def __init__(self) -> None:
        self._tweaks: dict[str, Tweak] = {}
        self._store = SnapshotStore()
        self._log = _setup_logger()

    def register(self, tweak: Tweak) -> None:
        if tweak.id in self._tweaks:
            raise ValueError(f"duplicate tweak id: {tweak.id}")
        self._tweaks[tweak.id] = tweak

    def tweaks(self) -> list[Tweak]:
        return list(self._tweaks.values())

    def tweaks_by_category(self) -> dict[Category, list[Tweak]]:
        grouped: dict[Category, list[Tweak]] = {c: [] for c in Category}
        for t in self._tweaks.values():
            grouped[t.category].append(t)
        return grouped

    def is_active(self) -> bool:
        return self._store.is_active()

    def active_snapshot(self) -> Snapshot | None:
        return self._store.load_active()

    def activate(self, enabled_optins: set[str] | None = None) -> RunReport:
        """Activate tweaks. opt-in tweaks only run when their id is in
        ``enabled_optins``; non-opt-in tweaks always run."""
        if self.is_active():
            self._log.info("activate() called while already active — ignoring")
            existing = self._store.load_active()
            return RunReport(run_id=existing.run_id if existing else "unknown")

        enabled_optins = enabled_optins or set()
        snapshot = Snapshot.new(windows_version=_windows_version())
        report = RunReport(run_id=snapshot.run_id)
        self._log.info("ACTIVATE begin run_id=%s optins=%s", snapshot.run_id, sorted(enabled_optins))

        supported: list[tuple[Tweak, dict]] = []
        for tweak in self._tweaks.values():
            try:
                if tweak.opt_in and tweak.id not in enabled_optins:
                    res = TweakResult(
                        tweak_id=tweak.id,
                        status=TweakStatus.SKIPPED_UNSUPPORTED,
                        message="opt-in desativado",
                    )
                    report.skipped.append(res)
                    self._log.info("skip %s (opt-in off)", tweak.id)
                    continue
                if not tweak.is_supported():
                    res = TweakResult(
                        tweak_id=tweak.id,
                        status=TweakStatus.SKIPPED_UNSUPPORTED,
                        message="not supported on this system",
                    )
                    report.skipped.append(res)
                    self._log.info("skip %s (unsupported)", tweak.id)
                    continue
                previous = tweak.read_current()
                supported.append((tweak, previous))
                snapshot.tweaks.append(
                    TweakSnapshot(
                        tweak_id=tweak.id,
                        category=tweak.category.value,
                        label=tweak.label,
                        previous_state=previous,
                    )
                )
            except Exception as exc:
                report.failed.append(
                    TweakResult(
                        tweak_id=tweak.id,
                        status=TweakStatus.FAILED,
                        message="pre-check failed",
                        error=str(exc),
                    )
                )
                self._log.exception("pre-check failed for %s", tweak.id)

        self._store.save(snapshot)
        self._store.mark_active(snapshot)

        for tweak, _prev in supported:
            try:
                result = tweak.apply()
            except Exception as exc:
                result = TweakResult(
                    tweak_id=tweak.id,
                    status=TweakStatus.FAILED,
                    message="apply raised",
                    error=str(exc),
                )
                self._log.exception("apply raised for %s", tweak.id)

            if result.status == TweakStatus.APPLIED:
                report.applied.append(result)
                if tweak.requires_reboot:
                    report.reboot_required = True
                if result.state_update:
                    for entry in snapshot.tweaks:
                        if entry.tweak_id == tweak.id:
                            entry.previous_state.update(result.state_update)
                            break
                    self._store.save(snapshot)
            elif result.status == TweakStatus.FAILED:
                report.failed.append(result)
            else:
                report.skipped.append(result)

        self._log.info("ACTIVATE done run_id=%s %s", snapshot.run_id, report.summary())
        return report

    def deactivate(self) -> RunReport:
        snapshot = self._store.load_active()
        if snapshot is None:
            self._log.info("deactivate() called but no active snapshot")
            return RunReport(run_id="none")

        report = RunReport(run_id=snapshot.run_id)
        self._log.info("DEACTIVATE begin run_id=%s", snapshot.run_id)

        for entry in reversed(snapshot.tweaks):
            tweak = self._tweaks.get(entry.tweak_id)
            if tweak is None:
                report.skipped.append(
                    TweakResult(
                        tweak_id=entry.tweak_id,
                        status=TweakStatus.SKIPPED_UNSUPPORTED,
                        message="tweak no longer registered",
                    )
                )
                continue
            try:
                result = tweak.revert(entry.previous_state)
            except Exception as exc:
                result = TweakResult(
                    tweak_id=tweak.id,
                    status=TweakStatus.REVERT_FAILED,
                    message="revert raised",
                    error=str(exc),
                )
                self._log.exception("revert raised for %s", tweak.id)

            if result.status == TweakStatus.REVERTED:
                report.applied.append(result)
            elif result.status == TweakStatus.REVERT_FAILED:
                report.failed.append(result)
            else:
                report.skipped.append(result)

        self._store.archive_active()
        self._log.info("DEACTIVATE done run_id=%s %s", snapshot.run_id, report.summary())
        return report


def _windows_version() -> str:
    if sys.platform != "win32":
        return sys.platform
    info = sys.getwindowsversion()
    return f"{info.major}.{info.minor}.{info.build}"
