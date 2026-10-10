@echo off
rem The running toolbox from a terminal: it calls the toolbox's API.
rem   toolbox list            toolbox list obs.*            toolbox info hello.greet
rem   toolbox run hello.greet name=chat
rem The toolbox itself has to be running (start.bat). More: toolbox --help
setlocal
set "PYTHONPATH=%~dp0src"
"%~dp0.venv\Scripts\python.exe" -m streamer_toolbox.cli %*
