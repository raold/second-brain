@echo off
cd /d C:\Users\dro\second-brain
C:\Users\dro\AppData\Local\Programs\Python\Python310\python.exe -m uvicorn app.app:app --reload --port 8000