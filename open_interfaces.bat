@echo off
echo Opening Second Brain Interfaces...
echo.

REM Open Swagger UI in default browser
start http://localhost:8001/docs

REM Open Dashboard
start dashboard.html

REM Open Simple UI (commented out - uncomment if you want both)
REM start simple_ui.html

echo.
echo ✅ Interfaces opened in your browser!
echo.
echo Available at:
echo - Swagger API Docs: http://localhost:8001/docs
echo - Dashboard: dashboard.html
echo - Simple UI: simple_ui.html
echo.
pause