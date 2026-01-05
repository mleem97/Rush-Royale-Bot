@echo off
:: Rush Royale Bot Launcher - Python 3.13 Compatible
title Rush Royale Bot

echo Starting Rush Royale Bot...
echo ============================

:: Check if virtual environment exists
if not exist ".bot_env\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found!
    echo Please run install.bat first
    pause
    exit /b 1
)

:: Activate virtual environment
echo Activating virtual environment...
call .bot_env\Scripts\activate.bat

:: Check if GUI files exist
if not exist "Src\gui.py" (
    echo ERROR: GUI files not found!
    echo Please ensure all files are in the correct directory
    pause
    exit /b 1
)

:: Launch the bot GUI - Try modern first, fallback to legacy
echo Launching bot GUI...
echo.

:: Try Modern GUI first (requires CustomTkinter)
echo Attempting to launch GUI...
python -c "import customtkinter" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo Using GUI with Tkinter
    python -m Src.gui_modern
    if %ERRORLEVEL% EQU 0 goto :success
    echo Loading GUI failed, trying legacy...
)

:: Fallback to Legacy GUI
echo Using Legacy GUI
python Src\gui.py

:success

:: Keep window open if there's an error
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Bot exited with error code %ERRORLEVEL%
    pause
)