@echo off
echo.
echo =======================================================
echo  🎯 Rush Royale Bot - Development Environment Setup
echo =======================================================
echo.

REM Check if Python environment exists
if not exist ".venv313\Scripts\activate.bat" (
    echo ❌ Python environment not found!
    echo 💡 Please run: install.bat first
    echo.
    pause
    exit /b 1
)

REM Activate environment
call .venv313\Scripts\activate.bat

echo 🔧 Installing development dependencies...
echo.

REM Install development tools
pip install --upgrade pip
pip install pytest pytest-cov pytest-mock
pip install black isort mypy pylint
pip install bandit safety
pip install flake8 flake8-docstrings
pip install jupyter notebook ipykernel
pip install pre-commit

echo.
echo ✅ Development dependencies installed!
echo.

REM Setup pre-commit hooks
echo 🪝 Setting up pre-commit hooks...
pre-commit install 2>nul
if %ERRORLEVEL% EQU 0 (
    echo ✅ Pre-commit hooks installed
) else (
    echo ⚠️  Pre-commit setup skipped
)

REM Create development directories
echo 📁 Creating development directories...
if not exist "logs" mkdir logs
if not exist "reports" mkdir reports
if not exist "backups" mkdir backups

echo.
echo 🎯 Development environment ready!
echo.
echo Available commands:
echo   📊 run_tests.bat          - Run full test suite
echo   🧪 python tests/run_tests.py - Run specific tests
echo   🔍 python tools/health_check.py - System health check
echo   📈 jupyter notebook RR_bot.ipynb - Interactive development
echo   🎮 launch_gui.bat        - Start bot GUI
echo.
echo Development best practices:
echo   🔧 Use black for code formatting: python -m black .
echo   📋 Check with pylint: python -m pylint Src/
echo   🛡️  Security scan: python -m bandit -r Src/
echo   📊 Run tests before commits: run_tests.bat
echo.
pause
