# Phase 2 Test Cases - Testing Guide

## Overview

Phase 2 test cases (`interactions/phase2_demo.json`) include more complex scenarios that test advanced agent functionality:

1. **Email-based order lookup** - Finding orders by email address
2. **Multiple orders** - Handling cases where email has multiple orders (CONFIRM_ORDER scenario)
3. **Missing identifiers** - Testing need_identifier scenario when no order_id/email provided
4. **Generic questions** - Handling vague initial questions before issue classification
5. **Multi-turn conversations** - Complex follow-up questions and context handling

## Test Cases

### P2-DEMO-001: Basic Refund with Follow-up
- **Scenario**: Refund request with order ID, follow-up question
- **Turns**: 4 (user → assistant → user → assistant)
- **Key Test**: Multi-turn context preservation

### P2-DEMO-002: Refund (Damaged Item) with Follow-up
- **Scenario**: Refund request mentioning damage, follow-up about damaged items
- **Turns**: 4
- **Key Test**: Issue classification with multiple keywords, contextual follow-up

### P2-DEMO-003: Email Lookup with Follow-up
- **Scenario**: Late delivery reported with email, system finds order, follow-up question
- **Turns**: 4
- **Key Test**: Email-based order resolution, auto-selection when single order found

### P2-DEMO-004: Multiple Orders (User Selection)
- **Scenario**: Wrong item reported with email, multiple orders found, user selects one
- **Turns**: 6 (most complex)
- **Key Test**: CONFIRM_ORDER scenario, user order selection, follow-up question

### P2-DEMO-005: Missing Identifier Initially
- **Scenario**: Duplicate charge reported without identifier, system asks, user provides
- **Turns**: 4
- **Key Test**: NEED_IDENTIFIER scenario, RESOLVE path after identifier provided

### P2-DEMO-006: Email with No Orders
- **Scenario**: Refund requested with email that has no orders, then order ID provided
- **Turns**: 6
- **Key Test**: NO_ORDERS_FOUND scenario, recovery with order ID

### P2-DEMO-007: Generic Question First
- **Scenario**: Vague initial question, system asks for clarification, then issue resolved
- **Turns**: 6
- **Key Test**: Handling generic questions, NEED_IDENTIFIER, then full resolution

## Running Phase 2 Tests

### Prerequisites

1. **API Server Running**:
   ```bash
   # Terminal 1
   uv run uvicorn app.main:app --reload
   ```

2. **Environment Setup**:
   ```bash
   # Verify .env has OPENAI_API_KEY
   python check_env.py
   ```

### Run Tests

```bash
# Terminal 2
uv run python test_phase2_e2e.py
```

### Expected Output

```
======================================================================
Ticket Triage API - Phase 2 End-to-End Tests
======================================================================

[INFO] Checking environment variables...
[OK] OPENAI_API_KEY found: sk-proj...fm8A

[INFO] Checking API health...
[OK] API is running and healthy
[INFO] Loading test cases from interactions/phase2_demo.json...
[OK] Loaded 7 test conversations

[1/7]
======================================================================
Testing Conversation: P2-DEMO-001
======================================================================

----------------------------------------------------------------------
[INFO] Turn 1: USER
----------------------------------------------------------------------
[INFO] User message: I'd like a refund for order ORD1001...
[OK] Issue type: refund_request
[OK] Order ID: ORD1001
...

======================================================================
Test Summary
======================================================================

Total Tests: 7
[OK] Passed: 7
```

## Test Scenarios Covered

| Scenario | Test Cases | Description |
|----------|------------|-------------|
| **REPLY** | P2-DEMO-001, P2-DEMO-002 | Normal issue response with admin review |
| **Email Lookup** | P2-DEMO-003 | Single order found by email |
| **CONFIRM_ORDER** | P2-DEMO-004 | Multiple orders, user selection |
| **NEED_IDENTIFIER** | P2-DEMO-005, P2-DEMO-006, P2-DEMO-007 | Missing order_id/email |
| **NO_ORDERS_FOUND** | P2-DEMO-006 | Email has no orders |
| **RESOLVE Path** | P2-DEMO-005, P2-DEMO-006 | User provides identifier after initial request |
| **DRAFT Path** | All | Follow-up questions using existing context |

## Key Validations

Each test validates:

1. **Issue Classification** - Correct issue_type detected
2. **Order Resolution** - Order ID correctly extracted/resolved
3. **Scenario Detection** - Correct draft_scenario assigned
4. **Multi-turn Context** - State preserved across turns
5. **Response Quality** - LLM generates appropriate responses
6. **Admin Review** - REPLY scenarios go through review flow

## Output Files

All test outputs are saved to `test_outputs/`:

- **Per Conversation**: `P2-DEMO-XXX_YYYYMMDD_HHMMSS.json` and `.txt`
- **Summary**: `phase2_test_summary_YYYYMMDD_HHMMSS.json` and `.txt`

## Differences from Phase 1

| Feature | Phase 1 | Phase 2 |
|---------|---------|---------|
| Test Cases | 5 | 7 |
| Max Turns | 4 | 6 |
| Email Lookup | ❌ | ✅ |
| Multiple Orders | ❌ | ✅ |
| Missing Identifier | ❌ | ✅ |
| Generic Questions | ❌ | ✅ |
| Order Selection | ❌ | ✅ |

## Troubleshooting

### Issue: "Order ID not yet resolved"
**Cause**: Test case expects order_id but it's not provided initially (NEED_IDENTIFIER scenario)
**Solution**: This is expected behavior - order_id will be resolved in later turns

### Issue: "Multiple orders found"
**Cause**: Email has multiple orders (CONFIRM_ORDER scenario)
**Solution**: Test script handles this by detecting when user provides order ID in next turn

### Issue: "No orders found for email"
**Cause**: Email doesn't exist in orders.json (NO_ORDERS_FOUND scenario)
**Solution**: This is expected - test validates recovery when user provides order ID

## Advanced Scenarios

### P2-DEMO-004: Multiple Orders Flow

```
Turn 1: User: "Wrong item delivered. Email: user@example.com"
  → System: Finds 2 orders (ORD1005, ORD1006)
  → Scenario: CONFIRM_ORDER
  → Response: Lists orders, asks user to pick

Turn 2: User: "It's ORD1005"
  → System: Extracts order_id from message
  → Route: RESOLVE (new identifier provided)
  → Fetches ORD1005, resolves to REPLY scenario

Turn 3: User: "Do I need to return the wrong item first?"
  → System: Route: DRAFT (continuation question)
  → Uses existing context (order_id, order_details)
  → Generates contextual response
```

### P2-DEMO-006: Recovery from No Orders

```
Turn 1: User: "Refund. Email: noorders@x.com"
  → System: Searches by email, finds 0 orders
  → Scenario: NO_ORDERS_FOUND
  → Response: Asks for order ID or correct email

Turn 2: User: "Sorry — the order is ORD1014"
  → System: Extracts order_id from message
  → Route: RESOLVE (new identifier provided)
  → Fetches ORD1014, resolves to REPLY scenario
  → Full resolution flow

Turn 3: User: "When will I get the refund?"
  → System: Route: DRAFT (continuation)
  → Uses preserved context from Turn 2
```

## Success Criteria

All 7 test cases should pass with:
- ✅ Correct issue classification
- ✅ Proper order resolution (eventually)
- ✅ Appropriate scenario detection
- ✅ Multi-turn context preservation
- ✅ Contextual response generation
- ✅ Admin review flow (for REPLY scenarios)
