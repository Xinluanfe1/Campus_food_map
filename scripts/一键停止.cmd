@echo off
rem Stop script for local debug deployment.
rem ASCII-only on purpose; Chinese messages come from scripts\stop-localtest.ps1.
setlocal

set "PS1=%~dp0scripts\stop-localtest.ps1"
if not exist "%PS1%" set "PS1=%~dp0stop-localtest.ps1"

if not exist "%PS1%" (
    echo [ERROR] stop-localtest.ps1 not found.
    pause
    exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%PS1%"
exit /b %errorlevel%
