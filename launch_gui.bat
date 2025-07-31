@echo off
echo.
echo =======================================================
echo  🎮 Rush Royale Bot v2.0.0 - Launcher
echo =======================================================
echo.

echo 🔍 Running pre-launch health checks...
echo.

REM Check 1: Python Environment
echo ✅ Checking Python environment...
if not exist ".venv313\Scripts\activate.bat" (
    echo ❌ Python environment not found!
    echo 💡 Please run: install.bat
    echo.
    pause
    exit /b 1
)

REM Activate environment
call .venv313\Scripts\activate.bat

REM Run comprehensive health check
echo ✅ Running comprehensive system health check...
python tools\health_check.py
set HEALTH_EXIT_CODE=%ERRORLEVEL%

if %HEALTH_EXIT_CODE% EQU 1 (
    echo.
    echo ❌ Critical health check failures detected!
    echo 💡 Please fix the issues above before starting the bot
    echo.
    pause
    exit /b 1
) else if %HEALTH_EXIT_CODE% EQU 2 (
    echo.
    echo ⚠️  Health check passed with warnings
    choice /c YN /m "Continue with bot startup"
    if %ERRORLEVEL% EQU 2 (
        echo Bot startup cancelled by user
        exit /b 1
    )
) else (
    echo ✅ All health checks passed!
)

REM All checks passed
echo.
echo =======================================================
echo ✅ All health checks passed!
echo 🚀 Starting Rush Royale Bot GUI...
echo =======================================================
echo.

REM Launch the bot
python Src\gui.py

REM Check exit code
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ❌ Bot exited with error code: %ERRORLEVEL%
    echo 💡 Check the error messages above
    echo 🔧 For troubleshooting run: python tools\test_dependencies.py
    echo.
    pause
)