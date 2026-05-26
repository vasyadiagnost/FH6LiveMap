@echo off
setlocal
cd /d "%~dp0"

REM QR code generation needs the small qrcode package when running from source.
python -c "import qrcode, qrcode.image.svg" >nul 2>nul
if errorlevel 1 (
    echo Installing missing QR dependency: qrcode
    python -m pip install qrcode
)

python fh6_live_map_server.py
pause
