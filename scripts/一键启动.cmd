@echo off
rem One-click launcher for local debug deployment.
rem This file is ASCII-only on purpose: all Chinese messages are printed by
rem scripts\launch-localtest.ps1 so that Windows batch encoding never matters.
setlocal

set "PS1=%~dp0scripts\launch-localtest.ps1"
if not exist "%PS1%" set "PS1=%~dp0launch-localtest.ps1"

if not exist "%PS1%" (
    echo [ERROR] launch-localtest.ps1 not found.
    pause
    exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%PS1%"
exit /b %errorlevel%
