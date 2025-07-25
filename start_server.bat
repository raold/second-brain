@echo off
echo Starting Second Brain FastAPI server...
cd /d C:\Users\dro\second-brain
.venv\Scripts\python.exe -m uvicorn app.app:app --reload --port 8001
pause