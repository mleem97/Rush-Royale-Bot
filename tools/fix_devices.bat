@echo off
echo.
echo =======================================================
echo  Rush Royale Bot - Multiple Device Fix
echo =======================================================
echo.
echo This will help resolve the "more than one device/emulator" error
echo.

REM Navigate to parent directory and activate virtual environment
cd ..
call .venv313\Scripts\activate.bat

REM Run the device fix script from tools directory
python tools\fix_multiple_devices.py

echo.
echo =======================================================
echo After fixing devices, you can run:
echo   launch_gui.bat     - Start the bot GUI
echo   python tools\version_info.py - Check version info
echo =======================================================
echo.
pause
