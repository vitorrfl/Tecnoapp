"""
Updater — checa releases do GitHub e baixa a nova versão.

Fluxo:
    1. UpdateChecker (QThread) consulta a API de releases do GitHub
    2. Compara a tag da release com APP_VERSION (semver simples)
    3. Se houver versão nova, emite update_available com os detalhes
    4. O usuário clica em "Atualizar"; UpdateDownloader baixa o .exe
    5. O instalador roda e o app fecha para ser substituído

Nada aqui levanta exceção para fora: falha de rede é silenciosa
(update é opcional, não pode quebrar o app).
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import time
import urllib.request
import urllib.error

from PySide6.QtCore import QThread, Signal

from version import APP_VERSION, GITHUB_REPO

# /releases (plural): /releases/latest exclui pre-releases, e o app
# distribui betas. Pegamos a primeira release nao-draft da lista.
_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases?per_page=10"
_TIMEOUT = 8
_UA = {"User-Agent": f"TecnoApp/{APP_VERSION}", "Accept": "application/vnd.github+json"}


def parse_version(v: str) -> tuple:
    """
    'v1.2.3' -> (1, 2, 3, 1, 0)  — release final
    'v1.2.3-beta.4' -> (1, 2, 3, 0, 4)  — pre-release

    Os dois ultimos campos ordenam pre-releases: o flag 0 faz qualquer
    pre-release perder para a release final de mesmo numero (semver),
    e o contador separa beta.1 < beta.2.
    """
    raw = (v or "").strip().lstrip("vV").split("+")[0]
    base, _, pre = raw.partition("-")

    parts = []
    for chunk in base.split("."):
        try:
            parts.append(int(chunk))
        except ValueError:
            parts.append(0)
    while len(parts) < 3:
        parts.append(0)
    parts = parts[:3]

    if not pre:
        # Release final vence qualquer pre-release do mesmo numero
        return tuple(parts) + (1, 0)

    # Ultimo grupo numerico do sufixo: 'beta.4' -> 4, 'rc2' -> 2
    nums = re.findall(r"\d+", pre)
    return tuple(parts) + (0, int(nums[-1]) if nums else 0)


def is_newer(remote: str, local: str = APP_VERSION) -> bool:
    """True se a versão remota for estritamente maior que a local."""
    try:
        return parse_version(remote) > parse_version(local)
    except Exception:
        return False



def _juntar_notas(releases: list) -> str:
    """
    Junta as notas de todas as versoes pendentes, da mais nova para a mais
    antiga.

    Com uma so, devolve o texto puro. Com varias, prefixa cada bloco com o
    nome da versao para o usuario ver o que entrou em cada uma.
    """
    if not releases:
        return ""
    if len(releases) == 1:
        return releases[0].get("body") or ""

    partes = []
    for r in releases:
        corpo = (r.get("body") or "").strip()
        if not corpo:
            continue
        titulo = (r.get("tag_name") or "").lstrip("vV")
        partes.append("[ versao " + titulo + " ]\n" + corpo)
    return "\n\n".join(partes)


class UpdateChecker(QThread):
    """Consulta a release mais recente. Não bloqueia a UI."""

    # (versao, notas, url_download, tamanho_bytes)
    update_available = Signal(str, str, str, int)
    up_to_date = Signal()
    check_failed = Signal(str)

    def run(self):
        try:
            req = urllib.request.Request(_API, headers=_UA)
            with urllib.request.urlopen(req, timeout=_TIMEOUT) as r:
                data = json.loads(r.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:
            # 404 = repo sem release publicada ainda; não é erro do usuário
            self.check_failed.emit("sem releases" if e.code == 404 else f"HTTP {e.code}")
            return
        except Exception as e:
            self.check_failed.emit(f"{type(e).__name__}")
            return

        try:
            # /releases vem ordenado da mais recente para a mais antiga
            if isinstance(data, list):
                lista = [r for r in data if not r.get("draft")]
            else:
                lista = [data] if data else []

            if not lista:
                self.up_to_date.emit()
                return

            # Todas as versoes mais novas que a instalada, nao so a ultima:
            # quem pula da 2.0.0 para a 2.0.2 precisa saber o que entrou na
            # 2.0.1 tambem.
            pendentes = [r for r in lista if is_newer(r.get("tag_name") or "")]

            data = lista[0]
            tag = data.get("tag_name") or ""
            if not tag or not is_newer(tag):
                self.up_to_date.emit()
                return

            # Procura um .exe nos assets da release
            url, size = "", 0
            for asset in data.get("assets") or []:
                name = (asset.get("name") or "").lower()
                if name.endswith(".exe"):
                    url = asset.get("browser_download_url") or ""
                    size = int(asset.get("size") or 0)
                    break

            if not url:
                self.check_failed.emit("release sem instalador .exe")
                return

            notas = _juntar_notas(pendentes)
            self.update_available.emit(tag.lstrip("vV"), notas, url, size)
        except Exception as e:
            self.check_failed.emit(f"{type(e).__name__}")


class UpdateDownloader(QThread):
    """
    Baixa o instalador reportando progresso, retomando de onde parou.

    Sao ~126 MB: em conexao instavel a queda no meio e comum (WinError
    10054, "conexao fechada pelo host remoto"). Sem retomada, cada queda
    jogava fora tudo o que ja tinha sido baixado e o usuario via um erro
    tecnico sem saida.
    """

    progress = Signal(int)        # 0-100
    finished_ok = Signal(str)     # caminho do arquivo baixado
    failed = Signal(str)
    retrying = Signal(int, int)   # (tentativa, total) — para a UI avisar

    TENTATIVAS = 4
    ESPERA_S = 3

    def __init__(self, url: str, parent=None):
        super().__init__(parent)
        self._url = url

    def _tamanho_remoto(self) -> int:
        """Tamanho total do arquivo, para saber quando terminou."""
        try:
            req = urllib.request.Request(self._url, headers=_UA, method="HEAD")
            with urllib.request.urlopen(req, timeout=20) as r:
                return int(r.headers.get("Content-Length") or 0)
        except Exception:
            return 0

    def run(self):
        # Nome estavel (sem PID): permite retomar mesmo entre tentativas.
        dest = os.path.join(tempfile.gettempdir(), "TecnoApp-Setup-update.exe")
        total = self._tamanho_remoto()
        ultimo_erro = ""

        for tentativa in range(1, self.TENTATIVAS + 1):
            baixado = os.path.getsize(dest) if os.path.exists(dest) else 0

            # Ja completo de uma tentativa anterior
            if total and baixado >= total:
                self.progress.emit(100)
                self.finished_ok.emit(dest)
                return

            if tentativa > 1:
                self.retrying.emit(tentativa, self.TENTATIVAS)
                time.sleep(self.ESPERA_S)

            try:
                headers = dict(_UA)
                if baixado:
                    # Range: pede so o que falta em vez de recomecar
                    headers["Range"] = f"bytes={baixado}-"

                req = urllib.request.Request(self._url, headers=headers)
                with urllib.request.urlopen(req, timeout=60) as r:
                    # 206 = servidor aceitou continuar; 200 = mandou tudo de novo
                    if baixado and getattr(r, "status", 200) != 206:
                        baixado = 0
                    if not total:
                        total = int(r.headers.get("Content-Length") or 0) + baixado

                    modo = "ab" if baixado else "wb"
                    with open(dest, modo) as f:
                        while True:
                            chunk = r.read(65536)
                            if not chunk:
                                break
                            f.write(chunk)
                            baixado += len(chunk)
                            if total > 0:
                                self.progress.emit(min(100, int(baixado * 100 / total)))

                # Confere o tamanho: arquivo truncado nao pode virar instalador
                final = os.path.getsize(dest) if os.path.exists(dest) else 0
                if total and final < total:
                    ultimo_erro = "download incompleto"
                    continue

                self.progress.emit(100)
                self.finished_ok.emit(dest)
                return

            except Exception as e:
                ultimo_erro = f"{type(e).__name__}"
                continue

        # Esgotadas as tentativas: mensagem util, nao o erro cru do Python
        self.failed.emit(
            "A conexao caiu durante o download. Verifique a internet e tente "
            f"de novo, ou baixe manualmente pelo GitHub. ({ultimo_erro})"
        )


def run_installer_and_exit(installer_path: str) -> bool:
    """
    Executa o instalador e sinaliza que o app deve fechar.

    O app roda elevado, então o instalador herda a elevação e não dispara
    um segundo UAC. Retorna False se o arquivo sumiu.
    """
    try:
        if not os.path.isfile(installer_path):
            return False
        # Sem /RESTARTAPPLICATIONS: ele so reinicia o que o Restart Manager
        # fechou, e o app fecha sozinho logo apos esta chamada. Quem reabre
        # e a entrada [Run] do instalador marcada com Check: EhSilencioso.
        subprocess.Popen(
            [installer_path, "/SILENT", "/CLOSEAPPLICATIONS"],
            close_fds=True,
        )
        return True
    except Exception:
        return False
