"""
Pacote de UI do TecnoApp.

Exporta os componentes visuais reutilizáveis (Card, HeroCard,
MetricLabel, Chip) e os tokens de design (Palette, Spacing).

Uso típico:
    from ui import Card, HeroCard, MetricLabel, Chip, Palette
"""

from .widgets import (
    Card, HeroCard, MetricLabel, Chip, ResponsiveCardRow,
    Palette, Spacing,
    SidebarButton, SidebarRestoreButton, SidebarExitButton, GamerSidebarButton,
)
from .icons import lucide_icon, lucide_pixmap

__all__ = [
    "Card",
    "HeroCard",
    "MetricLabel",
    "Chip",
    "ResponsiveCardRow",
    "Palette",
    "Spacing",
    "SidebarButton",
    "SidebarRestoreButton",
    "SidebarExitButton",
    "GamerSidebarButton",
    "lucide_icon",
    "lucide_pixmap",
]
