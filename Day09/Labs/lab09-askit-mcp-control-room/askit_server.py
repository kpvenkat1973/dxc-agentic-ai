"""askit_server.py  --  the AskIT MCP server.   (read it, you do not need to edit it)

WHAT IT IS
  A small program that offers the 4 AskIT helpdesk tools (search_kb, get_ticket, update_ticket, reset_password)
  to ANY MCP client: your Lab 9 app, GitHub Copilot in VS Code, a Claude app, a colleague's agent.
  The tools themselves are the SAME Python functions you used on Day 5 (askit_core/tools.py).
  This file only wraps them in the MCP protocol, using the FastMCP library.

HOW THE LAB APP STARTS IT (you never type these yourself)
  stdio :  python askit_server.py            the app starts it as a child process and talks over stdin/stdout
  http  :  python askit_server.py --http     a small web server at http://127.0.0.1:8777/mcp

SWITCHES (environment variables the Lab 9 app sets for the incident / controls tabs)
  ASKIT_DELAY=3    get_ticket waits 3 seconds first   (a slow ticket system)
  ASKIT_FLAKY=2    the first 2 get_ticket calls fail  (a flaky ticket system)
  ASKIT_CONFIRM=1  reset_password first ASKS the user "are you sure?"  (MCP elicitation)
  ASKIT_WIRE=path  write one line per MCP message to this file (the "what went over the wire" view)
"""
import asyncio
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]                       # the course folder (C:\AskIT\dxc-agentic-ai)
sys.path.insert(0, str(ROOT))

from fastmcp import Context, FastMCP                                   # noqa: E402
from fastmcp.exceptions import ToolError                               # noqa: E402
from fastmcp.server.middleware import Middleware                       # noqa: E402
from mcp.types import ElicitRequest, ElicitRequestFormParams, InputRequiredResult   # noqa: E402

from askit_core import tools as T                                      # noqa: E402
from askit_core.data import load_kb                                    # noqa: E402

DESC = {s["toolSpec"]["name"]: s["toolSpec"]["description"] for s in T.TOOL_SPECS}   # same words the model read on Day 5
DELAY = float(os.getenv("ASKIT_DELAY", "0") or 0)
FLAKY = int(os.getenv("ASKIT_FLAKY", "0") or 0)
CONFIRM = os.getenv("ASKIT_CONFIRM", "") not in ("", "0")
WIRE = os.getenv("ASKIT_WIRE", "")
CALLS = {"get_ticket": 0}                    # counts calls, for ASKIT_FLAKY

mcp = FastMCP("AskIT Tools", instructions="Orbit Corp IT helpdesk tools: knowledge base, tickets, password reset.")


# ------------------------------------------------------------------------------------------------ the "wire" log
class WireLog(Middleware):
    """Runs around EVERY MCP message. Writes one line to the wire log: which method, what came in, how long it took."""

    async def on_message(self, context, call_next):
        t0 = time.time()
        error = ""
        try:
            return await call_next(context)
        except Exception as e:                                   # noqa: BLE001
            error = f"{type(e).__name__}: {e}"
            raise
        finally:
            if WIRE:
                try:
                    msg = context.message
                    params = msg.model_dump(exclude_none=True) if hasattr(msg, "model_dump") else {}
                    params.pop("meta", None)
                    params.pop("_meta", None)
                    with open(WIRE, "a", encoding="utf-8") as f:
                        f.write(json.dumps({"time": time.strftime("%H:%M:%S"), "method": context.method,
                                            "params": params, "ms": round((time.time() - t0) * 1000), "error": error},
                                           default=str) + "\n")
                except Exception:                                # noqa: BLE001  logging must never break a call
                    pass


mcp.add_middleware(WireLog())


# ------------------------------------------------------------------------------------------------ the 4 tools
@mcp.tool(description=DESC["search_kb"])
def search_kb(query: str) -> dict:
    return T.search_kb(query)


@mcp.tool(description=DESC["get_ticket"])
async def get_ticket(ticket_id: str) -> dict:
    CALLS["get_ticket"] += 1
    if DELAY:
        await asyncio.sleep(DELAY)                                    # ASKIT_DELAY: pretend the ticket system is slow
    if CALLS["get_ticket"] <= FLAKY:                                  # ASKIT_FLAKY: pretend it fails now and then
        raise ToolError("TRANSIENT: the ticket system is busy. Wait a moment and try again, or tell the user it is slow.")
    return T.get_ticket(ticket_id)


@mcp.tool(description=DESC["update_ticket"])
def update_ticket(ticket_id: str, note: str) -> dict:
    return T.update_ticket(ticket_id, note)


@mcp.tool(description=DESC["reset_password"])
async def reset_password(user_id: str, ctx: Context):
    if CONFIRM and not ctx.input_responses:
        # MCP "elicitation": the server answers "I need more input first". The client asks the human and calls again.
        return InputRequiredResult(input_requests={"confirm": ElicitRequest(params=ElicitRequestFormParams(
            message=f"Reset the password of {user_id}? A temporary password goes to their registered mobile.",
            requested_schema={"type": "object", "required": ["sure"],
                              "properties": {"sure": {"type": "boolean", "title": "Yes, reset it"}}}))})
    if CONFIRM:
        answer = ctx.input_responses["confirm"]
        if getattr(answer, "action", "") != "accept" or not (getattr(answer, "content", None) or {}).get("sure"):
            return {"ok": False, "message": "Cancelled: the user did not confirm, nothing was reset."}
    return T.reset_password(user_id)


# ------------------------------------------------------------------------------------------------ a resource and a prompt
@mcp.resource("kb://article/{article_id}", mime_type="text/markdown")
def kb_article(article_id: str) -> str:
    """One knowledge-base article, e.g. kb://article/KB-004. A resource is READ-ONLY data the client can load."""
    kb = load_kb()
    return kb.get(article_id.upper(), f"No article {article_id}.")


@mcp.prompt
def triage_ticket(ticket_text: str) -> str:
    """A ready-made instruction the client can offer to its users (a prompt template stored on the server)."""
    return ("You are an IT helpdesk triage assistant. Read the ticket, choose the team (Network, Access, Hardware, General), "
            f"and say in one sentence what to do next.\n\nTicket: {ticket_text}")


if __name__ == "__main__":
    if "--http" in sys.argv:
        port = int(sys.argv[sys.argv.index("--port") + 1]) if "--port" in sys.argv else 8777
        mcp.run(transport="http", host="127.0.0.1", port=port, show_banner=False)
    else:
        mcp.run(show_banner=False)                                    # stdio
