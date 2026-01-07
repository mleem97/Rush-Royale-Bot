@echo off
REM Launch Modern CustomTkinter GUI for Rush Royale Bot
cd /d "%~dp0\.."
if exist ".bot_env\Scripts\activate.bat" (
    call .bot_env\Scripts\activate.bat
)
python Src\gui.py
pause
