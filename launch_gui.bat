@echo off
setlocal enabledelayedexpansion
title Rush Royale Bot

echo ============================================
echo   Rush Royale Bot
echo ============================================
echo.

:: Prüfe ob virtuelle Umgebung existiert
if not exist ".bot_env\Scripts\activate.bat" (
    echo Virtuelle Umgebung nicht gefunden!
    echo Bitte zuerst install.bat ausfuehren.
    echo.
    pause
    exit /b 1
)

:: Prüfe ob Python-Pfad gespeichert wurde
if exist ".python_path" (
    set /p SAVED_PYTHON=<.python_path
    echo Gespeicherte Python-Version: !SAVED_PYTHON!
    echo.
)

:: Aktiviere Umgebung
echo Aktiviere Umgebung...
call .bot_env\Scripts\activate.bat

:: Starte GUI
echo Starte Bot GUI...
echo.
python Src\gui.py

if errorlevel 1 (
    echo.
    echo Bot wurde mit Fehler beendet.
    pause
)
