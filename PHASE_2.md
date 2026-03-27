Phase 2. HR Interview Task with Agentic RAG (tougher, 60 to 75 minutes live)
Objective
Add durable persistence, a human approval gate, and a focused agentic RAG
subgraph that grounds the system’s recommendations in policy documents.
Required
Persistence: compile the graph with a Postgres checkpointer. Demonstrate
stopping the process mid-run and resuming the same thread. (Yogesh: In-
memory persistence is already implemented in Phase 1. We can ask to
implement external persistence with Postgres)
Approval: node propose_remedy calls payments.refund_preview, then interrupts
for human approval. On resume, call payments.refund_commit.(Yogesh: Already
implemented in Phase 1)
Agentic RAG subgraph:
o Add a small knowledge base of 8 to 12 short policy files in Markdown
stored locally in the repo.
o Provide an indexing CLI kb_index that chunks and embeds the docs into a
vector store. You may use pgvector or Chroma.
o Build a kb_orchestrator node that plans retrieval: choose retriever, run top-
k retrieval, optionally call a reranker or an LLM-based re-scorer, and return
citations.
o Integrate RAG into policy_evaluator so proposed actions must cite
relevant policy sections.

Observability: show the run tree and node metadata in LangSmith or Langfuse,
including retrieved document IDs and citation spans (Yogesh : Did not show in
Phase 1, We can check if candidates does this in phase 2)
Live demo
Start a run, stop the server, restart, and resume to completion.
Show an interrupted run that resumes after approval.
Show RAG citations in the proposed remedy and in the final reply.