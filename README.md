# Ticket Triage System with LangGraph

A token-optimized LangGraph orchestrator for customer support ticket triage with Human-in-the-Loop (HITL) admin review and multi-turn conversation support.

## Loom Recording

- [Video walkthrough](https://share.vidyard.com/watch/aqABYbeHiGkdAHqwPpDEXv)

## Features

- **Multi-turn Conversations** - Maintains context across turns (thread-level persistence)
- **Dynamic Routing** - Intelligently skips steps for follow-up questions to save tokens
- **Unified Order Resolution** - Single node handles ID lookup, email search, and user selection
- **Smart Classification** - Priority-based keyword matching with tie-breaker logic
- **Human-in-the-Loop** - Admin review checkpoint for critical responses
- **Agentic RAG Policy Checks** - Action-aware policy retrieval and compliance evaluation before final drafting
- **Policy Citations for UI** - Structured `applied_policies` payload to display exactly which policies were used
- **Contextual Responses** - LLM-generated replies with conversation memory for natural interactions
- **Token Optimized** - 70-80% token reduction vs traditional approaches
- **Modern Python** - Supports both `uv` and `pip`

## Architecture

The system uses a stateful graph with 4 smart routing paths based on conversation context:

![Ticket Triage Graph Workflow](graph_diagram.png)

### Nodes (9 total)

| Node | Purpose |
|------|---------|
| `ingest` | Analyze input, extract identifiers, and decide routing path based on missing states |
| `classify_issue` | Priority-based keyword classification (skipped if issue already known) |
| `resolve_order` | Unified order resolution (fetch by ID, search by email, or ask for identifier) |
| `prepare_action` | Prepares the suggested action and sets review status to PENDING |
| `kb_orchestrator` | Agentic retrieval planner: selects policy retrieval strategy by issue/action context |
| `policy_evaluator` | Validates suggested action against retrieved policies and produces citations |
| `draft_reply` | Unified draft node generating contextual responses using LLM for all scenarios |
| `admin_review` | Pass-through checkpoint for HITL admin approval |
| `finalize` | Mark response as approved and save final state |

### RAG Integration (Position B)

RAG is invoked **after** `prepare_action` and **before** `draft_reply`:

```mermaid
graph TD
    resolveOrder[resolve_order] --> prepareAction[prepare_action]
    prepareAction --> routeRAG{"route_to_rag"}
    routeRAG -->|known issue type| kbOrchestrator[kb_orchestrator]
    routeRAG -->|unknown issue| draftReply[draft_reply]
    kbOrchestrator --> policyEvaluator[policy_evaluator]
    policyEvaluator --> draftReply
```

Why this placement:
- `prepare_action` creates a concrete proposed action first.
- `kb_orchestrator` retrieves the most relevant policies using `issue_type`, `ticket_text`, and `suggested_action`.
- `policy_evaluator` enriches admin-facing action text and emits structured `applied_policies`.

## State Management

The graph maintains a TypedDict state with the following fields:

- **Conversation**: `messages`, `ticket_text`, `thread_id`
- **Customer**: `order_id`, `email`, `order_details`, `candidate_orders`
- **Triage**: `issue_type`, `evidence`, `recommendation`
- **Workflow**: `draft_reply`, `draft_scenario`, `route_path`, `sender`
- **Policy RAG**: `policy_citations` (internal), `policy_evaluation`, `applied_policies` (frontend-friendly)
- **Admin Review**: `review_status` (PENDING/APPROVED/REJECTED), `admin_feedback`, `suggested_action`

## Policy Mapping and Fraud Escalation

Primary mappings:
- `chargeback_policy.md` -> `duplicate_charge`
- `delivery_policy.md` -> `late_delivery`
- `refund_policy.md` -> `refund_request`
- `warranty_policy.md` -> `defective_product`, `damaged_item`

Conditional mapping:
- `fraud_policy.md` is added when:
  - issue is `refund_request`, `wrong_item`, or `missing_item`, and
  - order amount is greater than 80 USD.

## Human-in-the-Loop (HITL) Architecture

This system implements a robust HITL pattern using LangGraph's checkpointing capabilities:

1. **Interrupt Mechanism**: The graph is compiled with `interrupt_before=["admin_review"]`. When the workflow reaches this node, it pauses execution and saves the state to the checkpointer.
2. **Persistence**: We use `AsyncPostgresSaver` (PostgreSQL-backed checkpointer) to persist graph state between turns and across server restarts.
3. **Two-Stage Response**:
   - **Stage 1 (Pending)**: System generates a contextual acknowledgment for the user and a `suggested_action` for the admin.
   - **Stage 2 (Final)**: After admin approval, the system generates the final resolution message with conversation context.
4. **Admin Review Flow**:
   - Graph pauses at `admin_review`
   - Admin API calls `update_state` to set `review_status` (APPROVED/REJECTED)
   - Admin API calls `invoke(None)` to resume execution
   - Graph proceeds to `draft_reply` to generate the final response based on the admin's decision

## Routing Logic

The `ingest` node uses smart routing to ensure efficiency and one-time detection:

- **FULL**: First message or both states missing → Run full pipeline
- **RECLASSIFY**: Only issue type missing → Run classify only
- **RESOLVE**: Only order details missing → Run resolve only
- **DRAFT**: Both states filled → Skip to drafting (no re-detection)

## Scenario Walkthroughs

### Scenario 1: Full Flow (Complete Info)
**User**: "I'd like a refund for order ORD1001"

```mermaid
sequenceDiagram
    participant User
    participant System as Graph Orchestrator
    participant Tool as Tool: fetch_order
    participant Admin
    
    User->>System: "I'd like a refund for order ORD1001"
    Note over System: Ingest: Extract ORD1001
    
    rect rgb(240, 240, 240)
        Note over System: Routing: FULL
        System->>System: Classify Issue (refund_request)
        System->>Tool: fetch_order("ORD1001")
        Tool-->>System: Order Details
        System->>System: Prepare Action
    end
    
    System-->>Admin: Request Review (Status: PENDING)
    System->>User: "Processing refund..."
    
    Note over Admin: ⏸️ INTERRUPT: Graph Paused
    Admin->>System: POST /admin/review (Status: APPROVED)
    Note over System: ▶️ RESUME: Graph Execution
    
    System->>System: Generate Template Response
    System->>User: "Refund approved..."
    Note over System: Finalize & End
```

### Scenario 2: Partial Info (Missing Issue)
**User**: "I have an issue with ORD1006"

```mermaid
sequenceDiagram
    participant User
    participant System as Graph Orchestrator
    participant Tool as Tool: fetch_order
    
    User->>System: "I have an issue with ORD1006"
    
    rect rgb(240, 240, 240)
        Note over System: Routing: FULL
        System->>System: Classify Issue (Unknown)
        System->>Tool: fetch_order("ORD1006")
        Tool-->>System: Order Details
    end
    
    System->>User: "Could you describe the issue?"
    
    User->>System: "It's broken"
    
    rect rgb(240, 240, 240)
        Note over System: Routing: RECLASSIFY (Order Known)
        System->>System: Classify Issue (damaged_item)
        Note right of System: Skip Resolution
        System->>System: Prepare Action
    end
    
    System-->>Admin: Request Review (Status: PENDING)
    System->>User: "Arranging replacement..."
```

### Scenario 3: Admin Rejection

```mermaid
sequenceDiagram
    participant User
    participant System as Graph Orchestrator
    participant Admin
    
    User->>System: Ticket Request
    System-->>Admin: Request Review (Status: PENDING)
    
    Note over Admin: ⏸️ INTERRUPT: Graph Paused
    Admin->>System: POST /admin/review (Status: REJECTED)
    Note over System: ▶️ RESUME: Graph Execution
    
    System->>System: Draft Rejection Message
    System->>User: "Unable to proceed, check email..."
    Note over System: Finalize & End
```

## API Endpoints

### POST `/triage/invoke`
Start or continue a conversation.
```bash
curl -X POST "http://localhost:8000/triage/invoke" \
  -H "Content-Type: application/json" \
  -d '{"ticket_text": "Refund for ORD1001", "thread_id": "optional-uuid"}'
```

Response includes RAG fields:
- `policy_evaluation`: policy-grounded compliance summary.
- `applied_policies`: list of exact policies/rules used for the decision.

### GET `/admin/review`
List all tickets waiting for admin approval.
```bash
curl http://localhost:8000/admin/review
```

Each pending ticket now includes:
- `suggested_action` (enriched with policy context)
- `applied_policies` (for direct frontend rendering)

### POST `/admin/review`
Submit admin decision (APPROVED/REJECTED).
```bash
curl -X POST "http://localhost:8000/admin/review?thread_id=uuid" \
  -H "Content-Type: application/json" \
  -d '{"action": {"status": "approved", "feedback": "Approved"}}'
```

### GET `/health`
Health check endpoint.

## Technical Stack

- **Framework**: LangGraph v1.0.5
- **LLM**: OpenAI GPT-4o-mini (via `langchain-openai>=0.2.0`)
- **Embeddings**: OpenAI `text-embedding-3-small`
- **Vector Store**: ChromaDB (persistent local path, collection: `viridien_policies`)
- **LangChain**: langchain>=0.3.0
- **Persistence**: `langgraph.checkpoint.postgres.aio.AsyncPostgresSaver` (PostgreSQL-backed checkpointing)
- **API**: FastAPI v0.115.0 with Pydantic v2.9.2
- **Server**: Uvicorn v0.30.6
- **Tools**: Custom tool nodes for order fetching (fetch_order, search_orders)

## Token Optimization Strategy

| Component | Strategy |
|-----------|----------|
| **Classification** | **Deterministic** (Regex/Keyword) - No LLM usage |
| **Routing** | **Deterministic** (State-based) - No LLM usage |
| **Order Resolution** | **Tool-based** - No LLM usage |
| **Drafting** | **LLM-powered** - Contextual responses with conversation memory and template guidance |
| **Follow-ups** | **Context Aware** - Skips unnecessary steps (Classification/Resolution) |

## Quick Start

### With UV (Recommended)
```bash
pip install uv
uv sync
cp .env.example .env
# Add OPENAI_API_KEY to .env
# DATABASE_URL defaults to local Docker Postgres in .env.example
docker compose up -d
uv run uvicorn app.main:app --reload
```

### With pip
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

## Knowledge Base Indexing CLI

Use the reusable CLI to index or update policy docs in Chroma:

```bash
python kb_index.py index
python kb_index.py list
python kb_index.py query --text "refund for duplicate charge" --issue-type duplicate_charge
python kb_index.py add --file policies/refund_policy.md
```

## Quick Interactive Demo (API Chat)

An interactive terminal chat client is included:

```bash
python demo_rag_chat.py --base-url http://localhost:8000
```

Options:
- `--auto-approve`: auto-submit admin approval whenever review status is pending.
- Commands inside chat:
  - `/pending` -> show current pending admin tickets
  - `/quit` or `/exit` -> stop demo

This demo calls:
- `POST /triage/invoke`
- `GET /admin/review`
- `POST /admin/review`

and prints RAG output fields (`policy_evaluation`, `applied_policies`) for quick validation.

Visit: http://localhost:8000/docs

### Local PostgreSQL with Docker

This project uses Docker Compose for local Postgres. Current image:
- `postgres:14.21-trixie`

Start database:
```bash
docker compose up -d
docker compose ps
```

Stop database:
```bash
docker compose stop
```

Remove container (keep data volume):
```bash
docker compose down
```

Remove container + volume data:
```bash
docker compose down -v
```

## Project Structure

```
├── app/
│   ├── graph/
│   │   ├── nodes.py       # Core node implementations
│   │   ├── state.py       # GraphState definition
│   │   ├── tools.py       # Order tools
│   │   └── workflow.py    # Graph wiring & routing logic
│   ├── rag/
│   │   ├── config.py      # RAG config and policy mappings
│   │   ├── indexer.py     # Chroma indexing utilities
│   │   ├── retriever.py   # Retrieval and reranking
│   │   └── rag_nodes.py   # kb_orchestrator + policy_evaluator
│   ├── main.py            # FastAPI app & endpoints
│   └── schema.py          # Pydantic models & Enums
├── kb_index.py            # Policy KB indexing CLI
├── demo_rag_chat.py       # Interactive API demo chat client
├── mock_data/             # JSON data sources
├── interactions/          # Demo conversation logs
└── requirements.txt       # Dependencies
```

## Configuration

**Environment Variables** (`.env`):
```env
# Required
OPENAI_API_KEY=your-api-key-here
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/ticket_triage

# Optional: LangSmith Tracing
LANGCHAIN_TRACING_V2=true
LANGSMITH_API_KEY=your-langsmith-api-key-here
LANGCHAIN_PROJECT=ticket-triage-system

# Optional: Local Chroma persistence directory
CHROMA_PERSIST_DIR=.chroma
```

**LangSmith Tracing**:
- Set `LANGCHAIN_TRACING_V2=true` to enable tracing
- Add your `LANGSMITH_API_KEY` from [LangSmith](https://smith.langchain.com/)
- View traces at: https://smith.langchain.com/

**Classification Rules** (`mock_data/issues.json`):
Editable JSON file to customize keyword matching logic without code changes.

## How I used AI for the project

First I created an initial draft about the project with the required flow and features that I want to build for the project. I referred the following LangChain & LangGraph blogs to decide on the agent architecture that I want to build,

- https://docs.langchain.com/oss/python/langchain/multi-agent
- https://docs.langchain.com/oss/python/langchain/multi-agent/handoffs-customer-support

After I'm ready with my requirements I started building the project on Cursor.

Models used:

- **Brainstorming and Planning**: Claude Opus, Gemini 3 Pro
- **Coding**: Claude Opus, Sonnet and Haiku (Depending on complexity)

I used Antigravity with Claude Sonnet to build the frontend.
