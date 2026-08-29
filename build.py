r"""
Build completo do TecnoApp: PyInstaller + instalador Inno Setup.

    .venv\Scripts\python.exe build.py            # exe + instalador
    .venv\Scripts\python.exe build.py --exe-only # so o PyInstaller

A versao vem de app/version.py e e injetada no instalador, para nao
existir versao duplicada em dois arquivos.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV_PY = ROOT / ".venv" / "Scripts" / "python.exe"
DIST = ROOT / "dist" / "TecnoApp"
OUT = ROOT / "installer_output"

ISCC_CANDIDATES = [
    # winget instala por usuario em LOCALAPPDATA; instalador manual vai em Program Files
    Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Inno Setup 6" / "ISCC.exe",
    Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Inno Setup 6" / "ISCC.exe",
    Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Inno Setup 6" / "ISCC.exe",
]


def log(msg: str) -> None:
    print(f"[build] {msg}", flush=True)


def read_version() -> str:
    """APP_VERSION de app/version.py, sem importar o modulo."""
    src = (ROOT / "app" / "version.py").read_text(encoding="utf-8")
    m = re.search(r'APP_VERSION\s*=\s*["\']([^"\']+)["\']', src)
    if not m:
        sys.exit("ERRO: APP_VERSION nao encontrado em app/version.py")
    return m.group(1)


def find_iscc() -> Path | None:
    for p in ISCC_CANDIDATES:
        if p.is_file():
            return p
    found = shutil.which("ISCC.exe")
    return Path(found) if found else None


def build_exe() -> None:
    log("PyInstaller: empacotando (leva alguns minutos)...")
    r = subprocess.run(
        [str(VENV_PY), "-m", "PyInstaller", "tecnoapp.spec", "--noconfirm", "--clean"],
        cwd=ROOT,
    )
    if r.returncode != 0:
        sys.exit(f"ERRO: PyInstaller falhou (exit {r.returncode})")
    if not (DIST / "TecnoApp.exe").is_file():
        sys.exit(f"ERRO: {DIST / 'TecnoApp.exe'} nao foi gerado")

    size_mb = sum(f.stat().st_size for f in DIST.rglob("*") if f.is_file()) / (1024 ** 2)
    log(f"exe pronto — {size_mb:.0f} MB em {DIST}")


def build_installer(version: str) -> None:
    iscc = find_iscc()
    if not iscc:
        log("Inno Setup nao encontrado — pulando o instalador.")
        log("  Instale com:  winget install JRSoftware.InnoSetup")
        return

    OUT.mkdir(exist_ok=True)
    log(f"Inno Setup: compilando instalador v{version}...")
    r = subprocess.run(
        [str(iscc), f"/DAppVersion={version}", "installer.iss"],
        cwd=ROOT,
    )
    if r.returncode != 0:
        sys.exit(f"ERRO: ISCC falhou (exit {r.returncode})")

    setup = OUT / f"TecnoApp-Setup-{version}.exe"
    if setup.is_file():
        log(f"instalador pronto — {setup.stat().st_size / (1024 ** 2):.0f} MB")
        log(f"  {setup}")
    else:
        log(f"AVISO: esperado {setup}, nao encontrado")


def main() -> None:
    version = read_version()
    log(f"TecnoApp v{version}")

    build_exe()
    if "--exe-only" not in sys.argv:
        build_installer(version)

    log("concluido.")
    if "--exe-only" not in sys.argv:
        print()
        print("  Para publicar a atualizacao:")
        print(f"    git tag v{version} && git push --tags")
        print(f"    gh release create v{version} installer_output/TecnoApp-Setup-{version}.exe")


if __name__ == "__main__":
    main()
