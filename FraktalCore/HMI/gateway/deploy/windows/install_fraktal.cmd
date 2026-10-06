@echo off
rem IExpress AppLaunched entry point. Runs the WinForms component wizard, or a
rem silent install when components/endpoints are passed on the command line.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0fraktal_wizard.ps1" %*
exit /b %ERRORLEVEL%
