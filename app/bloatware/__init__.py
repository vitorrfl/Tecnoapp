"""
Deteccao e remocao de bloatware (software pre-instalado de fabrica).

    catalog.py  — regras por fabricante + allowlist de drivers
    scanner.py  — varre registro, UWP e servicos; classifica pelo catalogo
    remover.py  — desinstalacao, sempre com confirmacao explicita
"""

from .scanner import BloatScanner, scan_installed
from .catalog import classify, RISK_SAFE, RISK_CAUTION, RISK_KEEP

__all__ = [
    "BloatScanner", "scan_installed", "classify",
    "RISK_SAFE", "RISK_CAUTION", "RISK_KEEP",
]
