@echo off
rem The test window: the checklist of what has to be tested (docs\tested), in a browser tab of its own,
rem and next to it the test toolbox (see test-toolbox.bat): a second toolbox on temp\test_settings, port 8855,
rem the same toolbox as start.bat. Both run in this console; one stops, both stop.
rem The test window stays open while the toolbox is restarted. A tick is written into docs\tested at once.
rem Another port for the test window: test-window.bat 8860
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

set "SETTINGS=%CD%\temp\test_settings"
set "PYTHONPATH=%CD%\src"

rem The test window starts the test toolbox itself and is tied to it: Ctrl+C, closing this console or closing
rem the toolbox's window stops both. (Not start /b: that switches Ctrl+C off, and the toolbox stayed running.)
"%PY%" -m streamer_toolbox.devtools.tested window --toolbox "%SETTINGS%" %*
if errorlevel 1 pause
