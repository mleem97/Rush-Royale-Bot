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

:: Ensure scrcpy exists in .scrcpy (download if missing)
echo.
echo Checking scrcpy in .scrcpy ...
set "SCRCPY_VERSION=3.3.1"
set "SCRCPY_ZIP=scrcpy-win64-v%SCRCPY_VERSION%.zip"
set "SCRCPY_DIR=scrcpy-win64-v%SCRCPY_VERSION%"
set "SCRCPY_URL=https://github.com/Genymobile/scrcpy/releases/download/v%SCRCPY_VERSION%/scrcpy-win64-v%SCRCPY_VERSION%.zip"

if exist ".scrcpy\adb.exe" (
    echo Found scrcpy: .scrcpy\adb.exe
) else (
    echo scrcpy not found. Downloading %SCRCPY_ZIP% ...
    where powershell >nul 2>&1
    if %ERRORLEVEL% NEQ 0 (
        echo ERROR: PowerShell is required to download and extract scrcpy.
        echo Please install scrcpy manually: %SCRCPY_URL%
        pause
        exit /b 1
    )

    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
        "$ErrorActionPreference='Stop'; " ^
        "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; " ^
        "Invoke-WebRequest -Uri '%SCRCPY_URL%' -OutFile '%SCRCPY_ZIP%';"
    if not exist "%SCRCPY_ZIP%" (
        echo ERROR: Download failed: %SCRCPY_ZIP%
        pause
        exit /b 1
    )

    echo Extracting %SCRCPY_ZIP% ...
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
        "$ErrorActionPreference='Stop'; " ^
        "Expand-Archive -Path '%SCRCPY_ZIP%' -DestinationPath '.' -Force;"
    if not exist "%SCRCPY_DIR%" (
        echo ERROR: Extracted folder not found: %SCRCPY_DIR%
        echo Please extract the zip manually and rename the folder to .scrcpy
        pause
        exit /b 1
    )

    if exist ".scrcpy" (
        echo Removing existing .scrcpy ...
        rmdir /s /q ".scrcpy"
    )

    echo Renaming %SCRCPY_DIR% to .scrcpy ...
    ren "%SCRCPY_DIR%" ".scrcpy"
    if exist "%SCRCPY_ZIP%" del /f /q "%SCRCPY_ZIP%"

    if exist ".scrcpy\adb.exe" (
        echo scrcpy installed successfully in .scrcpy
    ) else (
        echo ERROR: .scrcpy\adb.exe not found after installation.
        echo Please verify contents of the .scrcpy directory.
        pause
        exit /b 1
    )
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