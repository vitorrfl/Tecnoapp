# Tecnosup Design System — Tokens Python/Qt
# Importação: from app.ui.tokens import Palette, Spacing, Typography, GLOBAL_STYLESHEET

from PySide6.QtGui import QColor, QFont


class Palette:
    # ── Backgrounds ─────────────────────────────────────────────────────
    BG_BASE        = "#030407"
    BG_CARD        = "#0a0d14"
    BG_CARD_HOVER  = "#0d1220"
    BG_SIDEBAR     = QColor(3, 4, 7, 245)       # rgba(3,4,7,0.96)

    # ── Borders ──────────────────────────────────────────────────────────
    BORDER_SUBTLE  = "#1a2230"
    BORDER_FOCUS   = QColor(14, 179, 255, 153)   # rgba(14,179,255,0.6)
    SIDEBAR_BORDER = QColor(14, 179, 255, 25)    # rgba(14,179,255,0.1)

    # ── Accents ──────────────────────────────────────────────────────────
    CYAN           = "#0eb3ff"
    PURPLE         = "#7000ff"
    CYAN_DIM       = QColor(14, 179, 255, 25)    # rgba(14,179,255,0.10)
    PURPLE_DIM     = QColor(112, 0, 255, 38)     # rgba(112,0,255,0.15)

    # Aliases de compatibilidade com o código existente
    ACCENT_CYAN    = CYAN
    ACCENT_PURPLE  = PURPLE

    # ── States ───────────────────────────────────────────────────────────
    STATE_ON       = "#4caf50"
    STATE_WARN     = "#ffbd2e"
    STATE_OFF      = "#888888"
    STATE_OFF_BRD  = "#333333"
    STATE_DANGER   = "#ff4b4b"

    # ── Foreground / Text ─────────────────────────────────────────────────
    FG_PRIMARY     = "#ffffff"
    FG_BODY        = "#ccd2e0"
    FG_MUTED       = "#888888"
    FG_SUBTLE      = "#444444"

    # ── Glows (QGraphicsDropShadowEffect) ────────────────────────────────
    GLOW_CYAN      = QColor(14, 179, 255)        # blur=16, offset=(0,0)
    GLOW_PURPLE    = QColor(112, 0, 255)         # blur=16, offset=(0,0)
    GLOW_CYAN_SM   = QColor(14, 179, 255, 102)   # blur=8,  offset=(0,0)

    # ── Gradients (strings Qt QSS) ────────────────────────────────────────
    GRADIENT_GAMER       = "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0eb3ff, stop:1 #7000ff)"
    GRADIENT_GAMER_HOVER = "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2dc3ff, stop:1 #8a2bff)"


class Spacing:
    # ── Escala ───────────────────────────────────────────────────────────
    XS    = 4    # micro gap
    SM    = 8    # gap interno pequeno
    MD    = 12   # gap padrão entre elementos
    LG    = 14   # gap entre cards
    XL    = 20   # card padding
    XXL   = 24   # screen vertical padding
    XXXL  = 32   # screen horizontal padding

    # ── Layout ───────────────────────────────────────────────────────────
    SIDEBAR_WIDTH = 220

    # ── Radii ────────────────────────────────────────────────────────────
    RADIUS_CARD   = 12   # cards e hero cards
    RADIUS_BTN    = 8    # botões
    RADIUS_CHIP   = 12   # chips / pills
    RADIUS_BAR    = 4    # progress bars
    RADIUS_ROW    = 6    # item rows (clean/optimize/gamer)
    RADIUS_SCROLL = 3    # scroll handles

    # Aliases de compatibilidade com o código existente
    CARD_RADIUS       = RADIUS_CARD
    CARD_PADDING      = XL
    CARD_BORDER_WIDTH = 1
    STRIPE_HEIGHT     = 3
    CHIP_HEIGHT       = 24
    CHIP_RADIUS       = RADIUS_CHIP


class Typography:
    # ── Famílias ──────────────────────────────────────────────────────────
    FONT_BODY = "Segoe UI"
    FONT_MONO = "Consolas"

    # ── Tamanhos (pt) ──────────────────────────────────────────────────────
    SIZE_TITLE   = 22   # h1
    SIZE_SECTION = 16   # h2
    SIZE_LABEL   = 11   # section labels (CAPS, tracked)
    SIZE_BODY    = 12   # corpo de texto
    SIZE_MONO    = 12   # readouts monospace
    SIZE_METRIC  = 32   # MetricLabel (número grande)
    SIZE_CAPTION = 10   # captions
    SIZE_STATUS  = 9    # status bar
    SIZE_VERSION = 9    # "v 1.0 · Tecnosup"

    # ── Pesos ─────────────────────────────────────────────────────────────
    WEIGHT_NORMAL   = QFont.Weight.Normal    # 400
    WEIGHT_SEMIBOLD = QFont.Weight.DemiBold  # 600
    WEIGHT_BOLD     = QFont.Weight.Bold      # 700

    # ── Helpers ───────────────────────────────────────────────────────────
    @staticmethod
    def title() -> QFont:
        f = QFont(Typography.FONT_BODY, Typography.SIZE_TITLE)
        f.setWeight(QFont.Weight.Bold)
        return f

    @staticmethod
    def label() -> QFont:
        f = QFont(Typography.FONT_BODY, Typography.SIZE_LABEL)
        f.setWeight(QFont.Weight.Bold)
        f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1)
        return f

    @staticmethod
    def body() -> QFont:
        return QFont(Typography.FONT_BODY, Typography.SIZE_BODY)

    @staticmethod
    def mono(size: int = None) -> QFont:
        return QFont(Typography.FONT_MONO, size or Typography.SIZE_MONO)

    @staticmethod
    def metric() -> QFont:
        f = QFont(Typography.FONT_BODY, Typography.SIZE_METRIC)
        f.setWeight(QFont.Weight.Bold)
        return f

    @staticmethod
    def status() -> QFont:
        return QFont(Typography.FONT_MONO, Typography.SIZE_STATUS)


# ── Stylesheet global (aplique em QApplication) ───────────────────────────────
GLOBAL_STYLESHEET = f"""
QWidget {{
    background-color: {Palette.BG_BASE};
    color: {Palette.FG_BODY};
    font-family: Segoe UI;
    font-size: 12px;
}}

QScrollBar:vertical {{
    width: 6px;
    background: #111111;
    border-radius: {Spacing.RADIUS_SCROLL}px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {Palette.CYAN};
    border-radius: {Spacing.RADIUS_SCROLL}px;
    min-height: 20px;
}}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{ height: 0px; }}
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {{ background: none; }}

QScrollBar:horizontal {{
    height: 6px;
    background: #111111;
    border-radius: {Spacing.RADIUS_SCROLL}px;
}}
QScrollBar::handle:horizontal {{
    background: {Palette.CYAN};
    border-radius: {Spacing.RADIUS_SCROLL}px;
    min-width: 20px;
}}
QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {{ width: 0px; }}

QToolTip {{
    background: {Palette.BG_CARD};
    color: {Palette.FG_BODY};
    border: 1px solid {Palette.BORDER_SUBTLE};
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 10px;
}}
"""
