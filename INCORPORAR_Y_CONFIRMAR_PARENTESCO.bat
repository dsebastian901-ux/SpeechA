@echo off
setlocal
set "MRS_CONTACT_APP=%~dp0proyecto\MRS_Speech_Analytics_v3.6.19_Revision"
if not exist "%MRS_CONTACT_APP%\INCORPORAR_Y_CONFIRMAR_PARENTESCO.bat" (
    echo Extraiga el ZIP completo antes de ejecutar esta herramienta.
    echo No se encontro la carpeta proyecto junto a este archivo.
    pause
    exit /b 1
)
call "%MRS_CONTACT_APP%\INCORPORAR_Y_CONFIRMAR_PARENTESCO.bat"
