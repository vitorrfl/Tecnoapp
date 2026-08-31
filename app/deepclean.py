"""
Limpeza profunda via cleanmgr (Limpeza de Disco do Windows).

Alcanca o que a limpeza rapida nao toca — instalacoes anteriores do
Windows, otimizacao de entrega, pacotes de driver antigos. E onde estao
os GBs, nao os MBs.

O .bat original usava `cleanmgr /sageset:65535`, que abre uma janela do
Windows para o usuario marcar as caixas na mao. Aqui o perfil e escrito
direto no registro (que e tudo o que o /sageset faz) e executado com
/sagerun — sem janela nenhuma, com a selecao vindo da tela do TecnoApp.

SEGURANCA: DownloadsFolder nunca e oferecido. Ele apaga a pasta Downloads
do usuario — o proprio Windows parou de marca-lo por padrao depois de
reclamacoes de perda de arquivos.
"""

from __future__ import annotations

import subprocess
import winreg

from PySide6.QtCore import QThread, Signal

_VOLUME_CACHES = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\VolumeCaches"
_SAGE_ID = 65535
_NO_WINDOW = subprocess.CREATE_NO_WINDOW

# Handlers que NUNCA sao oferecidos, por apagarem dados do usuario.
_BLOCKED = {
    "DownloadsFolder",          # a pasta Downloads inteira
}

# Rotulo e explicacao em portugues. O nome do handler no registro e em
# ingles e nao diz nada para o usuario final.
_LABELS = {
    "Previous Installations": (
        "Instalacoes anteriores do Windows",
        "A pasta Windows.old, de quando o Windows foi atualizado de versao. "
        "Costuma ser o maior item da lista.",
        "Remove a possibilidade de voltar para a versao anterior do Windows.",
    ),
    "Update Cleanup": (
        "Atualizacoes antigas do Windows",
        "Versoes antigas de arquivos substituidos por atualizacoes. O Windows "
        "as mantem para permitir desinstalar updates.",
        "Updates ja instalados nao poderao mais ser desinstalados.",
    ),
    "Delivery Optimization Files": (
        "Arquivos de otimizacao de entrega",
        "Updates baixados e guardados para compartilhar com outros PCs da rede.",
        "",
    ),
    "Device Driver Packages": (
        "Pacotes de driver antigos",
        "Versoes anteriores de drivers, mantidas para reverter atualizacoes.",
        "Nao sera possivel reverter para drivers anteriores.",
    ),
    "Windows Error Reporting Files": (
        "Relatorios de erro do Windows",
        "Arquivos gerados quando programas travam. Uteis so para diagnostico.",
        "",
    ),
    "D3D Shader Cache": (
        "Cache de shaders DirectX",
        "Cache de compilacao grafica. E recriado automaticamente; os primeiros "
        "minutos de jogo podem ficar levemente mais lentos.",
        "",
    ),
    "Windows ESD installation files": (
        "Arquivos de instalacao do Windows",
        "Usados para 'Restaurar este PC'.",
        "A restauracao do sistema precisara baixar os arquivos de novo.",
    ),
    "System error memory dump files": (
        "Despejos de memoria de tela azul",
        "Arquivos grandes gerados em travamentos do sistema.",
        "",
    ),
    "System error minidump files": (
        "Minidumps de tela azul",
        "Versao reduzida dos despejos de travamento.",
        "",
    ),
    "Temporary Files": (
        "Arquivos temporarios do sistema",
        "Temporarios que o Windows nao removeu sozinho.",
        "",
    ),
    "Thumbnail Cache": (
        "Cache de miniaturas",
        "Miniaturas de fotos e videos. Sao recriadas ao abrir as pastas.",
        "",
    ),
    "Recycle Bin": (
        "Lixeira",
        "Arquivos que voce excluiu e ainda estao na Lixeira.",
        "Os arquivos da Lixeira nao poderao mais ser recuperados.",
    ),
    "Internet Cache Files": (
        "Cache de internet do sistema",
        "Cache do Internet Explorer / componentes web do Windows.",
        "",
    ),
    "Setup Log Files": (
        "Logs de instalacao",
        "Registros de instalacoes e atualizacoes ja concluidas.",
        "",
    ),
    "Windows Upgrade Log Files": (
        "Logs de atualizacao do Windows",
        "Registros de upgrades de versao ja concluidos.",
        "",
    ),
    "Old ChkDsk Files": (
        "Fragmentos recuperados pelo ChkDsk",
        "Pedacos de arquivos que o ChkDsk recuperou e quase nunca sao uteis.",
        "",
    ),
    "Upgrade Discarded Files": (
        "Arquivos descartados em upgrades",
        "Sobras de atualizacoes de versao do Windows.",
        "",
    ),
    "Downloaded Program Files": (
        "Controles ActiveX e applets Java",
        "Componentes antigos baixados por paginas web.",
        "",
    ),
    "Temporary Setup Files": (
        "Arquivos temporarios de instalacao",
        "Sobras de instaladores ja executados.",
        "",
    ),
    "RetailDemo Offline Content": (
        "Conteudo de demonstracao de loja",
        "Arquivos do modo demonstracao usado em lojas. Inutil em uso normal.",
        "",
    ),
}

# Marcados por padrao: alto retorno em espaco e baixo risco.
_DEFAULT_ON = {
    "Update Cleanup",
    "Delivery Optimization Files",
    "Windows Error Reporting Files",
    "Temporary Files",
    "Setup Log Files",
    "Windows Upgrade Log Files",
    "Old ChkDsk Files",
    "Upgrade Discarded Files",
    "Temporary Setup Files",
    "RetailDemo Offline Content",
    "Downloaded Program Files",
}


def list_handlers() -> list[dict]:
    """
    Handlers de limpeza disponiveis nesta maquina.

    Le o registro em vez de assumir uma lista fixa: o conjunto varia por
    versao do Windows e pelo que ha instalado.
    """
    out: list[dict] = []
    try:
        root = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, _VOLUME_CACHES)
    except OSError:
        return out

    try:
        i = 0
        while True:
            try:
                name = winreg.EnumKey(root, i)
            except OSError:
                break
            i += 1

            if name in _BLOCKED:
                continue

            label, desc, warning = _LABELS.get(
                name, (name, "Categoria de limpeza do Windows.", "")
            )
            out.append({
                "id": name,
                "label": label,
                "desc": desc,
                "warning": warning,
                "default": name in _DEFAULT_ON,
                "checked": name in _DEFAULT_ON,
            })
    finally:
        root.Close()

    out.sort(key=lambda h: (not h["default"], h["label"].lower()))
    return out


def _write_profile(selected: set[str]) -> int:
    """
    Escreve o perfil sageset no registro.

    E exatamente o que `cleanmgr /sageset:65535` faz pela janela: grava
    StateFlags<id> = 2 (marcado) ou 0 (desmarcado) em cada handler.
    """
    value_name = f"StateFlags{_SAGE_ID:04d}"
    written = 0
    try:
        root = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, _VOLUME_CACHES)
    except OSError:
        return 0

    try:
        i = 0
        names = []
        while True:
            try:
                names.append(winreg.EnumKey(root, i))
                i += 1
            except OSError:
                break

        for name in names:
            if name in _BLOCKED:
                flag = 0          # garante que nunca roda, mesmo se pedido
            else:
                flag = 2 if name in selected else 0
            try:
                k = winreg.OpenKey(root, name, 0, winreg.KEY_SET_VALUE)
                try:
                    winreg.SetValueEx(k, value_name, 0, winreg.REG_DWORD, flag)
                    if flag:
                        written += 1
                finally:
                    k.Close()
            except OSError:
                continue
    finally:
        root.Close()

    return written


class DeepCleanWorker(QThread):
    """
    Executa a limpeza profunda.

    Nao ha como obter progresso item a item do cleanmgr — ele nao reporta
    nada em modo silencioso. Por isso o worker sinaliza inicio e fim, e a
    UI avisa que a operacao pode demorar.
    """

    step_done = Signal(str, int)          # (label, bytes) — bytes sempre 0
    finished_deep = Signal(bool, str)     # (ok, mensagem)

    def __init__(self, selected: set[str], parent=None):
        super().__init__(parent)
        self._selected = set(selected or [])

    def run(self):
        if not self._selected:
            self.finished_deep.emit(False, "Nenhuma categoria selecionada.")
            return

        n = _write_profile(self._selected)
        if n == 0:
            self.finished_deep.emit(False, "Nao foi possivel gravar o perfil de limpeza.")
            return

        self.step_done.emit(f"Perfil gravado ({n} categorias)", 0)
        self.step_done.emit("Executando limpeza de disco (pode demorar varios minutos)", 0)

        try:
            r = subprocess.run(
                ["cleanmgr.exe", f"/sagerun:{_SAGE_ID}"],
                capture_output=True, creationflags=_NO_WINDOW, timeout=3600,
            )
            ok = r.returncode == 0
        except subprocess.TimeoutExpired:
            self.finished_deep.emit(False, "A limpeza excedeu 1 hora e foi interrompida.")
            return
        except Exception as e:
            self.finished_deep.emit(False, f"Falha ao executar: {type(e).__name__}")
            return

        self.finished_deep.emit(
            ok,
            "Limpeza profunda concluida. Reinicie o PC para liberar todo o espaco."
            if ok else "A limpeza terminou com erros.",
        )
