"""
Versão única do TecnoApp.

Fonte da verdade para: UI (rodapé da sidebar), updater (comparação com
a release do GitHub) e o build do PyInstaller.

Esquema de versao: o numero cresce, o sufixo nao. Em vez de beta.3,
beta.4, beta.8..., cada entrega recebe uma versao nova mantendo o "-beta":
2.0.0-beta, 2.1.0-beta, 2.2.0-beta. Sai o "-beta" quando a versao for
considerada estavel.

Ao lançar uma versão nova:
    1. bump APP_VERSION aqui
    2. git tag v<APP_VERSION> && git push --tags
    3. publicar o instalador na release do GitHub
"""

APP_VERSION = "2.0.2-beta"
GITHUB_REPO = "vitorrfl/Tecnoapp"

__all__ = ["APP_VERSION", "GITHUB_REPO"]
