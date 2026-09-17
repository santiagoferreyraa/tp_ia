@echo off
REM Truco contra el G1 con cartas de verdad: abre la pantalla del operador.
REM Si el simulador (INICIAR_SIMULADOR) esta abierto, el G1 saluda cuando canta.
cd /d "%~dp0"
call EJECUTAR_TRUCO.bat --operador
