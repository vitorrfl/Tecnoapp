"""
Instancia unica do TecnoApp.

Duas instancias mexendo nos mesmos tweaks e no mesmo snapshot em
%APPDATA% podem corromper o estado do Modo Gamer: uma aplica enquanto a
outra reverte, e o snapshot que deveria permitir voltar atras fica
inconsistente.

Usa um mutex nomeado do Windows — o mecanismo padrao para isso. Ao
contrario de arquivo de lock, o SO libera automaticamente se o processo
morrer (crash, kill, queda de energia), entao nao ha lock orfao travando
a proxima abertura.

O nome fica em Global\\ para valer entre sessoes: sem isso, o app
elevado e o normal viveriam em namespaces diferentes e a checagem falharia
justamente por causa da auto-elevacao.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes

_MUTEX_NAME = "Global\\TecnoApp_SingleInstance_A7F3B2C1"
_ERROR_ALREADY_EXISTS = 183

# Mantido em escopo de modulo: se o handle for coletado, o mutex e
# liberado e a protecao cai no meio da execucao.
_handle = None


def acquire() -> bool:
    """
    Tenta tomar posse da instancia unica.

    True  = esta e a unica instancia, pode seguir.
    False = ja ha outra rodando.
    """
    global _handle

    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateMutexW.argtypes = [wintypes.LPCVOID, wintypes.BOOL, wintypes.LPCWSTR]
        kernel32.CreateMutexW.restype = wintypes.HANDLE

        _handle = kernel32.CreateMutexW(None, True, _MUTEX_NAME)
        erro = ctypes.get_last_error()

        if not _handle:
            # Sem handle nao da para garantir nada; deixa abrir em vez de
            # travar o app por uma falha do proprio mecanismo.
            return True

        if erro == _ERROR_ALREADY_EXISTS:
            return False
        return True
    except Exception:
        # Qualquer falha inesperada nao pode impedir o app de abrir.
        return True


def is_running() -> bool:
    """
    Ha outra instancia rodando?

    Diferente de acquire(), NAO toma posse: abre o mutex existente e fecha
    em seguida. Serve para o processo nao-elevado checar antes de disparar
    a elevacao, sem roubar a posse de quem ja esta rodando.
    """
    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenMutexW.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]
        kernel32.OpenMutexW.restype = wintypes.HANDLE

        SYNCHRONIZE = 0x00100000
        h = kernel32.OpenMutexW(SYNCHRONIZE, False, _MUTEX_NAME)
        if h:
            kernel32.CloseHandle(h)
            return True
        return False
    except Exception:
        return False


def release() -> None:
    """Libera o mutex. O Windows tambem libera sozinho ao fim do processo."""
    global _handle
    if not _handle:
        return
    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.ReleaseMutex(_handle)
        kernel32.CloseHandle(_handle)
    except Exception:
        pass
    finally:
        _handle = None


def focus_existing() -> bool:
    """
    Traz a janela da instancia que ja roda para a frente.

    Sem isso o usuario clica no atalho, nada acontece, e ele conclui que o
    app nao abriu — pior que abrir uma segunda janela.
    """
    try:
        user32 = ctypes.WinDLL("user32", use_last_error=True)

        titulo_alvo = "Tecnosup"
        encontrada = []

        WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

        def _cb(hwnd, _lparam):
            if not user32.IsWindowVisible(hwnd):
                return True
            n = user32.GetWindowTextLengthW(hwnd)
            if n <= 0:
                return True
            buf = ctypes.create_unicode_buffer(n + 1)
            user32.GetWindowTextW(hwnd, buf, n + 1)
            if titulo_alvo.lower() in buf.value.lower():
                encontrada.append(hwnd)
                return False
            return True

        user32.EnumWindows(WNDENUMPROC(_cb), 0)
        if not encontrada:
            return False

        hwnd = encontrada[0]
        SW_RESTORE = 9
        if user32.IsIconic(hwnd):
            user32.ShowWindow(hwnd, SW_RESTORE)
        user32.SetForegroundWindow(hwnd)
        return True
    except Exception:
        return False
