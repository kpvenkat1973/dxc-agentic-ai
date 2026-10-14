"""design_decision.py  --  builds your team's ADR-AskIT-02 from your choices + your lab numbers.
Used by tab 9 of the app. You do not need to edit this file.

An ADR is a one-page record of ONE important design decision: context, decision, rejected alternatives, evidence, cost.
Review boards (ARB) and clients read ADRs before they approve money or go-live.
"""
import statistics
from datetime import date

CURVEBALLS = {
    "team-a": {"title": "Four more teams want the same ticket tools",
               "from": "Orbit Corp CIO",
               "detail": "Next quarter an HR bot, a Finance bot, a Facilities bot and a partner's agent all need to read tickets and "
                         "search the knowledge base. Today each agent team would copy the tool code. What do you do?",
               "evidence": "Tab 1: one server, many clients. Tab 7: the N × M slider (agents × tools).",
               "topic": "Reuse, ownership and versioning of tools (why MCP)"},
    "team-b": {"title": "Every call logged, personal data masked, writes only by role",
               "from": "Orbit Corp CISO",
               "detail": "Security wants every tool call logged, names / e-mails / phones masked before the AI sees them, and write tools "
                         "limited by role. They do NOT trust each agent team to remember to do it. Where do these controls live?",
               "evidence": "Tab 4: the controls. Which of them could a careless agent team forget?",
               "topic": "Where controls live: in each agent, in the server, or in a gateway"},
    "team-c": {"title": "The real ticket system is inside our data centre",
               "from": "Orbit Corp Head of Network",
               "detail": "The production ticket system sits behind the firewall and has no internet address. A Lambda in AWS cannot reach it. "
                         "Where should the MCP server run, and how does the agent reach it?",
               "evidence": "Tab 5: the three homes and what each can reach. Compare latency of the homes in the evidence table.",
               "topic": "Connectivity, networking and where the server runs"},
    "team-d": {"title": "On Monday mornings the ticket system is slow",
               "from": "Orbit Corp Head of Operations",
               "detail": "Every Monday around 9 the ticket system takes 30+ seconds to answer. Agents hang, users wait, costs rise. "
                         "What is your design for slow and flaky tools?",
               "evidence": "Tab 6: the incident. Which timeout and retry settings gave the best result?",
               "topic": "Timeouts, retries, fallbacks and graceful failure"},
}

HOMES = ["Inside each agent's own code (no MCP)", "One MCP server we run on a VM or container",
         "MCP server on AWS Lambda (serverless)", "A managed gateway in front of our APIs (AgentCore Gateway)"]
CONTROLS = ["In each agent / client (interceptors)", "Inside the MCP server", "In a gateway in front of the server"]
IDENTITY = ["A shared secret in a header (fine for class only)", "IAM-signed requests or OAuth tokens per caller",
            "The gateway checks identity for us"]

RUBRIC = [("Decision", "One clear sentence a CIO understands"),
          ("Alternatives", "At least one option rejected, with a real reason"),
          ("Controls + identity", "Where logging, masking, role checks and identity live, and why there"),
          ("Evidence", "Numbers from the lab: latency, tool definition size, incident result"),
          ("Curveball", "What changed in the design, and what did NOT change")]


def evidence_from(calls, probe, incident):
    """calls: list of {'home','tool','ms'}; probe: {'preset': (right, total)}; incident: dict or None."""
    if not calls and not probe and not incident:
        return None
    by_home = {}
    for c in calls:
        by_home.setdefault(c["home"], []).append(c["ms"])
    return {"latency": {h: (len(v), round(statistics.median(v)), max(v)) for h, v in by_home.items()}, "probe": probe or {},
            "incident": incident}


def build_markdown(team, members, home, controls, identity, why, rejected, curveball_answer, slow_rows, ev, model_label):
    cb = CURVEBALLS[team]
    lines = []
    if ev and ev["latency"]:
        lines.append("| Home of the tool server | Calls measured | Median ms | Slowest ms |\n|---|---|---|---|")
        names = {"stdio": "This VM · stdio", "http": "This VM · HTTP", "lambda": "AWS Lambda"}
        lines += [f"| {names.get(h, h)} | {n} | {med} | {mx} |" for h, (n, med, mx) in ev["latency"].items()]
    if ev and ev["probe"]:
        lines.append("\n| Tool descriptions (6 test questions) | Right tool picked |\n|---|---|")
        lines += [f"| {k} | {r}/{t} |" for k, (r, t) in ev["probe"].items()]
    if ev and ev["incident"]:
        i = ev["incident"]
        lines.append(f"\n**Incident test:** server delay {i['delay']} s, flaky first {i['flaky']} calls, client timeout {i['timeout']} s, "
                     f"retries {i['retries']} → {i['result']}.")
    evidence = "\n".join(lines) if lines else "_Use tabs 1, 3, 5 and 6 first, so your ADR gets real numbers._"
    slow = "| Tool | Timeout | Retries | What the user is told if it still fails |\n|---|---|---|---|\n" + "\n".join(
        f"| {r.get('Tool', '')} | {r.get('Timeout', '')} | {r.get('Retries', '')} | {r.get('If it still fails', '')} |" for r in slow_rows)
    return f"""# ADR-AskIT-02: Where do AskIT's tools live?

**Team:** {team} ({members or 'names'}) · **Date:** {date.today():%d %b %Y} · **Status:** Proposed

## 1. Context
- AskIT's 4 tools (search_kb, get_ticket, update_ticket, reset_password) must be used by agents today and by more agents later.
- Two of the tools CHANGE data. Tools can be slow or fail. Calls cross a network.
- **Client curveball ({cb['from']}):** {cb['title']}. {cb['detail']}

## 2. Decision
- **Where the tools live:** {home}
- **Where logging, masking and role checks live:** {controls}
- **How callers prove who they are:** {identity}
- **Why:** {why or '___'}

## 3. Alternatives we rejected
{rejected or '___'}

## 4. Slow and failing tools
{slow}

## 5. How we handle the curveball
{curveball_answer or '___'}

## 6. Evidence from the lab ({model_label})
{evidence}

## 7. Consequences
- A shared MCP server means one place to fix, log and secure, but it becomes a service somebody must own and keep running.
- Every network hop adds latency and a new way to fail: timeouts, retries and clear error messages are part of the design.

## 8. Board verdict (filled by the board)
| Criterion | Score (0-5) |
|---|---|
""" + "\n".join(f"| {k}: {v} | |" for k, v in RUBRIC) + "\n\n**Verdict:** Approved · Approved with conditions · Rejected — Conditions: ___\n"
