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
br = Bridge(main_window=None, parent=v)
ch = QWebChannel(pg); ch.registerObject("bridge", br); pg.setWebChannel(ch)
v.load(QUrl.fromLocalFile(r"C:\Projects\Tecnoapp\app\webview\index.html"))

def go():
    js = """(function(){
      window.__hits = {};
      ['metricsUpdated','cleanStep','cleanFinished','bloatProgress','updateStatus','repairStatus']
        .forEach(function(n){
          window.__hits[n] = 0;
          if (window.bridge[n] && window.bridge[n].connect) {
            window.bridge[n].connect(function(){ window.__hits[n]++; });
          }
        });
      return 'ok';
    })()"""
    pg.runJavaScript(js, lambda r: (print(">> assinados:", r), emitir()))

def emitir():
    print(">> emitindo um de cada")
    br.cleanStep.emit("a", 1)
    br.cleanFinished.emit({"ok": True})
    br.bloatProgress.emit(1, 1, "x")
    br.updateStatus.emit("teste")
    br.repairStatus.emit("teste")
    # metricsUpdated ja e emitido sozinho pelo QTimer de 1s
    QTimer.singleShot(3000, ler)

def ler():
    pg.runJavaScript("JSON.stringify(window.__hits)",
        lambda r: (print(">> RECEBIDOS:", r), app.quit()))

QTimer.singleShot(7000, go)
app.exec()
