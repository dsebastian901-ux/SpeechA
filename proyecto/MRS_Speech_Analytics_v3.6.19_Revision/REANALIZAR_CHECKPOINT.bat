@echo off
setlocal
cd /d "%~dp0"
set "MRS_PYTHON=python"
py -3.10 --version >nul 2>&1
if not errorlevel 1 set "MRS_PYTHON=py -3.10"
%MRS_PYTHON% tools\reanalyze_checkpoint.py
if errorlevel 1 echo No se completo el reanalisis. Revise el mensaje anterior.
pause
