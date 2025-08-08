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

:: Launch the bot GUI
echo Launching bot GUI...
python Src\gui.py

:: Keep window open if there's an error
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Bot exited with error code %ERRORLEVEL%
    pause
)