@echo off
REM Second Brain Dashboard Server Management Script for Windows

if "%1"=="" (
    echo Usage: dashboard.bat [start^|stop^|restart^|status^|logs]
    echo.
    echo Commands:
    echo   start    - Start the dashboard server
    echo   stop     - Stop the dashboard server
    echo   restart  - Restart the dashboard server
    echo   status   - Show server status
    echo   logs     - Show recent server logs
    echo.
    exit /b 1
)

python server_manager.py %*
