"""
Catalogo de classificacao de bloatware.

Nada aqui e hardcoded por GUID: os GUIDs mudam entre versoes do mesmo
pacote. A classificacao e por PADRAO DE NOME, o que funciona em qualquer
maquina de qualquer fabricante.

Tres niveis:
    RISK_KEEP     — nunca oferecer. Driver ou dependencia de driver.
    RISK_CAUTION  — removivel, mas o usuario pode querer. Avisa o porque.
    RISK_SAFE     — bloat sem funcao real para a maioria.

A allowlist (KEEP) tem prioridade sobre tudo. Na duvida, mantem:
desinstalar e irreversivel, ao contrario dos tweaks do Modo Gamer.
"""

from __future__ import annotations

import re

RISK_KEEP = "keep"
RISK_CAUTION = "caution"
RISK_SAFE = "safe"

# ─────────────────────────────────────────────────────────────────────
# NUNCA REMOVER — driver, runtime ou dependencia de hardware.
# Remover qualquer um destes pode deixar a maquina sem audio, rede,
# video ou touchpad. Esta lista vence qualquer regra abaixo.
# ─────────────────────────────────────────────────────────────────────
_KEEP_PATTERNS = [
    # Audio
    r"realtek", r"waves\s*maxx", r"maxxaudio", r"dolby", r"dts\b",
    r"conexant", r"cirrus\s*logic", r"sound\s*blaster", r"nahimic",
    # Video / GPU
    r"nvidia", r"amd\s+(software|radeon|chipset)", r"intel.*graphics",
    r"geforce\s+experience",
    # Rede
    r"killer\s+(network|performance|control)", r"intel.*wireless",
    r"qualcomm", r"mediatek", r"bluetooth",
    # Input / chipset / plataforma
    r"synaptics", r"elan\b", r"alps\b", r"precision\s+touchpad",
    r"intel.*(chipset|management engine|rapid storage|serial io)",
    r"amd.*chipset", r"thunderbolt",
    # Runtimes que outros apps dependem
    r"visual c\+\+", r"\.net\s+(framework|runtime|desktop)",
    r"directx", r"edge\s*webview", r"microsoft edge$",
    r"windows\s+(driver|sdk)", r"hotfix", r"security update",
    # Seguranca do sistema
    r"defender", r"bitlocker", r"secure\s*boot",
]

# ─────────────────────────────────────────────────────────────────────
# Bloat por fabricante. (padrao, risco, explicacao para o usuario)
# ─────────────────────────────────────────────────────────────────────
_BLOAT_RULES = [
    # ── Dell ────────────────────────────────────────────────────────
    (r"supportassist.*analytics",  RISK_SAFE,    "Telemetria da Dell. Ja teve falhas de seguranca conhecidas."),
    (r"dell\s+core\s+services",    RISK_SAFE,    "Servico base do TechHub. Nao e driver."),
    (r"dell\s+techhub",            RISK_SAFE,    "Hub de suporte da Dell."),
    (r"dell\s+digital\s+delivery", RISK_SAFE,    "Entrega de software promocional."),
    (r"dell\s+connected\s+service",RISK_SAFE,    "Servico de conteudo da Dell."),
    (r"dell\s+customer\s+connect", RISK_SAFE,    "Marketing e pesquisas da Dell."),
    (r"supportassist.*recovery",   RISK_CAUTION, "Recuperacao da Dell. O Windows tem a propria."),
    (r"dell\s+update",             RISK_CAUTION, "Atualiza drivers da Dell. Util se voce usa."),
    (r"dell\s+power\s?manager",    RISK_CAUTION, "Gerencia bateria. Util em notebook."),

    # ── Lenovo ──────────────────────────────────────────────────────
    (r"lenovo\s+vantage",          RISK_CAUTION, "Central da Lenovo. Tambem atualiza drivers."),
    (r"lenovo\s+now|lenovo\s+app", RISK_SAFE,    "Promocional da Lenovo."),
    (r"lenovo\s+(welcome|migration|smart)", RISK_SAFE, "Bloat da Lenovo."),
    (r"lenovo\s+solution\s+center",RISK_SAFE,    "Diagnostico legado, descontinuado."),
    (r"mccafee|mcafee",            RISK_SAFE,    "Antivirus trial pre-instalado."),

    # ── HP ──────────────────────────────────────────────────────────
    (r"hp\s+support\s+(assistant|solutions)", RISK_CAUTION, "Suporte HP. Tambem atualiza drivers."),
    (r"hp\s+(jumpstart|connected|documentation|orbit)", RISK_SAFE, "Bloat da HP."),
    (r"hp\s+wolf\s+security",      RISK_CAUTION, "Seguranca HP. Pesado, mas e antivirus."),

    # ── ASUS / Acer / MSI ───────────────────────────────────────────
    (r"asus\s+(giftbox|webstorage|live\s*update)", RISK_SAFE, "Bloat da ASUS."),
    (r"armoury\s+crate",           RISK_CAUTION, "Controla RGB e perfis ASUS."),
    (r"acer\s+(care|jumpstart|collection|product\s*reg)", RISK_SAFE, "Bloat da Acer."),
    (r"msi\s+(center|dragon)",     RISK_CAUTION, "Controla perfis e RGB MSI."),

    # ── Trials e promocionais genericos ─────────────────────────────
    (r"norton|avast|avg\s|kaspersky.*trial", RISK_CAUTION, "Antivirus trial. Remova so se tiver outro."),
    (r"wildtangent|candy\s*crush|booking\.com|spotify.*stub", RISK_SAFE, "Aplicativo promocional."),
    (r"office.*(trial|hub)|onedrive.*setup",  RISK_CAUTION, "Trial ou stub da Microsoft."),

    # ── UWP da Microsoft ────────────────────────────────────────────
    (r"microsoft\.(bing|3dbuilder|mixedreality|zune|people|getstarted)", RISK_SAFE, "App padrao raramente usado."),
    (r"microsoft\.(xbox|gaming)",  RISK_CAUTION, "Xbox. Alguns jogos dependem do Game Bar."),
    (r"microsoft\.(skypeapp|yourphone|todos|officehub)", RISK_SAFE, "App padrao raramente usado."),
    (r"clipchamp|linkedin",        RISK_SAFE, "App promocional pre-instalado."),
]

_KEEP_RE = [re.compile(p, re.I) for p in _KEEP_PATTERNS]
_RULES_RE = [(re.compile(p, re.I), risk, why) for p, risk, why in _BLOAT_RULES]


def classify(name: str, publisher: str = "") -> tuple[str, str]:
    """
    Classifica um programa instalado.

    Retorna (risco, explicacao). Programas nao reconhecidos voltam como
    RISK_KEEP — a ferramenta so oferece o que sabe identificar, nunca
    tenta adivinhar se algo desconhecido e descartavel.
    """
    blob = f"{name} {publisher}".strip()
    if not blob:
        return RISK_KEEP, ""

    # Allowlist vence tudo
    for rx in _KEEP_RE:
        if rx.search(blob):
            return RISK_KEEP, "Driver ou componente do sistema."

    for rx, risk, why in _RULES_RE:
        if rx.search(blob):
            return risk, why

    return RISK_KEEP, ""


def is_removable(risk: str) -> bool:
    """Só SAFE e CAUTION aparecem na lista; KEEP nunca é oferecido."""
    return risk in (RISK_SAFE, RISK_CAUTION)
