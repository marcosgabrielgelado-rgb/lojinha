@echo off
setlocal
cd /d "%~dp0"
title Magrao Imports - Instalacao

echo ========================================
echo   MAGRAO IMPORTS - INSTALACAO
echo ========================================
echo.

where py >nul 2>&1
if errorlevel 1 goto no_python
py -3 --version >nul 2>&1
if errorlevel 1 goto no_python

if not exist ".venv\Scripts\python.exe" (
    echo Criando ambiente Python...
    py -3 -m venv .venv
    if errorlevel 1 goto venv_error
)

echo Atualizando ferramentas de instalacao...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto pip_error

echo.
echo Instalando bibliotecas do site...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto install_error

echo.
echo Instalacao concluida!
echo Agora execute configurar_admin_windows.bat para criar seu login e senha.
echo Depois execute iniciar_windows.bat para abrir a loja.
echo.
pause
exit /b 0

:no_python
echo ERRO: Python 3 nao foi encontrado.
echo Instale Python 3.11 ou superior em https://www.python.org/downloads/windows/
echo Durante a instalacao, marque a opcao para adicionar Python ao PATH.
echo Depois feche esta janela e execute este arquivo novamente.
pause
exit /b 1

:venv_error
echo ERRO: nao foi possivel criar o ambiente Python.
echo Tente reinstalar Python 3.11 ou superior e execute novamente.
pause
exit /b 1

:pip_error
echo ERRO ao atualizar pip. Verifique sua conexao com a internet e tente novamente.
pause
exit /b 1

:install_error
echo ERRO ao instalar as dependencias. Verifique a internet e tente novamente.
pause
exit /b 1
