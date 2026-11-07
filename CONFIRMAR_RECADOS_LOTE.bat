@echo off
setlocal
set "MRS_RECADO_APP=%~dp0proyecto\MRS_Speech_Analytics_v3.6.19_Revision"
if not exist "%MRS_RECADO_APP%\CONFIRMAR_RECADOS_LOTE.bat" (
    echo Extraiga el ZIP completo antes de ejecutar esta herramienta.
    pause
    exit /b 1
)
call "%MRS_RECADO_APP%\CONFIRMAR_RECADOS_LOTE.bat"
