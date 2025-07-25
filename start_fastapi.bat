@echo off
echo Starting Second Brain FastAPI server...
echo.
echo Server will be available at:
echo   - Ingestion interface: http://localhost:8000/ingestion
echo   - API docs: http://localhost:8000/docs
echo   - Main dashboard: http://localhost:8000/
echo.
C:\Users\dro\second-brain\.venv\Scripts\python.exe run_server.py
pause