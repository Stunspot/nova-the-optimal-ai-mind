@echo off
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  python -B -X utf8 host.py %*
) else (
  py -3 -B -X utf8 host.py %*
)
if errorlevel 1 pause
