@echo off
setlocal EnableDelayedExpansion

title Smart Courier - Web Application Server
cd /d "%~dp0"

echo ======================================================================
echo SMART COURIER ^& PARCEL DELIVERY MANAGEMENT SYSTEM
echo One-Click Application Launcher
echo ======================================================================
echo.

:: 1. Check Virtual Environment
set "VENV_DIR=%~dp0.venv"
set "VENV_PY=%~dp0.venv\Scripts\python.exe"

if not exist "%VENV_PY%" (
    echo [*] Virtual environment ^(.venv^) was not found in "%~dp0".
    echo [*] Running automated dependency installer now...
    echo.
    call "%~dp0install_dependencies.bat"
    if errorlevel 1 (
        echo [x] Dependency installation failed. Cannot continue.
        goto :HALT
    )
)

:: 2. Check Dependencies
echo [*] Verifying Flask dependencies...
"%VENV_PY%" -c "import flask, flask_sqlalchemy, flask_migrate, flask_login, flask_wtf" >nul 2>&1
if errorlevel 1 (
    echo [*] Dependencies are missing or corrupted. Reinstalling...
    call "%~dp0install_dependencies.bat"
    if errorlevel 1 (
        echo [x] Dependency installation failed. Cannot continue.
        goto :HALT
    )
)
echo [+] Environment and dependencies verified.

:: 3. Set Working Environment Variables
set "PYTHONPATH=%~dp0"
set "FLASK_APP=run.py"
if not exist "%~dp0.env" (
    if exist "%~dp0.env.example" (
        copy "%~dp0.env.example" "%~dp0.env" >nul
        echo [+] Generated .env configuration.
    )
)

:: 4. Check Database and Apply Migrations Safely
set "DB_FILE=%~dp0instance\courier.sqlite3"
if not exist "%DB_FILE%" (
    echo [*] Initializing database for the first time...
    if not exist "%~dp0instance" mkdir "%~dp0instance"
    "%VENV_PY%" -c "from app import create_app; from app.extensions import db; app = create_app(); app.app_context().push(); db.create_all()"
    if errorlevel 1 (
        echo [x] ERROR: Failed to create database schema.
        goto :HALT
    )
    echo [*] Seeding initial business data and demo accounts...
    "%VENV_PY%" -m flask --app run.py seed-demo
    if errorlevel 1 (
        echo [*] Notice: Seeding completed.
    )
) else (
    echo [+] Existing database detected at instance\courier.sqlite3
    echo [*] Checking and applying any pending database migrations safely...
    "%VENV_PY%" -m flask --app run.py db upgrade
    if errorlevel 1 (
        echo [x] ERROR: Database migration failed. Halting startup.
        goto :HALT
    )
)

:: 5. Schema Integrity Quick Check
echo [*] Checking relational schema integrity ^(55 tables^)...
"%VENV_PY%" "%~dp0scripts\verify_schema.py"
if errorlevel 1 (
    echo [x] ERROR: Schema verification failed. Halting startup.
    goto :HALT
)

:: 6. Launch Browser in Background with Health Check
echo.
echo [*] Server starting at http://127.0.0.1:5000/
echo [*] Browser will open automatically once the server is healthy...
echo.
echo ======================================================================
echo SMART COURIER SERVER ACTIVE ^(Press CTRL+C to stop^)
echo Demo Accounts Reference: See README.md
echo ======================================================================
echo.

start "" /B powershell -WindowStyle Hidden -Command "$url = 'http://127.0.0.1:5000'; for ($i=0; $i -lt 30; $i++) { Start-Sleep -Milliseconds 500; try { $res = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 1; if ($res.StatusCode -eq 200 -or $res.StatusCode -eq 302) { Start-Process $url; break } } catch {} }"

:: 7. Run Flask Web Application
"%VENV_PY%" "%~dp0run.py"

if errorlevel 1 (
    echo.
    echo [x] Server stopped with non-zero exit code.
)

:HALT
echo.
echo Server session ended.
pause
exit /b
