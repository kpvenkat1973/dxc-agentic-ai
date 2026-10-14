"""mcp_client.py  --  everything on the CLIENT side of MCP.   (read it, you do not need to edit it)

WHO DOES WHAT
  app.py            the screen.
  mcp_client.py     THIS FILE. Connects to a tool server (3 possible homes), asks "what tools do you have?", calls tools,
                    and wraps every call in "controls" (role block, timeout + retry, redaction, logging).
  askit_server.py   the MCP server: the 4 AskIT tools. Runs on this VM (stdio or HTTP) ...
  aws/askit-mcp-lambda.zip   ... or on AWS Lambda. Same 4 tools, same protocol.
  model_factory.py  picks the AI model (Bedrock main, Azure / OpenAI backup, Offline stand-in).

THE 3 HOMES  (the agent code is IDENTICAL for all three, only the line that connects is different)
  stdio  : the app starts askit_server.py as a child process and talks to it through stdin/stdout.
  http   : askit_server.py runs as a small web service on this VM:  http://127.0.0.1:8777/mcp
  lambda : the same tools run in AWS Lambda behind a Function URL (https://....lambda-url.us-east-1.on.aws/)

THE "CONTROLS" (called tool interceptors in LangChain)
  A function that runs around EVERY tool call, before the call and after it. The tool and the agent never change.
  Order here:  1 role / VIP block  ->  2 timeout + retry  ->  3 call the server  ->  4 redact  ->  5 log
"""
import asyncio
import atexit
import json
import os
import re
import signal
import socket
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import httpx
from fastmcp import Client
from fastmcp.client.elicitation import ElicitResult
from fastmcp.client.transports import StdioTransport, StreamableHttpTransport

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from askit_core.data import load_users                                   # noqa: E402

WIRE_DIR = HERE / ".wire"
SERVER_PY = HERE / "askit_server.py"
LAMBDA_FILE = HERE / "aws" / "my_lambda.json"
HTTP_PORT = 8777
WRITE_TOOLS = {"update_ticket", "reset_password"}
MODERN = "2026-07-28"

HOME_LABELS = {"stdio": "1 · This VM · stdio", "http": "2 · This VM · HTTP", "lambda": "3 · AWS Lambda"}
HOME_HELP = {
    "stdio": "The app starts the server as a child process and talks through stdin/stdout. Nothing can be reached from outside.",
    "http": "The server runs as a small web service on this VM (port 8777). Any client on this machine can call it.",
    "lambda": "The same tools run in AWS Lambda behind an HTTPS Function URL. Anyone with the URL and key can call it.",
}

USERS = {u["user_id"]: u for u in load_users()}


@dataclass
class Home:
    kind: str = "stdio"
    url: str = ""
    key: str = ""

    @property
    def label(self):
        return HOME_LABELS[self.kind]


@dataclass
class Controls:
    role: str = "service-desk"          # "service-desk" can write, "read-only" cannot
    vip_block: bool = False             # VIP users: write tools are blocked (a human must do it)
    redact: bool = False                # mask emails, phone numbers and names in tool results
    redact_ids: bool = False            # ... and employee ids too (strict)
    timeout_s: float = 6.0
    retries: int = 1
    confirm_on: bool = False            # server asks "are you sure?" before reset_password
    confirm_answer: bool = True         # what the human answers
    delay_s: float = 0.0                # server switches (local homes only; Lambda uses its own environment variables)
    flaky: int = 0

    def summary(self):
        bits = [f"role={self.role}", f"timeout={self.timeout_s:g}s", f"retries={self.retries}"]
        bits += [n for n, on in (("VIP block", self.vip_block), ("redact", self.redact), ("strict redact", self.redact_ids),
                                 ("confirm", self.confirm_on)) if on]
        return " · ".join(bits)


# ------------------------------------------------------------------------------------------------ servers on this VM
def server_env(ctl, wire_name):
    WIRE_DIR.mkdir(exist_ok=True)
    env = dict(os.environ)
    env.update({"PYTHONIOENCODING": "utf-8", "FASTMCP_LOG_LEVEL": "CRITICAL", "ASKIT_DELAY": str(ctl.delay_s), "ASKIT_FLAKY": str(ctl.flaky),
                "ASKIT_CONFIRM": "1" if ctl.confirm_on else "0", "ASKIT_WIRE": str(WIRE_DIR / f"{wire_name}.jsonl")})
    return env


def _port_open(port):
    with socket.socket() as s:
        s.settimeout(0.3)
        return s.connect_ex(("127.0.0.1", port)) == 0


def stop_local_http():
    pid_file = WIRE_DIR / "http.pid"
    if pid_file.exists():
        try:
            os.kill(int(pid_file.read_text().split()[0]), signal.SIGTERM)
        except Exception:                                        # noqa: BLE001
            pass
        pid_file.unlink(missing_ok=True)
    for _ in range(30):
        if not _port_open(HTTP_PORT):
            break
        time.sleep(0.1)


atexit.register(stop_local_http)


def ensure_local_http(ctl):
    """Start (or restart, when the switches changed) the local HTTP server. Returns (ok, message)."""
    WIRE_DIR.mkdir(exist_ok=True)
    sig = f"{ctl.delay_s}|{ctl.flaky}|{ctl.confirm_on}"
    pid_file = WIRE_DIR / "http.pid"
    if _port_open(HTTP_PORT) and pid_file.exists() and pid_file.read_text().split()[1:] == [sig]:
        return True, "already running"
    stop_local_http()
    if _port_open(HTTP_PORT):
        return False, f"Port {HTTP_PORT} is used by another program. Close it and press the button again."
    log = open(WIRE_DIR / "http_server.log", "w", encoding="utf-8")
    proc = subprocess.Popen([sys.executable, str(SERVER_PY), "--http", "--port", str(HTTP_PORT)], cwd=str(HERE),
                            env=server_env(ctl, "http"), stdout=log, stderr=log)
    pid_file.write_text(f"{proc.pid} {sig}")
    for _ in range(100):
        if _port_open(HTTP_PORT):
            return True, "started"
        if proc.poll() is not None:
            return False, "The server stopped at start-up. See .wire/http_server.log"
        time.sleep(0.2)
    return False, "The server did not start in 20 seconds."


def load_lambda():
    try:
        return json.loads(LAMBDA_FILE.read_text(encoding="utf-8"))
    except Exception:                                            # noqa: BLE001
        return {"url": "", "key": ""}


def save_lambda(url, key):
    LAMBDA_FILE.parent.mkdir(exist_ok=True)
    LAMBDA_FILE.write_text(json.dumps({"url": url.strip(), "key": key.strip()}), encoding="utf-8")


def home_ready(home, ctl):
    """(ok, why-not) before we try to connect."""
    if home.kind == "lambda" and not home.url.startswith("https://"):
        return False, "Add your Lambda Function URL in tab 5 (☁️ Move to AWS) first."
    if home.kind == "http":
        return ensure_local_http(ctl)
    return True, ""


# ------------------------------------------------------------------------------------------------ connecting
class Asked:
    """Remembers every time the server asked the human a question (MCP elicitation)."""

    def __init__(self, answer):
        self.answer, self.log = answer, []

    async def handler(self, message, response_type, params, context):
        self.log.append(message)
        return ElicitResult(action="accept", content={"sure": bool(self.answer)})


def make_client(home, ctl, asked=None):
    asked = asked or Asked(ctl.confirm_answer)
    if home.kind == "stdio":
        tr = StdioTransport(sys.executable, [str(SERVER_PY)], env=server_env(ctl, "stdio"), cwd=str(HERE), keep_alive=False)
    elif home.kind == "http":
        tr = StreamableHttpTransport(f"http://127.0.0.1:{HTTP_PORT}/mcp")
    else:
        tr = StreamableHttpTransport(home.url, headers={"x-askit-key": home.key} if home.key else {})
    return Client(tr, elicitation_handler=asked.handler)


def wire_file(home):
    return WIRE_DIR / f"{home.kind}.jsonl"


def clear_wire(home):
    WIRE_DIR.mkdir(exist_ok=True)
    wire_file(home).write_text("", encoding="utf-8")


def read_wire(home):
    try:
        return [json.loads(x) for x in wire_file(home).read_text(encoding="utf-8").splitlines() if x.strip()]
    except Exception:                                            # noqa: BLE001
        return []


def explain_error(e, home):
    """Turn a scary exception into one plain sentence."""
    text = f"{type(e).__name__}: {e}"
    if isinstance(e, (asyncio.TimeoutError, TimeoutError)):
        return "Timed out: the server did not answer in time."
    if "401" in text or "Unauthorized" in text:
        return "The server refused the call (401). The key (header x-askit-key) does not match the ASKIT_KEY set on the Lambda."
    if "502" in text or "504" in text:
        return "HTTP 502/504 from AWS: the Lambda probably ran longer than its Timeout (default 3 s) or crashed. Look at its CloudWatch logs."
    if "403" in text:
        return "HTTP 403 from AWS: the Function URL is not public yet (Auth type must be NONE, and the permission must exist)."
    if "404" in text or "Name or service not known" in text or "getaddrinfo" in text:
        return "Cannot reach that address. Check the Function URL for typos."
    return text[:300]


# ------------------------------------------------------------------------------------------------ inspect (tab 1)
async def inspect(home, ctl):
    """Connect, then ask the server what it offers. Returns a dict for the screen."""
    t0 = time.time()
    out = {"home": home.kind}
    async with make_client(home, ctl) as c:
        out["connect_ms"] = round((time.time() - t0) * 1000)
        info = c.server_info
        out.update({"server": f"{info.name} {info.version}" if info else "?", "protocol": getattr(c, "protocol_version", "?"),
                    "capabilities": [k for k, v in (c.server_capabilities.model_dump(exclude_none=True).items() if c.server_capabilities else []) if v is not None]})
        t1 = time.time()
        tools = await c.list_tools()
        out["list_ms"] = round((time.time() - t1) * 1000)
        out["tools"] = [{"name": t.name, "description": t.description or "", "schema": t.input_schema} for t in tools]
        for key, fn in (("resources", c.list_resources), ("templates", c.list_resource_templates), ("prompts", c.list_prompts)):
            try:
                out[key] = [getattr(x, "name", str(x)) + (f"  ({getattr(x, 'uri_template', '')})" if key == "templates" else "")
                            for x in await fn()]
            except Exception:                                    # noqa: BLE001
                out[key] = []
    return out


async def read_extras(home, ctl):
    """Read one resource and one prompt (only the local servers offer them)."""
    res = {}
    async with make_client(home, ctl) as c:
        try:
            r = await c.read_resource("kb://article/KB-004")
            res["resource"] = r[0].text
        except Exception as e:                                   # noqa: BLE001
            res["resource"] = f"(this server has no resources: {explain_error(e, home)[:100]})"
        try:
            p = await c.get_prompt("triage_ticket", {"ticket_text": "VPN keeps failing with error 809"})
            res["prompt"] = p.messages[0].content.text
        except Exception as e:                                   # noqa: BLE001
            res["prompt"] = f"(this server has no prompts: {explain_error(e, home)[:100]})"
    return res


async def call_by_hand(home, ctl, tool, args):
    """Tab 1: one raw tool call, no controls."""
    t0 = time.time()
    async with make_client(home, ctl) as c:
        res = await c.call_tool(tool, args, raise_on_error=False)
    text = res.content[0].text if res.content else ""
    return {"ok": not res.is_error, "text": text, "ms": round((time.time() - t0) * 1000)}


def raw_rpc(home, method, params=None):
    """Send ONE hand-written JSON message to an HTTP home with the plain `httpx` library. No MCP library at all."""
    body = {"jsonrpc": "2.0", "id": 1, "method": method,
            "params": {**(params or {}), "_meta": {"io.modelcontextprotocol/protocolVersion": MODERN,
                                                   "io.modelcontextprotocol/clientInfo": {"name": "raw-httpx", "version": "0"},
                                                   "io.modelcontextprotocol/clientCapabilities": {}}}}
    url = f"http://127.0.0.1:{HTTP_PORT}/mcp" if home.kind == "http" else home.url
    headers = {"content-type": "application/json", "accept": "application/json, text/event-stream", "mcp-protocol-version": MODERN}
    if home.kind == "lambda" and home.key:
        headers["x-askit-key"] = home.key
    t0 = time.time()
    r = httpx.post(url, json=body, headers=headers, timeout=20)
    ms = round((time.time() - t0) * 1000)
    try:
        shown = json.dumps(r.json(), indent=2)
    except ValueError:
        shown = r.text
    return {"url": url, "headers": {k: v for k, v in headers.items()}, "request": json.dumps(body, indent=2),
            "status": r.status_code, "response": shown, "ms": ms}


# ------------------------------------------------------------------------------------------------ the controls (interceptors)
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
PHONE = re.compile(r"(?<![\w-])\+?\d[\d\s-]{8,}\d(?![\w-])")


def redact_text(text, strict):
    t = EMAIL.sub("[email]", text)
    t = PHONE.sub("[phone]", t)
    for u in USERS.values():
        t = t.replace(u["name"], "[name]")
    if strict:
        t = re.sub(r"EMP-\d+", "EMP-****", t)
    return t


def is_vip(user_id):
    return USERS.get(str(user_id).upper(), {}).get("vip") == "yes"


async def guarded_call(client, asked, name, args, ctl, home, trace, who=""):
    """ONE tool call, wrapped in the controls. Returns {'ok','text','fired','attempts','ms'}; also appends a row to `trace`."""
    t0 = time.time()
    fired, attempts, raw_text, ok = [], [], "", True
    asked_before = len(asked.log)
    row = {"step": len(trace) + 1, "home": home.kind, "tool": name, "args": json.dumps(args, ensure_ascii=False)}

    def finish(text, ok_, blocked=False):
        row.update({"controls fired": ", ".join(fired) or "-", "attempts": len(attempts), "ms": round((time.time() - t0) * 1000),
                    "server sent": raw_text[:240], "model sees": text[:240], "result": "blocked" if blocked else ("ok" if ok_ else "ERROR")})
        row["attempt detail"] = attempts
        trace.append(row)
        return {"ok": ok_, "text": text, "fired": fired, "attempts": attempts, "ms": row["ms"], "blocked": blocked}

    # 1 · role / VIP block: decided in plain code, BEFORE the server is called
    if name in WRITE_TOOLS and ctl.role == "read-only":
        fired.append("role block")
        return finish(json.dumps({"error": "Blocked by policy: this agent has a READ-ONLY role and may not use write tools."}), False, True)
    if name in WRITE_TOOLS and ctl.vip_block and is_vip(args.get("user_id", "")):
        fired.append("VIP block")
        return finish(json.dumps({"error": "Blocked by policy: VIP users are handled by a human agent. Tell the user a human will call."}), False, True)

    # 2 · timeout + retry around the real call
    result = None
    for attempt in range(1, ctl.retries + 2):
        a0 = time.time()
        try:
            result = await asyncio.wait_for(client.call_tool(name, args, raise_on_error=False), ctl.timeout_s)
            raw_text = result.content[0].text if result.content else ""
            if result.is_error and raw_text.startswith("TRANSIENT"):
                attempts.append({"attempt": attempt, "seconds": round(time.time() - a0, 2), "outcome": "server said: busy"})
                result = None
            else:
                attempts.append({"attempt": attempt, "seconds": round(time.time() - a0, 2), "outcome": "answered"})
                break
        except asyncio.TimeoutError:
            attempts.append({"attempt": attempt, "seconds": round(time.time() - a0, 2), "outcome": f"TIMEOUT after {ctl.timeout_s:g}s"})
            raw_text = f"(no answer within {ctl.timeout_s:g} s)"
        except Exception as e:                                   # noqa: BLE001
            msg = explain_error(e, home)
            attempts.append({"attempt": attempt, "seconds": round(time.time() - a0, 2), "outcome": "ERROR"})
            raw_text = msg
            result = None
            break
        if attempt <= ctl.retries:
            fired.append(f"retry {attempt}")
            await asyncio.sleep(0.4 * attempt)                   # a short back-off before trying again
    if len(asked.log) > asked_before:
        fired.append(f"server asked: “{asked.log[-1][:60]}…” → you said {'YES' if ctl.confirm_answer else 'NO'}")

    if result is None:
        text = json.dumps({"error": f"The tool '{name}' did not answer after {len(attempts)} attempt(s): {raw_text}"})
        return finish(text, False)
    ok = not result.is_error
    text = raw_text if not ok else (json.dumps(result.data, ensure_ascii=False) if result.data is not None else raw_text)
    if ok:
        raw_text = text

    # 3 · redact what the model is allowed to see
    if ctl.redact and ok:
        masked = redact_text(text, ctl.redact_ids)
        if masked != text:
            fired.append("redact" + (" (strict)" if ctl.redact_ids else ""))
        text = masked
    return finish(text, ok)


# ------------------------------------------------------------------------------------------------ the agent
SYSTEM = ("You are AskIT, the IT helpdesk agent of Orbit Corp. Use the tools you are given. Use search_kb for how-to questions and cite "
          "the article id like [KB-004]. Use get_ticket for ticket ids. Use reset_password ONLY when the user clearly asks you to reset "
          "a password for an employee id. If a tool reports an error, say so honestly. Answer in 2-3 short sentences.")


# Tab 3 only: a NEUTRAL prompt with no tool hints, so the model must choose from the descriptions alone.
# (SYSTEM above names the right tool for each kind of question and would hide bad descriptions.)
PROBE_SYSTEM = "You are the AskIT helpdesk agent. Use the tools you are given to answer the user."


def build_tools(client, asked, mcp_tools, ctl, home, trace, desc_override=None):
    """Turn each MCP tool into a LangChain tool. The model sees ONLY name + description + inputs."""
    from langchain_core.tools import StructuredTool
    tools = []
    for t in mcp_tools:
        def make(tool_name):
            async def run(**kwargs):
                res = await guarded_call(client, asked, tool_name, kwargs, ctl, home, trace)
                return res["text"]
            return run
        tools.append(StructuredTool(name=t.name, description=(desc_override or {}).get(t.name, t.description or ""),
                                    args_schema=t.input_schema, coroutine=make(t.name)))
    return tools


def _tokens(msgs):
    tin = tout = 0
    for m in msgs:
        u = getattr(m, "usage_metadata", None) or {}
        tin += u.get("input_tokens", 0)
        tout += u.get("output_tokens", 0)
    return tin, tout


async def run_agent(question, home, ctl, model, desc_override=None, max_steps=8):
    """Ask the agent ONE question. The agent code is the same for every home."""
    from langchain.agents import create_agent
    from langgraph.errors import GraphRecursionError
    import model_factory as mf
    trace, t0 = [], time.time()
    asked = Asked(ctl.confirm_answer)
    gave_up = False
    async with make_client(home, ctl, asked) as client:
        mcp_tools = await client.list_tools()
        agent = create_agent(model=model, tools=build_tools(client, asked, mcp_tools, ctl, home, trace, desc_override), system_prompt=SYSTEM)
        try:
            out = await agent.ainvoke({"messages": [{"role": "user", "content": question}]}, {"recursion_limit": 2 * max_steps + 1})
            msgs = out["messages"]
        except GraphRecursionError:
            msgs, gave_up = [], True
    steps = []
    for m in msgs:
        if m.type == "ai" and getattr(m, "tool_calls", None):
            for c in m.tool_calls:
                steps.append({"who": "🧠 model decides", "what": f"call {c['name']}({json.dumps(c['args'], ensure_ascii=False)})"})
        elif m.type == "tool":
            steps.append({"who": "🛠️ tool answers", "what": mf.text_of(m)[:260]})
        elif m.type == "ai":
            steps.append({"who": "💬 final answer", "what": mf.text_of(m)})
    tin, tout = _tokens(msgs)
    final = next((mf.text_of(m) for m in reversed(msgs) if m.type == "ai" and not getattr(m, "tool_calls", None)), "")
    if gave_up:
        final = f"(The agent gave up after {max_steps} steps: it kept calling tools without finishing.)"
    return {"home": home.kind, "question": question, "final": final, "steps": steps, "trace": trace,
            "tokens_in": tin, "tokens_out": tout, "llm_calls": sum(1 for m in msgs if m.type == "ai"),
            "seconds": round(time.time() - t0, 2), "tool_ms": sum(r["ms"] for r in trace), "gave_up": gave_up,
            "asked": asked.log}


async def call_with_controls(home, ctl, tool, args):
    """Tabs 4 + 6: ONE tool call through the controls, no AI model involved. Returns (result, trace row, questions the server asked)."""
    trace, asked = [], Asked(ctl.confirm_answer)
    async with make_client(home, ctl, asked) as c:
        res = await guarded_call(c, asked, tool, args, ctl, home, trace)
    return res, trace[0], asked.log


async def time_calls(home, ctl, n=3):
    """Tab 5: n identical calls, each on a fresh connection. The first one on a sleeping Lambda is the slow 'cold start'."""
    out = []
    for _ in range(n):
        t0 = time.time()
        async with make_client(home, ctl) as c:
            await c.call_tool("get_ticket", {"ticket_id": "TKT-0004"}, raise_on_error=False)
        out.append(round((time.time() - t0) * 1000))
    return out


async def probe_tool_choice(questions, home, ctl, model, desc_override):
    """Tab 3: for each question, which tool does the model WANT to call? (We stop before running any tool.)"""
    import model_factory as mf
    picks = []
    async with make_client(home, ctl) as client:
        mcp_tools = await client.list_tools()
        tools = build_tools(client, Asked(True), mcp_tools, ctl, home, [], desc_override)
        bound = model.bind_tools(tools)
        for q in questions:
            try:
                reply = await bound.ainvoke([{"role": "system", "content": PROBE_SYSTEM}, {"role": "user", "content": q}])
                calls = [c["name"] for c in (getattr(reply, "tool_calls", None) or [])]
                u = getattr(reply, "usage_metadata", None) or {}
                picks.append({"picked": calls[0] if calls else "(no tool)", "tokens_in": u.get("input_tokens", 0),
                              "tokens_out": u.get("output_tokens", 0), "text": mf.text_of(reply)[:120]})
            except Exception as e:                               # noqa: BLE001
                picks.append({"picked": f"error: {str(e)[:80]}", "tokens_in": 0, "tokens_out": 0, "text": ""})
    return picks


def run(coro):
    """Run an async function from the (non-async) Streamlit screen."""
    return asyncio.run(coro)
