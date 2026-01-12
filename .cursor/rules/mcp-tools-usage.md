---
alwaysApply: true
description: MCP Tools Usage Rule for External Library Documentation
---

# MCP Tools Usage Rule

**Applies to:** All Tasks Involving External Libraries

When working with external libraries and frameworks, follow these rules without exception:

## Core Principle
- **Before suggesting code for any external library**, use MCP tools: `SearchDocsByLangChain`, `resolve-library-id`, and `get-library-docs`
- **Never rely on training data** for framework APIs (LangChain, LangGraph, FastAPI, Next.js, React, etc.)
- **Pull docs first, then code** - Always retrieve up-to-date documentation before implementing

## Tool Selection by Library Type

### LangChain Ecosystem Libraries
For all LangChain-specific libraries (LangChain, LangGraph, LangSmith, etc.):
- **Use `SearchDocsByLangChain`** tool to search for relevant documentation, code examples, API references, and guides

### All Other Libraries
For all other external libraries:
- **Use Context7 tools**:
  1. First use `resolve-library-id` to get the Context7-compatible library ID
  2. Then use `get-library-docs` (or `query-docs`) to retrieve up-to-date documentation

## Documentation Version Priority
- **Use version-specific documentation when available**
- Prefer version-specific library IDs (e.g., `/org/project/version`) over general ones when the version matters

## Workflow
1. Identify the external library/framework needed
2. Determine tool set (LangChain tools vs Context7 tools)
3. Search/resolve library ID first
4. Retrieve documentation and examples
5. Then write code based on the retrieved documentation

**Reminder:** Always verify current API usage against official documentation. Training data may be outdated or incorrect for framework-specific implementations.
