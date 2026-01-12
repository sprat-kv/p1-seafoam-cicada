# LangGraph HITL Implementation Plan

This plan breaks down the implementation into strict stages to allow for verification after each step.

## Stage 1: Skeleton & Schema (COMPLETED)
- **Goal**: Setup the project structure, dependencies, and define the data models (API Schema & Graph State) without implementing the core logic.
- **Tasks**:
    1.  [x] **Dependencies**: Pin `langgraph==1.0.5`, `langchain-openai`, `pydantic`.
    2.  [x] **Schema**: Create `app/schema.py` (Order, ReviewStatus, ReviewAction).
    3.  [x] **State**: Create `app/graph/state.py` (GraphState definition).
    4.  [x] **Tools**: Create `app/graph/tools.py` (Empty shell/interface for `fetch_order`).
    5.  [x] **Nodes**: Create `app/graph/nodes.py` (Function signatures only).
    6.  [x] **Workflow**: Create `app/graph/workflow.py` (Basic Graph definition with no compiled edges yet).

## Stage 2: Core Logic & Nodes
- **Goal**: Implement the functional logic for the Assistant and Tools.
- **Tasks**:
    1.  **Tool Logic**: Implement `fetch_order_tool` in `app/graph/tools.py` (load from JSON).
    2.  **Node Logic**: Implement `ingest`, `classify`, `draft_reply` in `app/graph/nodes.py` using LLM/Regex.
    3.  **Graph Construction**: Wire the nodes in `app/graph/workflow.py` with edges (excluding HITL for now).

## Stage 3: Admin Review & HITL
- **Goal**: Implement the Admin loop and Interrupts.
- **Tasks**:
    1.  **Admin Node**: Implement `admin_review_node` logic (handling Approve/Reject/RequestChanges).
    2.  **Workflow Update**: Add `interrupt_before`, conditional edges, and checkpointer.
    3.  **API Endpoints**: Update `app/main.py` to support `/triage/invoke` and `/admin/review`.

## Stage 4: Testing & Final Polish
- **Goal**: Verify end-to-end flow.
- **Tasks**:
    1.  **Test Script**: Create a script to simulate User -> Assistant -> Admin -> User flow.
    2.  **Refinement**: Tweak prompts or logic based on test results.
    3.  **Documentation**: Update README with usage instructions.

## Key Technical Decisions
*   **Graph Architecture**: State Machine with conditional routing (not generic ReAct).
*   **HITL Pattern**: `interrupt_before` using `MemorySaver` checkpointer.
*   **Schema**:
    *   `ReviewStatus`: PENDING, APPROVED, REJECTED, REQUEST_CHANGES.
    *   `GraphState`: Explicit fields for `draft_reply` vs `admin_feedback`.
