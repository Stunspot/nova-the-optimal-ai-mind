@echo off
where py >nul 2>nul
if errorlevel 1 goto python
py -3 "%~dp0workspace\launch.py" %*
goto finish
:python
python "%~dp0workspace\launch.py" %*
:finish
if errorlevel 1 pause
