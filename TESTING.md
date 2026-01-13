# Testing Guide

## End-to-End API Tests

The `test_e2e.py` script tests the ticket triage API using test cases from `interactions/phase1_demo.json`.

## Prerequisites

1. **Install dependencies:**
   ```bash
   # With uv
   uv sync
   
   # Or with pip
   pip install -r requirements.txt
   ```

2. **Set up environment:**
   ```bash
   cp .env.example .env
   # Add your OPENAI_API_KEY to .env
   ```

3. **Start the API server:**
   ```bash
   # With uv
   uv run uvicorn app.main:app --reload
   
   # Or with pip
   uvicorn app.main:app --reload
   ```

   The server should be running at `http://localhost:8000`

## Running Tests

### Option 1: Run all tests

```bash
# With uv
uv run python test_e2e.py

# Or with pip
python test_e2e.py
```

### Option 2: Run with custom API URL

```bash
API_BASE_URL=http://localhost:8000 python test_e2e.py
```

## What the Tests Do

1. **Health Check** - Verifies API is running
2. **Load Test Cases** - Reads `interactions/phase1_demo.json`
3. **For Each Conversation:**
   - Sends first user message to `/triage/invoke`
   - Validates issue_type and order_id match expected outcomes
   - If REPLY scenario, tests admin review flow
   - Displays results with color-coded output

## Test Output

The script provides:
- ✅ Green checkmarks for passed validations
- ❌ Red X marks for failed validations
- ℹ️ Blue info messages for status updates
- ⚠️ Yellow warnings for issues

## Example Output

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

ℹ User message: I'd like a refund for order ORD1001. The mouse is not working.
ℹ Invoking triage endpoint...
ℹ Triage Results:
  Thread ID: abc-123-def
  Order ID: ORD1001
  Issue Type: refund_request
  Draft Scenario: reply
  Review Status: pending
  Draft Reply: Hi Ava Chen, we are sorry for the inconvenience...
ℹ Validating expected outcome...
✓ Issue type: refund_request
✓ Order ID: ORD1001
ℹ Testing admin review (APPROVED)...
✓ Admin review completed
  Final Review Status: approved

======================================================================
Test Summary
======================================================================

Total Tests: 5
✓ Passed: 5
```

## Troubleshooting

### API not running
```
✗ Cannot connect to API at http://localhost:8000
ℹ Make sure the server is running: uvicorn app.main:app --reload
```

**Solution:** Start the server in a separate terminal before running tests.

### Missing dependencies
```
ModuleNotFoundError: No module named 'requests'
```

**Solution:** Install dependencies:
```bash
uv sync  # or pip install -r requirements.txt
```

### API key not set
If you see LLM errors, make sure `OPENAI_API_KEY` is set in `.env`:
```bash
echo "OPENAI_API_KEY=sk-your-key-here" >> .env
```

## Test Cases

The test cases in `interactions/phase1_demo.json` cover:

1. **P1-DEMO-001** - Refund request (ORD1001)
2. **P1-DEMO-002** - Late delivery (ORD1002)
3. **P1-DEMO-003** - Defective product (ORD1004)
4. **P1-DEMO-004** - Wrong item (ORD1006)
5. **P1-DEMO-005** - Missing item (ORD1005)

Each test validates:
- Correct issue type classification
- Correct order ID extraction
- Proper draft scenario assignment
- Admin review flow (for REPLY scenarios)
