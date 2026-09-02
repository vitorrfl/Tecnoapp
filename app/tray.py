"""
Icone na bandeja do sistema.

Pedido por usuarios: poder fechar a janela e o app continuar rodando ao
lado do relogio, em vez de sair de vez.

Decisao importante: fechar no X MINIMIZA para a bandeja, mas o botao SAIR
encerra de verdade. Sao acoes diferentes e o usuario espera coisas
diferentes de cada uma — fechar no X e reversivel, SAIR e definitivo.

O menu mostra o estado do Modo Gamer porque e o que sobrevive ao
fechamento da janela: alguem pode fechar o app sem lembrar que os tweaks
continuam aplicados.
"""

from __future__ import annotations

import os
import sys

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenu, QSystemTrayIcon


def _icon_path() -> str:
    """Icone empacotado (PyInstaller) ou do fonte."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    for rel in ("assets/tecnoapp.ico", "tecnoapp.ico"):
        p = os.path.join(base, rel.replace("/", os.sep))
        if os.path.isfile(p):
            return p
    # fallback: caminho do fonte
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "tecnoapp.ico")
    return p if os.path.isfile(p) else ""


class TrayIcon(QObject):
    """Icone da bandeja com menu de contexto."""

    mostrar_pedido = Signal()
    sair_pedido = Signal()
    gamer_toggle = Signal(bool)   # True = ativar, False = desativar

    def __init__(self, janela, engine_getter=None, parent=None):
        super().__init__(parent)
        self._janela = janela
        self._engine_getter = engine_getter
        self._tray = None
        self._acao_gamer = None

    def disponivel(self) -> bool:
        try:
            return QSystemTrayIcon.isSystemTrayAvailable()
        except Exception:
            return False

    def montar(self) -> bool:
        """Cria o icone. False se a bandeja nao existir no sistema."""
        if not self.disponivel():
            return False

        try:
            caminho = _icon_path()
            icone = QIcon(caminho) if caminho else QIcon()
            self._tray = QSystemTrayIcon(icone, self)
            self._tray.setToolTip("TecnoApp — Tecnosup")

            menu = QMenu()

            abrir = QAction("Abrir TecnoApp", menu)
            abrir.triggered.connect(self.mostrar_pedido.emit)
            menu.addAction(abrir)

            menu.addSeparator()

            # Atalho para o que mais importa quando a janela esta fechada
            self._acao_gamer = QAction("Modo Gamer", menu)
            self._acao_gamer.triggered.connect(self._alternar_gamer)
            menu.addAction(self._acao_gamer)

            menu.addSeparator()

            sair = QAction("Sair", menu)
            sair.triggered.connect(self.sair_pedido.emit)
            menu.addAction(sair)

            self._tray.setContextMenu(menu)
            # Clique simples ja restaura: e o que se espera de um icone
            # de bandeja, e o duplo clique nem sempre e descoberto.
            self._tray.activated.connect(self._clique)
            self._tray.show()
            self.atualizar_estado()
            return True
        except Exception:
            self._tray = None
            return False

    def _clique(self, motivo):
        if motivo in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self.mostrar_pedido.emit()

    def _gamer_ativo(self) -> bool:
        try:
            eng = self._engine_getter() if self._engine_getter else None
            return bool(eng.is_active()) if eng else False
        except Exception:
            return False

    def _alternar_gamer(self):
        self.gamer_toggle.emit(not self._gamer_ativo())

    def atualizar_estado(self):
        """
        Reflete o Modo Gamer no menu e no tooltip.

        Quem fecha a janela precisa conseguir ver que os tweaks continuam
        aplicados sem reabrir o app.
        """
        if not self._tray:
            return
        try:
            ativo = self._gamer_ativo()
            if self._acao_gamer:
                self._acao_gamer.setText(
                    "Desativar Modo Gamer" if ativo else "Ativar Modo Gamer"
                )
            self._tray.setToolTip(
                "TecnoApp — Modo Gamer ATIVO" if ativo else "TecnoApp — Tecnosup"
            )
        except Exception:
            pass

    def avisar(self, titulo: str, texto: str):
        """Notificacao do Windows a partir da bandeja."""
        if not self._tray:
            return
        try:
            self._tray.showMessage(titulo, texto, QSystemTrayIcon.Information, 4000)
        except Exception:
            pass

    def esconder(self):
        if self._tray:
            try:
                self._tray.hide()
            except Exception:
                pass
