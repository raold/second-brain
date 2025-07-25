@echo off
echo Starting Second Brain Server with correct Python...
cd /d C:\Users\dro\second-brain

REM Use the Python from the virtual environment directly
if exist ".venv\Scripts\python.exe" (
    echo Using virtual environment Python...
    .venv\Scripts\python.exe -m uvicorn app.app:app --reload --port 8000
) else (
    echo Virtual environment not found, using system Python...
    C:\Users\dro\AppData\Local\Programs\Python\Python310\python.exe -m uvicorn app.app:app --reload --port 8000
)
pause