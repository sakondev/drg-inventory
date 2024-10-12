@echo off
echo Starting the data processing pipeline...

:: รัน main_process.py
python main_process.py

:: ตรวจสอบสถานะการทำงาน
if %errorlevel% neq 0 (
    echo An error occurred during the process.
    pause
    exit /b %errorlevel%
)

echo Data processing completed successfully.
pause