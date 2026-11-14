@echo off
setlocal
cd /d "%~dp0"
title MRS Speech Analytics - Reanalizar sin Whisper
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" "REANALIZAR_CHECKPOINT_SIN_WHISPER.py" %*
) else (
  where py >nul 2>&1
  if not errorlevel 1 (
    py -3 "REANALIZAR_CHECKPOINT_SIN_WHISPER.py" %*
  ) else (
    python "REANALIZAR_CHECKPOINT_SIN_WHISPER.py" %*
  )
)
echo.
pause
