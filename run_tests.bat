@echo off
echo.
echo =======================================================
echo  🧪 Rush Royale Bot - Test Suite Runner
echo =======================================================
echo.

REM Check if Python environment exists
if not exist ".venv313\Scripts\activate.bat" (
    echo ❌ Python environment not found!
    echo 💡 Please run: install.bat
    echo.
    pause
    exit /b 1
)

REM Activate environment
call .venv313\Scripts\activate.bat

echo 🔍 Installing test dependencies...
pip install pytest pytest-cov black isort mypy pylint bandit safety

echo.
echo 🚀 Running comprehensive test suite...
echo.

REM Run unit tests
echo ✅ Running unit tests...
python -m pytest tests/ -v --cov=Src --cov-report=term-missing --cov-report=html

REM Check exit code
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ❌ Unit tests failed!
    echo.
    pause
    exit /b 1
)

echo.
echo 🔍 Running code quality checks...
echo.

REM Code formatting check
echo ✅ Checking code formatting (Black)...
python -m black --check --diff . 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ⚠️  Code formatting issues found
    echo 💡 Run: python -m black . to fix
) else (
    echo ✅ Code formatting OK
)

REM Import sorting check
echo ✅ Checking import sorting (isort)...
python -m isort --check-only --diff . 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ⚠️  Import sorting issues found
    echo 💡 Run: python -m isort . to fix
) else (
    echo ✅ Import sorting OK
)

REM Type checking
echo ✅ Running type checks (mypy)...
python -m mypy Src/ --ignore-missing-imports 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ⚠️  Type checking issues found
) else (
    echo ✅ Type checking OK
)

REM Security checks
echo ✅ Running security checks (bandit)...
python -m bandit -r Src/ -q 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ⚠️  Security issues found
) else (
    echo ✅ Security checks OK
)

REM Dependency tests
echo.
echo 🔍 Running system checks...
echo.

echo ✅ Testing dependencies...
python test_dependencies.py

echo ✅ Running health check...
python tools\health_check.py

echo.
echo =======================================================
echo 🎉 Test suite completed successfully!
echo.
echo 📊 Coverage report generated: htmlcov/index.html
echo 🚀 Bot is ready for deployment
echo =======================================================
echo.
pause
