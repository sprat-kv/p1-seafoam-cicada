# Ticket Triage System with LangGraph

A token-optimized LangGraph orchestrator for customer support ticket triage with Human-in-the-Loop (HITL) admin review.

## Features

- **Unified Order Resolution** - Single node handles all order lookup scenarios
- **Smart Classification** - Priority-based keyword matching with tie-breaker logic
- **LLM-Backed Drafting** - Single unified draft node with template guidance
- **Human-in-the-Loop** - Admin review checkpoint for critical responses
- **Token Optimized** - 70-80% token reduction vs traditional approaches
- **Modern Python** - Supports both `uv` and `pip`

## Architecture

```
START → ingest → classify_issue → resolve_order → draft_reply
                                                       ↓
                               ┌───────────────────────┴───────────────────────┐
                               ↓                                               ↓
                       (scenario=REPLY)                                (other scenarios)
                               ↓                                               ↓
                         admin_review                                         END
                               ↓
               ┌───────────────┴───────────────┐
               ↓                               ↓
           (APPROVED)                    (REQUEST_CHANGES)
               ↓                               ↓
           finalize ← ─ ─ ─ ─ ─ ─ ─ ─ ─   draft_reply
               ↓
              END
```

### Nodes (7 total)

| Node | Purpose |
|------|---------|
| `ingest` | Extract order_id and email from ticket text |
| `classify_issue` | Priority-based keyword classification |
| `resolve_order` | Unified order resolution (fetch by ID, search by email, or ask for identifier) |
| `draft_reply` | LLM-backed response generation for all scenarios |
| `admin_review` | HITL checkpoint for admin approval |
| `finalize` | Mark response as approved |

### Scenarios

| Scenario | Description | Goes to Admin? |
|----------|-------------|----------------|
| `REPLY` | Normal issue response | Yes |
| `NEED_IDENTIFIER` | Ask for order_id or email | No |
| `ORDER_NOT_FOUND` | Order ID doesn't exist | No |
| `NO_ORDERS_FOUND` | No orders for email | No |
| `CONFIRM_ORDER` | Multiple orders, ask user to pick | No |

## Quick Start

### With UV (Recommended)

```bash
# Install uv (if not installed)
pip install uv

# Sync dependencies
uv sync

# Create environment file
cp .env.example .env
# Add your OPENAI_API_KEY to .env

# Run the server
uv run uvicorn app.main:app --reload
```

### With pip

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create environment file
cp .env.example .env
# Add your OPENAI_API_KEY to .env

# Run the server
uvicorn app.main:app --reload
```

Visit: http://localhost:8000/docs

## API Endpoints

### POST `/triage/invoke` - Start Triage

```bash
curl -X POST "http://localhost:8000/triage/invoke" \
  -H "Content-Type: application/json" \
  -d '{"ticket_text": "Refund for ORD1001. Not working."}'
```

**Response:**
```json
{
  "thread_id": "uuid",
  "order_id": "ORD1001",
  "issue_type": "refund_request",
  "draft_scenario": "reply",
  "draft_reply": "Hi Ava, we are sorry...",
  "review_status": "pending"
}
```

### POST `/admin/review` - Admin Decision

```bash
curl -X POST "http://localhost:8000/admin/review?thread_id=<uuid>" \
  -H "Content-Type: application/json" \
  -d '{"action": {"status": "approved", "feedback": "Looks good"}}'
```

### GET `/health` - Health Check

```bash
curl http://localhost:8000/health
```

## Project Structure

```
├── app/
│   ├── graph/
│   │   ├── __init__.py
│   │   ├── nodes.py       # Node implementations (7 nodes)
│   │   ├── state.py       # GraphState (14 fields)
│   │   ├── tools.py       # fetch_order, search_orders
│   │   └── workflow.py    # Graph wiring
│   ├── main.py            # FastAPI app
│   └── schema.py          # Pydantic models
├── mock_data/
│   ├── orders.json        # 12 sample orders
│   ├── issues.json        # Classification rules with priority
│   └── replies.json       # Response templates
├── interactions/
│   └── phase1_demo.json   # Demo conversations
├── pyproject.toml         # Modern Python config
├── requirements.txt       # Pinned dependencies
├── .python-version        # Python 3.11
├── .env.example           # Environment template
└── .gitignore
```

## Configuration

### Environment Variables

Create `.env` from `.env.example`:

```env
OPENAI_API_KEY=your-api-key-here
```

### Classification Rules

Edit `mock_data/issues.json` to customize keyword matching:

```json
{
  "keyword": "refund",
  "issue_type": "refund_request",
  "priority": 1
}
```

Lower priority = higher importance. Tie-breaker: longer keyword wins.

### Response Templates

Edit `mock_data/replies.json` to customize responses:

```json
{
  "issue_type": "refund_request",
  "template": "Hi {{customer_name}}, we reviewed order {{order_id}}..."
}
```

## How It Works

### 1. Ingest
Extracts identifiers from ticket text:
- Order ID: regex `ORD\d+`
- Email: regex `[\w.-]+@[\w.-]+\.\w+`

### 2. Classify
Priority-based keyword matching:
- Scans for all matching keywords
- Selects lowest priority (most important)
- Tie-breaker: longer keyword wins

### 3. Resolve Order
Single node handles all scenarios:
- **Order ID present**: Fetch by ID → found/not found
- **Email present**: Search → 0/1/N results
- **Neither**: Ask for identifier

### 4. Draft Reply
LLM generates contextual response:
- Receives scenario + full state
- Uses templates as tone/structure guidance
- Only REPLY scenario goes to admin

### 5. Admin Review (HITL)
- `APPROVED` → Finalize and end
- `REQUEST_CHANGES` → Re-draft with feedback
- `REJECTED` → Finalize anyway

## Token Optimization

| Component | Uses LLM? | Notes |
|-----------|-----------|-------|
| Ingest | No | Regex extraction |
| Classify | No | Keyword matching |
| Resolve Order | No | Tool invocation |
| Draft Reply | **Yes** | Single LLM call |
| Admin Review | No | State update |
| Finalize | No | State update |

**Result**: LLM called once per ticket (vs 3-5 times traditionally)

## Dependencies

- **fastapi** 0.115.0 - Web framework
- **langgraph** 1.0.5 - Graph orchestration
- **langchain-openai** ≥0.2.0 - OpenAI integration
- **pydantic** 2.9.2 - Data validation
- **python-dotenv** ≥1.0.0 - Environment loading

## License

MIT
