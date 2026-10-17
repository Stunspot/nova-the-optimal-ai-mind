@echo off
where py >nul 2>nul
if errorlevel 1 goto python
py -3 "%~dp0scripts\giles.py" %* serve
goto finish
:python
python "%~dp0scripts\giles.py" %* serve
:finish
if errorlevel 1 pause
