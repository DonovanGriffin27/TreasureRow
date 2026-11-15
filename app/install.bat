@echo off
REM Jonah Goodwine
REM CSC 404 - Fall 26'
REM Iteration 4 - install.bat
REM One-time setup for Treasure Row on Windows. Double-click to run.
REM 1. checks for Python 3.12 or newer
REM 2. creates the virtual environment (venv)
REM 3. installs the packages in requirements.txt
REM 4. creates .env and the local database (backend\install_setup.py)
REM 5. creates the tables (backend\init_db.py)

setlocal
REM always run from the app folder, even if double-clicked from somewhere else
cd /d "%~dp0"

echo ==========================================
echo   Treasure Row installer
echo ==========================================
echo.

REM ---- 1. find Python 3.12+ (py launcher first, then python on PATH)
set "PY="
for %%C in ("py -3.13" "py -3.12" "py -3" "python") do (
    if not defined PY (
        %%~C -c "import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)" >nul 2>&1 && set "PY=%%~C"
    )
)

if not defined PY (
    echo ERROR: Python 3.12 or newer was not found.
    echo Install it from https://www.python.org/downloads/
    echo and check "Add Python to PATH" during the install, then run install.bat again.
    goto :fail
)
for /f "delims=" %%V in ('%PY% --version') do echo [1/5] Found %%V

REM ---- 2. virtual environment
if exist "venv\Scripts\python.exe" (
    echo [2/5] Virtual environment already exists
) else (
    echo [2/5] Creating virtual environment...
    %PY% -m venv venv
    if errorlevel 1 goto :fail
)

REM ---- 3. packages
echo [3/5] Installing packages - this can take a minute...
venv\Scripts\python.exe -m pip install --upgrade pip --quiet
venv\Scripts\python.exe -m pip install -r requirements.txt --quiet
if errorlevel 1 goto :fail

REM ---- 4. .env settings and the local database
echo [4/5] Setting up .env and the local database...
venv\Scripts\python.exe backend\install_setup.py
if errorlevel 1 goto :fail

REM ---- 5. tables
echo [5/5] Creating database tables...
venv\Scripts\python.exe backend\init_db.py
if errorlevel 1 goto :fail

echo.
echo ==========================================
echo   Install complete!
echo   Double-click "Launch TreasureRow.bat" to start the app.
echo ==========================================
pause
exit /b 0

:fail
echo.
echo Install did not finish. Read the message above, fix it, and run install.bat again.
pause
exit /b 1
