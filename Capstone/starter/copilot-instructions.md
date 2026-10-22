# Rules for GitHub Copilot - AskIT Ticket Desk

Build a small multi-agent app. Keep everything simple and easy to read.

## Files (create only the file the current prompt asks for)
- mcp_server.py : MCP server with 4 tools: search_kb, get_ticket, get_user, reset_password (mock)
- mcp_client.py : call_tool(name, **args) and list_tools(); starts mcp_server.py over stdio
- llm.py        : ask(system, user, fallback) - Amazon Nova on Bedrock if AWS keys exist, else returns fallback
- agents.py     : triage_agent, resolver_agent, reviewer_agent
- pipeline.py   : handle_ticket(text, user_id) runs the 3 agents; approve_action(user_id)
- app.py        : Streamlit page
- check.py      : 5 checks, prints PASS or FAIL

## Rules
- Python 3.11+, plain functions, short docstrings. No classes, no LangChain, no LangGraph.
- Use the official `mcp` package, version 1.x: `from mcp.server.fastmcp import FastMCP`.
- Data folder: data/ (kb/*.md, tickets.csv, users.csv). Use the csv module, not pandas.
- Never write, print or hard-code AWS keys. Keys come only from the .env file.
- Safety rules live in CODE, not only in prompts: a VIP user never gets reset_password.
- Do only what the prompt asks. Do not edit other files. Keep each file under 120 lines.
- When you finish, tell me the one command to run to test it.
