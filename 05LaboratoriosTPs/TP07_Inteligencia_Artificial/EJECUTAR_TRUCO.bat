@echo off
REM ============================================================
REM   Truco Argentino con IA para Robot Unitree G1
REM   Lanza la Mesa Virtual interactiva de Truco.
REM ============================================================
cd /d "%~dp0"

set ARCHIVO=card_game_framework\main_cli.py

REM Buscar Python
set "PYTHON="
set "PYARGS="

py -3 -c "import sys" >nul 2>&1 && set "PYTHON=py"
if defined PYTHON set "PYARGS=-3"

if not defined PYTHON for /f "delims=" %%P in ('where python 2^>nul') do call :probar_python "%%P"

if not defined PYTHON for %%V in (313 312 311 310) do call :probar_ruta "%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe"
if not defined PYTHON for %%V in (313 312 311 310) do call :probar_ruta "%ProgramFiles%\Python%%V\python.exe"
if not defined PYTHON for %%V in (313 312 311 310) do call :probar_ruta "C:\Python%%V\python.exe"

if defined PYTHON goto :python_encontrado

echo.
echo    NO ENCUENTRO PYTHON
pause
exit /b 1

:probar_python
if defined PYTHON goto :eof
echo %~1| find /i "WindowsApps" >nul
if not errorlevel 1 goto :eof
"%~1" -c "import sys" >nul 2>&1 && set "PYTHON=%~1"
goto :eof

:probar_ruta
if defined PYTHON goto :eof
if not exist "%~1" goto :eof
"%~1" -c "import sys" >nul 2>&1 && set "PYTHON=%~1"
goto :eof

:python_encontrado

REM La mesa usa pygame. Si falta, se instala una sola vez para este usuario.
"%PYTHON%" %PYARGS% -c "import pygame" >nul 2>&1
if errorlevel 1 (
  echo    Instalando pygame, una sola vez...
  "%PYTHON%" %PYARGS% -m pip install --user pygame
)

"%PYTHON%" %PYARGS% "%ARCHIVO%" %*
echo.
pause
