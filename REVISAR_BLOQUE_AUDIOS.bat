@echo off
setlocal
set "MRS_BLOCK_APP=%~dp0proyecto\MRS_Speech_Analytics_v3.6.19_Revision"
if not exist "%MRS_BLOCK_APP%\REVISAR_BLOQUE_AUDIOS.bat" (
    echo Extraiga el ZIP completo antes de ejecutar esta herramienta.
    echo No se encontro la carpeta proyecto junto a este archivo.
    pause
    exit /b 1
)
call "%MRS_BLOCK_APP%\REVISAR_BLOQUE_AUDIOS.bat"
