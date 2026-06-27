@echo off
echo ================================================
echo  FTBL7 Labs - Push Update ke GitHub
echo ================================================
echo.

cd /d "%~dp0"

echo [0] Set identitas Git...
git config --global user.email "richifajar80@gmail.com"
git config --global user.name "richifajar"

REM -- Inisialisasi repo jika belum ada
if not exist ".git" (
    echo [INIT] Repo baru, melakukan git init...
    git init
    git branch -M main
)

REM -- Pastikan remote origin sudah benar
git remote remove origin 2>nul
git remote add origin https://github.com/richifajar80-svg/ftbl7_labs.git

echo.
echo [1] Menambahkan semua perubahan...
git add .
echo.

echo [2] Commit message (Enter untuk pakai default):
set /p MSG="Pesan commit: "
if "%MSG%"=="" set MSG=Update: FTBL7 Labs Dashboard

git commit -m "%MSG%"
echo.

echo [3] Push ke GitHub...
git branch -M main
git push -u origin main
echo.

if %ERRORLEVEL%==0 (
    echo ================================================
    echo  BERHASIL! Cek di:
    echo  https://github.com/richifajar/ftbl7_labs
    echo ================================================
) else (
    echo ================================================
    echo  Jika ada konflik, jalankan dulu:
    echo    git pull origin main --rebase
    echo  lalu jalankan file ini lagi.
    echo ================================================
)
echo.
pause
