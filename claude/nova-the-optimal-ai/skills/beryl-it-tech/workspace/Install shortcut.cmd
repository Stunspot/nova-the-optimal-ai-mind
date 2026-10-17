@echo off
where py >nul 2>nul
if not errorlevel 1 (
  py -3 "%~dp0install_shortcut.py" %*
) else (
  python "%~dp0install_shortcut.py" %*
)
if errorlevel 1 (
  echo The shortcut was not created. Read the message above for the next step.
  pause
  exit /b 1
)
