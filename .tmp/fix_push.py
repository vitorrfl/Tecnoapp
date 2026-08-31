# -*- coding: utf-8 -*-
"""Entrega o progresso via runJavaScript em vez de sinais QWebChannel.

Os sinais de progresso (cleanStep, repairStep, optimizeStep...) nao eram
entregues ao JS, embora metricsUpdated funcionasse. Em vez de insistir no
canal de sinais, o WebScreen passa a expor um push direto: a Bridge chama
uma funcao JS na pagina, que e o mesmo mecanismo que o _Page ja usa.
"""
import io

# ── 1) web_screen.py: dar a Bridge acesso a pagina ──────────────────
P1 = r"C:\Projects\Tecnoapp\app\web_screen.py"
s = io.open(P1, encoding="utf-8").read()

old = """        # Bridge: registra o objeto que o JS acessa via window.bridge
        self.bridge = Bridge(main_window=main_window, parent=self)"""
new = """        # Bridge: registra o objeto que o JS acessa via window.bridge
        self.bridge = Bridge(main_window=main_window, parent=self)
        # Push direto para a pagina: os sinais de progresso do QWebChannel
        # nao chegavam ao JS, entao a Bridge chama funcoes JS diretamente.
        self.bridge.set_page(self._page)"""
if old not in s:
    raise SystemExit("ancora do web_screen nao encontrada")
s = s.replace(old, new, 1)
io.open(P1, "w", encoding="utf-8", newline="\n").write(s)
print("web_screen.py: bridge.set_page(page)")

# ── 2) bridge.py: metodo de push + uso nos handlers ─────────────────
P2 = r"C:\Projects\Tecnoapp\app\bridge.py"
b = io.open(P2, encoding="utf-8").read()

# 2a) helper
anchor = "    def _on_hardware(self, info: dict):"
helper = '''    # ── Push direto para o JS ───────────────────────────────────
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

'''
if anchor not in b:
    raise SystemExit("ancora _on_hardware nao encontrada")
b = b.replace(anchor, helper + anchor, 1)

# 2b) import json
if "\nimport json" not in b:
    b = b.replace("from __future__ import annotations",
                  "from __future__ import annotations\n\nimport json", 1)

# 2c) _page inicial
b = b.replace("        self._main = main_window",
              "        self._main = main_window\n        self._page = None", 1)

# 2d) limpeza: emite sinal E empurra
b = b.replace(
    """    def _on_clean_step(self, label: str, freed: int):
        self._clean_total += int(freed or 0)
        self.cleanStep.emit(str(label), int(freed or 0))""",
    """    def _on_clean_step(self, label: str, freed: int):
        self._clean_total += int(freed or 0)
        self.cleanStep.emit(str(label), int(freed or 0))
        self._js("onCleanStep", str(label), int(freed or 0))""",
    1)

b = b.replace(
    """        self.cleanFinished.emit({
            "ok": True,
            "total": total,
            "human": self._fmt_size(total),
        })""",
    """        payload = {"ok": True, "total": total, "human": self._fmt_size(total)}
        self.cleanFinished.emit(payload)
        self._js("onCleanFinished", payload)""",
    1)

b = b.replace(
    "        self._clean_worker.calculating.connect(self.cleanCalculating.emit)",
    """        self._clean_worker.calculating.connect(self.cleanCalculating.emit)
        self._clean_worker.calculating.connect(lambda: self._js("onCleanCalculating"))""",
    1)

# 2e) reparos
b = b.replace(
    """        self._repair_worker.step_done.connect(
            lambda lbl, ok, det: self.repairStep.emit(str(lbl), bool(ok), str(det or "")))""",
    """        self._repair_worker.step_done.connect(
            lambda lbl, ok, det: (self.repairStep.emit(str(lbl), bool(ok), str(det or "")),
                                  self._js("onRepairStep", str(lbl), bool(ok), str(det or ""))))""",
    1)

b = b.replace(
    """        self.repairFinished.emit({"ok": bool(ok), "summary": str(summary or "")})""",
    """        payload = {"ok": bool(ok), "summary": str(summary or "")}
        self.repairFinished.emit(payload)
        self._js("onRepairFinished", payload)""",
    1)

# 2f) otimizacao
b = b.replace(
    """        self._optimize_worker.step_done.connect(
            lambda lbl, ok, det: self.optimizeStep.emit(str(lbl), bool(ok), str(det or "")))""",
    """        self._optimize_worker.step_done.connect(
            lambda lbl, ok, det: (self.optimizeStep.emit(str(lbl), bool(ok), str(det or "")),
                                  self._js("onOptimizeStep", str(lbl), bool(ok), str(det or ""))))""",
    1)

b = b.replace(
    """        self.optimizeFinished.emit({
            "ok": True, "applied": int(applied or 0), "failed": int(failed or 0),
        })""",
    """        payload = {"ok": True, "applied": int(applied or 0), "failed": int(failed or 0)}
        self.optimizeFinished.emit(payload)
        self._js("onOptimizeFinished", payload)""",
    1)

io.open(P2, "w", encoding="utf-8", newline="\n").write(b)
print("bridge.py: push via runJavaScript nos 3 fluxos")
