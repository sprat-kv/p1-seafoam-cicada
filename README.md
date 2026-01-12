# Ticket Triage System with LangGraph HITL

A multi-turn LangGraph orchestrator for customer support ticket triage with Human-in-the-Loop (HITL) admin review capabilities.

## Overview

This system classifies customer tickets, fetches order details, drafts appropriate replies, and pauses for admin review before sending responses to customers.

## Features

- **Order ID Extraction**: Automatically extracts order IDs from ticket text using regex
- **Issue Classification**: Keyword-based classification of customer issues
- **Order Details Fetching**: Retrieves order information via tool interface
- **Reply Drafting**: Template-based reply generation with customer/order context
- **Human-in-the-Loop**: Interrupts workflow for admin review with approve/reject/request changes options
- **Durable Execution**: State persistence using LangGraph checkpointer for pause/resume workflows
- **FastAPI Endpoints**: Production-ready API for ticket triage and admin review

## Architecture

### Graph Workflow

```
START
  |
  v
ingest (extract order_id)
  |
  v
classify_issue (keyword matching)
  |
  v
fetch_order (tool call)
  |
  v
draft_reply (template-based)
  |
  v
[INTERRUPT: admin_review]
  |
  +-- APPROVED --> final_response --> END
  |
  +-- REJECTED --> classify_issue (retry)
  |
  +-- REQUEST_CHANGES --> draft_reply (redraft)
```

### Key Components

- **State Management**: TypedDict-based state with conversation history, order details, and review status
- **Nodes**: `ingest`, `classify_issue`, `fetch_order_node`, `draft_reply`, `admin_review`, `final_response`
- **Tools**: `fetch_order` tool for retrieving order details from mock data
- **Checkpointer**: `MemorySaver` for in-memory state persistence (production would use database-backed)
- **Interrupts**: `interrupt_before=["admin_review"]` for HITL pattern

## Installation

### Using uv (Recommended)

```bash
# Create virtual environment
uv venv

# Install dependencies
uv pip install -r requirements.txt
```

### Using pip

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Running Tests

### Stage 2: Core Logic (without HITL)

```bash
python test_stage2.py
```

Tests:
- Order ID extraction
- Issue classification
- Order fetching
- Reply drafting
- End-to-end flow without interrupts

### Stage 3: HITL Workflow

```bash
python test_stage3.py
```

Tests:
- Admin approval flow
- Admin request changes flow
- Admin rejection flow
- State persistence and resume

## Running the API

### Start the Server

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

### API Documentation

Interactive API docs: `http://localhost:8000/docs`

### API Endpoints

#### 1. POST `/triage/invoke` - Start or Continue Triage

Invokes the triage workflow. Creates a new thread or continues an existing one.

**Request:**
```json
{
  "ticket_text": "I'd like a refund for order ORD1001. The mouse is not working.",
  "order_id": null,
  "thread_id": null
}
```

**Response:**
```json
{
  "thread_id": "uuid-string",
  "order_id": "ORD1001",
  "issue_type": "refund_request",
  "draft_reply": "Hi Ava Chen, we are sorry...",
  "review_status": "pending",
  "messages": [...]
}
```

#### 2. POST `/admin/review` - Admin Review Decision

Resumes the workflow after admin review with a decision.

**Request:**
```json
{
  "action": {
    "status": "approved",  // or "rejected", "request_changes"
    "feedback": "Looks good!"
  }
}
```

**Query Parameters:**
- `thread_id`: The thread ID from the triage response

**Response:**
```json
{
  "thread_id": "uuid-string",
  "order_id": "ORD1001",
  "issue_type": "refund_request",
  "draft_reply": "Hi Ava Chen...",
  "review_status": "approved",
  "messages": [...]
}
```

#### 3. GET `/health` - Health Check

Returns API health status.

### Testing the API

```bash
python test_api.py
```

Make sure the server is running before executing API tests.

## Project Structure

```
p1-seafoam-cicada/
├── app/
│   ├── graph/
│   │   ├── __init__.py
│   │   ├── nodes.py          # Node implementations
│   │   ├── state.py          # GraphState definition
│   │   ├── tools.py          # Tool definitions (fetch_order)
│   │   └── workflow.py       # Graph construction and compilation
│   ├── main.py               # FastAPI application
│   └── schema.py             # Pydantic schemas
├── mock_data/
│   ├── orders.json           # Mock order data
│   ├── issues.json           # Classification rules
│   └── replies.json          # Response templates
├── interactions/
│   └── phase1_demo.json      # Demo conversation examples
├── requirements.txt
├── test_stage2.py            # Core logic tests
├── test_stage3.py            # HITL workflow tests
├── test_api.py               # API integration tests
├── FINDINGS.md               # Analysis and design decisions
├── IMPLEMENTATION_PLAN.md    # Implementation stages
└── README.md
```

## Design Decisions

### 1. State Machine Architecture

Chose explicit state machine over generic ReAct pattern for predictable, controllable flow.

### 2. Direct Tool Wrapper

Instead of LLM-based tool calling, implemented direct tool wrapper (`fetch_order_node`) for deterministic behavior without LLM costs.

### 3. Keyword Classification

Used simple keyword matching for issue classification (fast, deterministic) rather than LLM classification.

### 4. Template-Based Replies

Draft replies use template substitution rather than LLM generation for consistency and cost control.

### 5. MemorySaver Checkpointer

Used in-memory checkpointer for demo. Production should use `AsyncPostgresSaver` or similar for true persistence.

### 6. Static Breakpoints

Used `interrupt_before=["admin_review"]` (static breakpoint) rather than dynamic `interrupt()` calls for simpler HITL implementation.

## Technical Stack

- **Framework**: LangGraph 1.0.5
- **API**: FastAPI 0.115.0
- **LLM SDK**: langchain-openai (prepared for LLM integration if needed)
- **Persistence**: langgraph.checkpoint.memory.MemorySaver
- **Environment**: Python 3.11+

## Future Enhancements

1. **LLM Integration**: Replace keyword classification with LLM-based classification for better accuracy
2. **Database Persistence**: Replace MemorySaver with PostgreSQL-backed checkpointer
3. **Streaming**: Add streaming support for real-time updates
4. **Multi-turn Conversations**: Enhance to handle ongoing customer conversations
5. **Analytics Dashboard**: Add metrics and monitoring for ticket handling
6. **Authentication**: Add API authentication and authorization
7. **Rate Limiting**: Implement rate limiting for production use

## Development Stages

### Stage 1: Skeleton & Schema (COMPLETED)
- Project structure
- Dependencies
- Schemas and state definitions

### Stage 2: Core Logic & Nodes (COMPLETED)
- Node implementations
- Tool logic
- Graph construction
- Conditional routing

### Stage 3: Admin Review & HITL (COMPLETED)
- Admin review node
- Interrupt configuration
- API endpoints
- State persistence

### Stage 4: Testing & Polish (COMPLETED)
- Unit tests
- Integration tests
- API tests
- Documentation

## License

MIT

## Contributing

This is an assessment project. For production use, please adapt with appropriate error handling, authentication, and database persistence.
