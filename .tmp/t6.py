# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r"C:\Projects\Tecnoapp\app")
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer, QUrl
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtWebChannel import QWebChannel
from bridge import Bridge

app = QApplication(sys.argv)
v = QWebEngineView(); pg = QWebEnginePage(v); v.setPage(pg)
br = Bridge(main_window=None)          # <-- SEM parent
ch = QWebChannel(pg); ch.registerObject("bridge", br); pg.setWebChannel(ch)
v.load(QUrl.fromLocalFile(r"C:\Projects\Tecnoapp\app\webview\index.html"))

def go():
    pg.runJavaScript(
        "window.__n=0; window.bridge.cleanStep.connect(function(){window.__n++;}); 'ok'",
        lambda r: (print(">> assinado:", r), emitir()))

def emitir():
    br.cleanStep.emit("a", 1); br.cleanStep.emit("b", 2)
    QTimer.singleShot(2000, ler)

def ler():
    pg.runJavaScript("String(window.__n)",
        lambda r: (print(">> SEM parent, recebidos:", r), app.quit()))

QTimer.singleShot(7000, go)
app.exec()
