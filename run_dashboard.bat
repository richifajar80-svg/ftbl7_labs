@echo off
echo ================================================
echo  FTBL7 Labs - Install ^& Run Dashboard
echo ================================================
echo.

cd /d "%~dp0"

echo [1/2] Install dependencies...
pip install -r requirements.txt
echo.

echo [2/2] Menjalankan Streamlit dashboard...
echo.
echo  Akses dari laptop : http://localhost:8501
echo  Akses dari HP Android (WiFi sama):
echo.

for /f "tokens=2 delims=:" %%A in ('ipconfig ^| findstr /i "IPv4 Address"') do (
    set "IP=%%A"
    setlocal enabledelayedexpansion
    set "IP=!IP: =!"
    echo     http://!IP!:8501
    endlocal
)

echo.
echo  Pastikan HP ^& laptop terhubung ke WiFi yang sama!
echo  Tekan Ctrl+C di window ini untuk stop.
echo.
python -m streamlit run app.py --server.address=0.0.0.0 --server.port=8501

pause
