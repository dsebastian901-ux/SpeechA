@echo off
setlocal
cd /d "%~dp0"
echo Generar base de 95 llamadas con las diez lecturas ya existentes.
echo Se usa numero_de_tarjeta del Excel para corregir nombres, segun su instruccion previa.
echo No ejecuta Whisper ni modifica los archivos originales.
set "MRS_PYTHON=python"
py -3.10 --version >nul 2>&1
if not errorlevel 1 set "MRS_PYTHON=py -3.10"
%MRS_PYTHON% tools\rebuild_checkpoint_base.py --use-excel-card --expected-calls 95 --expected-readings 10
if errorlevel 1 echo Revise el mensaje anterior; no utilice una base incompleta.
pause
