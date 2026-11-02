@echo off
setlocal
cd /d "%~dp0"
echo Recuperar solo mora faltante desde el Excel y reanalizar en una copia.
echo Primero seleccione Checkpoint_r27_Recuperado.json y despues Calidad Noviembre.xlsx.
echo Se cotejan archivo, tarjeta y datos de cuenta. No se ejecuta Whisper.
set "MRS_PYTHON=python"
py -3.10 --version >nul 2>&1
if not errorlevel 1 set "MRS_PYTHON=py -3.10"
%MRS_PYTHON% -X utf8 tools\reanalyze_checkpoint.py --fill-mora-from-excel
if errorlevel 1 echo No se completo la actualizacion. Revise el mensaje anterior; los originales no cambian.
pause
