@echo off
echo ================================================
echo   STARTING POSTGRESQL FOR SECOND BRAIN
echo ================================================
echo.

cd C:\tools\second-brain

echo Starting PostgreSQL with pgvector...
docker-compose up -d postgres

if errorlevel 1 (
    echo.
    echo ❌ ERROR: Docker is not running!
    echo.
    echo Please start Docker Desktop first!
    pause
    exit /b 1
)

echo.
echo ✅ PostgreSQL starting...
echo.
echo Waiting for database to be ready...
timeout /t 10 /nobreak

echo.
echo ================================================
echo   POSTGRESQL SHOULD BE RUNNING!
echo ================================================
echo.
echo Now go back to WSL2 and run:
echo   ./start_postgres_only.sh
echo.
echo Or test the connection:
echo   docker exec -it secondbrain-postgres psql -U secondbrain
echo.
pause