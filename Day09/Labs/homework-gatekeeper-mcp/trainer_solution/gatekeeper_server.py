"""AskIT Gatekeeper MCP server v1. Built strictly from SPEC.md.

Thin wrapper: all rules stay in gatekeeper.py (single source of truth).
Run:  python gatekeeper_server.py          (stdio, default)
      python gatekeeper_server.py --http   (HTTP on port 8778)
"""
import os
import sys

# Make `import gatekeeper` work no matter where the server is started from.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastmcp import FastMCP  # noqa: E402

import gatekeeper  # noqa: E402

mcp = FastMCP("AskIT Gatekeeper")


@mcp.tool
def route_ticket(text: str) -> str:
    """Pick the support team (Security, Access, Network, Hardware or General) that should handle an IT ticket, from its text."""
    return gatekeeper.route(text)


@mcp.tool
def needs_approval(action: str, user_id: str, hour: int) -> dict:
    """Decide whether an IT helpdesk action needs human approval, and who must approve it, from the action name, the employee id and the hour of day (0-23)."""
    return gatekeeper.needs_approval(action, user_id, hour)


if __name__ == "__main__":
    if "--http" in sys.argv:
        mcp.run(transport="http", host="127.0.0.1", port=8778, show_banner=False)
    else:
        mcp.run(show_banner=False)  # stdio
