@echo off
REM aINeedJob Quick Start Script (Windows)

echo ======================================
echo aINeedJob V1 - Quick Start Setup
echo ======================================

REM Check Python
echo.
echo [1/7] Checking Python...
python --version >nul 2>&1 || (
    echo Error: Python not found or not in PATH
    pause
    exit /b 1
)
python --version
echo OK

REM Create virtual environment
echo.
echo [2/7] Creating virtual environment...
if not exist venv (
    python -m venv venv
    echo Created
) else (
    echo Already exists
)

REM Activate virtual environment
echo.
echo [3/7] Activating virtual environment...
call venv\Scripts\activate.bat
echo OK

REM Upgrade pip
echo.
echo [4/7] Upgrading pip...
python -m pip install --quiet --upgrade pip
echo OK

REM Install dependencies
echo.
echo [5/7] Installing dependencies...
pip install --quiet -r requirements.txt
echo OK

REM Check .env file
echo.
echo [6/7] Checking environment configuration...
if not exist .env (
    if exist .env.example (
        copy .env.example .env
        echo Created .env from .env.example
        echo.
        echo WARNING: Edit .env with your credentials:
        echo   - DATABASE_URL
        echo   - ANTHROPIC_API_KEY
        echo   - OPENAI_API_KEY
        echo   - ADZUNA_APP_ID and ADZUNA_API_KEY
        echo.
    ) else (
        echo Error: .env.example not found
        pause
        exit /b 1
    )
) else (
    echo .env file exists
)

REM Test imports
echo.
echo [7/7] Testing Python imports...
python -c "import fastapi, langgraph, anthropic, openai, psycopg2" 2>nul || (
    echo Warning: Some imports may not work yet (check .env configuration^)
)
echo OK

REM Summary
echo.
echo ======================================
echo Setup complete!
echo ======================================
echo.
echo Next steps:
echo 1. Edit .env with your API credentials
echo 2. Set up PostgreSQL database
echo 3. Run tests: pytest tests/test_pipeline.py -v
echo 4. Start server: uvicorn api.main:app --reload
echo 5. Visit API docs: http://localhost:8000/docs
echo.
echo For detailed instructions, see SETUP.md
echo ======================================
echo.
pause
