"""
Componentes visuais reutilizáveis do TecnoApp.

Fornecem a fundação visual para todas as telas do produto:
identidade neon escura preservada, cards com bordas suaves,
métricas tipograficamente destacadas e indicadores de estado.

Nenhum componente contém lógica de negócio — apenas apresentação.
As cores e medidas vivem em Palette e Spacing para garantir
consistência entre módulos.
"""

from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QSizePolicy, QWidget, QGridLayout
from PySide6.QtGui import QFont, QPainter, QColor, QBrush, QPainterPath
from PySide6.QtCore import Qt


# ═══════════════════════════════════════════════════════════════════════
# Design tokens
# ═══════════════════════════════════════════════════════════════════════

class Palette:
    """Paleta central do produto — referência única para todos os componentes."""
    # Fundo
    BG_BASE        = "#030407"
    BG_CARD        = "#0a0d14"
    BG_CARD_HOVER  = "#0d1220"
    # Bordas
    BORDER_SUBTLE  = "#1a2230"
    # Accents de módulo
    ACCENT_CYAN    = "#0eb3ff"   # Limpeza, Otimização, Reparos
    ACCENT_PURPLE  = "#7000ff"   # Modo Gamer
    # Estados
    STATE_ON       = "#4caf50"
    STATE_WARN     = "#ffbd2e"
    STATE_OFF      = "#888"
    STATE_OFF_BRD  = "#333"
    STATE_DANGER   = "#ff4b4b"
    # Texto
    FG_PRIMARY     = "#ffffff"
    FG_BODY        = "#ccd2e0"
    FG_MUTED       = "#888"
    FG_SUBTLE      = "#444"


class Spacing:
    """Medidas constantes usadas pelos componentes."""
    CARD_RADIUS       = 12
    CARD_PADDING      = 20
    CARD_BORDER_WIDTH = 1
    STRIPE_HEIGHT     = 3
    CHIP_HEIGHT       = 24
    CHIP_RADIUS       = 12


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
