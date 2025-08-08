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
echo Activating Virtual Environment...
call .bot_env\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Virtual Environment could not be activated!
    pause
    exit /b 1
)

:: Verify Virtual Environment is active
if "%VIRTUAL_ENV%"=="" (
    echo ERROR: Virtual Environment activation failed!
    echo VIRTUAL_ENV variable not set.
    pause
    exit /b 1
)

echo Virtual Environment active: %VIRTUAL_ENV%
echo.

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
