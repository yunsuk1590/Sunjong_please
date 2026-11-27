@echo off
chcp 65001 >nul
rem 처음 한 번 더블클릭: 파이썬 3.11 을 찾아 setup_env.py 를 실행한다.
cd /d "%~dp0"
py -3.11 --version >nul 2>&1
if errorlevel 1 goto nopython
py -3.11 setup_env.py
goto end

:nopython
echo.
echo [안내] 파이썬 3.11 을 찾지 못했습니다.
echo   https://www.python.org/downloads/release/python-3119/ 에서
echo   "Windows installer (64-bit)" 를 받아 설치한 뒤, 이 파일을 다시 더블클릭하세요.

:end
echo.
pause
