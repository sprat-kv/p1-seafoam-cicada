@echo off
REM Run end-to-end tests for Ticket Triage API
REM Make sure the API server is running first!

echo ========================================
echo Ticket Triage API - End-to-End Tests
echo ========================================
echo.
echo Make sure the API server is running:
echo   uvicorn app.main:app --reload
echo.
pause

python test_e2e.py

pause
