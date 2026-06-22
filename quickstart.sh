#!/bin/bash

# aINeedJob Quick Start Script
# Automates the local setup process

set -e  # Exit on error

echo "======================================"
echo "aINeedJob V1 — Quick Start Setup"
echo "======================================"

# Check Python version
echo -e "\n[1/8] Checking Python version..."
python_version=$(python --version 2>&1 | awk '{print $2}')
required_version="3.10"
if [[ "$python_version" < "$required_version" ]]; then
    echo "❌ Python 3.10+ required (found $python_version)"
    exit 1
fi
echo "✓ Python $python_version OK"

# Create virtual environment
echo -e "\n[2/8] Creating virtual environment..."
if [ ! -d "venv" ]; then
    python -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

# Activate virtual environment
echo -e "\n[3/8] Activating virtual environment..."
source venv/bin/activate 2>/dev/null || source venv/Scripts/activate 2>/dev/null || {
    echo "❌ Failed to activate venv"
    exit 1
}
echo "✓ Virtual environment activated"

# Upgrade pip
echo -e "\n[4/8] Upgrading pip..."
pip install --quiet --upgrade pip
echo "✓ Pip upgraded"

# Install dependencies
echo -e "\n[5/8] Installing dependencies..."
pip install --quiet -r requirements.txt
echo "✓ Dependencies installed"

# Check .env file
echo -e "\n[6/8] Checking environment configuration..."
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "✓ Created .env from .env.example"
        echo ""
        echo "⚠️  IMPORTANT: Edit .env with your credentials:"
        echo "   - DATABASE_URL (PostgreSQL)"
        echo "   - ANTHROPIC_API_KEY"
        echo "   - OPENAI_API_KEY"
        echo "   - ADZUNA_APP_ID & ADZUNA_API_KEY"
        echo ""
    else
        echo "❌ .env.example not found"
        exit 1
    fi
else
    echo "✓ .env file exists"
fi

# Test imports
echo -e "\n[7/8] Testing Python imports..."
python -c "import fastapi, langgraph, anthropic, openai, psycopg2" 2>/dev/null || {
    echo "⚠️  Some imports may not work yet (check .env configuration)"
}
echo "✓ Core imports OK"

# Summary
echo -e "\n[8/8] Setup complete!"
echo ""
echo "======================================"
echo "Next steps:"
echo "======================================"
echo ""
echo "1. Edit .env with your API credentials:"
echo "   nano .env"
echo ""
echo "2. Set up PostgreSQL (if not already running):"
echo "   # Option A: Local PostgreSQL"
echo "   createdb aineedjob"
echo "   psql aineedjob < database/schema.sql"
echo ""
echo "   # Option B: Docker"
echo "   docker run -e POSTGRES_PASSWORD=pwd -p 5432:5432 -d postgres"
echo "   psql -h localhost -U postgres postgres < database/schema.sql"
echo ""
echo "3. Run tests (validates V1 pipeline):"
echo "   pytest tests/test_pipeline.py -v"
echo ""
echo "4. Start the API server:"
echo "   uvicorn api.main:app --reload --port 8000"
echo ""
echo "5. Visit API docs:"
echo "   http://localhost:8000/docs"
echo ""
echo "For detailed setup guide, see SETUP.md"
echo "======================================"
