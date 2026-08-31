# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r"C:\Projects\Tecnoapp\app")
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from web_screen import WebScreen

app = QApplication(sys.argv)
w = WebScreen(main_window=None); w.resize(1000,700); w.show()
br = w.bridge

def fase1():
    # substitui o handler do sinal por um que escreve direto no DOM,
    # rodando NO MESMO contexto da pagina (via evento sintetico)
    js = """(function(){
      var out = {};
      out.tipoCleanStep = typeof window.bridge.cleanStep;
      // o Qt guarda os callbacks em um array interno
      var s = window.bridge.cleanStep;
      out.chavesDoSinal = Object.keys(s || {});
      out.temConnect = !!(s && s.connect);
      return JSON.stringify(out);
    })()"""
    w.page().runJavaScript(js, lambda r: (print(">> sinal:", r), fase2()))

def fase2():
    print(">> emitindo cleanStep")
    br.cleanStep.emit("passo-teste", 12345)
    QTimer.singleShot(2000, fase3)

def fase3():
    js = """JSON.stringify({
      linhas: document.getElementById('clean-terminal').querySelectorAll('.terminal-line').length,
      display: document.getElementById('clean-terminal').style.display
    })"""
    w.page().runJavaScript(js, lambda r: (print(">> terminal:", r), app.quit()))

QTimer.singleShot(8000, fase1)
app.exec()
