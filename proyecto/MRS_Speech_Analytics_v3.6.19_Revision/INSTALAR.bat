@echo off
setlocal
cd /d "%~dp0"
title Instalador MRS Speech Analytics v3.5.7
echo ============================================================
echo       MRS SPEECH ANALYTICS PROFESSIONAL v3.5.7
echo ============================================================
echo.
where py >nul 2>&1
if %errorlevel%==0 (
  py -3.10 --version >nul 2>&1
  if %errorlevel%==0 (
    set "PY=py -3.10"
    goto :python_ok
  )
)
where python >nul 2>&1
if not %errorlevel%==0 goto :no_python
for /f "tokens=2" %%V in ('python --version 2^>^&1') do set "PYVER=%%V"
echo Python detectado: %PYVER%
set "PY=python"
:python_ok
echo.
echo [1/4] Verificando Python...
%PY% -c "import sys; assert sys.version_info[:2] == (3,10), 'Se recomienda Python 3.10 de 64 bits'" >nul 2>&1
if not %errorlevel%==0 (
  echo ADVERTENCIA: Esta instalacion fue preparada y probada para Python 3.10.
  echo Si tiene Python 3.10 instalado, ejecute de nuevo usando py -3.10.
  pause
  exit /b 1
)
echo [2/4] Actualizando pip...
%PY% -m pip install --upgrade pip
if not %errorlevel%==0 goto :pip_error
echo [3/4] Instalando dependencias...
%PY% -m pip install -r requirements.txt
if not %errorlevel%==0 goto :pip_error
echo [4/4] Verificando componentes...
%PY% -c "import customtkinter; from PIL import Image; import openpyxl; import av; import imageio_ffmpeg; from faster_whisper import WhisperModel; print('Dependencias OK')"
if not %errorlevel%==0 goto :pip_error
echo.
echo ============================================================
echo INSTALACION COMPLETADA CORRECTAMENTE
echo Use INICIAR_MRS.bat para abrir el programa.
echo ============================================================
pause
exit /b 0
:no_python
echo.
echo ERROR: No se encontro Python.
echo Instale Python 3.10 de 64 bits y marque Add Python to PATH.
pause
exit /b 1
:pip_error
echo.
echo ERROR: No se pudieron instalar o verificar las dependencias.
echo Revise su conexion a Internet y vuelva a ejecutar INSTALAR.bat.
pause
exit /b 1
