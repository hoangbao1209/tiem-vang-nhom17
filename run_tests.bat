@echo off
chcp 65001 >nul
cd /d "%~dp0"

if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)

echo Dang chay bo kiem thu tu dong quy tac nghiep vu (SE104 - Nhom 17)...
echo.
python -m unittest discover -s tests -v
echo.
pause
