@echo off
setlocal
set "MRS_REBUILD_APP=%~dp0proyecto\MRS_Speech_Analytics_v3.6.19_Revision"
if not exist "%MRS_REBUILD_APP%\RECONSTRUIR_BASE_R25.bat" (
    echo Extraiga el ZIP completo antes de ejecutar esta herramienta.
    echo No se encontro la carpeta proyecto junto a este archivo.
    pause
    exit /b 1
)
call "%MRS_REBUILD_APP%\RECONSTRUIR_BASE_R25.bat"
