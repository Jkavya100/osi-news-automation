@echo off
REM ============================================
REM OSI News Automation - Windows Task Scheduler Setup
REM ============================================
REM This script creates a Windows scheduled task to run the pipeline every 3 hours
REM Run as Administrator for best results

echo.
echo ============================================
echo OSI News Automation - Scheduler Setup
echo ============================================
echo.

REM Get current directory and project root
set SCRIPT_DIR=%~dp0
set PROJECT_DIR=%SCRIPT_DIR%..

REM Get Python path
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python not found in PATH
    echo Please install Python 3.11+ and add to PATH
    pause
    exit /b 1
)

REM Get full Python path
for /f "delims=" %%i in ('where python') do set PYTHON_PATH=%%i

echo Python found: %PYTHON_PATH%
echo Project directory: %PROJECT_DIR%
echo.

REM Check if task already exists
schtasks /query /tn "OSI News Automation" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo Task "OSI News Automation" already exists.
    echo.
    choice /C YN /M "Do you want to delete and recreate it"
    if errorlevel 2 goto :end
    if errorlevel 1 (
        echo Deleting existing task...
        schtasks /delete /tn "OSI News Automation" /f
        echo.
    )
)

REM Create the scheduled task
echo Creating scheduled task...
echo.

schtasks /create ^
    /tn "OSI News Automation" ^
    /tr "\"%PYTHON_PATH%\" \"%PROJECT_DIR%\run_automation.py\" --mode once" ^
    /sc hourly ^
    /mo 3 ^
    /st 00:00 ^
    /f

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ============================================
    echo ✅ SUCCESS: Scheduled task created!
    echo ============================================
    echo.
    echo Task Name: OSI News Automation
    echo Schedule: Every 3 hours
    echo Start Time: 00:00 (midnight)
    echo Command: python run_automation.py --mode once
    echo.
    echo ============================================
    echo Useful Commands:
    echo ============================================
    echo.
    echo View task details:
    echo   schtasks /query /tn "OSI News Automation" /v
    echo.
    echo Run task now:
    echo   schtasks /run /tn "OSI News Automation"
    echo.
    echo Delete task:
    echo   schtasks /delete /tn "OSI News Automation" /f
    echo.
    echo View task history:
    echo   Open Task Scheduler GUI and check History tab
    echo.
) else (
    echo.
    echo ❌ ERROR: Failed to create scheduled task
    echo Try running this script as Administrator
    echo.
)

:end
echo.
pause
