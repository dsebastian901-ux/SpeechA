@echo off
setlocal
cd /d "%~dp0"
title Validacion r53 + GPT6 - pruebas de regresion
set "MRS_PYTHON=python"
where py >nul 2>&1
if not errorlevel 1 (
  py -3.10 --version >nul 2>&1
  if not errorlevel 1 set "MRS_PYTHON=py -3.10"
)
echo ================================================================
echo PRUEBAS DE REGRESION - NO MODIFICA CHECKPOINT NI AUDIOS
echo Para instalar pytest: %MRS_PYTHON% -m pip install -r requirements-dev.txt
echo ================================================================
%MRS_PYTHON% -m pytest -q tests\test_review_r53_exceptions_and_excel.py tests\test_review_r53_status_optimization.py
echo.
if errorlevel 1 (
  echo NO APROBADO: revise las fallas de prueba antes de integrar.
) else (
  echo Pruebas especificas completadas.
)
pause
