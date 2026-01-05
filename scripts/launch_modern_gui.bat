@echo off
echo ========================================
echo Rush Royale Bot - Modern GUI
echo Python 3.13 Required
echo ========================================
echo.

REM Check for Python 3.13
python --version 2>nul | findstr /C:"3.13" >nul
if %errorlevel% neq 0 (
    echo WARNING: Python 3.13 recommended!
    echo Current Python version:
    python --version
    echo.
)

REM Change to project root directory
cd /d "%~dp0\.."

REM Activate virtual environment if exists
if exist ".venv313\Scripts\activate.bat" (
    call .venv313\Scripts\activate.bat
    echo Using virtual environment: .venv313
) else if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
    echo Using virtual environment: .venv
)

echo.
echo Starting Modern GUI...
echo.

REM Run the modern GUI
python -m Src.gui_modern

pause