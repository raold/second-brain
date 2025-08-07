@echo off
echo ========================================
echo   STARTING SECOND BRAIN v4.2.0
echo   FULL SYSTEM WITH POSTGRESQL + AI
echo ========================================
echo.

echo [1/3] Starting PostgreSQL with pgvector...
docker-compose up -d postgres
if errorlevel 1 (
    echo ERROR: Docker not running or accessible!
    echo Please ensure Docker Desktop is running.
    pause
    exit /b 1
)

echo [2/3] Waiting for PostgreSQL to be ready...
timeout /t 5 /nobreak > nul

echo [3/3] PostgreSQL should be running on port 5432
echo.
echo ========================================
echo   DATABASE READY!
echo ========================================
echo.
echo Next steps:
echo 1. Return to WSL2 terminal
echo 2. Run: ./start_backend.sh
echo.
pause