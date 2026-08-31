"""
Reinicializacao com retorno ao app.

Regra de produto (README): o app NUNCA reinicia sozinho. O reboot so
acontece se o usuario clicar explicitamente — aqui apenas executamos a
decisao dele.

Para o app voltar depois, usa-se RunOnce: uma chave que o Windows executa
UMA vez na proxima inicializacao e apaga sozinha. Diferente de Run, nao
deixa o app na inicializacao permanente — seria contraditorio um app que
prega remover bloat de startup virar um item de startup.
"""

from __future__ import annotations

import os
import subprocess
import sys
import winreg

_RUNONCE = r"Software\Microsoft\Windows\CurrentVersion\RunOnce"
_KEY_NAME = "TecnoApp_PosReboot"
_NO_WINDOW = subprocess.CREATE_NO_WINDOW


def _launch_command() -> str:
    """
    Comando que reabre o app.

    Empacotado (PyInstaller): o proprio .exe.
    Em desenvolvimento: o python do venv + app3.py.
    """
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app3.py")
    return f'"{sys.executable}" "{script}"'


def schedule_return(flag: str = "gamer") -> bool:
    """
    Agenda a reabertura do app na proxima inicializacao.

    RunOnce roda uma vez e se remove; nada fica permanente na maquina.
    """
    try:
        k = winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, _RUNONCE, 0, winreg.KEY_SET_VALUE)
        try:
            winreg.SetValueEx(k, _KEY_NAME, 0, winreg.REG_SZ,
                              f"{_launch_command()} --pos-reboot={flag}")
            return True
        finally:
            k.Close()
    except OSError:
        return False


def cancel_return() -> bool:
    """Remove o agendamento, se existir."""
    try:
        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUNONCE, 0, winreg.KEY_SET_VALUE)
        try:
            winreg.DeleteValue(k, _KEY_NAME)
            return True
        except OSError:
            return False
        finally:
            k.Close()
    except OSError:
        return False


def reboot_now(delay_seconds: int = 5) -> bool:
    """
    Reinicia o computador.

    So deve ser chamado a partir de uma acao explicita do usuario. O delay
    da tempo do app fechar e da uma janela para cancelar via
    `shutdown /a`.
    """
    try:
        subprocess.Popen(
            ["shutdown", "/r", "/t", str(max(0, int(delay_seconds))),
             "/c", "Reiniciando para aplicar os tweaks do TecnoApp."],
            creationflags=_NO_WINDOW, close_fds=True,
        )
        return True
    except Exception:
        return False


def abort_reboot() -> bool:
    """Cancela um reboot agendado que ainda esteja na contagem."""
    try:
        subprocess.run(["shutdown", "/a"], capture_output=True,
                       creationflags=_NO_WINDOW, timeout=10)
        return True
    except Exception:
        return False


def came_from_reboot() -> str | None:
    """
    Le o --pos-reboot=<flag> da linha de comando.

    Retorna a flag ('gamer') quando o app foi reaberto pelo RunOnce, ou
    None numa abertura normal.
    """
    for arg in sys.argv[1:]:
        if arg.startswith("--pos-reboot="):
            return arg.split("=", 1)[1] or None
    return None
