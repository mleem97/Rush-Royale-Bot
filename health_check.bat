@echo off
echo.
echo =======================================================
echo  🏥 Rush Royale Bot - Quick Health Check
echo =======================================================
echo.

REM Activate environment
call .venv313\Scripts\activate.bat

REM Run health check
python tools\health_check.py

echo.
echo =======================================================
if %ERRORLEVEL% EQU 0 (
    echo ✅ All systems operational!
    echo 🚀 Bot is ready to run: launch_gui.bat
) else if %ERRORLEVEL% EQU 2 (
    echo ⚠️  Minor issues detected - bot should still work
    echo 🔧 For fixes see: tools\README.md
) else (
    echo ❌ Critical issues found - please fix before running bot
    echo 🛠️  For help see: README.md or tools\README.md
)
echo =======================================================
echo.
pause
