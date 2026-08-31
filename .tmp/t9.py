# -*- coding: utf-8 -*-
"""Le o DOM que o proprio app.js atualiza, sem injetar handlers."""
import sys
sys.path.insert(0, r"C:\Projects\Tecnoapp\app")
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from web_screen import WebScreen

app = QApplication(sys.argv)
w = WebScreen(main_window=None)
w.resize(1200, 800); w.show()
br = w.bridge

def fase1():
    # o metricsUpdated do app.js escreve nos cards; se o DOM mudou, o sinal chega
    js = """JSON.stringify({
      cpu: (document.querySelector('[data-metric=cpu] .metric-value')||{}).textContent,
      ram: (document.querySelector('[data-metric=ram] .metric-value')||{}).textContent
    })"""
    w.page().runJavaScript(js, lambda r: (print(">> cards apos 8s:", r), fase2()))

def fase2():
    print(">> emitindo cleanStep x3 pelo Python")
    br.cleanStep.emit("Temporarios do usuario", 1048576)
    br.cleanStep.emit("Cache DNS", 0)
    br.cleanStep.emit("Lixeira", 5242880)
    QTimer.singleShot(2500, fase3)

def fase3():
    js = """(function(){
      var t = document.getElementById('clean-terminal');
      return JSON.stringify({
        linhas: t ? t.querySelectorAll('.terminal-line').length : -1,
        texto: t ? t.textContent.slice(0,120) : null
      });
    })()"""
    w.page().runJavaScript(js, lambda r: (print(">> terminal:", r), app.quit()))

QTimer.singleShot(8000, fase1)
app.exec()
