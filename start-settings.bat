@echo off
rem start-settings: a small window to start the toolbox with (how it opens, its status, Open / Restart / Stop,
rem backups of the settings), with a tray icon next to the clock. No black console window.
rem Options are passed on, e.g. start-settings.bat --settings temp\test_settings --port 8855
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" (
    echo No .venv found in %CD%: create it first, see start.bat
    pause
    exit /b 1
)
set "PYTHONPATH=%~dp0src"
start "" ".venv\Scripts\pythonw.exe" -m streamer_toolbox.starter %*
