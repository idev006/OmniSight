@echo off
title OmniSight — First Time Setup
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

REM ── Check prerequisites ────────────────────────────────────────────────────

echo [CHECK] Python 3.12...
python --version 2>nul | findstr /C:"Python 3.12" >nul
if errorlevel 1 (
    echo.
    echo  [ERROR] Python 3.12 not found!
    echo  Download: https://www.python.org/downloads/release/python-3120/
    echo  Make sure to check "Add Python to PATH" during install.
    echo.
    pause
    exit /b 1
)
echo   OK

echo [CHECK] Node.js...
node --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  [ERROR] Node.js not found!
    echo  Download: https://nodejs.org  (LTS version)
    echo.
    pause
    exit /b 1
)
echo   OK

echo [CHECK] Docker...
docker info >nul 2>&1
if errorlevel 1 (
    echo.
    echo  [WARNING] Docker not running or not installed.
    echo  Please start Docker Desktop and re-run this script.
    echo  Download: https://www.docker.com/products/docker-desktop
    echo.
    pause
    exit /b 1
)
echo   OK

echo.
echo  All prerequisites found!
echo.
echo ─────────────────────────────────────────────────────────────────────────
echo.

REM ── Step 1: Python virtual environment ─────────────────────────────────────
echo [1/5] Creating Python virtual environment (my_env)...
if exist my_env (
    echo   Already exists — skipping
) else (
    python -m venv my_env
    if errorlevel 1 (
        echo  [ERROR] Failed to create venv
        pause
        exit /b 1
    )
    echo   Done
)
echo.

REM ── Step 2: Install Python dependencies ────────────────────────────────────
echo [2/5] Installing Python packages (this may take 3-5 minutes)...
my_env\Scripts\pip.exe install --upgrade pip --quiet
my_env\Scripts\pip.exe install -r requirements.txt --quiet
if errorlevel 1 (
    echo.
    echo  [ERROR] pip install failed.
    echo  If InsightFace fails, try: install_insightface_win.bat
    echo.
    pause
    exit /b 1
)
echo   Done
echo.

REM ── Step 3: Start Docker services ──────────────────────────────────────────
echo [3/5] Starting Docker services (PostgreSQL, Qdrant, Redis)...
docker compose up -d
if errorlevel 1 (
    echo  [ERROR] docker compose failed. Is Docker Desktop running?
    pause
    exit /b 1
)
echo   Waiting for services to be ready...
timeout /t 5 /nobreak >nul
echo   Done
echo.

REM ── Step 4: Database migration ─────────────────────────────────────────────
echo [4/5] Running database migrations...
cd backend
..\my_env\Scripts\alembic upgrade head
if errorlevel 1 (
    echo  [ERROR] Migration failed. Check that PostgreSQL is running.
    cd ..
    pause
    exit /b 1
)
cd ..
echo   Done
echo.

REM ── Step 5: Frontend dependencies ──────────────────────────────────────────
echo [5/5] Installing frontend packages (npm install)...
cd frontend
call npm install --loglevel error
if errorlevel 1 (
    echo  [ERROR] npm install failed.
    cd ..
    pause
    exit /b 1
)
cd ..
echo   Done
echo.

REM ── Done ───────────────────────────────────────────────────────────────────
echo =========================================================================
echo.
echo   Setup complete!
echo.
echo   To start development:
echo     Double-click  start-dev.bat
echo.
echo   Then open:
echo     Frontend  →  http://localhost:5173
echo     API Docs  →  http://localhost:8000/docs
echo     Grafana   →  http://localhost:3000  (admin / admin)
echo.
echo   Default login:
echo     Username: admin
echo     Password: admin
echo.
echo =========================================================================
echo.
pause
