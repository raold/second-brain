@echo off
cls
echo ================================================================
echo     SECOND BRAIN v4.2.0 - COMPLETE SYSTEM STARTUP
echo     PostgreSQL + pgvector + OpenAI + Full Web Interface
echo ================================================================
echo.

cd C:\tools\second-brain

echo [1/4] Starting PostgreSQL with pgvector...
docker-compose up -d postgres

if errorlevel 1 (
    echo.
    echo ================================================================
    echo     ERROR: Docker Desktop is not running!
    echo     Please start Docker Desktop and try again.
    echo ================================================================
    pause
    exit /b 1
)

echo [2/4] Waiting for database to initialize (15 seconds)...
timeout /t 15 /nobreak > nul

echo [3/4] Database should be ready at localhost:5432
echo.

echo [4/4] Opening interfaces in your browser...
timeout /t 2 /nobreak > nul

REM Open the main landing page
start index.html

REM Open the dashboard
start dashboard.html

REM Open API docs (will work once backend starts)
start http://localhost:8000/docs

echo.
echo ================================================================
echo     POSTGRESQL IS RUNNING!
echo ================================================================
echo.
echo Interfaces opened:
echo   - Landing Page: index.html
echo   - Dashboard: dashboard.html  
echo   - API Docs: http://localhost:8000/docs (once backend starts)
echo.
echo NOW DO THIS IN WSL2:
echo   cd /mnt/c/tools/second-brain
echo   ./start_postgres_only.sh
echo.
echo ================================================================
pause