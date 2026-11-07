@echo off
setlocal
chcp 65001 >nul
set "PYTHONUTF8=1"
cd /d "%~dp0"
set "MRS_PYTHON=python"
py -3.10 --version >nul 2>&1
if not errorlevel 1 set "MRS_PYTHON=py -3.10"
%MRS_PYTHON% tools\reanalyze_checkpoint.py --copy-corrected-labels
if errorlevel 1 echo No se completo el proceso. Revise el mensaje anterior; los originales se conservan.
pause
