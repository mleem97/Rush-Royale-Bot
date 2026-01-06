@echo off
setlocal enabledelayedexpansion
title Rush Royale Bot - Installation

echo ============================================
echo   Rush Royale Bot - Installation
echo ============================================
echo.

:: Search for all installed Python versions
set "PYTHON_COUNT=0"
set "PYTHON_LIST="

:: Helper function to add a Python version
:: Called below

:: 1. Search WindowsStore/WindowsApps versions (python3.XX.exe)
for %%p in (
    "%LOCALAPPDATA%\Microsoft\WindowsApps\python3.14.exe"
    "%LOCALAPPDATA%\Microsoft\WindowsApps\python3.13.exe"
    "%LOCALAPPDATA%\Microsoft\WindowsApps\python3.12.exe"
    "%LOCALAPPDATA%\Microsoft\WindowsApps\python3.11.exe"
    "%LOCALAPPDATA%\Microsoft\WindowsApps\python3.10.exe"
) do (
    if exist "%%~p" (
        :: Check for 0KB WindowsApps alias
        for %%F in ("%%~p") do set "SIZE=%%~zF"
        if !SIZE! EQU 0 (
            echo   -^> Skipping 0KB WindowsApp alias: %%~p
        ) else (
            set /a PYTHON_COUNT+=1
            set "PYTHON_!PYTHON_COUNT!=%%~p"
            for /f "tokens=*" %%v in ('"%%~p" --version 2^>^&1') do (
                set "PYTHON_VER_!PYTHON_COUNT!=%%v"
            )
        )
    )
)

:: 2. Search for standard python.exe in PATH (if not WindowsApps)
for /f "tokens=*" %%i in ('where python 2^>nul') do (
    :: Skip WindowsApps (already checked above)
    echo %%i | findstr /i "WindowsApps" >nul
    if errorlevel 1 (
        set "ALREADY_FOUND=0"
        for /l %%n in (1,1,!PYTHON_COUNT!) do (
            if "!PYTHON_%%n!"=="%%i" set "ALREADY_FOUND=1"
        )
        if "!ALREADY_FOUND!"=="0" (
            set /a PYTHON_COUNT+=1
            set "PYTHON_!PYTHON_COUNT!=%%i"
            for /f "tokens=*" %%v in ('"%%i" --version 2^>^&1') do (
                set "PYTHON_VER_!PYTHON_COUNT!=%%v"
            )
        )
    )
)

:: 3. Search in typical installation directories
for %%p in (
    "%LOCALAPPDATA%\Programs\Python\Python314\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python39\python.exe"
    "C:\Python314\python.exe"
    "C:\Python313\python.exe"
    "C:\Python312\python.exe"
    "C:\Python311\python.exe"
    "C:\Python310\python.exe"
    "C:\Python39\python.exe"
    "%ProgramFiles%\Python314\python.exe"
    "%ProgramFiles%\Python313\python.exe"
    "%ProgramFiles%\Python312\python.exe"
    "%ProgramFiles%\Python311\python.exe"
    "%ProgramFiles%\Python310\python.exe"
    "%USERPROFILE%\scoop\apps\python\current\python.exe"
    "%USERPROFILE%\scoop\apps\python314\current\python.exe"
    "%USERPROFILE%\scoop\apps\python313\current\python.exe"
    "%USERPROFILE%\scoop\apps\python311\current\python.exe"
    "C:\tools\python3\python.exe"
    "C:\tools\python314\python.exe"
    "C:\tools\python313\python.exe"
    "C:\tools\python311\python.exe"
) do (
    if exist "%%~p" (
        set "ALREADY_FOUND=0"
        for /l %%n in (1,1,!PYTHON_COUNT!) do (
            if "!PYTHON_%%n!"=="%%~p" set "ALREADY_FOUND=1"
        )
        if "!ALREADY_FOUND!"=="0" (
            set /a PYTHON_COUNT+=1
            set "PYTHON_!PYTHON_COUNT!=%%~p"
            for /f "tokens=*" %%v in ('"%%~p" --version 2^>^&1') do (
                set "PYTHON_VER_!PYTHON_COUNT!=%%v"
            )
        )
    )
)

:: 4. Try Python Launcher (py) if available
where py >nul 2>&1
if not errorlevel 1 (
    for /f "tokens=1,2,*" %%a in ('py -0p 2^>nul') do (
        set "PY_PATH=%%c"
        if not "!PY_PATH!"=="" (
            set "ALREADY_FOUND=0"
            for /l %%n in (1,1,!PYTHON_COUNT!) do (
                if "!PYTHON_%%n!"=="!PY_PATH!" set "ALREADY_FOUND=1"
            )
            if "!ALREADY_FOUND!"=="0" (
                set /a PYTHON_COUNT+=1
                set "PYTHON_!PYTHON_COUNT!=!PY_PATH!"
                for /f "tokens=*" %%v in ('"!PY_PATH!" --version 2^>^&1') do (
                    set "PYTHON_VER_!PYTHON_COUNT!=%%v"
                )
            )
        )
    )
)

:: No Python installation found
if %PYTHON_COUNT%==0 (
    echo ERROR: No Python installation found!
    echo.
    echo Please install Python 3.10 or newer from:
    echo https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

:: Only one version found - use automatically
if %PYTHON_COUNT%==1 (
    set "SELECTED_PYTHON=!PYTHON_1!"
    echo Found: !PYTHON_VER_1!
    echo Path: !SELECTED_PYTHON!
    echo.
    goto :install
)

:: Multiple versions found - show selection
echo Multiple Python versions found:
echo.
for /l %%n in (1,1,%PYTHON_COUNT%) do (
    echo   [%%n] !PYTHON_VER_%%n!
    echo       !PYTHON_%%n!
    echo.
)

:: User selection
:select_python
set /p "SELECTION=Choose Python version [1-%PYTHON_COUNT%]: "

:: Validate input
set "VALID=0"
for /l %%n in (1,1,%PYTHON_COUNT%) do (
    if "%SELECTION%"=="%%n" set "VALID=1"
)
if "%VALID%"=="0" (
    echo Invalid selection. Please enter a number from 1 to %PYTHON_COUNT%.
    goto :select_python
)

set "SELECTED_PYTHON=!PYTHON_%SELECTION%!"
echo.
echo Selected: !PYTHON_VER_%SELECTION%!
echo.

:install
:: Check if requirements.txt exists
if not exist "requirements.txt" (
    echo ERROR: requirements.txt not found!
    echo Please make sure you extracted all files.
    echo.
    pause
    exit /b 1
)

:: Save selected Python version for launch_gui.bat
echo %SELECTED_PYTHON%> .python_path

:: Create or update virtual environment
if exist ".bot_env" (
    echo.
    echo Virtual environment already exists.
    set /p "REINSTALL=Do you want to recreate it? (Y/N): "
    if /i "!REINSTALL!"=="Y" (
        echo Removing old environment...
        rmdir /s /q ".bot_env"
        echo Creating new virtual environment...
        "%SELECTED_PYTHON%" -m venv .bot_env
        if errorlevel 1 (
            echo ERROR: Could not create virtual environment!
            pause
            exit /b 1
        )
    ) else (
        echo Using existing environment...
    )
) else (
    echo Creating virtual environment...
    "%SELECTED_PYTHON%" -m venv .bot_env
    if errorlevel 1 (
        echo ERROR: Could not create virtual environment!
        pause
        exit /b 1
    )
)

:: Activate environment
echo Activating environment...
call .bot_env\Scripts\activate.bat

:: Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip

:: Install dependencies
echo.
echo Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo WARNING: Some packages could not be installed.
    echo Please check the error messages above.
)

:: Create launch_gui.bat if not present
if not exist "launch_gui.bat" (
    echo.
    echo Creating launcher script ^(launch_gui.bat^)...
    (
        echo @echo off
        echo setlocal enabledelayedexpansion
        echo title Rush Royale Bot
        echo.
        echo :: Read Python path
        echo set /p PYTHON_PATH=^<.python_path
        echo.
        echo if not exist "!PYTHON_PATH!" ^(
        echo     echo ERROR: Python path not found.
        echo     echo Please run install.bat.
        echo     pause
        echo     exit /b 1
        echo ^)
        echo.
        echo if not exist ".bot_env\Scripts\python.exe" ^(
        echo     echo ERROR: Virtual environment not found.
        echo     echo Please run install.bat.
        echo     pause
        echo     exit /b 1
        echo ^)
        echo.
        echo echo Starting Bot...
        echo ".bot_env\Scripts\python.exe" "Src\bot_handler.py"
        echo.
        echo if errorlevel 1 pause
    ) > launch_gui.bat
    echo   -^> launch_gui.bat created
)

echo.
echo ============================================
echo   Installation completed!
echo ============================================
echo.
echo Start the bot with: launch_gui.bat
echo.
pause
