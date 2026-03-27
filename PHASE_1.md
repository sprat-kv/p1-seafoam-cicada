Objective: Build a minimal LangGraph that classifies a ticket, fetches a fake order, and drafts a reply.

 

What to Deliver:

GitHub repo with setup instructions and a curl example

Loom video showing the agent in action

Passing tests in CI

A short paragraph on how you used Cursor or Claude Code

 

Key Requirements:

States: messages, ticket_text, order_id, issue_type, evidence, recommendation

Nodes: ingest, classify_issue, fetch_order (ToolNode), draft_reply

Control flow: extract order_id if missing

FastAPI endpoint POST /triage/invoke

Basic tracing with LangSmith or Langfuse

 

We anticipate the assignment should take around 90 minutes of focused work. Feel free to use any tools or resources that help you work effectively and efficiently.

 

Please share your GitHub link and Loom video with us by 01/16/2026. If you need additional time or run into any blockers, just let us know.

 

We appreciate the time and effort you put into this step and look forward to reviewing your submission!

ProTips:

Make sure to read the task thoroughly, as it covers several important concepts you’ll be tested on.

There are three entities involved in the langgraph interaction: customer, assistant, and admin. The customer initiates the process, the assistant handles most queries and suggests actions, and the admin approves or rejects these suggestions.

Take a few minutes to write a readme or plan without using any AI tools, outlining the concepts/utilities you’ll need and the graph architecture.

Once your plan is ready, start implementing it in modules, using your preferred coding copilot tool.

