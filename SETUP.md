# Local Development Setup — aINeedJob V1

Complete guide to set up the local environment and run the full stack.

## Prerequisites

- **Python 3.10+** (check with `python --version`)
- **PostgreSQL 14+** (local or Docker)
- **Git** (check with `git --version`)
- **Terminal/Shell** (bash, zsh, PowerShell)

## Step 1: Clone & Install Dependencies

```bash
# Clone the repository
git clone <repo-url>
cd aINeedaJob

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate

# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1

# On Windows (Command Prompt):
venv\Scripts\activate.bat

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

## Step 2: Configure Environment Variables

```bash
# Copy example to local .env
cp .env.example .env

# Edit .env with your credentials
# Required for V1:
#   - DATABASE_URL (PostgreSQL connection)
#   - ANTHROPIC_API_KEY (Claude API)
#   - OPENAI_API_KEY (GPT API)
#   - ADZUNA_APP_ID & ADZUNA_API_KEY
#   - THEMUSE_API_KEY (no auth needed, but optional)

# Example .env (adjust for your setup):
APP_ENV=development
DATABASE_URL=postgresql://user:password@localhost:5432/aineedjob
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_MODEL=claude-sonnet-4-6
ADZUNA_APP_ID=your_app_id
ADZUNA_API_KEY=your_api_key
```

## Step 3: Set Up PostgreSQL Database

### Option A: Local PostgreSQL

```bash
# Create database and user
psql -U postgres

# In psql prompt:
CREATE DATABASE aineedjob;
CREATE USER aineedjob_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE aineedjob TO aineedjob_user;
\q

# Load schema
psql -U aineedjob_user -d aineedjob < database/schema.sql

# Verify connection
psql -U aineedjob_user -d aineedjob -c "\dt"  # List tables
```

### Option B: Docker PostgreSQL

```bash
# Start PostgreSQL in Docker
docker run --name aineedjob-postgres \
  -e POSTGRES_USER=aineedjob_user \
  -e POSTGRES_PASSWORD=your_secure_password \
  -e POSTGRES_DB=aineedjob \
  -p 5432:5432 \
  -d postgres:16

# Load schema
psql -h localhost -U aineedjob_user -d aineedjob < database/schema.sql

# View logs
docker logs aineedjob-postgres
```

## Step 4: Verify Setup

```bash
# Test database connection
python -c "from tools.db import get_connection; conn = get_connection(); print('✓ DB connected')"

# Test imports
python -c "import fastapi, langgraph, anthropic, openai; print('✓ All imports OK')"

# List tables
psql -U aineedjob_user -d aineedjob -c "\dt"
```

## Step 5: Run Tests

```bash
# Run all tests (mocked APIs, no credits used)
pytest tests/test_pipeline.py -v

# Run with output
pytest tests/test_pipeline.py -v -s

# Run specific test
pytest tests/test_pipeline.py::TestPipelineEndToEnd::test_05_score_job -v
```

## Step 6: Start the Backend Server

```bash
# From project root
uvicorn api.main:app --reload --port 8000

# Server runs at: http://localhost:8000
# API docs: http://localhost:8000/docs
# Health check: http://localhost:8000/health
```

## Step 7: Test API Endpoints

```bash
# In a new terminal, test endpoints

# Health check
curl http://localhost:8000/health

# List jobs (requires x-user-id header)
curl -H "x-user-id: test-user-123" http://localhost:8000/api/jobs

# Trigger job search
curl -X POST http://localhost:8000/api/jobs/search \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test-user-123"}'

# Get user profile
curl -H "x-user-id: test-user-123" http://localhost:8000/api/users/profile
```

## Step 8: Optional — Run with Celery (V2 feature)

```bash
# Terminal 1: Redis
redis-server

# Terminal 2: Celery worker
celery -A agents.tasks worker --loglevel=info

# Terminal 3: Backend server
uvicorn api.main:app --reload
```

## File Structure

```
aINeedaJob/
├── api/                    # FastAPI backend
│   ├── main.py            # App entry point
│   ├── routes/            # Endpoint modules
│   └── models/            # Pydantic schemas
├── agents/                # LangGraph orchestration
│   └── pipeline.py        # State machine
├── tools/                 # Python scripts (deterministic)
│   ├── db.py             # Database utilities
│   ├── llm.py            # LLM wrapper
│   ├── logger.py         # Logging
│   ├── search_*.py       # Job board search
│   ├── parse_job.py      # Job parsing
│   ├── score_job.py      # Job scoring
│   └── update_*.py       # Database updates
├── workflows/            # Markdown SOPs (instructions)
│   ├── job_discovery.md
│   ├── job_parsing.md
│   ├── job_match.md
│   ├── decision.md
│   └── ... (7 more)
├── database/             # Database schema
│   └── schema.sql        # PostgreSQL DDL
├── tests/                # Test suite
│   └── test_pipeline.py  # End-to-end tests
├── .env.example          # Environment template
├── requirements.txt      # Python dependencies
├── CLAUDE.md            # AI guidance
├── SETUP.md             # This file
└── README.md            # Project overview
```

## Troubleshooting

### PostgreSQL Connection Error
```
Error: could not connect to server: Connection refused

Solution:
1. Verify PostgreSQL is running: psql -U postgres -c "SELECT 1"
2. Check DATABASE_URL in .env
3. Verify user/password/database exist
```

### ImportError: No module named 'anthropic'
```
Solution: pip install -r requirements.txt
```

### Port 8000 Already in Use
```
Solution: uvicorn api.main:app --reload --port 8001
```

### LangGraph Import Error
```
Solution: pip install --upgrade langgraph langchain langchain-core
```

### Playwright Installation
```
# Install system dependencies (macOS)
brew install playwright

# Install system dependencies (Ubuntu)
sudo apt-get install -y chromium-browser

# Then install Python package
pip install playwright
playwright install
```

## Development Workflow

### 1. Make Changes
```bash
# Edit code in api/, tools/, agents/

# Run tests to validate
pytest tests/test_pipeline.py -v
```

### 2. Test Locally
```bash
# Start server
uvicorn api.main:app --reload

# In another terminal, test endpoint
curl http://localhost:8000/health
```

### 3. Commit & Push
```bash
git add .
git commit -m "Feature: description"
git push origin branch-name
```

## API Documentation

Once server is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Key Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Health check |
| GET | `/api/jobs` | List jobs |
| GET | `/api/jobs/{job_id}` | Get job with fit score |
| POST | `/api/jobs/search` | Trigger discovery pipeline |
| GET | `/api/applications` | List applications |
| PATCH | `/api/applications/{id}/approve` | User approves job |
| PATCH | `/api/applications/{id}/dismiss` | User dismisses job |
| GET | `/api/users/profile` | Get user profile |
| PUT | `/api/users/profile` | Update user profile |

## Environment Variables Reference

```env
# App Configuration
APP_ENV=development|staging|production
APP_BASE_URL=http://localhost:3000

# Database (REQUIRED)
DATABASE_URL=postgresql://user:password@localhost:5432/aineedjob

# LLM Providers (REQUIRED)
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-sonnet-4-6
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o

# Job Boards (REQUIRED for V1)
ADZUNA_APP_ID=your_app_id
ADZUNA_API_KEY=your_api_key
THEMUSE_API_KEY=optional

# Security
JWT_SECRET_KEY=your-secret-key-64-chars
JWT_ALGORITHM=HS256
ENCRYPTION_KEY=your-fernet-key

# Redis (Optional, for V2)
REDIS_URL=redis://localhost:6379/0

# Email (Optional, for V2)
GMAIL_CLIENT_ID=...
OUTLOOK_CLIENT_ID=...
```

## Next Steps

1. ✅ Complete local setup (you are here)
2. Run end-to-end tests (`pytest tests/`)
3. Test API endpoints manually
4. Explore LangGraph pipeline logic
5. Plan V2 features (email monitoring, follow-ups, etc.)

## Support

- Review `CLAUDE.md` for architecture guidance
- Check `workflows/` for detailed agent instructions
- See `tests/README.md` for testing guidance
- Inspect `api/routes/` for endpoint documentation

Happy coding! 🚀
