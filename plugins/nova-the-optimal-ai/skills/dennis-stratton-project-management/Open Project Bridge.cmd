@echo off
where py >nul 2>nul
if errorlevel 1 goto python
py -3 "%~dp0..\nova-operations\scripts\nova_estate.py" run project-bridge -- %*
goto finish
:python
python "%~dp0..\nova-operations\scripts\nova_estate.py" run project-bridge -- %*
:finish
if errorlevel 1 pause
