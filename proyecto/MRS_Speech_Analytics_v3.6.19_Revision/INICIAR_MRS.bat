@echo off
setlocal
cd /d "%~dp0"
call "%~dp0ENTORNO_MRS.bat" iniciar
set "MRS_EXIT_CODE=%errorlevel%"
if not "%MRS_EXIT_CODE%"=="0" if not defined MRS_NO_PAUSE pause
exit /b %MRS_EXIT_CODE%
