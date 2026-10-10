@echo off
rem Start streamer-toolbox (GUI + HTTP API) and open the dashboard in its own window (Edge/Chrome app window).
rem start-browser.bat opens it as a browser tab instead. Extra options are passed on,
rem e.g. start.bat --port 8851 --config config\other.toml   or   start.bat --open none
rem Closing the dashboard window stops the toolbox (SAMMI and Kit can't reach it then). start-browser.bat keeps it
rem running after the tab is closed. Settings -> Restart starts it again; the window stays open.
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo No .venv found in %CD%
    echo Create it first: py -m venv .venv ^&^& .venv\Scripts\python.exe -m pip install -r requirements.txt
    pause
    exit /b 1
)

set "PYTHONPATH=%~dp0src"
".venv\Scripts\python.exe" -m streamer_toolbox --open window %*

rem keep the console open if the toolbox stopped with an error, so the message can be read
if errorlevel 1 pause
