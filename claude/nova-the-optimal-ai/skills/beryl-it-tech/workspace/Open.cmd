@echo off
where py >nul 2>nul
if not errorlevel 1 (
  py -3 "%~dp0launch.py" %*
) else (
  python "%~dp0launch.py" %*
)
if errorlevel 1 (
  echo.
  echo Beryl Repair Companion could not open. Python 3.10 or newer is required.
  echo Install Python from https://www.python.org/downloads/ and retry.
  pause
)
