@echo off
echo.
echo =======================================================
echo  Rush Royale Bot - Device Setup Optimizer
echo =======================================================
echo.
echo Preparing optimal device configuration...
echo.

REM Kill ADB server to clear all connections
echo 1. Stopping ADB server...
.scrcpy\adb kill-server
timeout /t 2 /nobreak >nul

REM Start ADB server
echo 2. Starting ADB server...
.scrcpy\adb start-server
timeout /t 2 /nobreak >nul

REM Show current devices
echo 3. Current devices:
.scrcpy\adb devices
echo.

REM Test connection to main emulator
echo 4. Testing primary emulator connection...
.scrcpy\adb -s emulator-5554 shell echo "Primary emulator OK" 2>nul
if %ERRORLEVEL% EQU 0 (
    echo ✅ Primary emulator emulator-5554 is ready!
    echo.
    echo =======================================================
    echo ✅ Setup complete! You can now start the bot:
    echo    launch_gui.bat
    echo =======================================================
) else (
    echo ❌ Primary emulator not responding
    echo 💡 Please make sure Bluestacks is running and try:
    echo    .scrcpy\adb connect 127.0.0.1:5554
)

echo.
pause
