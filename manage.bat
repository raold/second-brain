@echo off
REM Docker management script for Windows
REM Use start-dev.bat for initial setup and startup

if "%1"=="start" (
    echo Starting Second Brain services...
    docker-compose up -d
    echo Services running at http://localhost:8000
) else if "%1"=="stop" (
    echo Stopping services...
    docker-compose down
) else if "%1"=="restart" (
    echo Restarting app...
    docker-compose restart app
) else if "%1"=="logs" (
    docker-compose logs -f app
) else if "%1"=="test" (
    echo Running tests...
    docker exec -it secondbrain-app python -m pytest tests/unit/ -v
) else if "%1"=="shell" (
    echo Opening shell in app container...
    docker exec -it secondbrain-app /bin/bash
) else if "%1"=="db" (
    echo Connecting to database...
    docker exec -it secondbrain-postgres psql -U secondbrain
) else if "%1"=="format" (
    echo Formatting code...
    docker exec -it secondbrain-app black .
    docker exec -it secondbrain-app isort .
) else if "%1"=="lint" (
    echo Linting code...
    docker exec -it secondbrain-app ruff check .
) else (
    echo Usage: %0 {start^|stop^|restart^|logs^|test^|shell^|db^|format^|lint}
    exit /b 1
)