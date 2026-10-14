# SPEC: Gatekeeper MCP server v1

## Purpose
Expose the Day 8 `gatekeeper.py` as an MCP server so any agent can ask the Gatekeeper instead of copying its code. The server is a thin wrapper: NO business logic lives here.

## Server
- Name: "AskIT Gatekeeper".
- Library: fastmcp 4.1.0.
- Transport: stdio by default. With the argument `--http` it serves HTTP on port 8778.
- `gatekeeper.py` is imported and NOT changed.

## Tool 1: route_ticket(text: str) -> str
- Calls `route()` from gatekeeper.py. Returns the team name ("Security", "Access", "Network", "Hardware" or "General").
- Description: "Pick the support team (Security, Access, Network, Hardware or General) that should handle an IT ticket, from its text."
- Blank text: the tool returns an error (the ValueError from route()).

## Tool 2: needs_approval(action: str, user_id: str, hour: int) -> dict
- Calls `needs_approval()` from gatekeeper.py. Parameter names and types match the real function.
- Returns `{"approval": true|false, "approver": "<who>"}`. The dict is returned as is: the approver is needed by the caller, a bare true/false would lose it.
- Description: "Decide whether an IT helpdesk action needs human approval, and who must approve it, from the action name, the employee id and the hour of day (0-23)."
- Unknown action or hour outside 0-23: the tool returns an error (the ValueError from needs_approval()).

## Acceptance criteria
- AC1 The server lists exactly 2 tools: route_ticket, needs_approval.
- AC2 Each tool has a non-empty description.
- AC3 route_ticket("VPN error 809 since morning") -> "Network"
- AC4 route_ticket("Phishing email asked for my password") -> "Security"
- AC5 route_ticket("Cannot download files") -> "General"
- AC6 needs_approval("reset_password", "EMP-1002", 10) -> approval true, approver "service desk lead"
- AC7 needs_approval("search_kb", "EMP-1002", 10) -> approval false
- AC8 needs_approval("update_ticket", "EMP-1001", 10) -> approval true, approver "it manager"
- AC9 needs_approval("delete_user", "EMP-1002", 10) -> error, not a crash
- AC10 route_ticket("") -> error, not a crash
- AC11 `--http` serves on port 8778 and answers tools/list.

## Out of scope
Auth, logging, masking, timeouts (these are controls placed IN FRONT of the server, see my_notes.md), a database, LLM calls.
