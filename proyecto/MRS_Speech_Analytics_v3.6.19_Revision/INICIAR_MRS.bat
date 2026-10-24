@echo off
cd /d "%~dp0"
where py >nul 2>&1
if %errorlevel%==0 (
  py -3.10 --version >nul 2>&1
  if %errorlevel%==0 (
    py -3.10 main.py
    goto :end
  )
)
python main.py
:end
if not %errorlevel%==0 pause
