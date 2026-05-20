"""
Componentes visuais reutilizáveis do TecnoApp.

Fornecem a fundação visual para todas as telas do produto:
identidade neon escura preservada, cards com bordas suaves,
métricas tipograficamente destacadas e indicadores de estado.

Nenhum componente contém lógica de negócio — apenas apresentação.
As cores e medidas vivem em Palette e Spacing para garantir
consistência entre módulos.
"""

from PySide6.QtWidgets import (
    QFrame, QLabel, QVBoxLayout, QHBoxLayout, QSizePolicy, QWidget,
    QGridLayout, QPushButton,
)
from PySide6.QtGui import (
    QFont, QPainter, QColor, QBrush, QPainterPath, QPen, QLinearGradient,
    QCursor,
)
from PySide6.QtCore import Qt, QTimer, QPointF, QElapsedTimer
import math

from .icons import lucide_pixmap
from .tokens import Palette, Spacing


# ═══════════════════════════════════════════════════════════════════════
# Card — bloco visual base
# ═══════════════════════════════════════════════════════════════════════

class Card(QFrame):
    """
    Bloco retangular com fundo de card, borda sutil e cantos arredondados.
    É o container padrão para qualquer agrupamento visual nas telas.

    Cria internamente um QVBoxLayout com padding consistente (20px).
    Widgets são adicionados via `card.add(widget)` ou diretamente
    pela API do Qt (`card.layout().addWidget(...)`).

    Exemplo:
        card = Card()
        card.add(QLabel("Título"))
        card.add(QPushButton("Ação"))
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self.setStyleSheet(
            f"QFrame#Card {{"
            f"  background: {Palette.BG_CARD};"
            f"  border: {Spacing.CARD_BORDER_WIDTH}px solid {Palette.BORDER_SUBTLE};"
            f"  border-radius: {Spacing.CARD_RADIUS}px;"
            f"}}"
        )

        lyt = QVBoxLayout(self)
        lyt.setContentsMargins(
            Spacing.CARD_PADDING, Spacing.CARD_PADDING,
            Spacing.CARD_PADDING, Spacing.CARD_PADDING,
        )
        lyt.setSpacing(12)

    def add(self, widget, stretch: int = 0, alignment=None):
        """Açúcar sintático para `self.layout().addWidget(...)`."""
        if alignment is not None:
            self.layout().addWidget(widget, stretch, alignment)
        else:
            self.layout().addWidget(widget, stretch)

    def add_spacing(self, px: int):
        """Açúcar sintático para `self.layout().addSpacing(px)`."""
        self.layout().addSpacing(px)

    def add_stretch(self, stretch: int = 1):
        """Açúcar sintático para `self.layout().addStretch(stretch)`."""
        self.layout().addStretch(stretch)


# ═══════════════════════════════════════════════════════════════════════
# HeroCard — card central/focal com barra de accent no topo
# ═══════════════════════════════════════════════════════════════════════

class HeroCard(Card):
    """
    Card de destaque com uma barra colorida no topo, identificando o
    módulo ou a hierarquia da tela. É o card central/focal de cada tela
    (ex.: o bloco do CTA principal em Limpeza, Otimização, Gamer).

    A barra segue os cantos arredondados do card — pintada manualmente
    para garantir renderização consistente em qualquer tamanho.

    Parâmetros:
        accent_color: cor hex da barra (default: cyan do produto)

    Exemplo:
        hero = HeroCard(accent_color=Palette.ACCENT_PURPLE)
        hero.add(MetricLabel("● INATIVO"))
        hero.add(btn_activate)
    """

    def __init__(self, accent_color: str = Palette.ACCENT_CYAN, parent=None):
        super().__init__(parent)
        self.setObjectName("HeroCard")
        self._accent = QColor(accent_color)

        # Reaplica stylesheet usando o novo objectName.
        self.setStyleSheet(
            f"QFrame#HeroCard {{"
            f"  background: {Palette.BG_CARD};"
            f"  border: {Spacing.CARD_BORDER_WIDTH}px solid {Palette.BORDER_SUBTLE};"
            f"  border-radius: {Spacing.CARD_RADIUS}px;"
            f"}}"
        )

        # Margens internas reservam espaço para a barra no topo.
        self.layout().setContentsMargins(
            Spacing.CARD_PADDING,
            Spacing.CARD_PADDING + Spacing.STRIPE_HEIGHT,
            Spacing.CARD_PADDING,
            Spacing.CARD_PADDING,
        )

    def set_accent(self, color: str):
        """Troca a cor da barra em tempo de execução (ex.: on/off do Gamer)."""
        self._accent = QColor(color)
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)

        # Cria um path no formato do card (radius completo) e recorta
        # apenas a faixa superior. Resultado: stripe com cantos de topo
        # arredondados e base horizontal limpa.
        w, h = self.width(), self.height()
        r = Spacing.CARD_RADIUS
        stripe = Spacing.STRIPE_HEIGHT

        full = QPainterPath()
        full.addRoundedRect(0, 0, w, h, r, r)
        clip = QPainterPath()
        clip.addRect(0, 0, w, stripe)
        p.fillPath(full.intersected(clip), QBrush(self._accent))


# ═══════════════════════════════════════════════════════════════════════
# MetricLabel — número grande com unidade opcional
# ═══════════════════════════════════════════════════════════════════════

class MetricLabel(QLabel):
    """
    Texto de métrica em destaque — número grande em Segoe UI Bold,
    com unidade opcional em corpo menor e tom apagado.

    Renderizado em rich-text para permitir variação tipográfica
    inline (unidade menor que o número).

    Exemplos:
        MetricLabel("48.2", "GB")       → 48.2 [GB pequeno]
        MetricLabel("3 de 4")           → "3 de 4"
        MetricLabel("● INATIVO")        → texto puro, uso como status
    """

    def __init__(self, value: str = "", unit: str = "", parent=None):
        super().__init__(parent)
        self.setFont(QFont("Segoe UI", 32, QFont.Bold))
        self.setAlignment(Qt.AlignCenter)
        self.setTextFormat(Qt.RichText)
        self.setStyleSheet(
            f"color: {Palette.FG_PRIMARY}; background: transparent;"
        )
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.set_value(value, unit)

    def set_value(self, value: str, unit: str = ""):
        """Atualiza o texto exibido. Unidade vazia = sem sufixo."""
        if unit:
            self.setText(
                f"{value}"
                f"<span style='font-size:14pt; font-weight:400;"
                f" color:{Palette.FG_MUTED};'> {unit}</span>"
            )
        else:
            self.setText(str(value))


# ═══════════════════════════════════════════════════════════════════════
# Chip — indicador compacto de estado
# ═══════════════════════════════════════════════════════════════════════

class Chip(QLabel):
    """
    Indicador em formato de pílula — label curto + estado visual.
    Usado para sinalizar o estado de ajustes/serviços em listas
    compactas (ex.: "[Hibernação off] [Telemetria off]").

    Estados suportados:
        "on"   — verde, aplicado/ativo
        "off"  — cinza, inativo/desligado (padrão)
        "warn" — amarelo, atenção/alerta

    Estados inválidos caem silenciosamente em "off".

    Exemplo:
        c = Chip("Hibernação", state="on")
        c.set_state("off")
    """

    _STYLES = {
        # (bg, fg, border)
        "on":   ("rgba(76, 175, 80, 0.15)",   Palette.STATE_ON,   Palette.STATE_ON),
        "off":  ("transparent",                Palette.STATE_OFF,  Palette.STATE_OFF_BRD),
        "warn": ("rgba(255, 189, 46, 0.15)",  Palette.STATE_WARN, Palette.STATE_WARN),
    }

    def __init__(self, text: str, state: str = "off", parent=None):
        super().__init__(text, parent)
        self.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumHeight(Spacing.CHIP_HEIGHT)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self._state = "off"
        self.set_state(state)

    def set_state(self, state: str):
        """Atualiza o visual do chip. Repinta imediatamente."""
        bg, fg, border = self._STYLES.get(state, self._STYLES["off"])
        self._state = state if state in self._STYLES else "off"
        self.setStyleSheet(
            f"QLabel {{"
            f"  background: {bg};"
            f"  color: {fg};"
            f"  border: 1px solid {border};"
            f"  border-radius: {Spacing.CHIP_RADIUS}px;"
            f"  padding: 2px 12px;"
            f"}}"
        )

    def state(self) -> str:
        """Retorna o estado atual ('on', 'off' ou 'warn')."""
        return self._state


# ═══════════════════════════════════════════════════════════════════════
# ResponsiveCardRow — alterna entre 1×N e 2×(N/2) conforme largura
# ═══════════════════════════════════════════════════════════════════════

class ResponsiveCardRow(QWidget):
    """
    Container de cards que reagrupa entre uma única linha (wide) e
    duas linhas (narrow) conforme a largura disponível.

    Use quando vários cards precisam caber lado a lado em monitores
    grandes, mas devem cair em grade 2×N quando a janela está apertada.

    Parâmetros:
        cards          : lista de QWidget a colocar
        breakpoint_px  : abaixo dessa largura, vai pra modo narrow
        spacing        : px de espaçamento entre cards
    """

    def __init__(self, cards, breakpoint_px: int = 760, spacing: int = 12, parent=None):
        super().__init__(parent)
        self._cards = list(cards)
        self._bp = breakpoint_px
        self._mode = None

        self._grid = QGridLayout(self)
        self._grid.setSpacing(spacing)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._relayout("wide")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        new_mode = "wide" if self.width() >= self._bp else "narrow"
        if new_mode != self._mode:
            self._relayout(new_mode)

    def _relayout(self, mode: str):
        # Tira todos os cards do grid sem destruí-los.
        for c in self._cards:
            try:
                self._grid.removeWidget(c)
            except Exception:
                pass
        # Zera stretches anteriores (até 8 linhas/colunas).
        for i in range(8):
            self._grid.setColumnStretch(i, 0)
            self._grid.setRowStretch(i, 0)

        n = len(self._cards)
        if mode == "wide":
            for i, c in enumerate(self._cards):
                self._grid.addWidget(c, 0, i)
            for i in range(n):
                self._grid.setColumnStretch(i, 1)
            self._grid.setRowStretch(0, 1)
        else:
            for i, c in enumerate(self._cards):
                r, col = divmod(i, 2)
                self._grid.addWidget(c, r, col)
            self._grid.setColumnStretch(0, 1)
            self._grid.setColumnStretch(1, 1)
            rows = (n + 1) // 2
            for r in range(rows):
                self._grid.setRowStretch(r, 1)

        self._mode = mode


# ═══════════════════════════════════════════════════════════════════════
# Sidebar — botões fiéis ao Tecnosup Design System
# ═══════════════════════════════════════════════════════════════════════

class SidebarButton(QPushButton):
    """
    Item de menu da sidebar com ícone SVG (lucide), accent bar lateral
    cyan que aparece em hover/active e estado ativo destacado.

    Reproduz visualmente .menu-btn do design system
    (preview/components-sidebar.html). Não inclui shimmer animado —
    Qt não tem motor de transição CSS.

    Estados:
        active    — fundo + borda cyan, texto cyan, accent bar cheia
        hover     — fundo cyan-dim suave, texto branco, accent bar cheia
        repouso   — fundo transparente, borda neutra, texto cinza
    """

    HEIGHT = 36
    ICON_SIZE = 14
    ACCENT_W = 2

    def __init__(self, icon_name: str, label: str, parent=None):
        super().__init__(parent)
        self._icon_name = icon_name
        self._label = label
        self._active = False
        self._hovered = False
        self.setObjectName("SidebarBtn")
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setFixedHeight(self.HEIGHT)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self._h = QHBoxLayout(self)
        self._h.setContentsMargins(12, 0, 12, 0)
        self._h.setSpacing(8)

        self._icon_lbl = QLabel()
        self._icon_lbl.setFixedSize(self.ICON_SIZE, self.ICON_SIZE)
        self._icon_lbl.setStyleSheet("background: transparent; border: none;")
        self._h.addWidget(self._icon_lbl, 0, Qt.AlignVCenter)

        self._text_lbl = QLabel(label)
        self._text_lbl.setStyleSheet("background: transparent; border: none;")
        self._text_lbl.setFont(QFont("Segoe UI", 8, QFont.Bold))
        self._h.addWidget(self._text_lbl, 1, Qt.AlignVCenter)

        self._update_visual()

    def set_active(self, active: bool):
        if self._active != active:
            self._active = active
            self._update_visual()

    def isActive(self) -> bool:
        return self._active

    def enterEvent(self, e):
        self._hovered = True
        self._update_visual()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hovered = False
        self._update_visual()
        super().leaveEvent(e)

    def _palette_for_state(self):
        if self._active:
            border = "rgba(14, 179, 255, 0.50)"
            bg     = "rgba(14, 179, 255, 0.08)"
            txt    = Palette.ACCENT_CYAN
            ico    = Palette.ACCENT_CYAN
            stroke = 2.2
        elif self._hovered:
            border = "rgba(14, 179, 255, 0.45)"
            bg     = "rgba(14, 179, 255, 0.06)"
            txt    = "#ffffff"
            ico    = Palette.ACCENT_CYAN
            stroke = 2.0
        else:
            border = "rgba(14, 179, 255, 0.15)"
            bg     = "transparent"
            txt    = "#666666"
            ico    = "#555555"
            stroke = 2.0
        return border, bg, txt, ico, stroke

    def _update_visual(self):
        border, bg, txt, ico, stroke = self._palette_for_state()
        self.setStyleSheet(
            f"QPushButton#SidebarBtn {{"
            f"  background: {bg};"
            f"  border: 1px solid {border};"
            f"  border-radius: 8px;"
            f"  text-align: left;"
            f"}}"
        )
        self._text_lbl.setStyleSheet(
            f"background: transparent; border: none; color: {txt};"
            f" font-family: 'Segoe UI'; font-size: 11px; font-weight: 700;"
            f" letter-spacing: 0.3px;"
        )
        pix = lucide_pixmap(self._icon_name, color=ico, size=self.ICON_SIZE,
                            stroke_width=stroke)
        self._icon_lbl.setPixmap(pix)
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if not (self._active or self._hovered):
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(Palette.ACCENT_CYAN))
        h = self.height()
        bar_h = int(h * 0.6)
        y = (h - bar_h) // 2
        p.drawRoundedRect(0, y, self.ACCENT_W, bar_h, 1, 1)


class SidebarRestoreButton(QPushButton):
    """
    Botão "Criar Ponto de Restauração" — variação compacta do
    SidebarButton, com fonte menor (10px / 600), ícone shield e
    accent bar lateral em hover.
    """

    HEIGHT = 30
    ICON_SIZE = 11

    def __init__(self, parent=None):
        super().__init__(parent)
        self._hovered = False
        self.setObjectName("RestoreBtn")
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setFixedHeight(self.HEIGHT)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        h = QHBoxLayout(self)
        h.setContentsMargins(10, 0, 10, 0)
        h.setSpacing(6)
        h.addStretch(1)

        self._icon_lbl = QLabel()
        self._icon_lbl.setFixedSize(self.ICON_SIZE, self.ICON_SIZE)
        self._icon_lbl.setStyleSheet("background: transparent; border: none;")
        h.addWidget(self._icon_lbl, 0, Qt.AlignVCenter)

        self._text_lbl = QLabel("Criar Ponto de Restauração")
        self._text_lbl.setStyleSheet("background: transparent; border: none;")
        h.addWidget(self._text_lbl, 0, Qt.AlignVCenter)
        h.addStretch(1)

        self._update_visual()

    def enterEvent(self, e):
        self._hovered = True
        self._update_visual()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hovered = False
        self._update_visual()
        super().leaveEvent(e)

    def _update_visual(self):
        if self._hovered:
            border = "rgba(14, 179, 255, 0.45)"
            bg     = "rgba(14, 179, 255, 0.05)"
            txt    = Palette.FG_BODY
            ico    = Palette.ACCENT_CYAN
        else:
            border = "rgba(14, 179, 255, 0.15)"
            bg     = "transparent"
            txt    = "#555555"
            ico    = "#555555"
        self.setStyleSheet(
            f"QPushButton#RestoreBtn {{"
            f"  background: {bg};"
            f"  border: 1px solid {border};"
            f"  border-radius: 8px;"
            f"}}"
        )
        self._text_lbl.setStyleSheet(
            f"background: transparent; border: none; color: {txt};"
            f" font-family: 'Segoe UI'; font-size: 10px; font-weight: 600;"
            f" letter-spacing: 0.2px;"
        )
        self._icon_lbl.setPixmap(
            lucide_pixmap("shield", color=ico, size=self.ICON_SIZE,
                          stroke_width=2.0)
        )
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self._hovered:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(Palette.ACCENT_CYAN))
        h = self.height()
        bar_h = int(h * 0.6)
        y = (h - bar_h) // 2
        p.drawRoundedRect(0, y, 2, bar_h, 1, 1)


class SidebarExitButton(QPushButton):
    """Botão SAIR com ícone logout e variação vermelha em hover."""

    HEIGHT = 34
    ICON_SIZE = 12

    def __init__(self, parent=None):
        super().__init__(parent)
        self._hovered = False
        self.setObjectName("ExitSidebarBtn")
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setFixedHeight(self.HEIGHT)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        h = QHBoxLayout(self)
        h.setContentsMargins(10, 0, 10, 0)
        h.setSpacing(6)
        h.addStretch(1)

        self._icon_lbl = QLabel()
        self._icon_lbl.setFixedSize(self.ICON_SIZE, self.ICON_SIZE)
        self._icon_lbl.setStyleSheet("background: transparent; border: none;")
        h.addWidget(self._icon_lbl, 0, Qt.AlignVCenter)

        self._text_lbl = QLabel("SAIR")
        self._text_lbl.setStyleSheet("background: transparent; border: none;")
        h.addWidget(self._text_lbl, 0, Qt.AlignVCenter)
        h.addStretch(1)

        self._update_visual()

    def enterEvent(self, e):
        self._hovered = True
        self._update_visual()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hovered = False
        self._update_visual()
        super().leaveEvent(e)

    def _update_visual(self):
        if self._hovered:
            border = "#ff4b4b"
            bg     = "rgba(255, 75, 75, 0.28)"
            txt    = "#ffffff"
            ico    = "#ff6b6b"
        else:
            border = "rgba(255, 75, 75, 0.25)"
            bg     = "transparent"
            txt    = "#555555"
            ico    = "#555555"
        self.setStyleSheet(
            f"QPushButton#ExitSidebarBtn {{"
            f"  background: {bg};"
            f"  border: 1px solid {border};"
            f"  border-radius: 8px;"
            f"}}"
        )
        self._text_lbl.setStyleSheet(
            f"background: transparent; border: none; color: {txt};"
            f" font-family: 'Segoe UI'; font-size: 11px; font-weight: 700;"
            f" letter-spacing: 1px;"
        )
        self._icon_lbl.setPixmap(
            lucide_pixmap("logout", color=ico, size=self.ICON_SIZE,
                          stroke_width=2.5)
        )
        self.update()


class GamerSidebarButton(QPushButton):
    """
    Botão "MODO GAMER" da sidebar — gradient cyan→purple animado que
    acompanha o cursor do mouse e oscila sutilmente em repouso.

    Reproduz a animação do design (Sidebar.jsx / components-sidebar.html)
    via QTimer + paintEvent custom (Qt não suporta CSS transitions).
    """

    HEIGHT = 36
    ICON_SIZE = 14

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("GamerSidebarBtn")
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setFixedHeight(self.HEIGHT)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMouseTracking(True)
        self._active = False

        # Estado da animação
        self._mouse_x = 0.5
        self._target_x = 0.5
        self._idle_t = 0.0
        self._is_hovered = False
        self._last_move_ms = 0

        self._elapsed = QElapsedTimer()
        self._elapsed.start()

        h = QHBoxLayout(self)
        h.setContentsMargins(12, 0, 12, 0)
        h.setSpacing(8)

        self._icon_lbl = QLabel()
        self._icon_lbl.setFixedSize(self.ICON_SIZE, self.ICON_SIZE)
        self._icon_lbl.setStyleSheet("background: transparent; border: none;")
        self._icon_lbl.setPixmap(
            lucide_pixmap("gamer", color="#ffffff", size=self.ICON_SIZE,
                          stroke_width=2.0)
        )
        h.addWidget(self._icon_lbl, 0, Qt.AlignVCenter)

        self._text_lbl = QLabel("MODO GAMER")
        self._text_lbl.setStyleSheet(
            "background: transparent; border: none;"
            " color: #ffffff; font-family: 'Segoe UI';"
            " font-size: 11px; font-weight: 700; letter-spacing: 1px;"
        )
        h.addWidget(self._text_lbl, 1, Qt.AlignVCenter)

        # ~30fps suficiente; reduz custo de CPU em laptops fracos.
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(33)

    def set_active(self, active: bool):
        self._active = active
        self.update()

    def isActive(self) -> bool:
        return self._active

    def enterEvent(self, e):
        self._is_hovered = True
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._is_hovered = False
        self._target_x = 0.5
        super().leaveEvent(e)

    def mouseMoveEvent(self, e):
        w = max(1, self.width())
        self._target_x = max(0.0, min(1.0, e.position().x() / w))
        self._last_move_ms = self._elapsed.elapsed()
        super().mouseMoveEvent(e)

    @staticmethod
    def _lerp(a, b, t):
        return a + (b - a) * t

    def _tick(self):
        ts = self._elapsed.elapsed()
        if self._is_hovered:
            self._mouse_x = self._lerp(self._mouse_x, self._target_x, 0.18)
        else:
            self._idle_t += 0.012
            self._mouse_x = self._lerp(self._mouse_x, 0.5, 0.04)
        self.update()

    def paintEvent(self, event):
        # Gradient calculado com mesma fórmula do JS original.
        ts = self._elapsed.elapsed()
        if self._is_hovered:
            idle = math.sin(ts * 0.0008) * 0.25 if (ts - self._last_move_ms) > 600 else 0.0
        else:
            idle = math.sin(self._idle_t) * 0.15
        x = self._mouse_x

        s1 = max(0.0, min(60.0, x * 60.0 - idle * 8.0)) / 100.0
        s2 = min(100.0, 40.0 + x * 60.0 + idle * 8.0) / 100.0

        # Direção do gradient (CSS angle 80–120°): aproxima com vetor
        # quase-horizontal levemente inclinado.
        angle_deg = 80.0 + x * 40.0 + idle * 12.0
        rad = math.radians(angle_deg - 90.0)  # CSS->Qt: 0deg=top
        cx, cy = self.width() / 2.0, self.height() / 2.0
        L = max(self.width(), self.height())
        dx = math.cos(rad) * L
        dy = math.sin(rad) * L
        p1 = QPointF(cx - dx / 2.0, cy - dy / 2.0)
        p2 = QPointF(cx + dx / 2.0, cy + dy / 2.0)

        grad = QLinearGradient(p1, p2)
        grad.setColorAt(s1, QColor("#0eb3ff"))
        grad.setColorAt(s2, QColor("#7000ff"))

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(grad))
        p.drawRoundedRect(0, 0, self.width(), self.height(), 8, 8)

        if self._active:
            pen = QPen(QColor("#ffffff"))
            pen.setWidth(1)
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(0, 0, self.width() - 1, self.height() - 1, 8, 8)
