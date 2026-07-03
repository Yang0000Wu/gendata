@echo off
cd /d "%~dp0backend"
echo Installing dependencies...
pip install -r ..\requirements.txt -q
echo Starting GenData...
python main.py
pause
