@echo off
echo ================================
echo Rush Royale Bot - Debug Start
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
call .bot_env\Scripts\activate.bat

:: Run System Check
echo Running System Check...
python Src\system_check.py

echo.
echo Press Enter to continue anyway or Ctrl+C to cancel...
pause

:: Start normal GUI
echo.
echo Starting GUI...
call launch_gui.bat
