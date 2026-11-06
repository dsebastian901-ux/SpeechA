@echo off
setlocal
set "MRS_IMPORT_APP=%~dp0proyecto\MRS_Speech_Analytics_v3.6.19_Revision"
if not exist "%MRS_IMPORT_APP%\INCORPORAR_LECTURAS_BLOQUE.bat" (
    echo Extraiga el ZIP completo antes de ejecutar esta herramienta.
    echo No se encontro la carpeta proyecto junto a este archivo.
    pause
    exit /b 1
)
call "%MRS_IMPORT_APP%\INCORPORAR_LECTURAS_BLOQUE.bat"
