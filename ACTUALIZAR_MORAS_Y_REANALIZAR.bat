@echo off
setlocal
set "MRS_MORA_APP=%~dp0proyecto\MRS_Speech_Analytics_v3.6.19_Revision"
if not exist "%MRS_MORA_APP%\ACTUALIZAR_MORAS_Y_REANALIZAR.bat" (
    echo Extraiga el ZIP completo antes de ejecutar esta herramienta.
    echo No se encontro la carpeta proyecto junto a este archivo.
    pause
    exit /b 1
)
call "%MRS_MORA_APP%\ACTUALIZAR_MORAS_Y_REANALIZAR.bat"
