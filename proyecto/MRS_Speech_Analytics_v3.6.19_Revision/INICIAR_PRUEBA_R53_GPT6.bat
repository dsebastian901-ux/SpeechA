@echo off
setlocal
cd /d "%~dp0"
title MRS Speech Analytics r53 + GPT6 - PRUEBA
echo ================================================================
echo MRS Speech Analytics - 3.6.19-r53-gpt6-test2
echo Version de prueba independiente. No sobrescribir r51 ni r53.
echo ================================================================
echo.
if not exist main.py (
  echo ERROR: La carpeta de instalacion esta incompleta.
  pause
  exit /b 1
)
set "MRS_PYTHON=python"
where py >nul 2>&1
if not errorlevel 1 (
  py -3.10 --version >nul 2>&1
  if not errorlevel 1 set "MRS_PYTHON=py -3.10"
)
%MRS_PYTHON% -m compileall -q app tools
if errorlevel 1 (
  echo ERROR FATAL: Existen archivos Python con errores de sintaxis.
  echo No se ejecutara el programa ni Whisper. Consulte a Codex.
  pause
  exit /b 1
)

call "INICIAR_MRS.bat"
