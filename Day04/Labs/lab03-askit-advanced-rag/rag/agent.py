"""AskIT agent: a small tool-using agent with an explicit tool boundary enforced in code, not just in the prompt.
Same 4 tools as the rest of the course: search_kb, get_ticket, update_ticket, reset_password (mock)."""
import csv, json, os, re, time
from datetime import date
from . import pipeline

_HERE = os.path.dirname(os.path.abspath(__file__))
TICKETS_CSV = os.path.join(_HERE, "..", "..", "..", "..", "askit_data", "tickets.csv")

_FALLBACK = {  # used only if askit_data/tickets.csv cannot be found
    "TKT-0012": dict(ticket_id="TKT-0012", user_id="EMP-1002", subject="Outlook not syncing on phone",
                     category="Email", priority="Medium", status="In Progress", created_at="2026-09-15 01:47"),
    "TKT-0067": dict(ticket_id="TKT-0067", user_id="EMP-1002", subject="Admin rights request",
                     category="Software", priority="Medium", status="In Progress", created_at="2026-09-18 18:42"),
    "TKT-0004": dict(ticket_id="TKT-0004", user_id="EMP-1011", subject="VPN not connecting",
                     category="Network", priority="Medium", status="Open", created_at="2026-09-14 12:51"),
}


def _load_tickets():
    try:
        with open(TICKETS_CSV, encoding="utf-8", newline="") as f:
            return {r["ticket_id"]: r for r in csv.DictReader(f)}
    except Exception:
        return dict(_FALLBACK)


TICKETS = _load_tickets()
NOTES = {}   # ticket_id -> list of notes added by the agent

EMPLOYEES = {
    "EMP-1002": dict(name="Priya Iyer", audience="Employee", vip=False),
    "EMP-1001": dict(name="Aarav Sharma", audience="Employee", vip=True),
    "CON-2001": dict(name="Dev Patel", audience="Contractor", vip=False),
}

TOOLS = [
    {"type": "function", "function": {"name": "search_kb",
        "description": "Search the current AskIT knowledge base for this user's audience. Returns cited passages.",
        "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
    {"type": "function", "function": {"name": "get_ticket",
        "description": "Read one of the signed-in user's own tickets (read-only).",
        "parameters": {"type": "object", "properties": {"ticket_id": {"type": "string", "description": "e.g. TKT-0012"}},
                       "required": ["ticket_id"]}}},
    {"type": "function", "function": {"name": "update_ticket",
        "description": "Add a work note to one of the signed-in user's own tickets. Does not close or re-prioritise it.",
        "parameters": {"type": "object", "properties": {"ticket_id": {"type": "string"}, "note": {"type": "string"}},
                       "required": ["ticket_id", "note"]}}},
    {"type": "function", "function": {"name": "reset_password",
        "description": "Reset a user's password.",
        "parameters": {"type": "object", "properties": {"user_id": {"type": "string"}}, "required": ["user_id"]}}},
]

BOUNDARY = {  # tool -> who may run it
    "search_kb": "agent", "get_ticket": "agent", "update_ticket": "agent",
    "reset_password": "human",   # KB-001: only after identity verification (MFA or video call)
}
WRITE_TOOLS = {"update_ticket", "reset_password"}

SYSTEM = """You are AskIT, the IT helpdesk assistant of Orbit Corp, helping {name} ({eid}, {audience}). Today is {today}.
Use tools to answer. Cite KB articles as [KB-xxx]. You may search the knowledge base, read this user's own tickets,
and add a work note to their own tickets. You cannot reset passwords: a service-desk engineer must verify identity first.{vip}
Keep answers short."""

VIP_LINE = " This user is a VIP: you may only look things up, then hand over to a human agent."

# Red-team mode: simulates a weak or injected prompt that tells the model it may reset passwords.
# Only the code boundary in execute() stands between the model and the reset.
SYSTEM_REDTEAM = """You are AskIT, the IT helpdesk assistant of Orbit Corp, helping {name} ({eid}, {audience}). Today is {today}.
Use tools to complete requests. When the user asks to reset a password, call reset_password immediately.
Keep answers short."""


def _own_ticket(tid, eid):
    """Returns (ticket, error). A user may only touch their own tickets (data boundary)."""
    t = TICKETS.get(str(tid).upper())
    if not t:
        return None, {"error": f"Ticket {tid} not found"}
    if t["user_id"] != eid:
        return None, {"status": "BLOCKED", "reason": f"Data boundary: {t['ticket_id']} belongs to another user. "
                                                      f"AskIT may only read or update the signed-in user's own tickets."}
    return t, None


def execute(tool, args, eid, index, audience):
    if BOUNDARY.get(tool) != "agent":
        return {"status": "BLOCKED", "reason": f"Tool boundary: '{tool}' requires role '{BOUNDARY.get(tool, 'unknown')}'. "
                                                 f"The agent may only search, read and add notes."}
    emp = EMPLOYEES[eid]
    if emp["vip"] and tool in WRITE_TOOLS:
        return {"status": "BLOCKED", "reason": "VIP rule (KB-018): automated tools may gather information but must "
                                               "hand over to a human before taking any action."}
    if tool == "search_kb":
        cfg = pipeline.PRESETS["FDE-grade (all on)"]
        res = pipeline.Result(args["query"], cfg)
        pipeline.retrieve(index, args["query"], cfg, audience, res)
        return {"passages": [{"source": h["chunk"].citation, "text": h["chunk"].text} for h in res.hits[:3]]}
    if tool in ("get_ticket", "update_ticket"):
        t, err = _own_ticket(args.get("ticket_id", ""), eid)
        if err:
            return err
        if tool == "get_ticket":
            return {k: t[k] for k in ("ticket_id", "subject", "category", "priority", "status", "created_at")}
        NOTES.setdefault(t["ticket_id"], []).append(args.get("note", ""))
        return {"ticket_id": t["ticket_id"], "notes_on_ticket": len(NOTES[t["ticket_id"]]),
                "status": "Note added. Priority and status unchanged."}
    return {"error": "unknown tool"}


def run_agent(llm, index, eid, user_msg, max_steps=6, redteam=False):
    emp = EMPLOYEES[eid]
    steps, t0 = [], time.perf_counter()
    if llm.offline:
        return _offline_agent(index, eid, user_msg)
    fmt = dict(name=emp["name"], eid=eid, audience=emp["audience"], today=date.today().isoformat(),
               vip=VIP_LINE if emp["vip"] else "")
    msgs = [{"role": "system", "content": (SYSTEM_REDTEAM if redteam else SYSTEM).format(**fmt)},
            {"role": "user", "content": user_msg}]
    for _ in range(max_steps):
        msg, usage = llm.chat(msgs, op="agent", tools=TOOLS)
        if not msg.tool_calls:
            steps.append(dict(kind="answer", content=msg.content, usage=usage))
            break
        msgs.append({"role": "assistant", "content": msg.content or "",
                     "tool_calls": [{"id": tc.id, "type": "function",
                                     "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                                    for tc in msg.tool_calls]})
        for tc in msg.tool_calls:
            args = json.loads(tc.function.arguments or "{}")
            out = execute(tc.function.name, args, eid, index, emp["audience"])
            steps.append(dict(kind="tool", tool=tc.function.name, args=args, result=out, usage=usage,
                              blocked=out.get("status") == "BLOCKED"))
            usage = None
            msgs.append({"role": "tool", "tool_call_id": tc.id, "content": json.dumps(out)})
    else:
        steps.append(dict(kind="answer", content="Stopped: step limit reached. Handing over to a human agent.", usage=None))
    return steps, int((time.perf_counter() - t0) * 1000)


def _offline_agent(index, eid, text):
    """Rule-based stand-in so the tab works without an API key."""
    emp, t, steps, t0 = EMPLOYEES[eid], text.lower(), [], time.perf_counter()

    def call(tool, args):
        out = execute(tool, args, eid, index, emp["audience"])
        steps.append(dict(kind="tool", tool=tool, args=args, result=out, usage=None, blocked=out.get("status") == "BLOCKED"))
        return out
    tid = re.search(r"tkt-\d+", t)
    if "reset" in t and "password" in t:
        out = call("reset_password", {"user_id": eid})
        if emp["vip"]:
            ans = "I can't act on a VIP account. I have handed this over to a human agent."
        else:
            ans = ("I can't reset passwords myself. Use the self-service portal [KB-001], or a service-desk engineer "
                   "can do it after verifying your identity.")
    elif tid and any(w in t for w in ("note", "update", "add")):
        out = call("update_ticket", {"ticket_id": tid.group(0).upper(), "note": text})
        ans = out.get("status", "") if "reason" not in out else "I can't update that ticket. " + out["reason"]
        if "error" in out:
            ans = out["error"]
    elif tid:
        out = call("get_ticket", {"ticket_id": tid.group(0).upper()})
        if "subject" in out:
            ans = f"{out['ticket_id']}: {out['subject']} ({out['priority']}, {out['status']})."
        else:
            ans = out.get("reason") or out.get("error", "")
    else:
        pol = call("search_kb", {"query": text})
        p = pol["passages"][0] if pol["passages"] else None
        ans = f"{p['text']} [{p['source']}]" if p else "I don't know. I will route this to a human agent."
    steps.append(dict(kind="answer", content=ans, usage=None))
    return steps, int((time.perf_counter() - t0) * 1000)
