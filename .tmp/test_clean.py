# -*- coding: utf-8 -*-
"""Dispara a limpeza pelo front e observa o terminal inline."""
import sys

sys.path.insert(0, r"C:\Projects\Tecnoapp\app")

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer, QUrl
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtWebChannel import QWebChannel

from bridge import Bridge

errs = []


class P(QWebEnginePage):
    def javaScriptConsoleMessage(self, lv, msg, line, src):
        n = int(lv.value) if hasattr(lv, "value") else int(lv)
        tag = {0: "log", 1: "warn", 2: "err"}.get(n, "log")
        errs.append("[" + tag + "] " + msg + " (" + src.split("/")[-1] + ":" + str(line) + ")")


app = QApplication(sys.argv)
v = QWebEngineView()
pg = P(v)
v.setPage(pg)
br = Bridge(main_window=None, parent=v)
ch = QWebChannel(pg)
ch.registerObject("bridge", br)
pg.setWebChannel(ch)

sinais = {"step": 0, "calc": 0, "fim": None}
br.cleanStep.connect(lambda l, f: sinais.__setitem__("step", sinais["step"] + 1))
br.cleanCalculating.connect(lambda: sinais.__setitem__("calc", sinais["calc"] + 1))
br.cleanFinished.connect(lambda r: sinais.__setitem__("fim", r))

v.load(QUrl.fromLocalFile(r"C:\Projects\Tecnoapp\app\webview\index.html"))


def disparar():
    print(">> chamando window.cleanStart() (mesmo caminho do botao)")
    js = """(function(){
      navigate('limpeza-config');
      var antes = {
        temCleanStart: typeof window.cleanStart,
        temCleanRunQuick: typeof window.cleanRunQuick,
        temStartCleanWith: !!(window.bridge && window.bridge.startCleanWith),
        temSinalStep: !!(window.bridge && window.bridge.cleanStep)
      };
      if (window.cleanStart) window.cleanStart();
      return JSON.stringify(antes);
    })()"""
    pg.runJavaScript(js, lambda r: print(">> estado antes:", r))
    QTimer.singleShot(15000, inspecionar)


def inspecionar():
    js = """(function(){
      var t = document.getElementById('clean-terminal');
      return JSON.stringify({
        terminalExiste: !!t,
        display: t ? t.style.display : null,
        linhas: t ? t.querySelectorAll('.terminal-line').length : -1,
        texto: t ? t.textContent.slice(0,200) : null,
        status: (document.querySelector('[data-bind=clean_status]')||{}).textContent
      });
    })()"""

    def done(r):
        print()
        print("=== TERMINAL NO DOM ===")
        print(r)
        print()
        print("=== SINAIS NO PYTHON ===")
        print("cleanStep:", sinais["step"], "| calculating:", sinais["calc"])
        print("cleanFinished:", sinais["fim"])
        print()
        print("=== CONSOLE JS ===")
        for e in errs[-12:]:
            print("  ", e)
        app.quit()

    pg.runJavaScript(js, done)


QTimer.singleShot(8000, disparar)
app.exec()
