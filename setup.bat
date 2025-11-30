@echo off
REM FastAPI Speech Translation API - Setup Script
REM For Windows

setlocal EnableDelayedExpansion

echo ==========================================
echo FastAPI Speech Translation API Setup
echo ==========================================
echo.

REM Check for Python 3.13 or higher
echo Checking for Python 3.13...

set PYTHON_CMD=
set PYTHON_VERSION=

REM Try different Python commands
for %%P in (python3.13 python3 python py) do (
    where %%P >nul 2>nul
    if !errorlevel! equ 0 (
        for /f "tokens=2" %%V in ('%%P --version 2^>^&1') do (
            set VERSION=%%V
            for /f "tokens=1,2 delims=." %%A in ("!VERSION!") do (
                set MAJOR=%%A
                set MINOR=%%B
                if !MAJOR! equ 3 if !MINOR! geq 13 (
                    set PYTHON_CMD=%%P
                    set PYTHON_VERSION=!VERSION!
                    goto :found_python
                )
            )
        )
    )
)

:found_python
if "%PYTHON_CMD%"=="" (
    echo [ERROR] Python 3.13 or higher is required but not found!
    echo.
    echo Please install Python 3.13+ from:
    echo   - https://www.python.org/downloads/
    echo.
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

echo [SUCCESS] Found Python %PYTHON_VERSION% at %PYTHON_CMD%
echo.

REM Check if virtual environment already exists
if exist "venv" (
    echo Virtual environment already exists.
    set /p RECREATE="Do you want to recreate it? (y/N): "
    if /i "!RECREATE!"=="y" (
        echo Removing existing virtual environment...
        rmdir /s /q venv
    ) else (
        echo Using existing virtual environment.
    )
)

REM Create virtual environment if it doesn't exist
if not exist "venv" (
    echo Creating virtual environment...
    %PYTHON_CMD% -m venv venv
    if !errorlevel! neq 0 (
        echo [ERROR] Failed to create virtual environment!
        pause
        exit /b 1
    )
    echo [SUCCESS] Virtual environment created
)

echo.

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip --quiet

echo.

REM Install dependencies
echo Installing dependencies from requirements.txt...
pip install -r requirements.txt

if !errorlevel! neq 0 (
    echo [ERROR] Failed to install dependencies!
    pause
    exit /b 1
)

echo [SUCCESS] All dependencies installed successfully!

echo.
echo ==========================================
echo Setup Complete! 🎉
echo ==========================================
echo.
echo Next steps:
echo   1. Activate the virtual environment:
echo      venv\Scripts\activate
echo.
echo   2. Configure your environment variables:
echo      copy .env.example .env
echo      Then edit .env with your API keys
echo.
echo   3. Make sure Redis is running:
echo      redis-cli ping (should return PONG)
echo      Or use Docker: docker run -d -p 6379:6379 redis:alpine
echo.
echo   4. Start the application:
echo      uvicorn app.main:app --reload
echo.
echo   5. Visit the API documentation:
echo      http://localhost:8000/docs
echo.

pause
