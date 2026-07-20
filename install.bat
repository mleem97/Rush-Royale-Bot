@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo Installing RushBot for Windows...
echo ================================

where python >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python was not found in PATH.
    echo Install Python 3.11 or newer and enable "Add Python to PATH".
    exit /b 1
)

python -c "import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)"
if errorlevel 1 (
    echo ERROR: RushBot requires Python 3.11 or newer.
    exit /b 1
)
python --version

where adb >nul 2>&1
if not errorlevel 1 goto adb_ready
if exist ".scrcpy\adb.exe" (
    set "ADB_PATH=%CD%\.scrcpy\adb.exe"
    goto adb_ready
)

echo ADB was not found.
where winget >nul 2>&1
if errorlevel 1 goto adb_missing

echo Installing the official scrcpy package, which includes ADB...
winget install --exact Genymobile.scrcpy --accept-package-agreements --accept-source-agreements
where adb >nul 2>&1
if not errorlevel 1 goto adb_ready

echo The installation completed, but this terminal cannot see adb yet.
echo Close this terminal, open a new one, and run install.bat again.
exit /b 1

:adb_missing
echo Install Android SDK Platform Tools or the official scrcpy package.
echo You may also extract scrcpy to .scrcpy or set ADB_PATH to adb.exe.
exit /b 1

:adb_ready
if not exist ".bot_env\Scripts\python.exe" (
    python -m venv .bot_env
    if errorlevel 1 exit /b 1
)

.bot_env\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
if errorlevel 1 exit /b 1
.bot_env\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 exit /b 1

echo.
echo Installation completed.
echo Start the GUI with launch_gui.bat
endlocal
