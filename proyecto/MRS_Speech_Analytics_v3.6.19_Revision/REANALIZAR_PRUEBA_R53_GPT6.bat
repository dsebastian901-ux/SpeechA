@echo off
setlocal
cd /d "%~dp0"
title MRS r53 + GPT6 - Reanalizar sin Whisper
echo ================================================================
echo REANALISIS DE REGLAS - SIN WHISPER - SOLO PRUEBA r53+GPT6
echo Seleccione el checkpoint original o una copia. No se sobrescribe.
echo ================================================================
echo.
set "MRS_PYTHON=python"
where py >nul 2>&1
if not errorlevel 1 (
  py -3.10 --version >nul 2>&1
  if not errorlevel 1 set "MRS_PYTHON=py -3.10"
)
%MRS_PYTHON% tools\reanalyze_checkpoint.py
if errorlevel 1 (
  echo ERROR en el reanalisis. Revise el mensaje anterior.
) else (
  echo Reanalisis terminado; consulte la carpeta nueva indicada.
)
echo.
pause
