# Quick Test Commands

## All-in-One Test Commands

### Windows (PowerShell)

```powershell
# Terminal 1: Start the API server
uv run uvicorn app.main:app --reload

# Terminal 2: Run tests
uv run python test_e2e.py
```

### Linux/Mac

```bash
# Terminal 1: Start the API server
uv run uvicorn app.main:app --reload

# Terminal 2: Run tests
uv run python test_e2e.py
```

### Using Helper Scripts

**Windows:**
```cmd
run_tests.bat
```

**Linux/Mac:**
```bash
chmod +x run_tests.sh
./run_tests.sh
```

## Step-by-Step

### 1. Install Dependencies

```bash
# With uv (recommended)
uv sync

# Or with pip
pip install -r requirements.txt
```

### 2. Set Up Environment

```bash
# Create .env file
cp .env.example .env

# Edit .env and add your OPENAI_API_KEY
# On Windows: notepad .env
# On Linux/Mac: nano .env

# Verify environment is set correctly
python check_env.py
```

**Required Environment Variable:**
- `OPENAI_API_KEY` - Your OpenAI API key (required)

**Optional Environment Variables:**
- `LANGCHAIN_TRACING_V2` - Enable LangSmith tracing
- `LANGCHAIN_API_KEY` - LangSmith API key
- `LANGCHAIN_PROJECT` - LangSmith project name

### 3. Start API Server

**Terminal 1:**
```bash
# With uv
uv run uvicorn app.main:app --reload

# Or with pip
uvicorn app.main:app --reload
```

Wait for: `Uvicorn running on http://127.0.0.1:8000`

### 4. Run Tests

**Terminal 2:**
```bash
# With uv
uv run python test_e2e.py

# Or with pip
python test_e2e.py
```

## Expected Output

```
======================================================================
Ticket Triage API - End-to-End Tests
======================================================================

ℹ Checking API health...
✓ API is running and healthy
ℹ Loading test cases from interactions/phase1_demo.json...
✓ Loaded 5 test conversations

[1/5]
======================================================================
Testing Conversation: P1-DEMO-001
======================================================================

ℹ User message: I'd like a refund for order ORD1001...
✓ Issue type: refund_request
✓ Order ID: ORD1001
✓ Admin review completed

...

======================================================================
Test Summary
======================================================================

Total Tests: 5
✓ Passed: 5

✓ All tests passed!
```

## Troubleshooting

**API not running:**
```bash
# Check if server is running
curl http://localhost:8000/health
```

**Missing requests library:**
```bash
pip install requests
# or
uv add requests
```

**API key error:**
```bash
# Make sure .env exists and has OPENAI_API_KEY
cat .env | grep OPENAI_API_KEY
```
