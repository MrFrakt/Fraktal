@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_gateway.ps1"
exit /b %ERRORLEVEL%
