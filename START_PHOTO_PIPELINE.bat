@echo off
echo ========================================
echo   PHOTO PIPELINE STARTUP SCRIPT
echo   Version 5.0.0 - WORKING STATE
echo ========================================
echo.

echo [1/5] Checking Google Drive...
if exist "G:\My Drive\Takeout" (
    echo ✓ Google Drive mounted at G:\
) else (
    echo ✗ Google Drive NOT found! Please start Google Drive first.
    pause
    exit /b 1
)

echo.
echo [2/5] Checking Docker...
docker ps >nul 2>&1
if %errorlevel% neq 0 (
    echo ✗ Docker not running! Starting Docker Desktop...
    start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    echo Waiting for Docker to start...
    timeout /t 20 /nobreak >nul
)
docker ps | findstr secondbrain-app >nul 2>&1
if %errorlevel% neq 0 (
    echo Starting Second Brain containers...
    docker-compose up -d
    timeout /t 10 /nobreak >nul
) else (
    echo ✓ Docker containers running
)

echo.
echo [3/5] Checking Second Brain API...
curl -s http://localhost:8000/ | findstr "5.0.0" >nul 2>&1
if %errorlevel% neq 0 (
    echo ✗ Wrong version or not running! Restarting...
    docker-compose restart app
    timeout /t 10 /nobreak >nul
)
echo ✓ Second Brain v5.0.0 running

echo.
echo [4/5] Checking LLaVA...
curl -s http://127.0.0.1:1234/ >nul 2>&1
if %errorlevel% neq 0 (
    echo ✗ LLaVA not running at port 1234
    echo Please start LM Studio with LLaVA model
) else (
    echo ✓ LLaVA service available
)

echo.
echo [5/6] Checking CLIP Service...
curl -s http://localhost:8002/ >nul 2>&1
if %errorlevel% neq 0 (
    echo ✗ CLIP not running at port 8002
    echo Starting CLIP service...
    cd services\gpu\clip
    start cmd /k python clip_api.py
    cd ..\..\..
    timeout /t 5 /nobreak >nul
) else (
    echo ✓ CLIP service available
)

echo.
echo [6/6] Opening Photo Pipeline Dashboard...
start http://localhost:8000/api/photo-pipeline/

echo.
echo ========================================
echo   PHOTO PIPELINE READY!
echo ========================================
echo.
echo Dashboard: http://localhost:8000/api/photo-pipeline/
echo.
echo If START button doesn't work:
echo   Run: python app/services/photo_processor.py
echo.
pause