@echo off
setlocal
cd /d "%~dp0"
call "%~dp0ENTORNO_MRS.bat" comprobar
set "MRS_EXIT_CODE=%errorlevel%"
if "%MRS_EXIT_CODE%"=="0" echo Puede abrir INICIAR_MRS.bat con el entorno verificado.
if not defined MRS_NO_PAUSE pause
exit /b %MRS_EXIT_CODE%
