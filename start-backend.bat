@echo off
title OmniSight Backend
cd /d "%~dp0backend"
echo Starting OmniSight Backend...
echo Venv: %~dp0my_env
echo.
"%~dp0my_env\Scripts\python.exe" -m alembic upgrade head
"%~dp0my_env\Scripts\uvicorn" main:app --reload --host 0.0.0.0 --port 8000
pause
