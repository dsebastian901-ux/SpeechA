@echo off
setlocal
cd /d "%~dp0"
set "MRS_PYTHON=python"
py -3.10 --version >nul 2>&1
if not errorlevel 1 set "MRS_PYTHON=py -3.10"
%MRS_PYTHON% tools\import_checkpoint_reviews.py
if errorlevel 1 echo No se incorporaron las validaciones. Revise el mensaje anterior.
pause
