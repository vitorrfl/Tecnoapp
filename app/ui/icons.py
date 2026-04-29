"""
Ícones SVG do TecnoApp — extraídos do Tecnosup Design System.

Os pictogramas são os mesmos do design (lucide icons), o que mantém
fidelidade visual com o design exportado em vez de depender da fonte
Segoe MDL2 Assets, cujos glifos são diferentes.

Uso:
    from ui.icons import lucide_icon
    btn.setIcon(lucide_icon("home", color="#0eb3ff", size=14))
"""

from PySide6.QtCore import Qt, QByteArray, QSize
from PySide6.QtGui import QIcon, QPixmap, QPainter
from PySide6.QtSvg import QSvgRenderer


_LUCIDE_PATHS = {
    "home":       '<path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>',
    "limpeza":    '<polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4h6v2"/>',
    "otimizacao": '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>',
    "reparos":    '<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>',
    "specs":      '<rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/>',
    "gamer":      '<line x1="6" y1="12" x2="18" y2="12"/><line x1="12" y1="6" x2="12" y2="18"/><rect x="2" y="6" width="20" height="12" rx="2"/>',
    "shield":     '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
    "logout":     '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>',
}


def _render_svg(name: str, color: str, size: int, stroke_width: float = 2.0) -> QPixmap:
    inner = _LUCIDE_PATHS.get(name, "")
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}"'
        f' viewBox="0 0 24 24" fill="none" stroke="{color}"'
        f' stroke-width="{stroke_width}" stroke-linecap="round" stroke-linejoin="round">'
        f'{inner}</svg>'
    )
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    renderer.render(p)
    p.end()
    return pix


def lucide_pixmap(name: str, color: str = "#555555", size: int = 14, stroke_width: float = 2.0) -> QPixmap:
    """Renderiza um ícone lucide como QPixmap na cor especificada."""
    return _render_svg(name, color, size, stroke_width)


def lucide_icon(name: str, color: str = "#555555", size: int = 14, stroke_width: float = 2.0) -> QIcon:
    """Renderiza um ícone lucide como QIcon."""
    return QIcon(_render_svg(name, color, size, stroke_width))
