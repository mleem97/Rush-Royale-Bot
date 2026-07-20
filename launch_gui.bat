@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title RushBot

if not exist ".bot_env\Scripts\python.exe" (
    echo ERROR: Virtual environment not found. Run install.bat first.
    exit /b 1
)
if not exist "Src\gui.py" (
    echo ERROR: Src\gui.py was not found.
    exit /b 1
)

.bot_env\Scripts\python.exe Src\gui.py
if errorlevel 1 (
    echo.
    echo RushBot exited with error code %ERRORLEVEL%.
    pause
)
endlocal
