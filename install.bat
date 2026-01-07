@echo off
REM cSpell:ignore setlocal enabledelayedexpansion errorlevel VENV venv
REM =============================================================================
REM Rush Royale Bot - Windows Installation Script
REM Usage: install.bat [--dev]
REM   --dev    Install development dependencies (testing, linting, ML tools)
REM =============================================================================
setlocal enabledelayedexpansion
title Rush Royale Bot - Installation

:: Parse arguments
set "DEV_MODE=0"
if "%~1"=="--dev" set "DEV_MODE=1"
if "%~1"=="-dev" set "DEV_MODE=1"

echo ============================================
if "!DEV_MODE!"=="1" (
    echo   Rush Royale Bot - Installation [DEV]
) else (
    echo   Rush Royale Bot - Installation [PROD]
)
echo ============================================
echo.

:: 1. PRÜFUNG: Python Launcher (py.exe) oder Python im PATH
set "PYTHON_CMD="

:: Versuche zuerst den Python Launcher (bevorzugt für Version Selection)
where py >nul 2>&1
if %errorlevel% EQU 0 (
    echo [INFO] Python Launcher (py) gefunden.
    :: Suche nach der neuesten installierten Version (3.10 oder neuer)
    set "PYTHON_CMD=py -3"
) else (
    :: Fallback auf direkten python Befehl
    where python >nul 2>&1
    if %errorlevel% EQU 0 (
        echo [INFO] Standard 'python' Befehl gefunden.
        set "PYTHON_CMD=python"
    )
)

:: Wenn kein Python gefunden wurde
if "!PYTHON_CMD!"=="" (
    color 0C
    echo [ERROR] Keine Python-Installation gefunden!
    echo.
    echo Bitte installieren Sie Python 3.10+ von python.org
    echo Wichtig: Haken Sie "Add Python to PATH" im Installer an.
    echo.
    pause
    exit /b 1
)

:: 2. VERSIONSPRÜFUNG
echo [INFO] Pruefe Python Version...
!PYTHON_CMD! -c "import sys; print(str(sys.version_info.major) + '.' + str(sys.version_info.minor))" > .ver_tmp 2>&1
if %errorlevel% NEQ 0 (
    color 0C
    echo [ERROR] Python konnte nicht ausgefuehrt werden!
    del .ver_tmp 2>nul
    pause
    exit /b 1
)
set /p PY_VER_NUM=<.ver_tmp
del .ver_tmp

echo      Gefundene Version: !PY_VER_NUM!

:: Einfacher Check: Wir brauchen 3.10+ (Also Major 3, Minor >= 10)
for /f "tokens=1,2 delims=." %%a in ("!PY_VER_NUM!") do (
    if %%a LSS 3 (
        color 0C
        echo [ERROR] Python 3.x wird benoetigt!
        pause
        exit /b 1
    )
    if %%b LSS 10 (
        color 0C
        echo [ERROR] Python Version zu alt (!PY_VER_NUM!). Bitte 3.10 oder neuer installieren.
        pause
        exit /b 1
    )
)

:: 3. VIRTUELLE UMGEBUNG (VENV) SETUP
set "VENV_DIR=.bot_env"

if exist "!VENV_DIR!" (
    echo.
    echo [INFO] Virtuelle Umgebung '!VENV_DIR!' existiert bereits.
    set /p REINSTALL="Soll sie neu erstellt werden? (J/N): "
    if /i "!REINSTALL!"=="J" (
:create_venv
echo.
echo [INFO] Erstelle virtuelle Umgebung (.bot_env)...
!PYTHON_CMD! -m venv !VENV_DIR!
if %errorlevel% NEQ 0 (
    color 0C
    echo [ERROR] Konnte venv nicht erstellen. Pruefen Sie Ihre Python-Installation.
    pause
    exit /b 1
)
echo.
echo [INFO] Erstelle virtuelle Umgebung (.bot_env)...
!PYTHON_CMD! -m venv !VENV_DIR!
if !errorlevel! NEQ 0 (
    color 0C
    echo [ERROR] Konnte venv nicht erstellen. Pruefen Sie Ihre Python-Installation.
    pause
    exit /b 1
)

echo.
echo [INFO] Aktualisiere pip...
"!VENV_DIR!\Scripts\python.exe" -m pip install --upgrade pip
if %errorlevel% NEQ 0 (
    color 0E
    echo [WARNUNG] pip Update fehlgeschlagen, fahre fort...
)

:: Install based on mode
if "!DEV_MODE!"=="1" (
    echo [INFO] Installiere Entwicklungs-Bibliotheken aus requirements-dev.txt...
    "!VENV_DIR!\Scripts\python.exe" -m pip install -r requirements-dev.txt
) else (
    echo [INFO] Installiere Produktions-Bibliotheken aus requirements.txt...
    "!VENV_DIR!\Scripts\python.exe" -m pip install -r requirements.txt
)

if !errorlevel! NEQ 0 (
    color 0E
    echo.
    echo [WARNUNG] Es gab Fehler bei der Installation einiger Pakete.
    echo Bitte pruefen Sie das Log oben.
)

:: 5. LAUNCHER ERSTELLEN (launch_gui.bat)
echo.
echo [INFO] Erstelle Start-Skript (launch_gui.bat)...
(
    echo @echo off
    echo setlocal enabledelayedexpansion
    echo title Rush Royale Bot Launcher
    echo cd /d "%%~dp0"
    echo.
    echo if not exist ".bot_env\Scripts\python.exe" ^(
    echo     echo [ERROR] Virtuelle Umgebung nicht gefunden. Bitte install.bat ausfuehren.
    echo     pause
    echo     exit /b 1
    echo ^)
    echo.
    echo echo Starte Bot GUI...
    echo ".bot_env\Scripts\python.exe" "Src\gui.py"
    echo.
    echo if %%errorlevel%% NEQ 0 pause
) > launch_gui.bat

echo.
echo ============================================
if "!DEV_MODE!"=="1" (
    echo    Installation [DEV] erfolgreich!
) else (
    echo    Installation [PROD] erfolgreich!
)
echo ============================================
echo.
echo Sie koennen den Bot nun mit 'launch_gui.bat' starten.
if "!DEV_MODE!"=="0" (
    echo.
    echo Fuer Entwicklungsumgebung: install.bat --dev
)
echo.
pause