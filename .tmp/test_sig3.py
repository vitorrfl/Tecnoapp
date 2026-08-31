# -*- coding: utf-8 -*-
"""Emite sinais de dentro do event loop, como os workers fazem."""
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

estado = {"fase": 0}


def armar():
    js = """(function(){
      window.__c = 0;
      window.bridge.cleanStep.connect(function(l, f){
        window.__c++;
        var t = document.getElementById('clean-terminal');
        if (t) {
          t.style.display='block';
          var d=document.createElement('div');
          d.className='terminal-line';
          d.textContent='> '+l;
          t.appendChild(d);
        }
      });
      return 'ok';
    })()"""
    pg.runJavaScript(js, lambda r: print(">> assinado:", r))
    # emite espacado, deixando o event loop girar entre cada um
    QTimer.singleShot(800, lambda: tick(1))


def tick(n):
    if n > 3:
        QTimer.singleShot(1500, ler)
        return
    print(">> emitindo cleanStep #" + str(n))
    br.cleanStep.emit("passo-" + str(n), n * 1024)
    QTimer.singleShot(700, lambda: tick(n + 1))


def ler():
    def done(r):
        print()
        print("=== RESULTADO ===")
        print(r)
        app.quit()

    pg.runJavaScript(
        """JSON.stringify({
          recebidos: window.__c,
          linhas: document.getElementById('clean-terminal')
                    .querySelectorAll('.terminal-line').length
        })""",
        done,
    )


QTimer.singleShot(7000, armar)
app.exec()
