@echo off
:: Rush Royale Bot Installation - Python 3.13 Compatible
:: Enhanced installation script with better error handling

echo Installing Rush Royale Bot for Python 3.13...
echo ================================================

:: Check for Python installation
where python >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo Found Python installation
    python --version
    
    :: Check Python version (basic check)
    python -c "import sys; exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
    if %ERRORLEVEL% NEQ 0 (
        echo WARNING: Python 3.10+ recommended for best compatibility
    )
) else (
    echo ERROR: Python not found in PATH
    echo Please install Python 3.13 from https://python.org
    pause
    exit /b 1
)

:: Create virtual environment
echo Creating virtual environment...
if exist .bot_env (
    echo Removing existing virtual environment...
    rmdir /s /q .bot_env
)
python -m venv .bot_env

:: Activate virtual environment
echo Activating virtual environment...
call .bot_env\Scripts\activate.bat

:: Upgrade pip and setuptools
echo Upgrading pip and setuptools...
python -m pip install --upgrade pip setuptools wheel

:: Install requirements with better error handling
echo Installing dependencies (this may take a few minutes)...
pip install -r requirements.txt --timeout 300 --retries 3

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✅ Installation completed successfully!
    echo To run the bot GUI: launch_gui.bat
    echo To run the notebook: jupyter notebook RR_bot.ipynb
) else (
    echo.
    echo ❌ Installation failed!
    echo Try running: pip install -r requirements.txt --no-deps
    echo Or check requirements.txt for compatibility issues
)

echo.
pause