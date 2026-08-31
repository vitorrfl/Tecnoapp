# -*- coding: utf-8 -*-
"""Verifica se um sinal QWebChannel com 2 argumentos chega ao JS."""
import sys

sys.path.insert(0, r"C:\Projects\Tecnoapp\app")

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer, QUrl
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtWebChannel import QWebChannel

from bridge import Bridge

logs = []


class P(QWebEnginePage):
    def javaScriptConsoleMessage(self, lv, msg, line, src):
        logs.append(msg)


app = QApplication(sys.argv)
v = QWebEngineView()
pg = P(v)
v.setPage(pg)
br = Bridge(main_window=None, parent=v)
ch = QWebChannel(pg)
ch.registerObject("bridge", br)
pg.setWebChannel(ch)
v.load(QUrl.fromLocalFile(r"C:\Projects\Tecnoapp\app\webview\index.html"))


def armar():
    # Assina o sinal manualmente e conta o que chega
    js = """(function(){
      window.__hits = [];
      window.bridge.cleanStep.connect(function(a, b){
        window.__hits.push([String(a), String(b)]);
      });
      return 'assinado; handler interno existe? ' + (typeof onCleanStep);
    })()"""
    pg.runJavaScript(js, lambda r: print(">>", r))
    QTimer.singleShot(1000, emitir)


def emitir():
    print(">> emitindo cleanStep do Python 3x")
    br.cleanStep.emit("teste-um", 1024)
    br.cleanStep.emit("teste-dois", 2048)
    br.cleanStep.emit("teste-tres", 4096)
    QTimer.singleShot(2500, ler)


def ler():
    js = """(function(){
      var t = document.getElementById('clean-terminal');
      return JSON.stringify({
        recebidosNoJS: (window.__hits || []).length,
        amostra: (window.__hits || []).slice(0,3),
        linhasNoTerminal: t ? t.querySelectorAll('.terminal-line').length : -1
      });
    })()"""

    def done(r):
        print()
        print("=== RESULTADO ===")
        print(r)
        if logs:
            print("--- console ---")
            for m in logs[-6:]:
                print("  ", m)
        app.quit()

    pg.runJavaScript(js, done)


QTimer.singleShot(7000, armar)
app.exec()
