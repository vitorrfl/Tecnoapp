# -*- mode: python ; coding: utf-8 -*-
"""
Build do TecnoApp — PyInstaller.

    .venv\Scripts\pyinstaller.exe tecnoapp.spec --noconfirm

Modo onedir (nao onefile): com o Chromium do WebEngine junto, onefile
extrai centenas de MB para o temp a cada execucao — inicializacao lenta
e frequentemente barrada por antivirus.
"""

block_cipher = None

a = Analysis(
    ['app/app3.py'],
    pathex=['app'],
    binaries=[],
    datas=[
        ('app/webview', 'webview'),      # front ativo (HTML/CSS/JS + assets)
        ('app/bg_grid.png', '.'),
    ],
    hiddenimports=[
        'psutil',
        'PySide6.QtWebEngineWidgets',
        'PySide6.QtWebEngineCore',
        'PySide6.QtWebChannel',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        'tkinter', 'matplotlib', 'numpy', 'PIL', 'pytest',
        'PySide6.QtQuick3D', 'PySide6.Qt3DCore', 'PySide6.QtCharts',
        'PySide6.QtDataVisualization', 'PySide6.QtMultimediaWidgets',
    ],
    cipher=block_cipher,
    noarchive=False,
)


# ── Poda: remove peso morto que o PySide6 arrasta ──────────────────
# Traducoes de todos os idiomas (~54MB) menos pt/en; QML (~29MB, o front
# e HTML, nao Qt Quick); OpenGL software fallback (~20MB, ha GPU real).
_DROP_DIRS = ('PySide6/qml', 'PySide6/translations/qtwebengine_locales')
_KEEP_LOCALES = ('pt-BR', 'pt_BR', 'en-US', 'en_US', 'en')

def _keep(entry):
    dest = entry[0].replace(chr(92), '/')
    if dest.endswith('opengl32sw.dll'):
        return False
    if dest.startswith('PySide6/qml/'):
        return False
    if '/qtwebengine_locales/' in dest:
        return dest.rsplit('/', 1)[-1] in ('pt-BR.pak', 'en-US.pak')
    if '/translations/' in dest or dest.startswith('PySide6/translations'):
        return any(loc in dest for loc in _KEEP_LOCALES)
    if '/qtwebengine_locales/' in dest:
        # .pak do Chromium: match exato do nome do arquivo (pt-BR.pak)
        return dest.rsplit('/', 1)[-1] in ('pt-BR.pak', 'en-US.pak')
    return True

a.binaries = TOC([e for e in a.binaries if _keep(e)])
a.datas    = TOC([e for e in a.datas    if _keep(e)])

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='TecnoApp',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,          # app GUI, sem janela de console
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # O app se auto-eleva via ShellExecuteW; nao pedimos manifest de admin
    # aqui para nao disparar dois UACs.
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='TecnoApp',
)
