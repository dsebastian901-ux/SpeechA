@echo off
setlocal
cd /d "%~dp0"
echo Incorporar lecturas y registrar un parentesco que el usuario ya confirmo.
echo Seleccione el checkpoint completo actual y luego revision_audios_bloque.json.
echo Despues indique el numero de llamada y el parentesco confirmado.
echo Los originales se conservan. No se ejecuta Whisper.
set "MRS_PYTHON=python"
py -3.10 --version >nul 2>&1
if not errorlevel 1 set "MRS_PYTHON=py -3.10"
%MRS_PYTHON% -X utf8 tools\import_audio_block_evidence.py --confirm-family
if errorlevel 1 echo No se completo la incorporacion. Revise el mensaje anterior.
pause
