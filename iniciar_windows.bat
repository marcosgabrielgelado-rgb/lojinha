@echo off
setlocal
cd /d "%~dp0"
title Magrao Imports - Loja
if not exist ".venv\Scripts\python.exe" (
    echo Execute instalar_windows.bat primeiro.
    pause
    exit /b 1
)
if not exist ".env" (
    echo Execute configurar_admin_windows.bat primeiro para criar o acesso administrativo.
    pause
    exit /b 1
)
echo Iniciando Magrao Imports...
echo A loja abre em http://127.0.0.1:5000
echo Painel administrativo: http://127.0.0.1:5000/admin
echo Mantenha esta janela aberta enquanto usar o site.
echo.
".venv\Scripts\python.exe" app.py
pause
