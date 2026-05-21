@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul 2>&1
title OmniSight — First Time Setup

REM ── FIX: always run from the directory that contains THIS script ──────────
REM    Protects against drag-drop, "Run as Administrator", or wrong cwd
cd /d "%~dp0"

color 0A
echo.
echo  ██████╗ ███╗   ███╗███╗   ██╗██╗███████╗██╗ ██████╗ ██╗  ██╗████████╗
echo  ██╔══██╗████╗ ████║████╗  ██║██║██╔════╝██║██╔════╝ ██║  ██║╚══██╔══╝
echo  ██║  ██║██╔████╔██║██╔██╗ ██║██║███████╗██║██║  ███╗███████║   ██║
echo  ██║  ██║██║╚██╔╝██║██║╚██╗██║██║╚════██║██║██║   ██║██╔══██║   ██║
echo  ██████╔╝██║ ╚═╝ ██║██║ ╚████║██║███████║██║╚██████╔╝██║  ██║   ██║
echo  ╚═════╝ ╚═╝     ╚═╝╚═╝  ╚═══╝╚═╝╚══════╝╚═╝ ╚═════╝ ╚═╝  ╚═╝   ╚═╝
echo.
echo  AI Face Recognition Attendance System — First Time Setup
echo  =========================================================
echo.


REM ══════════════════════════════════════════════════════════════════════════
REM  PREREQUISITE CHECKS
REM ══════════════════════════════════════════════════════════════════════════

REM ── Python 3.12 ────────────────────────────────────────────────────────────
echo [CHECK] Python 3.12...
set "PYTHON_CMD="

REM Try 'python' first (standard PATH install)
python --version 2>nul | findstr /C:"Python 3.12" >nul
if not errorlevel 1 (
    set "PYTHON_CMD=python"
) else (
    REM Fallback: Windows Python Launcher 'py -3.12'
    py -3.12 --version >nul 2>&1
    if not errorlevel 1 (
        set "PYTHON_CMD=py -3.12"
    )
)

if "!PYTHON_CMD!"=="" (
    echo.
    echo  [ERROR] Python 3.12 not found.
    echo.
    echo  Options:
    echo    A) Download: https://www.python.org/downloads/release/python-3120/
    echo       ^ Check "Add Python to PATH" during install
    echo    B) Already installed? Open a NEW terminal and re-run this script.
    echo       Or add Python to PATH via System ^> Environment Variables.
    echo.
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('!PYTHON_CMD! --version 2^>^&1') do echo   %%v  ^(command: !PYTHON_CMD!^)

REM ── Node.js v18+ ────────────────────────────────────────────────────────────
echo [CHECK] Node.js (v18+)...
node --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  [ERROR] Node.js not found.
    echo  Download LTS version from: https://nodejs.org
    echo.
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('node --version') do set NODE_FULL=%%v
REM Parse major version number: v20.11.0 -> 20
set NODE_MAJOR_STR=!NODE_FULL:v=!
for /f "delims=." %%m in ("!NODE_MAJOR_STR!") do set NODE_MAJOR=%%m
if !NODE_MAJOR! LSS 18 (
    echo.
    echo  [ERROR] Node.js v18 or later is required. Found: !NODE_FULL!
    echo  Download LTS from: https://nodejs.org
    echo.
    pause
    exit /b 1
)
echo   Node.js !NODE_FULL! — OK

REM ── Git ─────────────────────────────────────────────────────────────────────
echo [CHECK] Git...
git --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  [ERROR] Git not found.
    echo  Download: https://git-scm.com/download/win
    echo.
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('git --version') do echo   %%v — OK

REM ── Docker Desktop ──────────────────────────────────────────────────────────
echo [CHECK] Docker Desktop (must be running)...
docker info >nul 2>&1
if errorlevel 1 (
    echo.
    echo  [ERROR] Docker is not running or not installed.
    echo.
    echo  Steps to fix:
    echo    1. Install: https://www.docker.com/products/docker-desktop
    echo    2. Launch Docker Desktop and WAIT until the whale icon stops animating
    echo    3. Re-run this script
    echo.
    pause
    exit /b 1
)
echo   Docker — OK

echo.
echo  All prerequisites met!
echo.
echo ─────────────────────────────────────────────────────────────────────────
echo.


REM ══════════════════════════════════════════════════════════════════════════
REM  STEP 1 — Python virtual environment
REM ══════════════════════════════════════════════════════════════════════════
echo [1/5] Creating Python virtual environment (my_env)...

REM Check for activate.bat, not just the folder — folder may exist but be broken
if exist "my_env\Scripts\activate.bat" (
    echo   Already exists — skipping
) else (
    if exist my_env (
        echo   Found incomplete my_env — removing and recreating...
        rmdir /s /q my_env
    )
    !PYTHON_CMD! -m venv my_env
    if errorlevel 1 (
        echo.
        echo  [ERROR] Failed to create virtual environment.
        echo  Try: run this script as Administrator, or check available disk space.
        echo.
        pause
        exit /b 1
    )
    echo   Created
)
echo.


REM ══════════════════════════════════════════════════════════════════════════
REM  STEP 2 — Python packages
REM ══════════════════════════════════════════════════════════════════════════
echo [2/5] Installing Python packages (3–5 min on first run)...

echo   Upgrading pip...
"%~dp0my_env\Scripts\pip.exe" install --upgrade pip --quiet
if errorlevel 1 echo   [WARNING] pip upgrade failed — continuing anyway

echo   Installing requirements.txt ...
echo   (output visible so you can see progress and diagnose any failure)
echo.
"%~dp0my_env\Scripts\pip.exe" install -r "%~dp0requirements.txt"
if errorlevel 1 (
    echo.
    echo  ┌─────────────────────────────────────────────────────────────────┐
    echo  │  [ERROR] pip install failed.                                    │
    echo  │                                                                 │
    echo  │  Most common cause on Windows:                                  │
    echo  │  InsightFace requires Microsoft C++ Build Tools.                │
    echo  │                                                                 │
    echo  │  Fix:                                                           │
    echo  │    1. Download: https://aka.ms/vs/17/release/vs_BuildTools.exe  │
    echo  │    2. Select workload: "Desktop development with C++"           │
    echo  │    3. Install, then re-run this script                          │
    echo  │                                                                 │
    echo  │  Alternative: run  install_insightface.bat  separately           │
    echo  └─────────────────────────────────────────────────────────────────┘
    echo.
    pause
    exit /b 1
)
echo.
echo   Done
echo.


REM ══════════════════════════════════════════════════════════════════════════
REM  STEP 3 — Docker services + health check
REM ══════════════════════════════════════════════════════════════════════════
echo [3/5] Starting Docker services (PostgreSQL, Qdrant, Redis, Prometheus, Grafana)...

docker compose up -d
if errorlevel 1 (
    echo.
    echo  [ERROR] docker compose failed.
    echo  Make sure Docker Desktop is fully started (whale icon not animating).
    echo  If first time: docker may need a moment to initialize — wait 30s and retry.
    echo.
    pause
    exit /b 1
)

REM ── Wait for PostgreSQL to accept connections (up to 60s) ──────────────────
echo   Waiting for PostgreSQL to be ready...
set /a PG_ELAPSED=0

:wait_postgres
docker exec omnisight_postgres pg_isready -U omnisight -q >nul 2>&1
if not errorlevel 1 goto postgres_ready

set /a PG_ELAPSED+=3
if !PG_ELAPSED! GEQ 60 (
    echo.
    echo  [ERROR] PostgreSQL did not become ready within 60 seconds.
    echo  Check logs: docker logs omnisight_postgres
    echo.
    pause
    exit /b 1
)
timeout /t 3 /nobreak >nul
goto wait_postgres

:postgres_ready
echo   PostgreSQL ready (after !PG_ELAPSED!s)
echo   Done
echo.


REM ══════════════════════════════════════════════════════════════════════════
REM  STEP 4 — Database migrations
REM ══════════════════════════════════════════════════════════════════════════
echo [4/5] Running database migrations (Alembic)...

REM Use /d flag + absolute paths — safe across drives and cwd changes
cd /d "%~dp0backend"
"%~dp0my_env\Scripts\alembic.exe" upgrade head
if errorlevel 1 (
    echo.
    echo  [ERROR] Alembic migration failed.
    echo.
    echo  Possible causes:
    echo    - PostgreSQL not yet accepting connections (rare — wait 10s, retry)
    echo    - Wrong DATABASE_URL in backend\.env
    echo    - Migration conflict: check with  alembic history
    echo.
    cd /d "%~dp0"
    pause
    exit /b 1
)

cd /d "%~dp0"
echo   Done
echo.


REM ══════════════════════════════════════════════════════════════════════════
REM  STEP 5 — Frontend dependencies
REM ══════════════════════════════════════════════════════════════════════════
echo [5/5] Installing frontend packages (npm install)...

cd /d "%~dp0frontend"
call npm install --loglevel error
if errorlevel 1 (
    echo.
    echo  [ERROR] npm install failed.
    echo  Try: delete the frontend\node_modules folder and re-run this script.
    echo.
    cd /d "%~dp0"
    pause
    exit /b 1
)

cd /d "%~dp0"
echo   Done
echo.


REM ══════════════════════════════════════════════════════════════════════════
REM  STEP 6 (OPTIONAL) — Anti-spoofing model
REM ══════════════════════════════════════════════════════════════════════════
echo.
echo ─────────────────────────────────────────────────────────────────────────
echo  [OPTIONAL] Anti-spoofing model (MiniFASNet, ~2 MB)
echo.
echo  Enables liveness detection during enrollment (rejects printed photos).
echo  Can be skipped now and enabled later via Settings UI.
echo.
set /p DOWNLOAD_SPOOF="  Download anti-spoof model now? [Y/n]: "
if /i "!DOWNLOAD_SPOOF!"=="n" goto skip_antispoof
if /i "!DOWNLOAD_SPOOF!"=="N" goto skip_antispoof

echo   Downloading...
"%~dp0my_env\Scripts\python.exe" "%~dp0backend\scripts\download_anti_spoof_model.py"
if errorlevel 1 (
    echo   [WARNING] Download failed — you can retry later:
    echo     my_env\Scripts\python.exe backend\scripts\download_anti_spoof_model.py
) else (
    echo   Anti-spoof model ready.
)
goto done_antispoof

:skip_antispoof
echo   Skipped. To download later:
echo     my_env\Scripts\python.exe backend\scripts\download_anti_spoof_model.py

:done_antispoof
echo.

REM ══════════════════════════════════════════════════════════════════════════
REM  DONE
REM ══════════════════════════════════════════════════════════════════════════
echo =========================================================================
echo.
echo   Setup complete!  Everything is ready.
echo.
echo ─────────────────────────────────────────────────────────────────────────
echo   NEXT STEP — start development:
echo.
echo     Double-click:  start-dev.bat
echo.
echo ─────────────────────────────────────────────────────────────────────────
echo   URLS (available after start-dev.bat):
echo.
echo     Frontend   http://localhost:5173
echo     API Docs   http://localhost:8000/docs
echo     Grafana    http://localhost:3000    (admin / admin)
echo     Qdrant     http://localhost:6333/dashboard
echo     Prometheus http://localhost:9090
echo.
echo ─────────────────────────────────────────────────────────────────────────
echo   Default login:  admin / admin
echo.
echo ─────────────────────────────────────────────────────────────────────────
echo   NOTE — Face recognition models (~500 MB):
echo     Downloaded automatically on FIRST backend start.
echo     Be patient — first launch takes 2-3 minutes extra.
echo     Subsequent starts are fast (models cached in my_env).
echo.
echo =========================================================================
echo.

endlocal
pause
