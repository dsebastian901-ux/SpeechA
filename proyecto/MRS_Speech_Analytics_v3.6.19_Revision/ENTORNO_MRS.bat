@echo off
setlocal DisableDelayedExpansion
cd /d "%~dp0"
set "MRS_MODE=%~1"
set "MRS_READY="
set "MRS_PYTHON_EXE="
set "MRS_PYTHON_VERSION="

rem MRS_PYTHON permite reutilizar un Python local indicado explicitamente.
if defined MRS_PYTHON call :try_file "%MRS_PYTHON%"
rem Primero el entorno activado, luego entornos locales y runtime portable.
if not defined MRS_READY if defined VIRTUAL_ENV call :try_file "%VIRTUAL_ENV%\Scripts\python.exe"
if not defined MRS_READY call :try_file "%~dp0..\..\.venv\Scripts\python.exe"
if not defined MRS_READY call :try_file "%~dp0..\..\venv\Scripts\python.exe"
if not defined MRS_READY call :try_file "%~dp0.venv\Scripts\python.exe"
if not defined MRS_READY call :try_file "%~dp0venv\Scripts\python.exe"
if not defined MRS_READY call :try_file "%~dp0..\..\runtime\python\python.exe"
if not defined MRS_READY call :try_file "%~dp0runtime\python\python.exe"
if defined MRS_READY goto :ready

rem PATH respeta tambien Python activado por VS Code u otro entorno local.
where python >nul 2>&1
if not errorlevel 1 call :try_path
if defined MRS_READY goto :ready
where py >nul 2>&1
if errorlevel 1 goto :unavailable
call :try_py -3.10
if not defined MRS_READY call :try_py -3.11
if not defined MRS_READY call :try_py -3.12
if not defined MRS_READY call :try_py -3
if not defined MRS_READY goto :unavailable

:ready
if /i "%MRS_MODE%"=="comprobar" exit /b 0
if defined MRS_PYTHON_VERSION goto :run_py
"%MRS_PYTHON_EXE%" "%~dp0main.py"
exit /b %errorlevel%

:run_py
py %MRS_PYTHON_VERSION% "%~dp0main.py"
exit /b %errorlevel%

:unavailable
echo.
echo No se encontro un Python local con todos los componentes de MRS.
echo Revise arriba los componentes faltantes y el Python comprobado.
echo En VS Code seleccione el entorno que ya usa para MRS, o prepare
echo una .venv con las dependencias de requirements.txt.
echo No se instalaron paquetes ni se modificaron usuarios, datos o modelos.
exit /b 2

:try_file
if not exist "%~1" exit /b 1
"%~1" "%~dp0tools\check_startup_environment.py"
if errorlevel 1 exit /b 1
set "MRS_PYTHON_EXE=%~1"
set "MRS_READY=1"
exit /b 0

:try_path
python "%~dp0tools\check_startup_environment.py"
if errorlevel 1 exit /b 1
set "MRS_PYTHON_EXE=python"
set "MRS_READY=1"
exit /b 0

:try_py
py %1 --version >nul 2>&1
if errorlevel 1 exit /b 1
py %1 "%~dp0tools\check_startup_environment.py"
if errorlevel 1 exit /b 1
set "MRS_PYTHON_VERSION=%1"
set "MRS_READY=1"
exit /b 0
