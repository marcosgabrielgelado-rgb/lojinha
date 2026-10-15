@echo off
setlocal
cd /d "%~dp0"
title Magrao Imports - Configurar administrador
if not exist ".venv\Scripts\python.exe" (
    echo Execute instalar_windows.bat primeiro.
    pause
    exit /b 1
)
echo Crie seu login e uma senha forte para o painel administrativo.
echo A senha nao sera exibida enquanto voce digita.
echo.
".venv\Scripts\python.exe" setup_admin.py
pause
