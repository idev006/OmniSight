@echo off
title OmniSight Dev Launcher
echo ========================================
echo   OmniSight - Dev Mode
echo ========================================
echo.

echo [0/2] Cleaning up old Python processes...
taskkill /F /IM python.exe >nul 2>&1
taskkill /F /IM uvicorn.exe >nul 2>&1
timeout /t 1 /nobreak >nul
echo Done.
echo.

echo [1/2] Starting Backend  (http://localhost:8000)
echo [2/2] Starting Frontend (http://localhost:5173)
echo.
start "OmniSight Backend"  cmd /k "cd /d "%~dp0backend" && "%~dp0my_env\Scripts\python.exe" -m alembic upgrade head && "%~dp0my_env\Scripts\uvicorn" main:app --reload --host 0.0.0.0 --port 8000"
timeout /t 2 /nobreak >nul
start "OmniSight Frontend" cmd /k "cd /d "%~dp0frontend" && npm run dev"
echo.
echo Both services launched in separate windows.
echo Press any key to close this launcher.
pause >nul
