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

import json

from PySide6.QtCore import QObject, QTimer, Signal, Slot

import psutil

from version import APP_VERSION
from updater import UpdateChecker, UpdateDownloader, run_installer_and_exit
from bloatware import BloatScanner
from bloatware.remover import BloatRemover

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
    bloatScanned = Signal("QVariant")
    bloatProgress = Signal(int, int, str)
    bloatFinished = Signal("QVariant")
    # Signal(str, "QVariant") nao era entregue ao JS pelo QWebChannel;
    # tipos concretos funcionam (mesmo padrao de bloatProgress/repairStep).
    cleanStep = Signal(str, int)
    cleanCalculating = Signal()
    cleanFinished = Signal("QVariant")
    repairStatus = Signal(str)
    deepStep = Signal(str, int)
    deepFinished = Signal("QVariant")
    repairStep = Signal(str, bool, str)
    repairFinished = Signal("QVariant")
    optimizeStep = Signal(str, bool, str)
    optimizeFinished = Signal("QVariant")

    def __init__(self, main_window=None, parent=None):
        super().__init__(parent)
        self._main = main_window
        self._page = None
        self._cpu_static = cpu_static()
        self._os = os_info()
        self._hardware: dict | None = None

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(1000)

        self._update_info: dict | None = None
        self._checker = None
        self._downloader = None

        self._clean_worker = None
        self._clean_total = 0
        self._repair_worker = None
        self._deep_worker = None
        self._optimize_worker = None
        self._bloat: dict | None = None
        self._bloat_scanner = None
        self._bloat_remover = None

        self._hw_worker = HardwareInfoWorker()
        self._hw_worker.finished_info.connect(self._on_hardware)
        self._hw_worker.start()

        # Varredura de bloatware: 1-5s, roda uma vez em thread propria.
        # NAO entra no _tick() de 1s das metricas.
        self._bloat_scanner = BloatScanner()
        self._bloat_scanner.finished_scan.connect(self._on_bloat)
        self._bloat_scanner.start()

    # ── Push direto para o JS ───────────────────────────────────
    def set_page(self, page):
        """Recebe a QWebEnginePage para empurrar chamadas JS."""
        self._page = page

    def _js(self, fn: str, *args):
        """
        Chama uma funcao JS na pagina.

        Os sinais de progresso do QWebChannel nao eram entregues ao JS
        (metricsUpdated funcionava, cleanStep/repairStep nao), entao o
        progresso e empurrado por runJavaScript, o mesmo mecanismo que o
        _Page usa para o console.
        """
        page = getattr(self, "_page", None)
        if page is None:
            return
        try:
            payload = ", ".join(json.dumps(a, ensure_ascii=False) for a in args)
            page.runJavaScript(f"window.{fn} && window.{fn}({payload});")
        except Exception:
            pass

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
        """
        No-op: a navegacao e do front web.

        Rotear para as telas QWidgets legadas (show_home, show_limpeza,
        show_reparos...) as renderizava por cima do WebEngine, sem caminho
        de volta — a "janela solo". Mantido como slot para nao quebrar
        chamadas antigas do JS.
        """
        return

    @Slot()
    def runLimpeza(self):
        """Alias legado: usa o fluxo inline, sem tela Qt."""
        self.startCleanWith([])

    # ── Otimizacao ──────────────────────────────────────────────
    @Slot(result="QVariant")
    def getOptimizeCategories(self):
        """Categorias de otimizacao + selecao salva."""
        try:
            from app3 import _OPTIMIZE_CATEGORIES, _load_optimize_state
        except Exception:
            return {"categories": [], "active": 0, "total": 0}

        state = _load_optimize_state() or {}
        saved = state.get("user_selections") or {}

        # Estado real no sistema, nao o que esta marcado na tela.
        try:
            from optstate import get_states
            aplicadas = get_states()
        except Exception:
            aplicadas = {}

        cats = []
        for c in _OPTIMIZE_CATEGORIES:
            cid = c["id"]
            on = bool(saved[cid]) if cid in saved else bool(c.get("default"))
            cats.append({
                "id": cid,
                "label": c.get("label", cid),
                "desc": c.get("desc", ""),
                "impact": c.get("impact", ""),
                "warning": c.get("warning", ""),
                "default": bool(c.get("default")),
                "checked": on,
                "applied": aplicadas.get(cid),   # True / False / None (nao aplicavel)
            })

        reais = [c for c in cats if c["applied"] is True]
        checaveis = [c for c in cats if c["applied"] is not None]
        return {
            "categories": cats,
            "active": sum(1 for c in cats if c["checked"]),
            "total": len(cats),
            "applied": len(reais),
            "checkable": len(checaveis),
        }

    @Slot("QVariant")
    def setOptimizeSelection(self, ids):
        try:
            from app3 import _OPTIMIZE_CATEGORIES, _load_optimize_state, _save_optimize_state
        except Exception:
            return
        wanted = {str(i) for i in (ids or [])}
        state = _load_optimize_state() or {}
        state["user_selections"] = {c["id"]: (c["id"] in wanted) for c in _OPTIMIZE_CATEGORIES}
        _save_optimize_state(state)

    @Slot("QVariant", str)
    def startOptimize(self, ids, mode="apply"):
        """
        Aplica (ou reverte) otimizacoes reportando progresso por sinal.

        run_optimize_process() renderizava a tela QWidgets legada por cima
        do WebEngine; aqui o worker roda direto.
        """
        if self._optimize_worker is not None and self._optimize_worker.isRunning():
            return
        try:
            from app3 import OptimizeWorker, _OPTIMIZE_CATEGORIES, _load_optimize_state
        except Exception as e:
            self.optimizeFinished.emit({"ok": False, "error": f"{type(e).__name__}"})
            return

        selected = {str(i) for i in (ids or [])}
        if not selected:
            state = _load_optimize_state() or {}
            saved = state.get("user_selections") or {}
            selected = ({cid for cid, v in saved.items() if v} if saved
                        else {c["id"] for c in _OPTIMIZE_CATEGORIES if c.get("default")})

        self._optimize_worker = OptimizeWorker(selected, mode=str(mode or "apply"))
        self._optimize_worker.step_done.connect(
            lambda lbl, ok, det: (self.optimizeStep.emit(str(lbl), bool(ok), str(det or "")),
                                  self._js("onOptimizeStep", str(lbl), bool(ok), str(det or ""))))
        self._optimize_worker.finished.connect(self._on_optimize_finished)
        self._optimize_worker.start()

    def _on_optimize_finished(self, applied: int, failed: int):
        w = self._optimize_worker
        self._optimize_worker = None
        if w is not None:
            try:
                w.wait(); w.deleteLater()
            except Exception:
                pass
        try:
            from app3 import _save_module_status
            _save_module_status("optimize", f"✓  {applied} otimizacoes aplicadas")
        except Exception:
            pass
        payload = {"ok": True, "applied": int(applied or 0), "failed": int(failed or 0)}
        self.optimizeFinished.emit(payload)
        self._js("onOptimizeFinished", payload)
        # Reconsulta o estado real para a tela refletir o que ficou ativo
        try:
            self._js("onOptimizeCategories", self.getOptimizeCategories())
        except Exception:
            pass

    @Slot()
    def runOtimizacao(self):
        """Alias legado: aplica com a selecao salva."""
        self.startOptimize([], "apply")

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

    # ── Limpeza ─────────────────────────────────────────────────
    @Slot(result="QVariant")
    def getCleanCategories(self):
        """
        Categorias de limpeza + o que o usuario tem selecionado.

        Importa de app3 sob demanda para evitar import circular
        (app3 importa bridge via web_screen).
        """
        try:
            from app3 import _CLEAN_CATEGORIES, _load_clean_state
        except Exception:
            return {"categories": [], "active": 0, "total": 0, "last_clean": ""}

        state = _load_clean_state() or {}
        saved = state.get("user_selections") or {}

        cats = []
        for c in _CLEAN_CATEGORIES:
            cid = c["id"]
            on = bool(saved[cid]) if cid in saved else bool(c.get("default"))
            cats.append({
                "id": cid,
                "label": c.get("label", cid),
                "desc": c.get("desc", ""),
                "impact": c.get("impact", ""),
                "warning": c.get("warning", ""),
                "default": bool(c.get("default")),
                "checked": on,
            })

        return {
            "categories": cats,
            "active": sum(1 for c in cats if c["checked"]),
            "total": len(cats),
            "last_clean": state.get("last_clean") or "",
        }

    @Slot("QVariant")
    def setCleanSelection(self, ids):
        """Persiste a selecao do usuario no estado do app."""
        try:
            from app3 import _CLEAN_CATEGORIES, _load_clean_state, _save_clean_state
        except Exception:
            return
        wanted = {str(i) for i in (ids or [])}
        state = _load_clean_state() or {}
        state["user_selections"] = {c["id"]: (c["id"] in wanted) for c in _CLEAN_CATEGORIES}
        _save_clean_state(state)

    @Slot("QVariant")
    def startCleanWith(self, ids):
        """
        Inicia a limpeza reportando progresso por sinal.

        Roda o CleanWorker aqui em vez de chamar MainWindow.run_clean_process:
        aquele metodo faz clear_screen() e monta QWidgets por cima do
        WebEngine, que e a "janela solo" sem caminho de volta.
        """
        if self._clean_worker is not None and self._clean_worker.isRunning():
            return
        try:
            from app3 import CleanWorker, _CLEAN_CATEGORIES, _load_clean_state, _save_clean_state
        except Exception as e:
            self.cleanFinished.emit({"ok": False, "error": f"{type(e).__name__}"})
            return

        selected = {str(i) for i in (ids or [])}
        if not selected:
            state = _load_clean_state() or {}
            saved = state.get("user_selections") or {}
            selected = ({cid for cid, v in saved.items() if v} if saved
                        else {c["id"] for c in _CLEAN_CATEGORIES if c.get("default")})

        self._clean_total = 0
        self._clean_worker = CleanWorker(selected)
        self._clean_worker.step_done.connect(self._on_clean_step)
        self._clean_worker.calculating.connect(self.cleanCalculating.emit)
        self._clean_worker.calculating.connect(lambda: self._js("onCleanCalculating"))
        self._clean_worker.finished.connect(self._on_clean_finished)
        self._clean_worker.start()

    def _on_clean_step(self, label: str, freed: int):
        self._clean_total += int(freed or 0)
        self.cleanStep.emit(str(label), int(freed or 0))
        self._js("onCleanStep", str(label), int(freed or 0))

    def _on_clean_finished(self, total: int):
        total = int(total or 0)
        try:
            from app3 import _load_clean_state, _save_clean_state, _save_module_status
            msg = (f"✓  {self._fmt_size(total)} liberados" if total > 102_400
                   else "✓  Sistema ja estava limpo")
            _save_module_status("clean", msg)
            state = _load_clean_state() or {}
            from datetime import datetime
            state["last_clean"] = datetime.now().strftime("%d/%m/%Y as %H:%M")
            _save_clean_state(state)
        except Exception:
            pass

        w = self._clean_worker
        self._clean_worker = None
        if w is not None:
            try:
                w.wait(); w.deleteLater()
            except Exception:
                pass

        payload = {"ok": True, "total": total, "human": self._fmt_size(total)}
        self.cleanFinished.emit(payload)
        self._js("onCleanFinished", payload)

    @staticmethod
    def _fmt_size(b: int) -> str:
        b = float(b or 0)
        for unit in ("B", "KB", "MB", "GB"):
            if b < 1024 or unit == "GB":
                return f"{b:.2f} {unit}" if unit in ("MB", "GB") else f"{int(b)} {unit}"
            b /= 1024
        return f"{b:.2f} GB"

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

    # ── Debloat ─────────────────────────────────────────────────
    def _on_bloat(self, result: dict):
        self._bloat = dict(result or {})
        self.bloatScanned.emit(self._bloat)

    @Slot(result="QVariant")
    def getBloatware(self):
        """Resultado da varredura. None enquanto ainda esta rodando."""
        return self._bloat

    @Slot()
    def rescanBloatware(self):
        if self._bloat_scanner and self._bloat_scanner.isRunning():
            return
        self._bloat_scanner = BloatScanner()
        self._bloat_scanner.finished_scan.connect(self._on_bloat)
        self._bloat_scanner.start()

    @Slot("QVariant")
    def removeBloatware(self, names):
        """
        Remove os itens cujos nomes o usuario marcou.

        Recebe nomes (nao os dicts do JS) e resolve contra o resultado da
        varredura: o JS nunca dita o comando de desinstalacao executado.
        """
        if not self._bloat or not names:
            return
        wanted = {str(n) for n in names}
        items = [i for i in self._bloat.get("items", []) if i.get("name") in wanted]
        if not items:
            return
        if self._bloat_remover and self._bloat_remover.isRunning():
            return

        self._bloat_remover = BloatRemover(items, make_restore=True)
        self._bloat_remover.progress.connect(self.bloatProgress.emit)
        self._bloat_remover.progress.connect(
            lambda cur, tot, nome: self._js("onBloatProgress", int(cur), int(tot), str(nome)))
        self._bloat_remover.item_done.connect(
            lambda nome, ok, err: self._js("onBloatItem", str(nome), bool(ok), str(err or "")))
        self._bloat_remover.finished_all.connect(self._on_bloat_done)
        self._bloat_remover.start()

    def _on_bloat_done(self, summary: dict):
        payload = dict(summary or {})
        self.bloatFinished.emit(payload)
        self._js("onBloatFinished", payload)
        self.rescanBloatware()   # atualiza a lista com o que sobrou

    # ── Aliases com nomes usados pelo app.js novo ───────────────
    @Slot()
    def onStartClean(self):
        """Limpeza rapida: usa a selecao salva, sem renderizar tela Qt."""
        self.startCleanWith([])

    @Slot()
    def onConfigClean(self):
        """
        No-op: a configuracao agora e uma tela do proprio front web.
        Abrir show_limpeza() renderizava a janela QWidgets legada por cima
        do WebEngine, sem caminho de volta para o app.
        """
        return

    @Slot()
    def onGamerActivate(self):
        self.runGamerActivate()

    @Slot()
    def onGamerDeactivate(self):
        self.runGamerDeactivate()

    # ── Prioridade de jogo ──────────────────────────────────────
    @Slot(result="QVariant")
    def getGameCandidates(self):
        """Processos que podem ser o jogo, mais os ja escolhidos."""
        try:
            from gamer.gamedetect import list_candidates
            from gamer.prefs import load_priority_targets
        except Exception:
            return {"candidates": [], "targets": []}
        try:
            return {
                "candidates": list_candidates(),
                "targets": load_priority_targets(),
            }
        except Exception:
            return {"candidates": [], "targets": []}

    @Slot(result="QVariant")
    def getAllProcesses(self):
        """
        Todos os processos, para o usuario escolher o jogo na mao.

        Existe porque a deteccao heuristica pode nao achar o jogo — e
        pedir para digitar o nome do executavel nao funciona: quase
        ninguem sabe, e nao ha como validar o que foi digitado.
        """
        try:
            from gamer.gamedetect import list_all_processes
            from gamer.prefs import load_priority_targets
            return {
                "processes": list_all_processes(),
                "targets": load_priority_targets(),
            }
        except Exception:
            return {"processes": [], "targets": []}

    @Slot("QVariant")
    def setGameTargets(self, names):
        """Salva quais processos recebem prioridade alta no Modo Gamer."""
        try:
            from gamer.tweaks.priority import save_targets
            save_targets([str(n) for n in (names or [])])
        except Exception:
            pass

    @Slot(str, result="QVariant")
    def setPriorityNow(self, name: str):
        """
        Aplica prioridade alta imediatamente, sem esperar o Modo Gamer.

        Util para quem so quer priorizar o jogo pontualmente.
        """
        try:
            from gamer.gamedetect import find_by_names, set_priority, PRIORITY_HIGH
        except Exception as e:
            return {"ok": False, "msg": type(e).__name__}

        alvos = find_by_names([name])
        if not alvos:
            return {"ok": False, "msg": "processo nao esta em execucao"}

        ok_n, erro = 0, ""
        for a in alvos:
            ok, msg = set_priority(a["pid"], PRIORITY_HIGH)
            if ok:
                ok_n += 1
            else:
                erro = msg
        if ok_n:
            return {"ok": True, "msg": f"{name}: prioridade alta aplicada"}
        return {"ok": False, "msg": f"{name}: {erro or 'falhou'}"}

    # ── Reboot ──────────────────────────────────────────────────
    @Slot(result=str)
    def getPostRebootFlag(self):
        """
        'gamer' quando o app foi reaberto pelo RunOnce apos o reboot.

        O front usa isso para abrir direto no Modo Gamer em vez da Home.
        """
        try:
            from reboot import came_from_reboot
            return came_from_reboot() or ""
        except Exception:
            return ""


    def ask_reboot(self, tweaks):
        """Abre o modal de reboot no front, com os tweaks afetados."""
        self._js("onAskReboot", [str(t) for t in (tweaks or [])])

    @Slot()
    def rebootNow(self):
        """
        Reinicia — so a partir do clique do usuario no modal.

        O README proibe auto-reboot: a decisao e sempre dele. Agenda o
        retorno antes, para o app reabrir no Modo Gamer.
        """
        try:
            from reboot import schedule_return, reboot_now
        except Exception:
            return
        schedule_return("gamer")
        if not reboot_now(5):
            try:
                from reboot import cancel_return
                cancel_return()
            except Exception:
                pass
            self._js("onRebootFailed")

    @Slot()
    def cancelReboot(self):
        """Desfaz o agendamento se o usuario escolher reiniciar depois."""
        try:
            from reboot import cancel_return
            cancel_return()
        except Exception:
            pass

    # ── Limpeza profunda (cleanmgr) ─────────────────────────────
    @Slot(result="QVariant")
    def getDeepCleanCategories(self):
        """Handlers do cleanmgr disponiveis nesta maquina."""
        try:
            from deepclean import list_handlers
        except Exception:
            return {"categories": [], "total": 0, "active": 0}
        cats = list_handlers()
        return {
            "categories": cats,
            "total": len(cats),
            "active": sum(1 for c in cats if c["checked"]),
        }

    @Slot("QVariant")
    def startDeepClean(self, ids):
        """
        Executa a limpeza profunda.

        Escreve o perfil no registro e chama cleanmgr /sagerun — sem a
        janela que o /sageset do .bat original abria.
        """
        if self._deep_worker is not None and self._deep_worker.isRunning():
            return
        try:
            from deepclean import DeepCleanWorker
        except Exception as e:
            self._js("onDeepFinished", {"ok": False, "msg": f"{type(e).__name__}"})
            return

        selected = {str(i) for i in (ids or [])}
        if not selected:
            self._js("onDeepFinished", {"ok": False, "msg": "Nenhuma categoria selecionada."})
            return

        self._deep_worker = DeepCleanWorker(selected)
        self._deep_worker.step_done.connect(
            lambda lbl, n: (self.deepStep.emit(str(lbl), int(n)),
                            self._js("onDeepStep", str(lbl), int(n))))
        self._deep_worker.finished_deep.connect(self._on_deep_finished)
        self._deep_worker.start()

    def _on_deep_finished(self, ok: bool, msg: str):
        w = self._deep_worker
        self._deep_worker = None
        if w is not None:
            try:
                w.wait(); w.deleteLater()
            except Exception:
                pass
        payload = {"ok": bool(ok), "msg": str(msg or "")}
        self.deepFinished.emit(payload)
        self._js("onDeepFinished", payload)

    # ── Reparos ─────────────────────────────────────────────────
    @Slot(result="QVariant")
    def getRepairTools(self):
        """Ferramentas de reparo disponiveis, para o front montar a lista."""
        try:
            from app3 import _REPAIR_TOOLS
        except Exception:
            return []
        return [{
            "id": t["id"],
            "label": t.get("label", t["id"]),
            "desc": t.get("desc", ""),
            "duration": t.get("duration", ""),
            "warning": t.get("warning", ""),
            "reboot": bool(t.get("reboot")),
            "category": t.get("category", ""),
        } for t in _REPAIR_TOOLS]

    @Slot(str)
    def onRunRepair(self, tool_id: str):
        """
        Executa o reparo reportando progresso por sinal.

        Roda o RepairWorker aqui em vez de show_reparos_progresso(), que
        monta QWidgets por cima do WebEngine (a "janela solo").
        """
        if self._repair_worker is not None and self._repair_worker.isRunning():
            return
        try:
            from app3 import RepairWorker
        except Exception as e:
            self.repairFinished.emit({"ok": False, "error": f"{type(e).__name__}"})
            return

        self.repairStatus.emit("Iniciando reparo...")
        self._repair_worker = RepairWorker(str(tool_id))
        self._repair_worker.step_done.connect(
            lambda lbl, ok, det: (self.repairStep.emit(str(lbl), bool(ok), str(det or "")),
                                  self._js("onRepairStep", str(lbl), bool(ok), str(det or ""))))
        self._repair_worker.finished.connect(self._on_repair_finished)
        self._repair_worker.start()

    def _on_repair_finished(self, ok: bool, summary: str):
        w = self._repair_worker
        self._repair_worker = None
        if w is not None:
            try:
                w.wait(); w.deleteLater()
            except Exception:
                pass
        payload = {"ok": bool(ok), "summary": str(summary or "")}
        self.repairFinished.emit(payload)
        self._js("onRepairFinished", payload)

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
