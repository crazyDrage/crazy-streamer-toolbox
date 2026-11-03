@echo off
rem The test toolbox: a second toolbox on its own settings folder (temp\test_settings) and its own port (8855),
rem the same toolbox as start.bat, nothing added to the folder.
rem It runs next to your own toolbox and never touches its settings. Another folder: test-toolbox.bat <folder>
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

set "SETTINGS=%~1"
if "%SETTINGS%"=="" set "SETTINGS=%CD%\temp\test_settings"
set "PYTHONPATH=%CD%\src"

rem its own page settings too, so the two toolboxes don't write the same file
set "NICEGUI_STORAGE_PATH=%SETTINGS%\.nicegui"
"%PY%" -m streamer_toolbox --settings "%SETTINGS%" --port 8855 --open window
if errorlevel 1 pause
