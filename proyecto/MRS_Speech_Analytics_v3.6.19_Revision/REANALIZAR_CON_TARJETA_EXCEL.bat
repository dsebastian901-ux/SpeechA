@echo off
setlocal
cd /d "%~dp0"
echo Reanalizar reglas y corregir identificadores de nombre_final con numero_de_tarjeta.
echo Aplica la politica de origen Excel autorizada. Conserva originales y confirmaciones.
echo No solicita lecturas adicionales ni ejecuta Whisper.
set "MRS_PYTHON=python"
py -3.10 --version >nul 2>&1
if not errorlevel 1 set "MRS_PYTHON=py -3.10"
%MRS_PYTHON% -X utf8 tools\reanalyze_checkpoint.py --use-excel-card
if errorlevel 1 echo No se completo el reanalisis. Revise el mensaje anterior.
pause
