@echo off
setlocal
cd /d "%~dp0"
echo Registrar advertencia en domicilio en 1-2 PV ya confirmada por el usuario.
echo Seleccione el checkpoint completo actual, la llamada y el fragmento.
echo Marque solo los dos hechos que ya comprobo en el audio.
echo Se conservan los originales. No se ejecuta Whisper.
set "MRS_PYTHON=python"
py -3.10 --version >nul 2>&1
if not errorlevel 1 set "MRS_PYTHON=py -3.10"
%MRS_PYTHON% -X utf8 tools\confirm_privacy_disclosure.py --home-warning
if errorlevel 1 echo No se completo la confirmacion. Revise el mensaje anterior.
pause
