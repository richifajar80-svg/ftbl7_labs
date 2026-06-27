@echo off
echo ================================================
echo  FTBL7 Labs - Push to GitHub
echo ================================================
echo.

cd /d "%~dp0"

echo [0/6] Set identitas Git...
git config --global user.email "richifajar80@gmail.com"
git config --global user.name "richifajar"
echo Identitas OK
echo.

echo [1/6] git init...
git init
echo.

echo [2/6] git add semua file...
git add .
echo.

echo [3/6] git commit...
git commit -m "Initial commit: FTBL7 Labs Dashboard v1.0"
echo STATUS: %ERRORLEVEL%
echo.

echo [4/6] set branch main...
git branch -M main
echo.

echo [5/6] remote + push...
git remote remove origin 2>nul
git remote add origin https://github.com/richifajar/ftbl7_labs.git

echo [6/6] Pushing ke GitHub...
git push -u origin main
echo STATUS PUSH: %ERRORLEVEL%
echo.

echo ================================================
echo  Cek: https://github.com/richifajar/ftbl7_labs
echo ================================================
pause
