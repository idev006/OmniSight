@echo off
title OmniSight - Alembic Migration
cd /d "%~dp0backend"
echo ========================================
echo   OmniSight - Database Migration
echo ========================================
echo.

if "%1"=="" (
    echo Usage:
    echo   migrate.bat upgrade        -- apply all pending migrations
    echo   migrate.bat downgrade      -- rollback one step
    echo   migrate.bat autogenerate   -- generate new migration from ORM changes
    echo   migrate.bat history        -- show migration history
    echo.
    echo Running: upgrade head  ^(default^)
    echo.
    "%~dp0my_env\Scripts\alembic" upgrade head
) else if "%1"=="upgrade" (
    "%~dp0my_env\Scripts\alembic" upgrade head
) else if "%1"=="downgrade" (
    "%~dp0my_env\Scripts\alembic" downgrade -1
) else if "%1"=="autogenerate" (
    set /p MSG="Migration message: "
    "%~dp0my_env\Scripts\alembic" revision --autogenerate -m "%MSG%"
) else if "%1"=="history" (
    "%~dp0my_env\Scripts\alembic" history --verbose
) else (
    echo Unknown command: %1
)

echo.
pause
