"""multi_agent.py  --  the AskIT multi-agent graph behind the Control Room.   (read it, you do not need to edit it)

WHO DOES WHAT
  app.py            the screen (Streamlit): ticket box, live graph picture, Approve/Reject buttons, compare table.
  multi_agent.py    THIS FILE: the LangGraph graph (nodes + edges), the specialists, the approval policy.
  model_factory.py  picks the model: Bedrock (main) -> Azure -> OpenAI -> Offline.
  askit_core/tools.py  the 4 helpdesk tools from Day 5.

THE FLOW (a LangGraph StateGraph)
  router  ──►  network_agent | access_agent | hardware_agent | general_agent   (ONE specialist runs)
          ──►  policy  ──►  human_approval (pauses with interrupt())  ──►  act  ──►  respond
                      └──────────────(no approval needed)──────────────────────────►  respond

KEY DESIGN CHOICES (the ones a client will ask about)
  * The LLM ROUTES (decides which specialist). Plain-code POLICY decides when a human must approve. Never the LLM.
  * Specialists only get READ tools. The WRITE action (reset_password) runs in the 'act' node, after a human said yes.
  * A checkpointer saves the state after every node, so a crash or a 2-day wait for approval resumes where it stopped.
"""
import operator
import re
import time
from typing import Annotated, TypedDict

from langchain.agents import create_agent
from langchain.tools import tool
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

import model_factory as mf
from askit_core.data import load_users
from askit_core.tools import get_ticket, reset_password, search_kb

ROUTES = ["Network", "Access", "Hardware", "General"]
USERS = {u["user_id"]: u for u in load_users()}

# The 6 sample tickets used by the buttons and the compare tab. 'expect' = the right specialist.
SAMPLES = [
    {"label": "🌐 VPN error 809", "user": "EMP-1004", "expect": "Network",
     "text": "VPN keeps failing with error 809 since this morning, I am working from home and cannot reach any server."},
    {"label": "🔐 Locked out, please reset", "user": "EMP-1021", "expect": "Access",
     "text": "I am locked out of my laptop after changing my password. My ID is EMP-1021. Please reset my password, client call at 11."},
    {"label": "💻 Laptop blue screen", "user": "EMP-1012", "expect": "Hardware",
     "text": "My laptop shows a blue screen and restarts every time I open Excel. Ticket TKT-0007 has the details."},
    {"label": "👑 VIP: CEO email not syncing", "user": "EMP-1001", "expect": "General",
     "text": "Aarav here. My email is not syncing on my mobile and I have the board meeting in one hour."},
    {"label": "📦 Need Python installed", "user": "EMP-1002", "expect": "General",
     "text": "I need Python installed for a data project, it is not in Software Center."},
    {"label": "🎣 Suspicious email", "user": "EMP-1003", "expect": "General",
     "text": "I got an email asking me to confirm my bank details on a strange link. Is this phishing? What do I do?"},
]

ROUTER_PROMPT = """You are the router of the Orbit Corp IT helpdesk. Read the ticket and pick the ONE team that should handle it.
Network  = VPN, Wi-Fi, internet, connectivity
Access   = passwords, locked accounts, login, MFA, permissions
Hardware = laptops, screens, printers, phones, devices
General  = everything else (software, email, security questions, how-to)
Reply with ONE word only: Network, Access, Hardware or General."""

SPECIALISTS = {
    "Network": ("network_agent", "You are the AskIT NETWORK specialist. Use search_kb for VPN / Wi-Fi articles.", [search_kb]),
    "Access": ("access_agent", "You are the AskIT ACCESS specialist. Use search_kb for password / lockout / MFA articles. "
               "You can NOT reset passwords yourself: if a reset is needed, say that a reset has been requested for approval.",
               [search_kb, get_ticket]),
    "Hardware": ("hardware_agent", "You are the AskIT HARDWARE specialist. Use get_ticket when a ticket id is given, "
                 "and search_kb for device articles.", [search_kb, get_ticket]),
    "General": ("general_agent", "You are the AskIT GENERAL helpdesk agent. Use search_kb.", [search_kb]),
}
SPECIALIST_RULES = " Answer ONLY from the tools. Cite the article id like [KB-004]. Reply in 2-3 short sentences for the user."

SINGLE_PROMPT = """You are AskIT, the IT helpdesk agent of Orbit Corp. You handle EVERY kind of ticket alone.
Teams: Network (VPN, Wi-Fi), Access (passwords, lockouts, MFA), Hardware (laptops, printers, phones), General (everything else).
Use search_kb for how-to articles, get_ticket for ticket ids, update_ticket to add notes, reset_password to reset a password.
Start your reply with 'Team: <Network|Access|Hardware|General>.' then help the user in 2-3 sentences, citing [KB-xxx]."""


class TicketState(TypedDict, total=False):
    ticket: str
    user_id: str
    route: str
    specialist_reply: str
    action: str                 # "none" or "reset_password"
    why_approval: str
    approval: str               # "not needed" / "approved" / "rejected"
    approver_note: str
    action_result: str
    final: str
    trace: Annotated[list, operator.add]          # one row per node: appended, never overwritten


def _row(node, what, t0, tokens=0, calls=0):
    return [{"node": node, "what": what, "tokens": tokens, "llm calls": calls, "seconds": round(time.time() - t0, 2)}]


def _usage(messages):
    return sum((getattr(m, "usage_metadata", None) or {}).get("input_tokens", 0) for m in messages)


def build_graph(model, checkpointer, vip_rule=False, crash=None):
    """Builds and compiles the graph.
    vip_rule = the client curveball: 'VIP users always go to a human'.
    crash    = a dict like {"armed": True}; when armed, the policy node fails ONCE (to show resume from checkpoint)."""

    # ---------------------------------------------------------------- node 1: router (LLM picks the team)
    def router(state):
        t0 = time.time()
        reply = model.invoke([{"role": "system", "content": ROUTER_PROMPT}, {"role": "user", "content": state["ticket"]}])
        word = mf.text_of(reply).strip().split()[0].strip(".,:*") if mf.text_of(reply).strip() else "General"
        route = next((r for r in ROUTES if r.lower() == word.lower()), "General")
        tokens = (getattr(reply, "usage_metadata", None) or {}).get("input_tokens", 0)
        return {"route": route, "trace": _row("router", f"LLM picked → {route}", t0, tokens, 1)}

    # ---------------------------------------------------------------- nodes 2-5: the specialists (small agents)
    def make_specialist(route):
        name, prompt, tools = SPECIALISTS[route]
        agent = create_agent(model=model, tools=[tool(t) for t in tools], system_prompt=prompt + SPECIALIST_RULES)

        def specialist(state):
            t0 = time.time()
            out = agent.invoke({"messages": [{"role": "user", "content": state["ticket"]}]})
            msgs = out["messages"]
            used = sorted({c["name"] for m in msgs for c in getattr(m, "tool_calls", [])})
            calls = sum(1 for m in msgs if m.type == "ai")
            return {"specialist_reply": mf.text_of(msgs[-1]),
                    "trace": _row(name, f"answered · tools: {', '.join(used) or 'none'}", t0, _usage(msgs), calls)}
        return name, specialist

    # ---------------------------------------------------------------- node 6: policy (plain code, NO LLM)
    def policy(state):
        t0 = time.time()
        if crash and crash.get("armed"):
            crash["armed"] = False
            raise RuntimeError("💥 Simulated crash: the server restarted in the middle of the ticket")
        text = state["ticket"].lower()
        user = USERS.get(state.get("user_id", ""), {})
        # Policy does NOT trust the router: a reset request needs approval whichever team the LLM picked.
        wants_reset = any(w in text for w in ("reset my password", "reset password", "password reset", "locked out",
                                              "account locked", "reset my account"))
        is_vip = user.get("vip") == "yes"
        if wants_reset:
            action, why = "reset_password", "A password reset CHANGES data → a human must approve it."
        elif vip_rule and is_vip:
            action, why = "escalate_vip", "Client rule: VIP users always go to a human."
        else:
            action, why = "none", ""
        if vip_rule and is_vip and action == "reset_password":
            why += " The user is also a VIP."
        what = f"needs approval: {action}" if action != "none" else "no approval needed"
        return {"action": action, "why_approval": why, "approval": "not needed" if action == "none" else "pending",
                "trace": _row("policy", what, t0)}

    # ---------------------------------------------------------------- node 7: human approval (PAUSES the graph)
    def human_approval(state):
        t0 = time.time()
        decision = interrupt({"action": state["action"], "user_id": state.get("user_id"), "why": state["why_approval"],
                              "draft_reply": state.get("specialist_reply", "")})
        approved = str(decision.get("decision", "")).lower() == "approve"
        return {"approval": "approved" if approved else "rejected", "approver_note": decision.get("note", ""),
                "trace": _row("human_approval", f"human said {'YES' if approved else 'NO'}", t0)}

    # ---------------------------------------------------------------- node 8: act (the only place a WRITE happens)
    def act(state):
        t0 = time.time()
        if state.get("approval") != "approved":
            return {"action_result": "Not done: the approver rejected it. A human agent will contact you.",
                    "trace": _row("act", "skipped (rejected)", t0)}
        if state["action"] == "reset_password":
            res = reset_password(state.get("user_id", ""))
            msg = res.get("message") or res.get("error", "")
        else:
            msg = "A senior human agent has taken over this ticket."
        return {"action_result": msg, "trace": _row("act", f"executed {state['action']}", t0)}

    # ---------------------------------------------------------------- node 9: respond (assemble the reply, no LLM)
    def respond(state):
        t0 = time.time()
        parts = [state.get("specialist_reply", "")]
        if state.get("action_result"):
            parts.append(f"**Action:** {state['action_result']}")
        return {"final": "\n\n".join(p for p in parts if p), "trace": _row("respond", "reply sent", t0)}

    # ---------------------------------------------------------------- wire the graph: nodes + edges
    g = StateGraph(TicketState)
    g.add_node("router", router)
    for r in ROUTES:
        name, fn = make_specialist(r)
        g.add_node(name, fn)
        g.add_edge(name, "policy")
    g.add_node("policy", policy)
    g.add_node("human_approval", human_approval)
    g.add_node("act", act)
    g.add_node("respond", respond)
    g.add_edge(START, "router")
    g.add_conditional_edges("router", lambda s: SPECIALISTS[s["route"]][0],             # conditional routing
                            {SPECIALISTS[r][0]: SPECIALISTS[r][0] for r in ROUTES})
    g.add_conditional_edges("policy", lambda s: "human_approval" if s["action"] != "none" else "respond",
                            {"human_approval": "human_approval", "respond": "respond"})
    g.add_edge("human_approval", "act")
    g.add_edge("act", "respond")
    g.add_edge("respond", END)
    return g.compile(checkpointer=checkpointer)


def user_of(text, default):
    m = re.search(r"EMP-\d+", text, re.I)
    return m.group(0).upper() if m else default


# ------------------------------------------------------------------------------------------------ the single-agent baseline
def single_agent(model):
    """ONE agent with ALL 4 tools, including the write tools. Used only in the compare tab."""
    from askit_core.tools import update_ticket
    return create_agent(model=model, tools=[tool(search_kb), tool(get_ticket), tool(update_ticket), tool(reset_password)],
                        system_prompt=SINGLE_PROMPT)


def run_single(agent, ticket):
    t0 = time.time()
    out = agent.invoke({"messages": [{"role": "user", "content": ticket}]})
    msgs = out["messages"]
    text = mf.text_of(msgs[-1])
    team = re.search(r"Team:\s*(Network|Access|Hardware|General)", text, re.I)
    writes = [c["name"] for m in msgs for c in getattr(m, "tool_calls", []) if c["name"] in ("reset_password", "update_ticket")]
    return {"route": team.group(1).title() if team else _guess(text), "llm calls": sum(1 for m in msgs if m.type == "ai"),
            "tokens": _usage(msgs), "seconds": round(time.time() - t0, 1), "writes without approval": len(writes),
            "answer": text}


def _guess(text):
    return next((r for r in ROUTES if r.lower() in text.lower()), "General")
