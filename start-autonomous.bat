@echo off
echo Starting BioCatalyst Autonomous Controller...
cd /d "%~dp0"
powershell.exe -ExecutionPolicy Bypass -NoProfile -File "run-autonomous.ps1"
echo.
pause
