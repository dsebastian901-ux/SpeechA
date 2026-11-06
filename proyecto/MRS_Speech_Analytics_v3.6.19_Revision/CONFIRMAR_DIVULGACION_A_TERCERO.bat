@echo off
setlocal
cd /d "%~dp0"
echo Registrar divulgacion del gestor a un tercero ya confirmada por el usuario.
echo Seleccione el checkpoint completo actual y el numero de llamada.
echo Seleccione el fragmento y marque solo los dos hechos ya confirmados.
echo Se conservan los originales. No se ejecuta Whisper.
set "MRS_PYTHON=python"
py -3.10 --version >nul 2>&1
if not errorlevel 1 set "MRS_PYTHON=py -3.10"
%MRS_PYTHON% -X utf8 tools\confirm_privacy_disclosure.py
if errorlevel 1 echo No se completo la confirmacion. Revise el mensaje anterior.
pause
