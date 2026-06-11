@echo off
chcp 65001 >nul
:: Job collector — run daily via Windows Task Scheduler.
:: %~dp0 resolves to this file's directory (project root), so paths stay portable.

cd /d "%~dp0"

:: Activate virtualenv if present
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
) else if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

:: Run the collector, append output to logs\collector.log
if not exist "logs" mkdir logs
python scripts\run_collector.py >> logs\collector.log 2>&1
