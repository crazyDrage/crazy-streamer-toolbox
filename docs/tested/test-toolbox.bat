@echo off
rem The test toolbox: a second toolbox on its own settings folder (temp\test_settings) and its own port (8855),
rem with a numbered flow for every box (Start + that box) and every trigger, so nothing has to be built first.
rem The numbers are the ones the test window shows (test-window.bat). What you set in a test flow stays.
rem It runs next to your own toolbox and never touches its settings. Another folder: test-toolbox.bat <folder>
setlocal
cd /d "%~dp0..\.."

if not exist ".venv\Scripts\python.exe" (
    echo No .venv found in %CD%
    echo Create it first: py -m venv .venv ^&^& .venv\Scripts\python.exe -m pip install -r requirements.txt
    pause
    exit /b 1
)

set "SETTINGS=%~1"
if "%SETTINGS%"=="" set "SETTINGS=%CD%\temp\test_settings"
set "PYTHONPATH=%CD%\src"

echo Writing the test flows into %SETTINGS%\flows ...
".venv\Scripts\python.exe" -m streamer_toolbox.devtools.tested flows "%SETTINGS%"
if errorlevel 1 (
    pause
    exit /b 1
)

rem its own page settings too, so the two toolboxes don't write the same file
set "NICEGUI_STORAGE_PATH=%SETTINGS%\.nicegui"
".venv\Scripts\python.exe" -m streamer_toolbox --settings "%SETTINGS%" --port 8855 --open window
if errorlevel 1 pause
