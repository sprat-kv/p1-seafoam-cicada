# Ticket Triage System with LangGraph

A token-optimized LangGraph orchestrator for customer support ticket triage with Human-in-the-Loop (HITL) admin review and multi-turn conversation support.

## Features

- **Multi-turn Conversations** - Maintains context across turns (thread-level persistence)
- **Conditional HITL Flow** - Admin review via conditional routing (no interrupts)
- **Dynamic Routing** - Intelligently skips steps for follow-up questions to save tokens
- **Unified Order Resolution** - Single node handles ID lookup, email search, and suggested action generation
- **Smart Classification** - Priority-based keyword matching with tie-breaker logic
- **LLM-Backed Drafting** - Context-aware response generation using conversation history
- **Two-Stage Response** - Immediate acknowledgment when pending, full response after admin approval
- **Token Optimized** - 70-80% token reduction vs traditional approaches
- **Modern Python** - Supports both `uv` and `pip`

## Architecture

The system uses a stateful graph with conditional routing based on conversation context. Admin review is handled via conditional routing, not interrupts, allowing the graph to return immediately when pending and re-invoke for the final response after admin decision.

```
START → ingest
          │
          ├─(FULL/RECLASSIFY)→ classify_issue → resolve_order → draft_reply
          │                                                         │
          ├─(RESOLVE)────────→ resolve_order ───────────────────────┤
          │                                                         │
          ├─(DRAFT)─────────────────────────────────────────────────┤
          │                                                         │
          └─(ADMIN_RESUME)───→ admin_review ────────────────────────┤
                                                                    │
                             ┌──────────────────────────────────────┴───────┐
                             ↓                                              ↓
                     (scenario=REPLY)                               (other scenarios)
                             ↓                                              ↓
                    admin_approved!=None                                   END
                             ↓                                      (no admin needed)
                         finalize
                             ↓
                            END
```

### Two-Stage Response (REPLY Scenario)

1. **First Invocation** (`admin_approved=None`):
   - `draft_reply` generates "ticket raised" acknowledgment
   - Returns immediately with `review_status=pending`
   - Graph ends (`END`)

2. **Admin Decision** (via API):
   - `POST /admin/review` updates state with admin decision
   - Sets `review_status=approved/rejected/request_changes`

3. **Second Invocation** (`ADMIN_RESUME` routing):
   - `ingest` detects decision and routes to `admin_review`
   - `admin_review` sets `admin_approved=True/False/None`
   - `draft_reply` generates final message (approved, rejected, or re-draft with feedback)
   - `finalize` marks response complete
   - Graph ends (`END`)

### Nodes (6 total)

| Node | Purpose |
|------|---------|
| `ingest` | Analyze input, extract identifiers, detect admin resume, and decide routing path |
| `classify_issue` | Priority-based keyword classification (skipped for follow-ups) |
| `resolve_order` | Unified order resolution (fetch by ID, search by email) + generate suggested_action for admin |
| `draft_reply` | LLM-backed response generation based on `admin_approved` state (generates "ticket raised" when pending, final response when approved/rejected) |
| `admin_review` | Convert admin decision (`review_status`) to `admin_approved` flag |
| `finalize` | Mark response as complete |

### Routing Paths

| Path | Condition | Behavior |
|------|-----------|----------|
| `FULL` | New conversation | Run full pipeline: Classify → Resolve → Draft |
| `RECLASSIFY` | New issue keyword detected | Re-classify issue but keep order context |
| `RESOLVE` | New identifier provided | Skip classification, resolve order → Draft |
| `DRAFT` | Follow-up question | Skip directly to Draft (use existing context) |
| `ADMIN_RESUME` | Admin has made decision | Route to admin_review → Draft → Finalize |

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

Handles both new tickets and follow-up messages using `thread_id`. For REPLY scenarios, the first call returns `review_status=pending` with a "ticket raised" message.

```bash
curl -X POST "http://localhost:8000/triage/invoke" \
  -H "Content-Type: application/json" \
  -d '{
    "ticket_text": "Refund for ORD1001",
    "thread_id": "optional-uuid-for-continuation"
  }'
```

**Response (First Call - Pending):**
```json
{
  "thread_id": "uuid",
  "order_id": "ORD1001",
  "issue_type": "refund_request",
  "draft_scenario": "reply",
  "draft_reply": "Hi Ava, we identified a refund request for order ORD1001. Your ticket has been raised and is under review...",
  "review_status": "pending",
  "suggested_action": "Process refund for order ORD1001..."
}
```

### GET `/admin/review` - List Pending Tickets

```bash
curl http://localhost:8000/admin/review
```

**Response:**
```json
{
  "pending_count": 1,
  "tickets": [
    {
      "thread_id": "uuid",
      "order_id": "ORD1001",
      "customer_name": "Ava Chen",
      "issue_type": "refund_request",
      "suggested_action": "...",
      "draft_reply": "...",
      "created_at": "2026-01-14T..."
    }
  ]
}
```

### POST `/admin/review` - Admin Decision

Admin provides approval, rejection, or request for changes. This triggers the second invocation of the graph with the final response.

```bash
curl -X POST "http://localhost:8000/admin/review?thread_id=<uuid>" \
  -H "Content-Type: application/json" \
  -d '{"action": {"status": "approved", "feedback": "Looks good, process the refund"}}'
```

**Response (Second Call - Final):**
```json
{
  "thread_id": "uuid",
  "order_id": "ORD1001",
  "draft_reply": "Subject: Refund Approved for Order ORD1001\n\nDear Ava,\n\nThank you for reaching out...",
  "review_status": "approved"
}
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

**Result:** All 5 test conversations pass ✓

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
│   ├── main.py            # FastAPI app with conditional HITL flow
│   └── schema.py          # Pydantic models & Enums
├── mock_data/
│   ├── orders.json        # Sample orders database
│   ├── issues.json        # Classification rules
│   └── replies.json       # Response templates
├── interactions/
│   ├── phase1_demo.json   # Basic test cases
│   └── phase2_demo.json   # Advanced test cases
├── test_e2e.py            # Phase 1 tests
├── test_phase2_e2e.py     # Phase 2 tests
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
| **Drafting** | **LLM (Single Call per Scenario)** - Called for initial draft and after admin approval |
| **Follow-ups** | **Context Aware** - Skips unnecessary steps (Classification/Resolution) |

**Result**: LLM is called only when absolutely necessary, reducing costs by ~70-80% compared to full agentic loops.

## Implementation Notes

### No Interrupts - Pure Conditional Flow

The system uses **conditional routing** instead of interrupts for HITL. This design:
- Returns immediately when a response is pending admin review
- Allows the API to be stateless between invocations
- Uses the graph's built-in checkpointer for state persistence across calls
- Simplifies testing and deployment

### Merged `prepare_action` Node

The original `prepare_action` node has been merged into `resolve_order`. When a REPLY scenario is identified:
1. `resolve_order` fetches the order and generates `suggested_action` from templates
2. Sets `admin_approved=None` to mark the state as pending
3. Graph continues to `draft_reply`

### State Persistence Across Turns

Using LangGraph's `MemorySaver` checkpointer:
- Each thread_id maintains its own state
- Context (order_id, order_details, etc.) persists across API calls
- Follow-ups are routed efficiently based on existing context

## Dependencies

- **fastapi** - Web framework
- **langgraph** - Graph orchestration & state management
- **langchain-openai** - OpenAI integration
- **pydantic** - Data validation
- **python-dotenv** - Environment loading
