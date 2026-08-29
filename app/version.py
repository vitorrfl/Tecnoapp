"""
Versão única do TecnoApp.

Fonte da verdade para: UI (rodapé da sidebar), updater (comparação com
a release do GitHub) e o build do PyInstaller.

Ao lançar uma versão nova:
    1. bump APP_VERSION aqui
    2. git tag v<APP_VERSION> && git push --tags
    3. publicar o instalador na release do GitHub
"""

APP_VERSION = "1.0.0"
GITHUB_REPO = "vitorrfl/Tecnoapp"

__all__ = ["APP_VERSION", "GITHUB_REPO"]
