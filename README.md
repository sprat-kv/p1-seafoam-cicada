# Ticket Triage System with LangGraph

A token-optimized LangGraph orchestrator for customer support ticket triage with Human-in-the-Loop (HITL) admin review and multi-turn conversation support.

## Features

- **Multi-turn Conversations** - Maintains context across turns (thread-level persistence)
- **Dynamic Routing** - Intelligently skips steps for follow-up questions to save tokens
- **Unified Order Resolution** - Single node handles ID lookup, email search, and user selection
- **Smart Classification** - Priority-based keyword matching with tie-breaker logic
- **LLM-Backed Drafting** - Context-aware response generation using conversation history
- **Human-in-the-Loop** - Admin review checkpoint for critical responses
- **Token Optimized** - 70-80% token reduction vs traditional approaches
- **Modern Python** - Supports both `uv` and `pip`

## Architecture

The system uses a stateful graph with conditional routing based on conversation context:

```
START → ingest
          │
          ├─(FULL/RECLASSIFY)→ classify_issue → resolve_order → draft_reply
          │                                                         │
          ├─(RESOLVE)────────→ resolve_order ───────────────────────┤
          │                                                         │
          └─(DRAFT)─────────────────────────────────────────────────┤
                                                                    │
                             ┌──────────────────────────────────────┴───────┐
                             ↓                                              ↓
                     (scenario=REPLY)                               (other scenarios)
                             ↓                                              ↓
                       admin_review                                        END
                             ↓                                      (await user input)
             ┌───────────────┴───────────────┐
             ↓                               ↓
         (APPROVED)                    (REQUEST_CHANGES)
             ↓                               ↓
         finalize ← ─ ─ ─ ─ ─ ─ ─ ─ ─   draft_reply
             ↓
            END
```

### Nodes (6 total)

| Node | Purpose |
|------|---------|
| `ingest` | Analyze input, extract identifiers, and decide routing path |
| `classify_issue` | Priority-based keyword classification (skipped for follow-ups) |
| `resolve_order` | Unified order resolution (fetch by ID, search by email, or ask for identifier) |
| `draft_reply` | LLM-backed response generation using conversation history (last 5 messages) |
| `admin_review` | HITL checkpoint for admin approval |
| `finalize` | Mark response as approved and save final state |

### Routing Paths

| Path | Condition | Behavior |
|------|-----------|----------|
| `FULL` | New conversation | Run full pipeline: Classify → Resolve → Draft |
| `RECLASSIFY` | New issue keyword detected | Re-classify issue but keep order context |
| `RESOLVE` | New identifier provided | Skip classification, resolve order → Draft |
| `DRAFT` | Follow-up question | Skip directly to Draft (use existing context) |

### Scenarios

| Scenario | Description | Goes to Admin? |
|----------|-------------|----------------|
| `REPLY` | Normal issue response | **Yes** |
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

### POST `/triage/invoke` - Start/Continue Conversation

Handles both new tickets and follow-up messages using `thread_id`.

```bash
curl -X POST "http://localhost:8000/triage/invoke" \
  -H "Content-Type: application/json" \
  -d '{
    "ticket_text": "Refund for ORD1001",
    "thread_id": "optional-uuid-for-continuation"
  }'
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

## Testing

The project includes comprehensive end-to-end tests for both basic and advanced scenarios.

### 1. Basic Tests (Phase 1)
Tests simple single-turn and basic multi-turn flows.

```bash
uv run python test_e2e.py
```

### 2. Advanced Tests (Phase 2)
Tests complex scenarios like:
- Email-based order lookup
- Multiple orders (user selection)
- Missing identifiers recovery
- Generic questions handling

```bash
uv run python test_phase2_e2e.py
```

See `PHASE2_TESTING.md` for detailed test case descriptions.

## Project Structure

```
├── app/
│   ├── graph/
│   │   ├── __init__.py
│   │   ├── nodes.py       # Node implementations (6 nodes)
│   │   ├── state.py       # GraphState (14 fields)
│   │   ├── tools.py       # fetch_order, search_orders
│   │   └── workflow.py    # Graph wiring & routing logic
│   ├── main.py            # FastAPI app
│   └── schema.py          # Pydantic models & Enums
├── mock_data/
│   ├── orders.json        # Sample orders database
│   ├── issues.json        # Classification rules
│   └── replies.json       # Response templates
├── interactions/
│   ├── phase1_demo.json   # Basic test cases
│   └── phase2_demo.json   # Advanced test cases
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

## Token Optimization Strategy

| Component | Strategy |
|-----------|----------|
| **Classification** | **Deterministic** (Regex/Keyword) - No LLM usage |
| **Routing** | **Deterministic** (State-based) - No LLM usage |
| **Order Resolution** | **Tool-based** - No LLM usage |
| **Drafting** | **LLM (Single Call)** - Only called once at the end |
| **Follow-ups** | **Context Aware** - Skips unnecessary steps (Classification/Resolution) |

**Result**: LLM is called only when absolutely necessary (drafting), reducing costs by ~70-80% compared to full agentic loops.

## Dependencies

- **fastapi** - Web framework
- **langgraph** - Graph orchestration & state management
- **langchain-openai** - OpenAI integration
- **pydantic** - Data validation
- **python-dotenv** - Environment loading
