@echo off
chcp 65001 >nul
cd /d "%~dp0"

set "GIT_EXE=git"
where git >nul 2>nul
if errorlevel 1 (
    if exist "C:\Program Files\Git\cmd\git.exe" (
        set "GIT_EXE=C:\Program Files\Git\cmd\git.exe"
    ) else if exist "C:\Program Files (x86)\Git\cmd\git.exe" (
        set "GIT_EXE=C:\Program Files (x86)\Git\cmd\git.exe"
    ) else if exist "%LOCALAPPDATA%\Programs\Git\cmd\git.exe" (
        set "GIT_EXE=%LOCALAPPDATA%\Programs\Git\cmd\git.exe"
    ) else (
        echo [LOI] Khong tim thay Git tren may. Vui long mo Git Bash de push.
        pause
        exit /b 1
    )
)

echo [1/3] Dang them cac file thay doi...
"%GIT_EXE%" add .

echo [2/3] Dang tao commit...
"%GIT_EXE%" commit -m "Cap nhat day du san pham va giao dien quan ly"
if errorlevel 1 (
    echo [Thong bao] Khong co thay doi moi hoac da commit truoc do, tiep tuc day len GitHub...
)

echo [3/3] Dang day code len GitHub (Render se tu dong cap nhat)...
"%GIT_EXE%" push -u origin main --force
if errorlevel 1 (
    echo.
    echo [LOI] Push that bai. Vui long kiem tra mang hoac dang nhap GitHub.
    pause
    exit /b 1
)

echo.
echo [THANH CONG] Da day code len GitHub! Cho 1-2 phut de Render tu dong build lai trang web.
pause
