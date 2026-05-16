@echo off
title Install InsightFace
echo ========================================
echo   Installing InsightFace with MSVC
echo ========================================
echo.

call F:\BuildTools\VC\Auxiliary\Build\vcvarsall.bat x64
if errorlevel 1 (
    echo ERROR: vcvarsall.bat failed
    pause
    exit /b 1
)

set DISTUTILS_USE_SDK=1
set MSSdk=1

echo.
echo Verifying cl.exe is in PATH...
where cl.exe
if errorlevel 1 (
    echo ERROR: cl.exe not found in PATH after vcvarsall
    pause
    exit /b 1
)

echo.
echo Installing build dependencies...
F:\programming\python\OmniSight\my_env\Scripts\pip.exe install cython numpy setuptools wheel

echo.
echo Installing insightface...
F:\programming\python\OmniSight\my_env\Scripts\pip.exe install insightface --no-build-isolation

echo.
pause
