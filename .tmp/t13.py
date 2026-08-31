# -*- coding: utf-8 -*-
"""Chama startCleanWith PELO JS (caminho real) e observa o terminal."""
import sys
sys.path.insert(0, r"C:\Projects\Tecnoapp\app")
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from web_screen import WebScreen

app = QApplication(sys.argv)
w = WebScreen(main_window=None); w.resize(1000,700); w.show()
br = w.bridge
py = {"step":0, "fim":None}
br.cleanStep.connect(lambda l,f: py.__setitem__("step", py["step"]+1))
br.cleanFinished.connect(lambda r: py.__setitem__("fim", r))

def fase1():
    print(">> chamando window.cleanRunQuick() pelo JS")
    w.page().runJavaScript("window.cleanRunQuick ? (window.cleanRunQuick(), 'chamado') : 'ausente'",
                           lambda r: print(">>", r))
    QTimer.singleShot(20000, fase2)

def fase2():
    js = """JSON.stringify({
      linhas: document.getElementById('clean-terminal').querySelectorAll('.terminal-line').length,
      texto: document.getElementById('clean-terminal').textContent.slice(0,150),
      display: document.getElementById('clean-terminal').style.display
    })"""
    def done(r):
        print(">> TERMINAL:", r)
        print(">> lado Python -> cleanStep:", py["step"], "| finished:", py["fim"])
        app.quit()
    w.page().runJavaScript(js, done)

QTimer.singleShot(9000, fase1)
app.exec()
