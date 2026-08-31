# -*- coding: utf-8 -*-
"""Confere que o push alcanca os terminais de reparo e otimizacao."""
import sys
sys.path.insert(0, r"C:\Projects\Tecnoapp\app")
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from web_screen import WebScreen

app = QApplication(sys.argv)
w = WebScreen(main_window=None); w.resize(1000,700); w.show()
br = w.bridge

def fase1():
    print(">> empurrando passos de reparo e otimizacao")
    br._js("onRepairStep", "Verificando componentes", True, "ok")
    br._js("onRepairStep", "Executando SFC", False, "erro simulado")
    br._js("onRepairFinished", {"ok": True, "summary": "Reparo concluido"})
    br._js("onOptimizeStep", "Plano de energia", True, "aplicado")
    br._js("onOptimizeFinished", {"ok": True, "applied": 2, "failed": 0})
    QTimer.singleShot(2500, fase2)

def fase2():
    js = """JSON.stringify({
      reparo: {
        linhas: document.getElementById('repair-terminal').querySelectorAll('.terminal-line').length,
        texto: document.getElementById('repair-terminal').textContent.slice(0,90)
      },
      otimizacao: {
        linhas: document.getElementById('opt-terminal').querySelectorAll('.terminal-line').length,
        texto: document.getElementById('opt-terminal').textContent.slice(0,90)
      }
    })"""
    w.page().runJavaScript(js, lambda r: (print(">> RESULTADO:", r), app.quit()))

QTimer.singleShot(9000, fase1)
app.exec()
