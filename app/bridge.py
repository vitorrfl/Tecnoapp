"""
Bridge Python ↔ JS para o front WebEngine.

Expõe um QObject com:
- @Slot getInitialSnapshot() — snapshot inicial (sync via callback JS)
- Signal metricsUpdated(dict) — emitido a cada 1s pelo QTimer
- @Slot triggerLimpeza/Otimizacao/Reparos/Gamer/Restore — pontes
  para a MainWindow Qt (executar a ação real).

Uso:
    bridge = Bridge(main_window)
    channel = QWebChannel(view.page())
    channel.registerObject("bridge", bridge)
    view.page().setWebChannel(channel)
"""

from __future__ import annotations

from PySide6.QtCore import QObject, QTimer, Signal, Slot

import psutil

from version import APP_VERSION
from updater import UpdateChecker, UpdateDownloader, run_installer_and_exit

from system_info import (
    os_info, cpu_static, cpu_pct, mem_live, disk_c_info, disks_info,
    processes_count, uptime_seconds, format_uptime,
    HardwareInfoWorker,
)


class Bridge(QObject):
    metricsUpdated = Signal("QVariant")
    hardwareReady = Signal("QVariant")
    updateAvailable = Signal("QVariant")
    updateProgress = Signal(int)
    updateStatus = Signal(str)

    def __init__(self, main_window=None, parent=None):
        super().__init__(parent)
        self._main = main_window
        self._cpu_static = cpu_static()
        self._os = os_info()
        self._hardware: dict | None = None

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(1000)

        self._update_info: dict | None = None
        self._checker = None
        self._downloader = None

        self._hw_worker = HardwareInfoWorker()
        self._hw_worker.finished_info.connect(self._on_hardware)
        self._hw_worker.start()

    def _on_hardware(self, info: dict):
        self._hardware = dict(info)
        self.hardwareReady.emit(self._hardware)

    # ── snapshot helpers ────────────────────────────────────────
    def _snapshot(self) -> dict:
        m = mem_live()
        d = disk_c_info()
        return {
            "cpu": {
                "pct": float(cpu_pct()),
                "name": self._cpu_static.get("name", "—"),
                "threads": int(self._cpu_static.get("threads", 0) or 0),
                "freq": self._cpu_static.get("freq", "—"),
            },
            "ram": {
                "pct": float(m.get("pct", 0.0)),
                "used": int(m.get("used", 0) or 0),
                "total": int(m.get("total", 0) or 0),
            },
            "disk": {
                "pct": float(d.get("pct", 0.0)),
                "used": int(d.get("used", 0) or 0),
                "total": int(d.get("total", 0) or 0),
            },
            "proc": int(processes_count()),
            "os": {
                "system": self._os.get("system", "—"),
                "user": self._os.get("user", "—"),
                "machine": self._os.get("machine", "—"),
                "version": self._os.get("version", "—"),
            },
            "uptime": format_uptime(uptime_seconds()),
        }

    def _tick(self):
        try:
            self.metricsUpdated.emit(self._snapshot())
        except Exception as e:
            print(f"[bridge] tick error: {e}")

    # ── Slots callable from JS ──────────────────────────────────
    @Slot(result="QVariant")
    def getInitialSnapshot(self):
        return self._snapshot()

    @Slot(result="QVariant")
    def getHardware(self):
        """Hardware lento (GPU/mobo/BIOS). Pode retornar None se ainda
        estiver carregando — JS deve também escutar hardwareReady."""
        return self._hardware

    @Slot(result="QVariant")
    def getDisks(self):
        return disks_info()

    @Slot(result="QVariant")
    def getProcessStats(self):
        """Total + contadores agregados para a tela de specs."""
        try:
            cpu_5 = 0
            ram_500 = 0
            for p in psutil.process_iter(["cpu_percent", "memory_info"]):
                try:
                    cpu_p = p.info.get("cpu_percent") or 0
                    mem = p.info.get("memory_info").rss if p.info.get("memory_info") else 0
                    if cpu_p > 5:
                        cpu_5 += 1
                    if mem > 500 * 1024 * 1024:
                        ram_500 += 1
                except Exception:
                    pass
            return {
                "total": int(processes_count()),
                "cpu_high": cpu_5,
                "ram_high": ram_500,
                "uptime": format_uptime(uptime_seconds()),
            }
        except Exception:
            return {"total": 0, "cpu_high": 0, "ram_high": 0, "uptime": "—"}

    @Slot(str)
    def navigate(self, target: str):
        """JS pode pedir ao Python pra trocar de tela (caso queiramos
        rotear telas ainda em QWidgets)."""
        if not self._main:
            return
        m = self._main
        action = {
            "home":       getattr(m, "show_home", None),
            "limpeza":    getattr(m, "show_limpeza", None),
            "otimizacao": getattr(m, "show_otimizacao", None),
            "reparos":    getattr(m, "show_reparos", None),
            "specs":      getattr(m, "show_specs", None),
            "gamer":      getattr(m, "show_gamer", None),
        }.get(target)
        if action:
            action()

    @Slot()
    def runLimpeza(self):
        if self._main and hasattr(self._main, "run_clean_process"):
            self._main.run_clean_process()

    @Slot()
    def runOtimizacao(self):
        if self._main and hasattr(self._main, "run_optimize_process"):
            self._main.run_optimize_process()

    @Slot()
    def runGamerActivate(self):
        if self._main and hasattr(self._main, "run_gamer_activate"):
            self._main.run_gamer_activate()

    @Slot()
    def runGamerDeactivate(self):
        if self._main and hasattr(self._main, "run_gamer_deactivate"):
            self._main.run_gamer_deactivate()

    @Slot()
    def createRestorePoint(self):
        if self._main and hasattr(self._main, "criar_ponto_restauracao"):
            self._main.criar_ponto_restauracao()

    @Slot()
    def exitApp(self):
        if self._main:
            self._main.close()

    # ── Updater ─────────────────────────────────────────────────
    @Slot(result=str)
    def getVersion(self):
        return APP_VERSION

    @Slot()
    def checkForUpdates(self):
        """Dispara a checagem em background. JS escuta updateAvailable."""
        if self._checker and self._checker.isRunning():
            return
        self._checker = UpdateChecker()
        self._checker.update_available.connect(self._on_update_available)
        self._checker.up_to_date.connect(
            lambda: self.updateStatus.emit("Voce esta na versao mais recente."))
        self._checker.check_failed.connect(
            lambda why: self.updateStatus.emit(f"Nao foi possivel checar ({why})."))
        self._checker.start()

    def _on_update_available(self, ver, notes, url, size):
        self._update_info = {"version": ver, "notes": notes, "url": url, "size": size}
        self.updateAvailable.emit(self._update_info)

    @Slot()
    def downloadUpdate(self):
        """Baixa o instalador da versao detectada e executa ao terminar."""
        if not self._update_info:
            self.updateStatus.emit("Nenhuma atualizacao pendente.")
            return
        if self._downloader and self._downloader.isRunning():
            return
        self.updateStatus.emit("Baixando atualizacao...")
        self._downloader = UpdateDownloader(self._update_info["url"])
        self._downloader.progress.connect(self.updateProgress.emit)
        self._downloader.finished_ok.connect(self._on_download_done)
        self._downloader.failed.connect(
            lambda e: self.updateStatus.emit(f"Falha no download: {e}"))
        self._downloader.start()

    def _on_download_done(self, path: str):
        self.updateStatus.emit("Instalando... o app vai fechar.")
        if run_installer_and_exit(path):
            if self._main:
                self._main.close()
        else:
            self.updateStatus.emit("Nao foi possivel iniciar o instalador.")

    # ── Aliases com nomes usados pelo app.js novo ───────────────
    @Slot()
    def onStartClean(self):
        self.runLimpeza()

    @Slot()
    def onConfigClean(self):
        if self._main and hasattr(self._main, "show_limpeza"):
            self._main.show_limpeza()

    @Slot()
    def onGamerActivate(self):
        self.runGamerActivate()

    @Slot()
    def onGamerDeactivate(self):
        self.runGamerDeactivate()

    @Slot(str)
    def onRunRepair(self, tool_id: str):
        if self._main and hasattr(self._main, "show_reparos_progresso"):
            self._main.show_reparos_progresso(tool_id)

    @Slot(str, bool)
    def onToggle(self, toggle_id: str, checked: bool):
        pass  # persistência de opt-ins — implementar quando integrar gamer avançado

    @Slot()
    def onRestorePoint(self):
        self.createRestorePoint()

    @Slot()
    def onExit(self):
        self.exitApp()

    @Slot(str)
    def onNavigate(self, screen_id: str):
        pass  # navegação é gerida pelo JS; Python pode reagir se necessário
