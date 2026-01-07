@echo off
setlocal enabledelayedexpansion
title Rush Royale Bot
cd /d "%~dp0"

if not exist ".bot_env\Scripts\python.exe" (
    echo [ERROR] Virtuelle Umgebung nicht gefunden. Bitte install.bat ausfuehren.
    pause
    exit /b 1
)

".bot_env\Scripts\python.exe" "Src\gui.py"
if %errorlevel% NEQ 0 pause
