@echo off
rem The test window: the checklist of what has to be tested (docs\tested), in a browser tab of its own.
rem Keep it open next to the toolbox; it needs no running toolbox and stays open while that is restarted.
rem A tick is written into docs\tested at once. Another port: test-window.bat 8860
setlocal
cd /d "%~dp0..\.."

rem a downloaded build brings its own Python (python\); a copy of the code has a .venv
set "PY=python\python.exe"
if not exist "%PY%" set "PY=.venv\Scripts\python.exe"
if not exist "%PY%" (
    echo No Python found in %CD% ^(neither python\ nor .venv^)
    echo Create it first: py -m venv .venv ^&^& .venv\Scripts\python.exe -m pip install -r requirements.txt
    pause
    exit /b 1
)

set "PYTHONPATH=%CD%\src"
"%PY%" -m streamer_toolbox.devtools.tested window %*
if errorlevel 1 pause
