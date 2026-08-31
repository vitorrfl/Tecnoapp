"""
Remocao de bloatware.

Ao contrario dos tweaks do Modo Gamer, desinstalar e IRREVERSIVEL: nao ha
snapshot que traga o programa de volta. Por isso:

    - so remove o que o usuario marcou explicitamente
    - nunca aceita item classificado como RISK_KEEP, mesmo se pedido
    - cria ponto de restauracao antes do lote (best-effort)
"""

from __future__ import annotations

import re
import subprocess

from PySide6.QtCore import QThread, Signal

from .catalog import classify, is_removable

_MSI_GUID = re.compile(r"\{[0-9A-Fa-f\-]{36}\}")
_NO_WINDOW = subprocess.CREATE_NO_WINDOW


def create_restore_point(desc: str = "TecnoApp - antes do debloat") -> bool:
    """Ponto de restauracao. Best-effort: falha nao impede a remocao."""
    cmd = (
        f'Checkpoint-Computer -Description "{desc}" '
        f'-RestorePointType APPLICATION_INSTALL'
    )
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", cmd],
            capture_output=True, encoding="utf-8", errors="replace",
            creationflags=_NO_WINDOW, timeout=120,
        )
        return r.returncode == 0
    except Exception:
        return False


def _uninstall_registry(item: dict) -> tuple[bool, str]:
    """Desinstala via MSI ou o desinstalador proprio do programa."""
    cmd = (item.get("uninstall") or "").strip()
    if not cmd:
        return False, "sem comando de desinstalacao"

    guid = _MSI_GUID.search(cmd)
    try:
        if guid and "msiexec" in cmd.lower():
            # /X = remover. O registro as vezes traz /I (instalar).
            args = ["msiexec.exe", "/X", guid.group(0), "/qn", "/norestart"]
            r = subprocess.run(args, capture_output=True, timeout=600,
                               creationflags=_NO_WINDOW)
            # 3010 = sucesso, requer reboot
            if r.returncode in (0, 3010):
                return True, ""
            return False, f"msiexec exit {r.returncode}"

        # Desinstalador proprio: sem /qn garantido, pode abrir UI
        r = subprocess.run(cmd, shell=True, capture_output=True,
                           timeout=600, creationflags=_NO_WINDOW)
        return (r.returncode == 0), ("" if r.returncode == 0 else f"exit {r.returncode}")
    except subprocess.TimeoutExpired:
        return False, "timeout"
    except Exception as e:
        return False, f"{type(e).__name__}"


def _uninstall_appx(item: dict) -> tuple[bool, str]:
    full = (item.get("uninstall") or "").strip()
    if not full:
        return False, "sem PackageFullName"
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command",
             f'Remove-AppxPackage -Package "{full}" -ErrorAction Stop'],
            capture_output=True, encoding="utf-8", errors="replace",
            creationflags=_NO_WINDOW, timeout=300,
        )
        return (r.returncode == 0), ("" if r.returncode == 0 else "Remove-AppxPackage falhou")
    except Exception as e:
        return False, f"{type(e).__name__}"


def uninstall_one(item: dict) -> tuple[bool, str]:
    """
    Remove um item. Reclassifica antes: mesmo que a UI mande um item
    marcado como KEEP, aqui ele e recusado.
    """
    risk, _ = classify(item.get("name", ""), item.get("publisher", ""))
    if not is_removable(risk):
        return False, "protegido (driver ou componente do sistema)"

    if item.get("kind") == "appx":
        return _uninstall_appx(item)
    return _uninstall_registry(item)


class BloatRemover(QThread):
    """Remove uma lista de itens, reportando progresso item a item."""

    progress = Signal(int, int, str)      # atual, total, nome
    item_done = Signal(str, bool, str)    # nome, ok, erro
    finished_all = Signal("QVariant")     # resumo

    def __init__(self, items: list[dict], make_restore=True, parent=None):
        super().__init__(parent)
        self._items = list(items or [])
        self._restore = make_restore

    def run(self):
        if self._restore and self._items:
            create_restore_point()

        ok_count, freed = 0, 0
        failures = []
        total = len(self._items)

        for i, item in enumerate(self._items, 1):
            name = item.get("name", "?")
            self.progress.emit(i, total, name)
            ok, err = uninstall_one(item)
            if ok:
                ok_count += 1
                freed += int(item.get("size_mb") or 0)
            else:
                failures.append({"name": name, "error": err})
            self.item_done.emit(name, ok, err)

        self.finished_all.emit({
            "removed": ok_count,
            "failed": len(failures),
            "freed_mb": freed,
            "failures": failures,
        })
