@echo off
echo ================================
echo Rush Royale Bot - GUI Start
echo ================================
echo.

:: Check if Virtual Environment exists
if not exist ".bot_env" (
    echo ERROR: Virtual Environment not found!
    echo Please run install.bat first.
    pause
    exit /b 1
)

:: Activate Virtual Environment
echo Activating Virtual Environment...
call .bot_env\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Virtual Environment could not be activated!
    pause
    exit /b 1
)

:: Check if Src directory exists
if not exist "Src" (
    echo ERROR: Src directory not found!
    echo Make sure you are in the Bot main directory.
    pause
    exit /b 1
)

:: Check BlueStacks/ADB connection
echo Checking ADB connection...
adb devices >nul 2>&1
if errorlevel 1 (
    echo WARNING: ADB not found or BlueStacks not started
    echo Make sure that:
    echo - BlueStacks is running
    echo - ADB is enabled in BlueStacks (Port 5555)
    echo.
)

:: Create necessary directories
if not exist "units" mkdir units
if not exist "OCR_inputs" mkdir OCR_inputs

:: Check critical files
if not exist "config.ini" (
    echo Creating default config.ini...
    echo [bot] > config.ini
    echo floor = 7 >> config.ini
    echo mana_level = 1,2,3,4,5 >> config.ini
    echo units = demo, boreas, robot, dryad, franky_stein >> config.ini
    echo dps_unit = boreas >> config.ini
    echo pve = False >> config.ini
    echo require_shaman = False >> config.ini
    echo. >> config.ini
    echo [rl_system] >> config.ini
    echo enabled = False >> config.ini
)

:: Start GUI
echo Starting Rush Royale Bot GUI...
echo.
python Src\gui.py

if errorlevel 1 (
    echo.
    echo ERROR starting GUI!
    echo Check the error message above.
    pause
)

echo.
echo Bot was terminated.
pause