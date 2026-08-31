# -*- coding: utf-8 -*-
"""Descobre se connectBridge() rodou e se o connect foi efetivado."""
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
        logs.append(str(msg))


app = QApplication(sys.argv)
v = QWebEngineView()
pg = P(v)
v.setPage(pg)
br = Bridge(main_window=None, parent=v)
ch = QWebChannel(pg)
ch.registerObject("bridge", br)
pg.setWebChannel(ch)
v.load(QUrl.fromLocalFile(r"C:\Projects\Tecnoapp\app\webview\index.html"))


def inspecionar():
    js = """(function(){
      var b = window.bridge;
      var r = {
        bridgeDefinida: typeof b,
        // o objeto do canal e o mesmo que o app.js assinou?
        temCleanStep: b ? typeof b.cleanStep : 'sem bridge',
        connectEhFuncao: (b && b.cleanStep) ? typeof b.cleanStep.connect : 'n/a'
      };
      // conta quantos handlers o Qt registrou nesse sinal
      try {
        r.handlers = (b.cleanStep && b.cleanStep.__handlers)
          ? b.cleanStep.__handlers.length : 'sem __handlers';
      } catch(e) { r.handlers = 'erro: ' + e.message; }
      // assina agora e marca
      window.__novo = 0;
      if (b && b.cleanStep) b.cleanStep.connect(function(){ window.__novo++; });
      return JSON.stringify(r);
    })()"""

    def done(r):
        print(">> inspecao:", r)
        print(">> emitindo 2 sinais")
        br.cleanStep.emit("x", 1)
        br.cleanStep.emit("y", 2)
        QTimer.singleShot(2000, ler)

    pg.runJavaScript(js, done)


def ler():
    def done(r):
        print()
        print("=== recebidos apos assinar tardiamente ===")
        print(r)
        if logs:
            print("--- console (ultimos) ---")
            for m in logs[-8:]:
                print("  ", m)
        app.quit()

    pg.runJavaScript(
        """JSON.stringify({novoHandler: window.__novo,
          linhasTerminal: document.getElementById('clean-terminal')
            .querySelectorAll('.terminal-line').length})""",
        done,
    )


QTimer.singleShot(8000, inspecionar)
app.exec()
