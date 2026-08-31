# -*- coding: utf-8 -*-
"""Verifica se o JS ve o sinal como signal-object e se propertyUpdate chega."""
import sys

sys.path.insert(0, r"C:\Projects\Tecnoapp\app")

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer, QUrl, QObject, Signal, Slot
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtWebChannel import QWebChannel


class Mini(QObject):
    """Objeto minimo, sem nada do TecnoApp, para isolar."""

    ping = Signal(str, int)

    @Slot(result=str)
    def hello(self):
        return "oi"


app = QApplication(sys.argv)
v = QWebEngineView()
pg = QWebEnginePage(v)
v.setPage(pg)

mini = Mini()
ch = QWebChannel(pg)
ch.registerObject("mini", mini)
pg.setWebChannel(ch)

HTML = """<!doctype html><html><body>
<script src="qrc:///qtwebchannel/qwebchannel.js"></script>
<script>
window.__n = 0;
window.__pronto = false;
new QWebChannel(qt.webChannelTransport, function(ch){
  window.mini = ch.objects.mini;
  window.__pronto = true;
  window.mini.ping.connect(function(a,b){ window.__n++; });
});
</script></body></html>"""

v.setHtml(HTML, QUrl("file:///C:/Projects/Tecnoapp/app/webview/"))


def emitir():
    def depois(r):
        print(">> canal pronto no JS:", r)
        print(">> emitindo ping x3")
        mini.ping.emit("a", 1)
        mini.ping.emit("b", 2)
        mini.ping.emit("c", 3)
        QTimer.singleShot(2000, ler)

    pg.runJavaScript("String(window.__pronto)", depois)


def ler():
    def done(r):
        print()
        print("=== objeto minimo (sem TecnoApp) ===")
        print("pings recebidos no JS:", r)
        app.quit()

    pg.runJavaScript("String(window.__n)", done)


QTimer.singleShot(5000, emitir)
app.exec()
