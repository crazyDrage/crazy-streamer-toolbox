@echo off
rem The test window: the checklist of what has to be tested (docs\tested), in a browser tab of its own,
rem and next to it the test toolbox (see test-toolbox.bat): a second toolbox on temp\test_settings, port 8855,
rem with a numbered flow for every box. Both run in this console: closing it closes both.
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

echo Writing the test flows into %SETTINGS%\flows ...
"%PY%" -m streamer_toolbox.devtools.tested flows "%SETTINGS%"
if errorlevel 1 (
    pause
    exit /b 1
)

rem start /b keeps the test toolbox in this console, so closing the console (or Ctrl+C) stops it too.
rem Its own page settings, so the two toolboxes don't write the same file; only the toolbox gets them.
setlocal
set "NICEGUI_STORAGE_PATH=%SETTINGS%\.nicegui"
start "" /b "%PY%" -m streamer_toolbox --settings "%SETTINGS%" --port 8855 --open window
endlocal

"%PY%" -m streamer_toolbox.devtools.tested window %*
if errorlevel 1 pause
