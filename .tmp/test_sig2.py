# -*- coding: utf-8 -*-
"""Compara entrega de sinais: cleanStep vs bloatProgress (que ja funciona)."""
import sys

sys.path.insert(0, r"C:\Projects\Tecnoapp\app")

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer, QUrl
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtWebChannel import QWebChannel

from bridge import Bridge

app = QApplication(sys.argv)
v = QWebEngineView()
pg = QWebEnginePage(v)
v.setPage(pg)
br = Bridge(main_window=None, parent=v)
ch = QWebChannel(pg)
ch.registerObject("bridge", br)
pg.setWebChannel(ch)
v.load(QUrl.fromLocalFile(r"C:\Projects\Tecnoapp\app\webview\index.html"))


def armar():
    js = """(function(){
      window.__c = 0; window.__b = 0;
      var out = {};
      out.cleanStepExiste = !!window.bridge.cleanStep;
      out.bloatProgressExiste = !!window.bridge.bloatProgress;
      out.chaves = Object.keys(window.bridge).filter(function(k){
        return k.indexOf('clean') === 0 || k.indexOf('bloat') === 0;
      });
      if (window.bridge.cleanStep) {
        window.bridge.cleanStep.connect(function(){ window.__c++; });
      }
      if (window.bridge.bloatProgress) {
        window.bridge.bloatProgress.connect(function(){ window.__b++; });
      }
      return JSON.stringify(out);
    })()"""
    pg.runJavaScript(js, lambda r: print(">> bridge:", r))
    QTimer.singleShot(1200, emitir)


def emitir():
    print(">> emitindo cleanStep x2 e bloatProgress x2")
    br.cleanStep.emit("a", 1)
    br.cleanStep.emit("b", 2)
    br.bloatProgress.emit(1, 2, "x")
    br.bloatProgress.emit(2, 2, "y")
    QTimer.singleShot(2500, ler)


def ler():
    def done(r):
        print()
        print("=== RECEBIDOS NO JS ===")
        print(r)
        app.quit()

    pg.runJavaScript(
        "JSON.stringify({cleanStep: window.__c, bloatProgress: window.__b})", done
    )


QTimer.singleShot(7000, armar)
app.exec()
