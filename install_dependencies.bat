@echo off
setlocal EnableDelayedExpansion

title Smart Courier - Dependency Installer
cd /d "%~dp0"

echo ======================================================================
echo SMART COURIER ^& PARCEL DELIVERY MANAGEMENT SYSTEM
echo Automated Dependency Installer
echo ======================================================================
echo.

:: 1. Detect Python
echo [*] Detecting installed Python environment...
set "PYTHON_CMD="

where python >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set "PYTHON_CMD=python"
) else (
    where py >nul 2>&1
    if %ERRORLEVEL% EQU 0 (
        set "PYTHON_CMD=py -3"
    )
)

if "%PYTHON_CMD%"=="" (
    echo [x] ERROR: Python was not found in your system PATH.
    echo     Please install Python 3.10+ from https://www.python.org/
    echo     Make sure to check "Add Python to PATH" during installation.
    echo.
    goto :FAIL
)

for /f "tokens=*" %%v in ('%PYTHON_CMD% --version 2^>^&1') do set "PY_VER=%%v"
echo [+] Detected: %PY_VER%

:: 2. Create .venv if missing
if not exist "%~dp0.venv\Scripts\python.exe" (
    echo [*] Virtual environment not found. Creating .venv in project root...
    %PYTHON_CMD% -m venv "%~dp0.venv"
    if %ERRORLEVEL% NEQ 0 (
        echo [x] ERROR: Failed to create virtual environment in "%~dp0.venv".
        goto :FAIL
    )
    echo [+] Virtual environment created successfully.
) else (
    echo [+] Existing virtual environment detected at "%~dp0.venv".
)

:: 3. Set Virtual Environment Python and Pip
set "VENV_PY=%~dp0.venv\Scripts\python.exe"
set "VENV_PIP=%~dp0.venv\Scripts\pip.exe"

if not exist "!VENV_PY!" (
    echo [x] ERROR: Python executable not found in .venv: "!VENV_PY!"
    goto :FAIL
)

:: 4. Activate Virtual Environment
if exist "%~dp0.venv\Scripts\activate.bat" (
    call "%~dp0.venv\Scripts\activate.bat"
)

:: 5. Install Dependencies from requirements.txt
echo [*] Installing / updating dependencies from requirements.txt...
if not exist "%~dp0requirements.txt" (
    echo [x] ERROR: requirements.txt not found in "%~dp0".
    goto :FAIL
)

"!VENV_PY!" -m pip install --quiet --upgrade pip
if %ERRORLEVEL% NEQ 0 (
    echo [*] Notice: Failed to upgrade pip. Proceeding with existing pip...
)

"!VENV_PY!" -m pip install -r "%~dp0requirements.txt"
if %ERRORLEVEL% NEQ 0 (
    echo [x] ERROR: pip install -r requirements.txt failed.
    goto :FAIL
)

:: 6. Verify Installation
echo [*] Verifying core package imports...
"!VENV_PY!" -c "import flask, flask_sqlalchemy, flask_migrate, flask_login, flask_wtf, wtforms, werkzeug, pytest; print('    Core modules verified.')"
if %ERRORLEVEL% NEQ 0 (
    echo [x] ERROR: Dependency verification failed. Some packages are missing.
    goto :FAIL
)

:: 7. Ensure .env exists
if not exist "%~dp0.env" (
    if exist "%~dp0.env.example" (
        copy "%~dp0.env.example" "%~dp0.env" >nul
        echo [+] Created .env configuration from .env.example.
    )
)

echo.
echo ======================================================================
echo [+] SUCCESS: All dependencies installed and verified successfully!
echo     You can now launch the application by running: run.bat
echo ======================================================================
echo.
pause
exit /b 0

:FAIL
echo.
echo ======================================================================
echo [x] INSTALLATION FAILED! Check the error messages above.
echo ======================================================================
echo.
pause
exit /b 1
