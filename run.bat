@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist venv (
    echo [1/3] Tao moi truong ao venv...
    python -m venv venv
)
call venv\Scripts\activate.bat
echo [2/3] Cai thu vien...
pip install -q -r requirements.txt
echo [3/3] Chay website tai http://127.0.0.1:5000
python run.py
pause
