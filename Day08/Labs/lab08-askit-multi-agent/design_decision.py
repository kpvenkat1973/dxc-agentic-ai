"""design_decision.py  --  builds your team's Architecture Decision Record (ADR) from your choices + your lab numbers.
Used by tab 6 of the app. You do not need to edit this file.

An ADR is a one-page record of ONE important design decision: the context, what we decided, what we rejected and why,
and what it will cost us. Review boards (ARB) and clients read ADRs before they approve money or go-live.
"""
from datetime import date

# One curveball per team: each makes you defend a different part of the design, and points to evidence in the app.
CURVEBALLS = {
    "team-a": {"title": "VIP users must always go to a human",
               "from": "Orbit Corp CIO",
               "detail": "Any ticket from a VIP (see 👑 in the user list) must be handled or approved by a human agent.",
               "evidence": "Sidebar → switch 'VIP users always go to a human' ON, then send 👑 VIP in tab 1. Which node changed?",
               "topic": "Human-in-the-loop policy"},
    "team-b": {"title": "AI budget capped at $500 a month",
               "from": "Orbit Corp CFO",
               "detail": "Finance caps AI spend at $500 a month for 10,000 tickets a day. The business also asks for Claude Sonnet "
                         "(about $3 per million input tokens) in the specialists for better answers. Does it fit? Where would you use it?",
               "evidence": "Tab 3: tokens per ticket for ONE agent vs TEAM. The draft below converts them to $ per ticket.",
               "topic": "Model selection and cost (small vs large models)"},
    "team-c": {"title": "Nobody approves at night",
               "from": "Orbit Corp Service Desk Manager",
               "detail": "Between 8 pm and 8 am no approver is online. Password resets still arrive. Nothing may be lost or done without approval.",
               "evidence": "Tab 2: crash + resume. Tab 1: the graph waits at Human approval and the state is saved.",
               "topic": "Durable execution, timeouts and escalation"},
    "team-d": {"title": "Auditors want proof of every approval",
               "from": "Orbit Corp Internal Audit",
               "detail": "For every password reset we must show who approved it, when, and what the AI had proposed.",
               "evidence": "Tab 1: open '💾 Checkpoints saved' after an approval: every step is a saved snapshot.",
               "topic": "Audit trail, checkpoints and observability"},
}

PATTERNS = ["Router + specialist agents + human approval (what we ran)", "ONE agent with all the tools",
            "Handoffs between agents", "ONE agent with skills loaded on demand"]
APPROVERS = ["Plain-code policy decides (rules written from the client's policy)", "The LLM decides when to ask a human",
             "No approval step"]
ROUTER_MODELS = ["Small model (Nova Micro): cheap and fast", "Larger model (Nova Lite / Claude): more accurate, costs more"]

RUBRIC = [("Decision", "One clear sentence a CIO understands"),
          ("Alternatives", "At least one option rejected, with a real reason"),
          ("Human approval", "What needs approval, who approves, what happens if nobody answers"),
          ("Evidence", "Numbers from the lab: right team, tokens, $ per ticket, $ per month"),
          ("Curveball", "What changed in the design, and what did NOT change")]


def evidence_from(compare_df, cost_fn):
    """Turn the tab 3 table into the numbers an ADR needs. compare_df can be None (tab 3 not run yet)."""
    if compare_df is None or len(compare_df) == 0:
        return None
    n = len(compare_df)
    one_tok = compare_df["ONE agent: tokens"].sum() / n
    team_tok = compare_df["TEAM: tokens"].sum() / n
    one_usd, team_usd = cost_fn(one_tok, one_tok * 0.15), cost_fn(team_tok, team_tok * 0.15)   # output ≈ 15% of input
    return {
        "tickets": n,
        "one_right": int((compare_df["ONE agent: team"] == compare_df["right team"]).sum()),
        "team_right": int((compare_df["TEAM: team"] == compare_df["right team"]).sum()),
        "one_tok": round(one_tok), "team_tok": round(team_tok),
        "one_usd": one_usd, "team_usd": team_usd,
        "one_month": one_usd * 10_000 * 30, "team_month": team_usd * 10_000 * 30,
        "unapproved_writes": int(compare_df["ONE agent: writes with NO approval"].sum()),
        "approvals": int(compare_df["TEAM: approvals asked"].sum()),
    }


def build_markdown(team, members, pattern, approver, router_model, why, rejected, curveball_answer, hitl_rows, ev, model_label):
    cb = CURVEBALLS[team]
    if ev:
        evidence = (f"| Measure (Lab 8, {ev['tickets']} test tickets, {model_label}) | ONE agent | TEAM |\n|---|---|---|\n"
                    f"| Routed to the right team | {ev['one_right']}/{ev['tickets']} | {ev['team_right']}/{ev['tickets']} |\n"
                    f"| Tokens per ticket | {ev['one_tok']:,} | {ev['team_tok']:,} |\n"
                    f"| AI cost per ticket (approx.) | ${ev['one_usd']:.5f} | ${ev['team_usd']:.5f} |\n"
                    f"| AI cost per month at 10,000 tickets/day | ${ev['one_month']:,.0f} | ${ev['team_month']:,.0f} |\n"
                    f"| Writes done with NO human approval | {ev['unapproved_writes']} | 0 |\n"
                    f"| Approvals requested | 0 | {ev['approvals']} |")
    else:
        evidence = "_Run tab 3 (One agent vs a team) to fill this table with your numbers._"
    hitl = "| Action | Who approves | If nobody answers |\n|---|---|---|\n" + "\n".join(
        f"| {r.get('Action', '')} | {r.get('Who approves', '')} | {r.get('If nobody answers', '')} |" for r in hitl_rows)
    return f"""# ADR-AskIT-01: Team of agents and human approval for AskIT

**Team:** {team} ({members or 'names'}) · **Date:** {date.today():%d %b %Y} · **Status:** Proposed

## 1. Context
- AskIT gets 4 kinds of helpdesk tickets: Network, Access, Hardware, General.
- Some actions change data (password reset). Others only read (knowledge base, ticket status).
- **Client curveball ({cb['from']}):** {cb['title']}. {cb['detail']}

## 2. Decision
- **Pattern:** {pattern}
- **Who decides that a human must approve:** {approver}
- **Router model:** {router_model}
- **Why:** {why or '___'}

## 3. Alternatives we rejected
{rejected or '___'}

## 4. Human approval points
{hitl}

## 5. How we handle the curveball
{curveball_answer or '___'}

## 6. Evidence from the lab
{evidence}

## 7. Consequences
- Each ticket costs one extra router call compared with one agent; in return we get clean routing and a guaranteed human gate on writes.
- Approvals can wait minutes or days: the graph state is kept by the checkpointer, nothing is lost or repeated.

## 8. Board verdict (filled by the board)
| Criterion | Score (0-5) |
|---|---|
""" + "\n".join(f"| {k}: {v} | |" for k, v in RUBRIC) + "\n\n**Verdict:** Approved · Approved with conditions · Rejected — Conditions: ___\n"
