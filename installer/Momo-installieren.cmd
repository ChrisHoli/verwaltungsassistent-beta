@echo off
rem Momo installieren - Doppelklick genuegt.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0installieren.ps1" %*
echo.
pause
