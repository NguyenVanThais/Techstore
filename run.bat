@echo off
rem Chay TechStore: double-click file nay la duoc.
rem %~dp0 = thu muc chua file .bat, nen chay tu dau cung dung.
cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    echo Khong tim thay venv. Chay truoc:  python -m venv venv
    echo roi:  venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)

venv\Scripts\python.exe -m app.main

rem Chi giu cua so lai khi co loi, de doc duoc thong bao.
if errorlevel 1 (
    echo.
    echo App thoat voi loi. Doc thong bao o tren.
    pause
)
