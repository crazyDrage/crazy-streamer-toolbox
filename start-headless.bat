@echo off
rem Start streamer-toolbox without any window (headless): open it in any browser or on your phone, at the
rem address in this console (http://127.0.0.1:8850 unless the port was changed). Uses no window memory.
rem Closing this console (or Ctrl+C) stops the toolbox.
echo The toolbox runs without a window: open http://127.0.0.1:8850 (or your own port) in any browser.
call "%~dp0start.bat" --open none %*
