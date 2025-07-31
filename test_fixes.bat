@echo off
echo Testing Bot Fixes...
echo ==================

REM Check if Python is available
python --version >NUL 2>&1
if errorlevel 1 (
    echo ERROR: Python not found in PATH
    pause
    exit /b 1
)

REM Run the test script
python test_fixes.py

echo.
echo Test completed. Press any key to continue...
pause >NUL
