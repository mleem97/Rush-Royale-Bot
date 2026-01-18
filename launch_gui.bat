@echo off
setlocal enabledelayedexpansion
title Rush Royale Bot
cd /d "%~dp0"

if not exist ".bot_env\Scripts\python.exe" (
    echo [ERROR] Virtuelle Umgebung nicht gefunden. Bitte install.bat ausfuehren.
    pause
    exit /b 1
)

REM Use the new rush_bot package entry point
".bot_env\Scripts\python.exe" -m rush_bot.gui
if %errorlevel% NEQ 0 pause
