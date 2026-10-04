@echo off
chcp 65001 >nul
rem 더블클릭해서 실행. 설정을 바꾸려면 명령 창에서 run.bat --res 1280x720 처럼 붙인다.
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" goto nosetup
".venv\Scripts\python.exe" run.py %*
goto end

:nosetup
echo [안내] 아직 준비가 안 됐습니다. 먼저 setup.bat 을 더블클릭하세요.

:end
echo.
pause
