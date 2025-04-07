@echo off

IF EXIST .installed (
    REM Launch the application
    call .bot_env\Scripts\activate.bat
    python Src\gui.py
) ELSE (
    REM Installation process
    python -m venv .bot_env
    %LOCALAPPDATA%\Programs\Python\Python39\python -m venv .bot_env
    REM if this does not work add the path to where your python installation is located.
    call .bot_env\Scripts\activate.bat
    pip install -r requirements.txt
    REM Create .installed file to indicate installation is complete
    type nul > .installed
    REM Launch the application
    python Src\gui.py
)
