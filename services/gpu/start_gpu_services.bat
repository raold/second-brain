@echo off
REM Start GPU services for second-brain on Windows

echo Starting Second-Brain GPU Services...
echo.

REM Check for NVIDIA GPU
nvidia-smi >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: NVIDIA GPU not detected. Please ensure CUDA is installed.
    pause
    exit /b 1
)

echo GPU detected:
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
echo.

REM Create models directory if not exists
if not exist "models" mkdir models

REM Start services with Docker Compose
echo Starting Docker services...
docker-compose -f docker-compose.gpu.yml up -d

if %errorlevel% neq 0 (
    echo ERROR: Failed to start Docker services.
    echo Make sure Docker Desktop is running and WSL2 is configured.
    pause
    exit /b 1
)

echo.
echo Waiting for services to start...
timeout /t 10 /nobreak >nul

echo.
echo Checking service status:
echo.

REM Check CLIP
curl -s http://localhost:8002/clip/status >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] CLIP Service: Running on port 8002
) else (
    echo [WAIT] CLIP Service: Starting up...
)

REM Check LLaVA
curl -s http://localhost:8003/llava/status >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] LLaVA Service: Running on port 8003
) else (
    echo [WAIT] LLaVA Service: Starting up...
)

echo.
echo GPU Services Dashboard:
echo   - CLIP API: http://localhost:8002/docs
echo   - LLaVA API: http://localhost:8003/docs
echo.
echo To view logs: docker-compose -f docker-compose.gpu.yml logs -f
echo To stop services: docker-compose -f docker-compose.gpu.yml down
echo.
pause