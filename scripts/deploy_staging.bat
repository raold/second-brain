@echo off
REM Deploy Second Brain to Staging Environment (Windows)

setlocal enabledelayedexpansion

REM Configuration
set COMPOSE_FILE=docker-compose.staging.yml
set ENV_FILE=.env
set ENV_TEMPLATE=.env.staging

echo Second Brain Staging Deployment
echo ===============================

REM Check prerequisites
echo.
echo Checking prerequisites...

where docker >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Docker is not installed or not in PATH
    exit /b 1
)

where docker-compose >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Docker Compose is not installed or not in PATH
    exit /b 1
)

REM Check environment file
if not exist "%ENV_FILE%" (
    if exist "%ENV_TEMPLATE%" (
        echo Creating .env from template...
        copy "%ENV_TEMPLATE%" "%ENV_FILE%"
        echo Please edit .env and set your configuration values
        exit /b 1
    ) else (
        echo Error: No .env file found
        exit /b 1
    )
)

REM Parse command line arguments
set ACTION=%1
if "%ACTION%"=="" set ACTION=deploy

if "%ACTION%"=="deploy" (
    echo.
    echo Deploying staging environment...
    if "%2"=="--build" (
        docker-compose -f %COMPOSE_FILE% up -d --build
    ) else (
        docker-compose -f %COMPOSE_FILE% up -d
    )
    
    echo.
    echo Waiting for services to be ready...
    timeout /t 10 /nobreak >nul
    
    echo.
    echo Deployment complete!
    echo Services available at:
    echo   - Application: http://localhost:8000
    echo   - Database Admin: http://localhost:8081
    echo   - Monitoring: http://localhost:3001

) else if "%ACTION%"=="stop" (
    echo.
    echo Stopping staging environment...
    docker-compose -f %COMPOSE_FILE% stop

) else if "%ACTION%"=="down" (
    echo.
    echo Removing staging environment...
    docker-compose -f %COMPOSE_FILE% down

) else if "%ACTION%"=="clean" (
    echo.
    echo WARNING: This will delete all staging data!
    set /p CONFIRM="Are you sure? (y/N) "
    if /i "%CONFIRM%"=="y" (
        docker-compose -f %COMPOSE_FILE% down -v
        echo Staging environment cleaned
    )

) else if "%ACTION%"=="logs" (
    if "%2"=="" (
        docker-compose -f %COMPOSE_FILE% logs -f
    ) else (
        docker-compose -f %COMPOSE_FILE% logs -f %2
    )

) else if "%ACTION%"=="status" (
    echo.
    echo Staging environment status:
    docker-compose -f %COMPOSE_FILE% ps

) else if "%ACTION%"=="backup" (
    echo.
    echo Creating database backup...
    for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set datetime=%%I
    set BACKUP_FILE=backup_staging_%datetime:~0,8%_%datetime:~8,6%.sql
    docker-compose -f %COMPOSE_FILE% exec -T postgres pg_dump -U secondbrain secondbrain_staging > %BACKUP_FILE%
    echo Backup saved to: %BACKUP_FILE%

) else if "%ACTION%"=="migrate" (
    echo.
    echo Running database migrations...
    docker-compose -f %COMPOSE_FILE% exec app alembic upgrade head
    echo Migrations complete

) else (
    echo Usage: %0 {deploy^|stop^|down^|clean^|logs^|status^|backup^|migrate} [options]
    echo.
    echo Commands:
    echo   deploy [--build]  Deploy staging environment
    echo   stop              Stop all services
    echo   down              Stop and remove containers
    echo   clean             Remove everything including volumes
    echo   logs [service]    View logs (all services or specific)
    echo   status            Show service status
    echo   backup            Create database backup
    echo   migrate           Run database migrations
    exit /b 1
)

endlocal