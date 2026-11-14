@echo off
REM Jonah Goodwine
REM CSC 404 - Fall 26'
REM Iteration 4 - Launch TreasureRow.bat
REM Starts Treasure Row on port 5001 and opens the browser.
REM Run install.bat once before using this.

setlocal
cd /d "%~dp0"
set "URL=http://127.0.0.1:5001"

REM make sure install.bat has been run
if not exist "venv\Scripts\python.exe" goto :notinstalled
if not exist ".env" goto :notinstalled

REM if port 5001 is already taken the app is probably already running - just open it
netstat -ano | findstr /r /c:":5001 .*LISTENING" >nul
if not errorlevel 1 (
    echo Something is already running on port 5001 - opening %URL%
    start "" %URL%
    pause
    exit /b 0
)

echo Starting Treasure Row at %URL%
echo Keep this window open while you use the app. Close it or press Ctrl+C to stop.
echo.

REM open the browser after 4 seconds so the server has time to start
start "" /min powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 4; Start-Process '%URL%'"

venv\Scripts\python.exe -m flask --app app run --port 5001
pause
exit /b 0

:notinstalled
echo Treasure Row isn't installed yet. Double-click install.bat first.
pause
exit /b 1
