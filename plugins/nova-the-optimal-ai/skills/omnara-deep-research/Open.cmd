@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel% equ 0 (py -3 "%~dp0workspace\open.py" %*) else (python "%~dp0workspace\open.py" %*)
if errorlevel 1 pause
