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
call "INICIAR_MRS.bat"
