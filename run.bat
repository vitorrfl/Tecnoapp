@echo off
REM TecnoApp - atalho de execucao
REM Usa o Python do venv (o "python" solto cai no alias da Microsoft Store).
cd /d "%~dp0app"
"%~dp0.venv\Scripts\python.exe" app3.py
if errorlevel 1 (
    echo.
    echo [ERRO] O app terminou com erro. Pressione uma tecla para fechar.
    pause >nul
)
