@echo off
setlocal
cd /d "%~dp0"
title OmniSight - Seed Dummy Employees

echo ========================================
echo   OmniSight - Seed Dummy Employees
echo ========================================
echo.
echo Default: 25,000 employees, EMP00001..EMP25000
echo.

"%~dp0my_env\Scripts\python.exe" "%~dp0backend\scripts\seed_dummy_employees.py" %*

echo.
pause
endlocal
