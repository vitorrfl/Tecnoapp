# -*- coding: utf-8 -*-
"""Usa o WebScreen real do app, em vez de montar o canal na mao."""
import sys
sys.path.insert(0, r"C:\Projects\Tecnoapp\app")
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from web_screen import WebScreen

app = QApplication(sys.argv)
w = WebScreen(main_window=None)
w.resize(1200, 800)
w.show()
br = w.bridge

def go():
    js = """(function(){
      window.__h = {metricsUpdated:0, cleanStep:0};
      window.bridge.metricsUpdated.connect(function(){ window.__h.metricsUpdated++; });
      window.bridge.cleanStep.connect(function(){ window.__h.cleanStep++; });
      return 'ok';
    })()"""
    w.page().runJavaScript(js, lambda r: (print(">> assinado:", r), emitir()))

def emitir():
    print(">> emitindo cleanStep x2 (metricsUpdated corre sozinho)")
    br.cleanStep.emit("a", 1)
    br.cleanStep.emit("b", 2)
    QTimer.singleShot(3000, ler)

def ler():
    w.page().runJavaScript("JSON.stringify(window.__h)",
        lambda r: (print(">> RECEBIDOS via WebScreen:", r), app.quit()))

QTimer.singleShot(8000, go)
app.exec()
