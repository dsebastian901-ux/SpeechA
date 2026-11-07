@echo off
setlocal
cd /d "%~dp0"
echo Registrar aceptacion de recado ya confirmada por el usuario.
echo Seleccione el checkpoint completo actual y el numero de llamada.
echo Se conservan los originales y las demas validaciones. No se ejecuta Whisper.
set "MRS_PYTHON=python"
py -3.10 --version >nul 2>&1
if not errorlevel 1 set "MRS_PYTHON=py -3.10"
%MRS_PYTHON% -X utf8 tools\confirm_recado_acceptance.py
if errorlevel 1 echo No se completo la confirmacion. Revise el mensaje anterior.
pause
