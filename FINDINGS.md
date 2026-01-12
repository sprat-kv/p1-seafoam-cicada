# Key Findings and Assessment Analysis

## Overview
The goal is to build a minimal multi-turn LangGraph orchestrator for ticket triage. The system needs to classify customer tickets, fetch order details, and draft appropriate replies.

## Assessment Context (JD Analysis)
The Job Description emphasizes:
*   **"Human-in-the-loop logic"**: This confirms the need for a breakpoint/review step (Admin) before finalizing actions.
*   **"Persistence with a database-backed checkpointer"**: Essential for pausing/resuming workflows (e.g., waiting for Admin or User input). For this "minimal" assessment, an in-memory checkpointer (`MemorySaver`) is acceptable, but the *architecture* must support persistence.
*   **"Agentic RAG / Tools"**: The `fetch_order` is a clear "Tool" usage.
*   **"FastAPI Production Endpoints"**: The API is not just a wrapper but a production-ready interface.
*   **"Clean, typed code"**: High emphasis on typing and structure.

## Existing Components
1.  **Mock API (`app/main.py`)**:
    *   `GET /orders/get`: Fetches order details by ID.
    *   `POST /classify/issue`: Classifies ticket text into issue types based on keywords.
    *   `POST /reply/draft`: Generates a reply using templates.
    *   `POST /triage/invoke`: Currently a procedural implementation combining the above steps. **This needs to be replaced or integrated with the LangGraph orchestrator.**

2.  **Data Sources (`mock_data/`)**:
    *   `orders.json`: Contains order details (ID, customer, items, status, etc.).
    *   `issues.json`: Classification rules (keyword mapping to issue types).
    *   `replies.json`: Response templates per issue type.

3.  **Example Interactions (`interactions/phase1_demo.json`)**:
    *   Provides ground truth for multi-turn conversations.
    *   Includes expected outcomes for `issue_type` and `order_id`.

## Revised Requirements Analysis

### 1. State Management (The "Memory")
The graph state must track:
*   `messages`: Conversation history (User, Assistant, Admin).
*   `ticket_text`: The current input text.
*   `order_id`: Extracted or provided order ID.
*   `issue_type`: Classified category.
*   `order_details`: The full order object (fetched from tool).
*   `draft_reply`: The Assistant's proposed draft (for Admin review).
*   `review_status`: Enum (`PENDING`, `APPROVED`, `REJECTED`, `REQUEST_CHANGES`).
*   `admin_feedback`: Text feedback from Admin if changes requested.
*   `sender`: Tracks the last active node.

### 2. Graph Structure (Nodes)
*   **`ingest`**: Parse input, likely extracting initial `ticket_text` and `order_id` if present.
*   **`classify_issue`**: Determine the nature of the request.
*   **`fetch_order`**: Retrieve order details (ToolNode).
*   **`draft_reply`**: Generate the *proposed* response using LLM + Templates.
*   **`admin_review`**: Processes the Admin's decision (Approve/Reject/Edit).
*   **`final_response`**: Sends the approved/edited message to the message history.

### 3. Control Flow & HITL
*   **Interrupt**: `interrupt_before=["admin_review"]`.
*   **Checkpointer**: Use `MemorySaver` (in-memory checkpointer).
*   **Routing**:
    *   If `order_id` missing -> Ask User (loop).
    *   If `order_id` present -> Fetch -> Draft -> Pause for Admin.
    *   Admin Approve -> Finalize -> End.
    *   Admin Reject/Request Changes -> Loop back to Classify or Draft.

### 4. Technical Stack
*   **Framework**: LangGraph (v1.0.5).
*   **LLM**: OpenAI (via `langchain-openai`).
*   **Persistence**: `langgraph.checkpoint.memory.MemorySaver`.
*   **API**: FastAPI with Pydantic schemas.

## Current Progress (Stage 1 Completed)
*   Project structure created (`app/graph/`).
*   Dependencies pinned.
*   Schemas defined (`app/schema.py`).
*   Graph skeletons created (`nodes.py`, `state.py`, `workflow.py`).
