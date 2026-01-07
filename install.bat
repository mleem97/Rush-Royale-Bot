@echo off
setlocal enabledelayedexpansion
title Rush Royale Bot - Installation

:: Parse arguments for dev mode
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

:: 1. SUCHE NACH PYTHON VERSIONEN
echo [INFO] Suche installierte Python Versionen...
echo.

set "PY_COUNT=0"
set "HAS_PY_LAUNCHER=0"

:: Pruefe ob py Launcher existiert (beste Methode)
where py >nul 2>&1
if !errorlevel! EQU 0 (
    set "HAS_PY_LAUNCHER=1"
    
    :: Liste alle verfuegbaren Python Versionen mit py -0p (zeigt auch Pfade)
    for /f "tokens=1,2,*" %%a in ('py -0p 2^>nul ^| findstr /R "^[ ]*-[0-9]"') do (
        set "ver_tag=%%a"
        set "ver_path=%%b"
        
        :: Pruefe ob der Pfad existiert und ausfuehrbar ist
        if exist "%%b" (
            set /a PY_COUNT+=1
            set "PY_VER_!PY_COUNT!=!ver_tag!"
            set "PY_PATH_!PY_COUNT!=%%b"
            
            :: Extrahiere Versionsnummer (z.B. -3.13-64 -> 3.13)
            set "ver=!ver_tag!"
            set "ver=!ver:-=!"
            for /f "tokens=1 delims=-" %%x in ("!ver!") do set "ver=%%x"
            set "PY_NUM_!PY_COUNT!=!ver!"
            
            echo   [!PY_COUNT!] Python !ver!  ^(%%b^)
        )
    )
)

:: Fallback: Manuelle Suche in Standard-Pfaden wenn py launcher nichts findet
if !PY_COUNT! EQU 0 (
    echo [INFO] Kein py Launcher, suche in Standard-Pfaden...
    
    :: Standard-Installationspfade durchsuchen
    for %%V in (314 313 312 311 310) do (
        :: Python.org Installation - User
        if exist "%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe" (
            set /a PY_COUNT+=1
            set "PY_PATH_!PY_COUNT!=%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe"
            set "ver=%%V"
            set "PY_NUM_!PY_COUNT!=!ver:~0,1!.!ver:~1!"
            set "PY_VER_!PY_COUNT!=path"
            echo   [!PY_COUNT!] Python !ver:~0,1!.!ver:~1!  ^(%LOCALAPPDATA%\Programs\Python\Python%%V^)
        )
        :: Python.org Installation - System
        if exist "C:\Python%%V\python.exe" (
            set /a PY_COUNT+=1
            set "PY_PATH_!PY_COUNT!=C:\Python%%V\python.exe"
            set "ver=%%V"
            set "PY_NUM_!PY_COUNT!=!ver:~0,1!.!ver:~1!"
            set "PY_VER_!PY_COUNT!=path"
            echo   [!PY_COUNT!] Python !ver:~0,1!.!ver:~1!  ^(C:\Python%%V^)
        )
        :: Program Files
        if exist "C:\Program Files\Python%%V\python.exe" (
            set /a PY_COUNT+=1
            set "PY_PATH_!PY_COUNT!=C:\Program Files\Python%%V\python.exe"
            set "ver=%%V"
            set "PY_NUM_!PY_COUNT!=!ver:~0,1!.!ver:~1!"
            set "PY_VER_!PY_COUNT!=path"
            echo   [!PY_COUNT!] Python !ver:~0,1!.!ver:~1!  ^(C:\Program Files\Python%%V^)
        )
    )
    
    :: Scoop Installation
    if exist "%USERPROFILE%\scoop\apps\python\current\python.exe" (
        for /f "tokens=*" %%v in ('"%USERPROFILE%\scoop\apps\python\current\python.exe" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2^>nul') do (
            set /a PY_COUNT+=1
            set "PY_PATH_!PY_COUNT!=%USERPROFILE%\scoop\apps\python\current\python.exe"
            set "PY_NUM_!PY_COUNT!=%%v"
            set "PY_VER_!PY_COUNT!=path"
            echo   [!PY_COUNT!] Python %%v  ^(Scoop^)
        )
    )
    
    :: Chocolatey
    if exist "C:\Python3\python.exe" (
        for /f "tokens=*" %%v in ('"C:\Python3\python.exe" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2^>nul') do (
            set /a PY_COUNT+=1
            set "PY_PATH_!PY_COUNT!=C:\Python3\python.exe"
            set "PY_NUM_!PY_COUNT!=%%v"
            set "PY_VER_!PY_COUNT!=path"
            echo   [!PY_COUNT!] Python %%v  ^(Chocolatey^)
        )
    )
)

:: Windows Store / WindowsApps Versionen (python3.XX.exe)
:: Diese sind 0-Byte Aliase, funktionieren aber trotzdem!
for %%V in (3.14 3.13 3.12 3.11 3.10) do (
    python%%V --version >nul 2>&1
    if !errorlevel! EQU 0 (
        set /a PY_COUNT+=1
        set "PY_PATH_!PY_COUNT!=python%%V"
        set "PY_NUM_!PY_COUNT!=%%V"
        set "PY_VER_!PY_COUNT!=winstore"
        echo   [!PY_COUNT!] Python %%V  ^(Windows Store^)
    )
)

:: Letzter Fallback: python im PATH (wenn noch nichts gefunden)
if !PY_COUNT! EQU 0 (
    where python >nul 2>&1
    if !errorlevel! EQU 0 (
        for /f "tokens=*" %%v in ('python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2^>nul') do (
            set /a PY_COUNT=1
            set "PY_VER_1=python"
            set "PY_NUM_1=%%v"
            set "PY_PATH_1=python"
            echo   [1] Python %%v ^(PATH^)
        )
    )
)

:: Keine Python Installation gefunden
if !PY_COUNT! EQU 0 (
    color 0C
    echo.
    echo [ERROR] Keine Python-Installation gefunden!
    echo.
    echo Bitte installieren Sie Python 3.10+ von python.org
    echo Wichtig: Haken Sie "Add Python to PATH" im Installer an.
    echo.
    pause
    exit /b 1
)

echo.

:: 2. BENUTZER WAEHLT PYTHON VERSION
if !PY_COUNT! GTR 1 (
    echo Mehrere Python Versionen gefunden.
    set /p "CHOICE=Welche Version moechten Sie verwenden? [1-!PY_COUNT!]: "
    
    :: Validiere Eingabe
    if "!CHOICE!"=="" set "CHOICE=1"
    if !CHOICE! LSS 1 set "CHOICE=1"
    if !CHOICE! GTR !PY_COUNT! set "CHOICE=!PY_COUNT!"
) else (
    set "CHOICE=1"
)

:: Setze gewaehlte Version
set "SELECTED_VER=!PY_VER_%CHOICE%!"
set "SELECTED_NUM=!PY_NUM_%CHOICE%!"
set "SELECTED_PATH=!PY_PATH_%CHOICE%!"

echo.
echo [INFO] Verwende Python !SELECTED_NUM!

:: Baue PYTHON_CMD basierend auf Erkennungsmethode
if "!SELECTED_VER!"=="winstore" (
    :: Windows Store Version (python3.13.exe etc.)
    set "PYTHON_CMD=!SELECTED_PATH!"
) else if "!HAS_PY_LAUNCHER!"=="1" (
    if "!SELECTED_VER!"=="path" (
        :: Direkter Pfad
        set "PYTHON_CMD="!SELECTED_PATH!""
    ) else if "!SELECTED_VER!"=="python" (
        set "PYTHON_CMD=python"
    ) else (
        :: py launcher mit Version-Tag (z.B. py -3.13)
        set "PYTHON_CMD=py !SELECTED_VER!"
    )
) else (
    if "!SELECTED_VER!"=="path" (
        set "PYTHON_CMD="!SELECTED_PATH!""
    ) else (
        set "PYTHON_CMD=python"
    )
)

:: 3. VERSIONSPRUEFUNG (mindestens 3.10)
for /f "tokens=1,2 delims=." %%a in ("!SELECTED_NUM!") do (
    if %%a LSS 3 (
        color 0C
        echo [ERROR] Python 3.x wird benoetigt!
        pause
        exit /b 1
    )
    if %%a EQU 3 if %%b LSS 10 (
        color 0C
        echo [ERROR] Python Version zu alt ^(!SELECTED_NUM!^). Bitte 3.10 oder neuer waehlen.
        pause
        exit /b 1
    )
)

echo [OK] Version !SELECTED_NUM! ist kompatibel.

:: 4. VIRTUELLE UMGEBUNG (VENV) SETUP
set "VENV_DIR=.bot_env"

if exist "!VENV_DIR!" (
    echo.
    echo [INFO] Virtuelle Umgebung '!VENV_DIR!' existiert bereits.
    set /p "REINSTALL=Soll sie neu erstellt werden? (J/N): "
    if /i "!REINSTALL!"=="J" (
        echo Entferne alte Umgebung...
        rmdir /s /q "!VENV_DIR!"
        goto :create_venv
    ) else (
        echo Nutze existierende Umgebung...
        goto :install_deps
    )
)

:create_venv
echo.
echo [INFO] Erstelle virtuelle Umgebung mit Python !SELECTED_NUM!...
!PYTHON_CMD! -m venv "!VENV_DIR!"
if !errorlevel! NEQ 0 (
    color 0C
    echo [ERROR] Konnte venv nicht erstellen. Pruefen Sie Ihre Python-Installation.
    pause
    exit /b 1
)
echo [OK] Virtuelle Umgebung erstellt.

:install_deps
:: 5. ABHAENGIGKEITEN INSTALLIEREN
echo.
echo [INFO] Aktualisiere pip...
"!VENV_DIR!\Scripts\python.exe" -m pip install --upgrade pip --quiet

:: Install based on mode
if "!DEV_MODE!"=="1" (
    if not exist "requirements-dev.txt" (
        color 0C
        echo [ERROR] requirements-dev.txt nicht gefunden!
        pause
        exit /b 1
    )
    echo [INFO] Installiere Entwicklungs-Bibliotheken...
    "!VENV_DIR!\Scripts\python.exe" -m pip install -r requirements-dev.txt
) else (
    if not exist "requirements.txt" (
        color 0C
        echo [ERROR] requirements.txt nicht gefunden!
        pause
        exit /b 1
    )
    echo [INFO] Installiere Produktions-Bibliotheken...
    "!VENV_DIR!\Scripts\python.exe" -m pip install -r requirements.txt
)

if !errorlevel! NEQ 0 (
    color 0E
    echo.
    echo [WARNUNG] Es gab Fehler bei der Installation einiger Pakete.
    echo Bitte pruefen Sie das Log oben.
)

:: 6. LAUNCHER ERSTELLEN (launch_gui.bat)
echo.
echo [INFO] Erstelle Start-Skript (launch_gui.bat)...
(
    echo @echo off
    echo setlocal enabledelayedexpansion
    echo title Rush Royale Bot
    echo cd /d "%%~dp0"
    echo.
    echo if not exist ".bot_env\Scripts\python.exe" ^(
    echo     echo [ERROR] Virtuelle Umgebung nicht gefunden. Bitte install.bat ausfuehren.
    echo     pause
    echo     exit /b 1
    echo ^)
    echo.
    echo ".bot_env\Scripts\python.exe" "Src\gui.py"
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
echo Python Version: !SELECTED_NUM!
echo Virtuelle Umgebung: !VENV_DIR!
echo.
echo Starten Sie den Bot mit: launch_gui.bat
if "!DEV_MODE!"=="0" (
    echo.
    echo Fuer Entwickler: install.bat --dev
)
echo.
pause
