@echo off
setlocal
cd /d "%~dp0"
echo Registrar varias confirmaciones de recado en una sola operacion.
echo Seleccione el checkpoint y escriba las llamadas ya comprobadas en la ventana.
echo Se genera un solo checkpoint final y Excel. No se ejecuta Whisper.
set "MRS_PYTHON=python"
py -3.10 --version >nul 2>&1
if not errorlevel 1 set "MRS_PYTHON=py -3.10"
%MRS_PYTHON% -X utf8 tools\confirm_recados_batch.py
if errorlevel 1 echo No se completo la operacion. Revise el mensaje anterior.
pause
