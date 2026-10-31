@echo off
setlocal
set "MRS_REANALYZE_APP=%~dp0proyecto\MRS_Speech_Analytics_v3.6.19_Revision"
if not exist "%MRS_REANALYZE_APP%\REANALIZAR_CON_TARJETA_EXCEL.bat" (
    echo Extraiga el ZIP completo antes de ejecutar esta herramienta.
    echo No se encontro la carpeta proyecto junto a este archivo.
    pause
    exit /b 1
)
call "%MRS_REANALYZE_APP%\REANALIZAR_CON_TARJETA_EXCEL.bat"
