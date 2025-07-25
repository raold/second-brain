@echo off
echo Fixing Python virtual environment...
cd /d C:\Users\dro\second-brain

echo Removing old virtual environment...
if exist .venv rmdir /s /q .venv

echo Creating new virtual environment with correct Python...
C:\Users\dro\AppData\Local\Programs\Python\Python310\python.exe -m venv .venv

echo Activating virtual environment...
call .venv\Scripts\activate.bat

echo Installing requirements...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo Done! Now run: run_server_fixed.bat
pause