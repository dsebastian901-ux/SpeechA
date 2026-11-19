@echo off
setlocal
cd /d "%~dp0"
if exist "%~dp0..\..\runtime\python\python.exe" (
    echo Esta version ya incluye Python, dependencias y Whisper local.
    echo No necesita descargar ni instalar componentes adicionales.
    echo Abra INICIAR_MRS.bat o MRS_Speech_Analytics.exe en la carpeta principal.
    pause
    exit /b 0
)
set "MRS_PYTHON=python"
py -3.10 --version >nul 2>&1
if not errorlevel 1 set "MRS_PYTHON=py -3.10"
%MRS_PYTHON% -c "import customtkinter, faster_whisper, openpyxl, docx, cryptography" >nul 2>&1
if errorlevel 1 (
    echo Faltan componentes locales. Utilice el ZIP portable completo de esta revision.
    echo Ese paquete incluye los componentes necesarios y funciona sin internet.
    pause
    exit /b 1
)
echo La instalacion local tiene los componentes necesarios.
echo Puede abrir INICIAR_MRS.bat. No se realizaron descargas.
pause
