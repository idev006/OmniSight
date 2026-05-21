@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul 2>&1
title OmniSight - First Time Setup

REM Always run from the directory that contains this script.
cd /d "%~dp0"

set "ROOT=%~dp0"
set "VENV_DIR=%ROOT%my_env"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"
set "VENV_PIP=%VENV_DIR%\Scripts\pip.exe"
set "VENV_ALEMBIC=%VENV_DIR%\Scripts\alembic.exe"

REM Local ports in this workspace are intentionally shifted by docker-compose.override.yml
REM because this machine already has other dev services on 5432, 6379, 9090, and 3000.
set "BACKEND_URL=http://localhost:8000"
set "FRONTEND_URL=https://localhost:5173"
set "POSTGRES_URL=localhost:15432"
set "REDIS_URL=localhost:16379"
set "QDRANT_URL=http://localhost:6333/dashboard"
set "PROMETHEUS_URL=http://localhost:19090"
set "GRAFANA_URL=http://localhost:13000"

color 0A
echo.
echo  OmniSight - AI Face Recognition Attendance System
echo  First Time / Repair Setup
echo  =================================================
echo.

REM ---------------------------------------------------------------------------
REM Prerequisite checks
REM ---------------------------------------------------------------------------

echo [CHECK] Python 3.12...
set "PYTHON_EXE="
set "PYTHON_ARGS="
set "VENV_VALID=0"

if exist "%VENV_PY%" (
    "%VENV_PY%" --version 2>nul | findstr /C:"Python 3.12" >nul
    if not errorlevel 1 (
        set "PYTHON_EXE=%VENV_PY%"
        set "VENV_VALID=1"
    )
)

if not defined PYTHON_EXE (
    python --version 2>nul | findstr /C:"Python 3.12" >nul
    if not errorlevel 1 (
        set "PYTHON_EXE=python"
    )
)

if not defined PYTHON_EXE (
    py -3.12 --version >nul 2>&1
    if not errorlevel 1 (
        set "PYTHON_EXE=py"
        set "PYTHON_ARGS=-3.12"
    )
)

if not defined PYTHON_EXE (
    echo.
    echo  [ERROR] Python 3.12 was not found.
    echo.
    echo  Install Python 3.12 from https://www.python.org/downloads/
    echo  During install, enable "Add python.exe to PATH", then open a new terminal.
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%v in ('"%PYTHON_EXE%" %PYTHON_ARGS% --version 2^>^&1') do echo   %%v

echo [CHECK] Node.js v18+...
node --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  [ERROR] Node.js was not found.
    echo  Install the LTS version from https://nodejs.org/
    echo.
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('node --version') do set "NODE_FULL=%%v"
set "NODE_MAJOR_STR=!NODE_FULL:v=!"
for /f "delims=." %%m in ("!NODE_MAJOR_STR!") do set "NODE_MAJOR=%%m"
if !NODE_MAJOR! LSS 18 (
    echo.
    echo  [ERROR] Node.js v18 or later is required. Found: !NODE_FULL!
    echo.
    pause
    exit /b 1
)
echo   Node.js !NODE_FULL!

echo [CHECK] npm...
call npm --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  [ERROR] npm was not found. Reinstall Node.js LTS.
    echo.
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('call npm --version') do echo   npm %%v

echo [CHECK] Git...
git --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  [ERROR] Git was not found.
    echo  Install Git for Windows from https://git-scm.com/download/win
    echo.
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('git --version') do echo   %%v

echo [CHECK] Docker Desktop...
docker info >nul 2>&1
if errorlevel 1 (
    echo.
    echo  [ERROR] Docker is not running or not installed.
    echo.
    echo  Steps:
    echo    1. Install Docker Desktop.
    echo    2. Start Docker Desktop and wait until it is ready.
    echo    3. Re-run this script.
    echo.
    pause
    exit /b 1
)
docker compose version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  [ERROR] Docker Compose plugin was not found.
    echo  Update Docker Desktop, then re-run this script.
    echo.
    pause
    exit /b 1
)
echo   Docker OK

echo.
echo  All prerequisites passed.
echo.

REM ---------------------------------------------------------------------------
REM Step 1 - Python virtual environment
REM ---------------------------------------------------------------------------

echo [1/5] Preparing Python virtual environment...
if "!VENV_VALID!"=="1" (
    echo   Existing my_env is valid.
) else (
    if exist "%VENV_DIR%" (
        set "BACKUP_DIR=my_env.bak.!RANDOM!!RANDOM!"
        echo   Existing my_env is broken or incomplete.
        echo   Renaming it to !BACKUP_DIR!
        ren "%VENV_DIR%" "!BACKUP_DIR!"
        if errorlevel 1 (
            echo.
            echo  [ERROR] Could not rename existing my_env.
            echo  Close terminals/processes using it, then re-run this script.
            echo.
            pause
            exit /b 1
        )
    )

    "%PYTHON_EXE%" %PYTHON_ARGS% -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo.
        echo  [ERROR] Failed to create my_env.
        echo.
        pause
        exit /b 1
    )
)

"%VENV_PY%" --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  [ERROR] my_env Python is not runnable.
    echo.
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('"%VENV_PY%" --version 2^>^&1') do echo   %%v
echo.

REM ---------------------------------------------------------------------------
REM Step 2 - Python packages
REM ---------------------------------------------------------------------------

echo [2/5] Installing Python packages...
echo   Upgrading pip...
"%VENV_PY%" -m pip install --upgrade pip --quiet
if errorlevel 1 (
    echo.
    echo  [WARNING] pip upgrade failed. Continuing to requirements install.
)

echo   Installing requirements.txt...
"%VENV_PY%" -m pip install -r "%ROOT%requirements.txt"
if errorlevel 1 (
    echo.
    echo  [ERROR] Python package install failed.
    echo.
    echo  Common Windows fix:
    echo    Install Microsoft C++ Build Tools:
    echo    https://aka.ms/vs/17/release/vs_BuildTools.exe
    echo    Select "Desktop development with C++".
    echo.
    pause
    exit /b 1
)

"%VENV_PY%" -m pip check
if errorlevel 1 (
    echo.
    echo  [ERROR] pip check found broken dependencies.
    echo.
    pause
    exit /b 1
)
echo   Python dependencies OK.
echo.

REM ---------------------------------------------------------------------------
REM Step 3 - Docker services
REM ---------------------------------------------------------------------------

echo [3/5] Starting Docker services...
docker compose config >nul
if errorlevel 1 (
    echo.
    echo  [ERROR] docker compose config is invalid.
    echo.
    pause
    exit /b 1
)

docker compose up -d
if errorlevel 1 (
    echo.
    echo  [ERROR] docker compose failed.
    echo.
    echo  If this is a port conflict, check:
    echo    docker compose ps
    echo    netstat -ano ^| findstr ":5432 :6379 :9090 :3000"
    echo.
    pause
    exit /b 1
)

echo   Waiting for PostgreSQL...
set /a PG_ELAPSED=0
:wait_postgres
docker exec omnisight_postgres pg_isready -U omnisight -q >nul 2>&1
if not errorlevel 1 goto postgres_ready

set /a PG_ELAPSED+=3
if !PG_ELAPSED! GEQ 90 (
    echo.
    echo  [ERROR] PostgreSQL did not become ready within 90 seconds.
    echo  Check logs with: docker logs omnisight_postgres
    echo.
    pause
    exit /b 1
)
timeout /t 3 /nobreak >nul
goto wait_postgres

:postgres_ready
echo   PostgreSQL ready after !PG_ELAPSED!s.
echo.

REM ---------------------------------------------------------------------------
REM Step 4 - Database migrations
REM ---------------------------------------------------------------------------

echo [4/5] Running database migrations...
cd /d "%ROOT%backend"
"%VENV_ALEMBIC%" upgrade head
if errorlevel 1 (
    echo.
    echo  [ERROR] Alembic migration failed.
    echo.
    echo  Check that backend\.env points to the Docker port used by this repo.
    echo  Current expected DB endpoint: %POSTGRES_URL%
    echo.
    cd /d "%ROOT%"
    pause
    exit /b 1
)
cd /d "%ROOT%"
echo   Database schema OK.
echo.

REM ---------------------------------------------------------------------------
REM Step 5 - Frontend dependencies
REM ---------------------------------------------------------------------------

echo [5/5] Installing frontend packages...
cd /d "%ROOT%frontend"
call npm install --loglevel error
if errorlevel 1 (
    echo.
    echo  [ERROR] npm install failed.
    echo  Try deleting frontend\node_modules and re-running this script.
    echo.
    cd /d "%ROOT%"
    pause
    exit /b 1
)
cd /d "%ROOT%"
echo   Frontend dependencies OK.
echo.

REM ---------------------------------------------------------------------------
REM Optional anti-spoofing model
REM ---------------------------------------------------------------------------

echo [OPTIONAL] Anti-spoofing model (MiniFASNet, about 2 MB)
if exist "%ROOT%models\anti_spoof\2.7_80x80_MiniFASNetV2.onnx" (
    echo   Model already exists.
) else (
    echo   Enables liveness detection during enrollment.
    set /p DOWNLOAD_SPOOF="  Download anti-spoof model now? [Y/n]: "
    if /i "!DOWNLOAD_SPOOF!"=="n" goto skip_antispoof

    "%VENV_PY%" "%ROOT%backend\scripts\download_anti_spoof_model.py"
    if errorlevel 1 (
        echo   [WARNING] Download failed. Retry later with:
        echo     my_env\Scripts\python.exe backend\scripts\download_anti_spoof_model.py
    ) else (
        echo   Anti-spoof model ready.
    )
)
goto done_antispoof

:skip_antispoof
echo   Skipped. Retry later with:
echo     my_env\Scripts\python.exe backend\scripts\download_anti_spoof_model.py

:done_antispoof
echo.

REM ---------------------------------------------------------------------------
REM Done
REM ---------------------------------------------------------------------------

echo =================================================
echo   Setup complete.
echo =================================================
echo.
echo   Next step:
echo     Double-click start-dev.bat
echo.
echo   URLs after start-dev.bat:
echo     Frontend   %FRONTEND_URL%
echo     API Docs   %BACKEND_URL%/docs
echo     Qdrant     %QDRANT_URL%
echo     Prometheus %PROMETHEUS_URL%
echo     Grafana    %GRAFANA_URL%  (admin / admin)
echo.
echo   Local service ports:
echo     PostgreSQL %POSTGRES_URL%
echo     Redis      %REDIS_URL%
echo.
echo   Default login:
echo     admin / admin
echo.
echo   Note:
echo     First backend start may take a few minutes while InsightFace
echo     downloads/warms up the buffalo_l model.
echo.

endlocal
pause
