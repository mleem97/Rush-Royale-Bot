@echo off
setlocal enabledelayedexpansion
title Rush Royale Bot - Launcher

:: 1. Ensure we're in the correct directory (important for shortcuts!)
cd /d "%~dp0"

echo ============================================
echo    Rush Royale Bot
echo ============================================
echo.

:: 2. Define path to Python executable within venv
set "VENV_PYTHON=.bot_env\Scripts\python.exe"
set "MAIN_SCRIPT=Src\gui.py"

:: 3. Check if virtual environment exists (Better check on exe instead of activate.bat)
if not exist "!VENV_PYTHON!" (
    color 0C
    echo [ERROR] Virtual environment not found!
    echo Path searched: !VENV_PYTHON!
    echo.
    echo Please run 'install.bat' first.
    echo.
    pause
    exit /b 1
)

:: 4. Check if main script exists
if not exist "!MAIN_SCRIPT!" (
    color 0C
    echo [ERROR] File '!MAIN_SCRIPT!' not found!
    echo Are you sure you're in the correct directory?
    echo Current directory: %CD%
    echo.
    pause
    exit /b 1
)

:: 5. Start
echo Starting Bot GUI...
title Rush Royale Bot - Running...

:: We call Python directly from venv.
:: This is more stable than trusting 'activate.bat'.
"!VENV_PYTHON!" "!MAIN_SCRIPT!"

:: 6. Error handling after termination
set "EXIT_CODE=!errorlevel!"
if !EXIT_CODE! NEQ 0 (
    color 0C
    title Rush Royale Bot - Crashed
    echo.
    echo ============================================
    echo  BOT TERMINATED WITH ERROR (Code: !EXIT_CODE!)
    echo ============================================
    echo.
    echo Please take a screenshot of the errors above.
    pause
) else (
    echo.
    echo Bot terminated normally.
)
