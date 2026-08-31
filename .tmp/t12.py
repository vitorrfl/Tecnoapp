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
    # Conecta com um handler que grava numa global E escreve no DOM.
    # Se ESTE funcionar, o problema e o handler original; se nao, e a conexao.
    js = """(function(){
      window.__marcas = [];
      window.bridge.cleanStep.connect(function(l, f){
        window.__marcas.push(l);
        var t = document.getElementById('clean-terminal');
        if (t) { t.style.display='block';
          var d=document.createElement('div'); d.className='terminal-line';
          d.textContent='X '+l; t.appendChild(d); }
      });
      return 'conectado no contexto do runJavaScript';
    })()"""
    w.page().runJavaScript(js, lambda r: (print(">>", r), fase2()))

def fase2():
    print(">> emitindo")
    br.cleanStep.emit("ALFA", 1)
    QTimer.singleShot(2500, fase3)

def fase3():
    js = """JSON.stringify({
      marcas: window.__marcas || 'indefinido',
      linhas: document.getElementById('clean-terminal').querySelectorAll('.terminal-line').length
    })"""
    w.page().runJavaScript(js, lambda r: (print(">> resultado:", r), app.quit()))

QTimer.singleShot(9000, fase1)
app.exec()
