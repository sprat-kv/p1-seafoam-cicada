# Quick Start Guide

Get the Ticket Triage System running in 5 minutes.

## Prerequisites

- Python 3.11+
- uv (recommended) or pip

## Installation

```bash
# Clone/navigate to project directory
cd p1-seafoam-cicada

# Create virtual environment with uv
uv venv

# Install dependencies
uv pip install -r requirements.txt
```

## Run Tests

```bash
# Activate virtual environment (Windows)
.venv\Scripts\activate

# Run all validations
python validate_complete_project.py

# Or run individual test suites
python test_stage2.py   # Core logic tests
python test_stage3.py   # HITL workflow tests
```

**Expected Output**: All tests should pass (4/4 validations)

## Start the API Server

```bash
# Start FastAPI server
uvicorn app.main:app --reload
```

Server will start at: `http://localhost:8000`

API Documentation: `http://localhost:8000/docs`

## Test the API

### Option 1: Interactive API Docs

1. Open `http://localhost:8000/docs` in your browser
2. Try the `/triage/invoke` endpoint with:
   ```json
   {
     "ticket_text": "I want a refund for order ORD1001",
     "order_id": null,
     "thread_id": null
   }
   ```
3. Copy the `thread_id` from the response
4. Use `/admin/review` endpoint with the thread_id and:
   ```json
   {
     "action": {
       "status": "approved",
       "feedback": "Looks good!"
     }
   }
   ```

### Option 2: Python Test Script

```bash
# In a new terminal, with server running
python test_api.py
```

### Option 3: curl

```bash
# Initial triage request
curl -X POST "http://localhost:8000/triage/invoke" \
  -H "Content-Type: application/json" \
  -d '{
    "ticket_text": "Refund for order ORD1001 please",
    "order_id": null,
    "thread_id": null
  }'

# Save the thread_id from response, then approve:
curl -X POST "http://localhost:8000/admin/review?thread_id=YOUR_THREAD_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "action": {
      "status": "approved",
      "feedback": "Approved!"
    }
  }'
```

## Example Flow

### 1. User submits ticket
**Request**: `POST /triage/invoke`
```json
{
  "ticket_text": "I'd like a refund for order ORD1001. The mouse is not working.",
  "order_id": null
}
```

**Response**:
```json
{
  "thread_id": "abc-123",
  "order_id": "ORD1001",
  "issue_type": "refund_request",
  "draft_reply": "Hi Ava Chen, we are sorry for the inconvenience...",
  "review_status": "pending"
}
```

### 2. Admin reviews and approves
**Request**: `POST /admin/review?thread_id=abc-123`
```json
{
  "action": {
    "status": "approved",
    "feedback": "Good to go!"
  }
}
```

**Response**:
```json
{
  "thread_id": "abc-123",
  "review_status": "approved",
  "messages": [...]
}
```

## Available Test Orders

Use these order IDs in your tests:

- `ORD1001`: Ava Chen - Wireless Mouse (delivered)
- `ORD1002`: David Lee - Bluetooth Speaker (delivered)
- `ORD1003`: Sara Patel - Headphones (processing)
- `ORD1004`: John Smith - Smart Watch (delivered)
- `ORD1005`: Emily Rivera - Laptop Sleeves (shipped)

See `mock_data/orders.json` for full list.

## Issue Types

The system recognizes these keywords:

- `refund` → refund_request
- `broken` / `damaged` → damaged_item
- `late` / `not arrived` → late_delivery
- `missing` → missing_item
- `wrong item` → wrong_item
- `not working` → defective_product

See `mock_data/issues.json` for full list.

## Admin Actions

When reviewing drafts, admins can:

1. **Approve** (`"status": "approved"`): Send the draft reply as-is
2. **Reject** (`"status": "rejected"`): Restart classification
3. **Request Changes** (`"status": "request_changes"`): Redraft with feedback

## Troubleshooting

### Tests fail with "ModuleNotFoundError"
```bash
# Make sure you're in the virtual environment
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac
```

### API server won't start
```bash
# Check if port 8000 is in use
# On Windows:
netstat -ano | findstr :8000

# Kill the process or use a different port:
uvicorn app.main:app --port 8001
```

### Import errors
```bash
# Reinstall dependencies
uv pip install -r requirements.txt --force-reinstall
```

## Next Steps

- Read `README.md` for detailed architecture
- See `PROJECT_SUMMARY.md` for implementation details
- Check `FINDINGS.md` for design decisions
- Review `IMPLEMENTATION_PLAN.md` for stage breakdown

## Support

For issues or questions, check:
1. Test outputs for specific error messages
2. FastAPI docs at `/docs` endpoint
3. Code comments in `app/` directory
