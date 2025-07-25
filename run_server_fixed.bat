@echo off
cd /d C:\Users\dro\second-brain
call .venv\Scripts\activate.bat
python -m uvicorn app.app:app --reload --port 8000