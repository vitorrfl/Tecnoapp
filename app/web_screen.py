"""
WebScreen — QWebEngineView que carrega a UI HTML/JS do TecnoApp e
expõe o objeto Bridge via QWebChannel.
"""

from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView

from bridge import Bridge


class _Page(QWebEnginePage):
    """Encaminha console.log/warn/error do JS para o stdout do Python."""

    def javaScriptConsoleMessage(self, level, message, line, source_id):  # noqa: N802
        try:
            lv = int(level.value) if hasattr(level, "value") else int(level)
        except Exception:
            lv = 0
        prefix = {0: "log", 1: "warn", 2: "err"}.get(lv, "log")
        print(f"[web/{prefix}] {message}  ({source_id}:{line})")


class WebScreen(QWebEngineView):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self._page = _Page(self)
        self.setPage(self._page)

        s = self.settings()
        s.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        s.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
        s.setAttribute(QWebEngineSettings.LocalContentCanAccessFileUrls, True)
        s.setAttribute(QWebEngineSettings.AllowRunningInsecureContent, True)
        s.setAttribute(QWebEngineSettings.ShowScrollBars, False)

        # Bridge: registra o objeto que o JS acessa via window.bridge
        self.bridge = Bridge(main_window=main_window, parent=self)
        self.channel = QWebChannel(self._page)
        self.channel.registerObject("bridge", self.bridge)
        self._page.setWebChannel(self.channel)

        # Carrega o front
        web_dir = Path(__file__).resolve().parent / "webview"
        index = web_dir / "index.html"
        if not index.exists():
            raise FileNotFoundError(f"web/index.html não encontrado em {index}")
        self.load(QUrl.fromLocalFile(str(index)))
