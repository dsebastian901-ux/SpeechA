@echo off
setlocal
cd /d "%~dp0"
echo Registrar un recado y contacto ya confirmados por el usuario.
echo Seleccione el checkpoint completo actual y el numero de llamada.
echo Confirme por separado entrega del recado y del contacto. Describa el mensaje escuchado.
echo Se conservan los originales y las demas validaciones. No se ejecuta Whisper.
set "MRS_PYTHON=python"
py -3.10 --version >nul 2>&1
if not errorlevel 1 set "MRS_PYTHON=py -3.10"
%MRS_PYTHON% -X utf8 tools\confirm_recado_acceptance.py --delivered-recado
if errorlevel 1 echo No se completo la confirmacion. Revise el mensaje anterior.
pause
