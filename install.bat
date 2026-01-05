@echo off
setlocal enabledelayedexpansion
title Rush Royale Bot - Installation

echo ============================================
echo   Rush Royale Bot - Installation
echo ============================================
echo.

:: Suche alle installierten Python-Versionen
set "PYTHON_COUNT=0"
set "PYTHON_LIST="

:: Hilfsfunktion zum Hinzufügen einer Python-Version
:: Wird unten aufgerufen

:: 1. Suche WindowsStore/WindowsApps Versionen (python3.XX.exe)
for %%p in (
    "%LOCALAPPDATA%\Microsoft\WindowsApps\python3.14.exe"
    "%LOCALAPPDATA%\Microsoft\WindowsApps\python3.13.exe"
    "%LOCALAPPDATA%\Microsoft\WindowsApps\python3.12.exe"
    "%LOCALAPPDATA%\Microsoft\WindowsApps\python3.11.exe"
    "%LOCALAPPDATA%\Microsoft\WindowsApps\python3.10.exe"
) do (
    if exist "%%~p" (
        set /a PYTHON_COUNT+=1
        set "PYTHON_!PYTHON_COUNT!=%%~p"
        for /f "tokens=*" %%v in ('"%%~p" --version 2^>^&1') do (
            set "PYTHON_VER_!PYTHON_COUNT!=%%v"
        )
    )
)

:: 2. Suche Standard python.exe in PATH (falls nicht WindowsApps)
for /f "tokens=*" %%i in ('where python 2^>nul') do (
    :: Überspringe WindowsApps (haben wir schon oben)
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

:: 3. Suche in typischen Installationsordnern
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

:: 4. Versuche Python Launcher (py) falls vorhanden
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

:: Keine Python-Installation gefunden
if %PYTHON_COUNT%==0 (
    echo FEHLER: Keine Python-Installation gefunden!
    echo.
    echo Bitte installiere Python 3.10 oder neuer von:
    echo https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

:: Nur eine Version gefunden - automatisch nutzen
if %PYTHON_COUNT%==1 (
    set "SELECTED_PYTHON=!PYTHON_1!"
    echo Gefunden: !PYTHON_VER_1!
    echo Pfad: !SELECTED_PYTHON!
    echo.
    goto :install
)

:: Mehrere Versionen gefunden - Auswahl anzeigen
echo Mehrere Python-Versionen gefunden:
echo.
for /l %%n in (1,1,%PYTHON_COUNT%) do (
    echo   [%%n] !PYTHON_VER_%%n!
    echo       !PYTHON_%%n!
    echo.
)

:: Benutzerauswahl
:select_python
set /p "SELECTION=Waehle Python-Version [1-%PYTHON_COUNT%]: "

:: Validiere Eingabe
set "VALID=0"
for /l %%n in (1,1,%PYTHON_COUNT%) do (
    if "%SELECTION%"=="%%n" set "VALID=1"
)
if "%VALID%"=="0" (
    echo Ungueltige Auswahl. Bitte eine Zahl von 1 bis %PYTHON_COUNT% eingeben.
    goto :select_python
)

set "SELECTED_PYTHON=!PYTHON_%SELECTION%!"
echo.
echo Ausgewaehlt: !PYTHON_VER_%SELECTION%!
echo.

:install
:: Speichere ausgewählte Python-Version für launch_gui.bat
echo %SELECTED_PYTHON%> .python_path

:: Erstelle virtuelle Umgebung
echo Erstelle virtuelle Umgebung...
"%SELECTED_PYTHON%" -m venv .bot_env
if errorlevel 1 (
    echo FEHLER: Konnte virtuelle Umgebung nicht erstellen!
    pause
    exit /b 1
)

:: Aktiviere Umgebung
echo Aktiviere Umgebung...
call .bot_env\Scripts\activate.bat

:: Upgrade pip
echo Aktualisiere pip...
python -m pip install --upgrade pip

:: Installiere Abhängigkeiten
echo.
echo Installiere Abhaengigkeiten...
pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo WARNUNG: Einige Pakete konnten nicht installiert werden.
    echo Pruefe die Fehlermeldungen oben.
)

echo.
echo ============================================
echo   Installation abgeschlossen!
echo ============================================
echo.
echo Starte den Bot mit: launch_gui.bat
echo.
pause
