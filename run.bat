@echo off
setlocal
title ConnectHub

rem Always run from the ConnectHub folder, no matter where this .bat is started.
cd /d "%~dp0ConnectHub"

echo ============================================================
echo   ConnectHub
echo ============================================================
echo.

rem A full disk silently breaks migrations, Python and the browser cache.
for /f %%a in ('powershell -NoProfile -Command "[math]::Floor((Get-PSDrive C).Free/1MB)"') do set FREEMB=%%a
if not defined FREEMB set FREEMB=9999
if %FREEMB% LSS 500 (
    echo [WARN] Only %FREEMB% MB free on C:.
    echo        Free some space if the server or database fails to start.
    echo.
)

where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python was not found in PATH.
    echo Install Python 3.14+ and tick "Add Python to PATH".
    echo.
    pause
    exit /b 1
)

rem Create the database if MySQL is available. Safe to run every time.
if exist "C:\xampp\mysql\bin\mysql.exe" (
    "C:\xampp\mysql\bin\mysql.exe" -u root -e "CREATE DATABASE IF NOT EXISTS connecthub CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;" >nul 2>&1
)

rem Apply database migrations. Ignore failures so the API can still start in
rem degraded mode and /health can explain what is wrong.
python -m alembic upgrade head >nul 2>&1
if errorlevel 1 (
    echo [WARN] Could not apply database migrations.
    echo        Is MySQL running in the XAMPP Control Panel?
    echo.
)

rem Build the frontend on first run if it has not been built yet.
if not exist "frontend\dist\index.html" (
    if exist "frontend\node_modules" (
        echo Building the frontend for the first time...
        pushd frontend
        call npm run build
        popd
        echo.
    ) else (
        echo [WARN] frontend\dist is missing. Run these once:
        echo        cd frontend
        echo        npm install
        echo        npm run build
        echo.
    )
)

echo Starting the server at http://127.0.0.1:8000
echo API docs:            http://127.0.0.1:8000/docs
echo Health:              http://127.0.0.1:8000/health
echo.
echo Press Ctrl+C to stop.
echo.

rem Open the browser only after /health actually answers, so a slow start does
rem not land on "This site can't be reached".
if /i "%CONNECTHUB_NO_BROWSER%"=="1" goto :server
start "" powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%~dp0ConnectHub\scripts\open_when_ready.ps1"

:server
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

echo.
echo ConnectHub stopped.
pause
