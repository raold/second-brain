@echo off
REM Second Brain - Windows Development Environment Starter
REM Starts all services in the correct order

echo ========================================
echo Second Brain Development Environment
echo ========================================
echo.

REM Check if Docker is running
docker version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Docker is not running!
    echo Please start Docker Desktop first.
    pause
    exit /b 1
)

echo [1/4] Starting Docker services...
docker-compose up -d
if %errorlevel% neq 0 (
    echo ERROR: Failed to start Docker services
    pause
    exit /b 1
)

echo.
echo [2/4] Waiting for services to be ready...
timeout /t 5 >nul

echo.
echo [3/4] Starting CLIP service (GPU)...
start "CLIP Service" cmd /k "cd services\gpu\clip && python clip_api.py"

echo.
echo [4/4] Services Status:
echo ----------------------------------------
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | findstr "second"
echo.
echo ========================================
echo All services started successfully!
echo ========================================
echo.
echo Web Interfaces:
echo - Main App:        http://localhost:8000
echo - API Docs:        http://localhost:8000/docs  
echo - Photo Pipeline:  http://localhost:8000/static/photo-pipeline.html
echo - Database Admin:  http://localhost:8080
echo - LM Studio:       http://localhost:1234
echo.
echo GPU Services:
echo - CLIP (8002):     Running in separate window
echo - LM Studio:       Start manually if needed
echo.
echo To stop all services: docker-compose down
echo ========================================
pause