"""design_decision.py  --  builds your team's ADR-AskIT-05 (Ops & FinOps one-pager) from your choices + your lab numbers.
Used by tab 8 of the app. You do not need to edit this file.

An ADR is a one-page record of ONE important design decision. Tomorrow's boards read it before they approve go-live.
Today's board (Board 5, Ops & FinOps Review) asks: can you SEE it, can you AFFORD it, can you PROVE it works?
"""
from datetime import date

CURVEBALLS = {
    "team-a": {"title": "Finance wants the AI cost per department, every month",
               "from": "Orbit Corp CFO",
               "detail": "AskIT will serve HR, Finance, Facilities and Sales. The CFO wants to charge each department for what it uses, "
                         "and wants a target of under US$0.01 per ticket. How do you measure and show cost per department?",
               "evidence": "Tab 3: cost per ticket and the what-if table. Which tag or field on a trace would carry the department?",
               "topic": "Cost attribution, tags, budgets and alerts"},
    "team-b": {"title": "Traces contain employee names and ticket text",
               "from": "Orbit Corp CISO",
               "detail": "Every trace stores the question, the tool results and the answer. That is personal data. The CISO asks: where may "
                         "traces live, who can read them, how long do you keep them, and what do you mask before sending?",
               "evidence": "Tab 1: look at the 3 places a run is stored. Tab 5: what AWS logs on its own side.",
               "topic": "Where traces live, masking, retention and access"},
    "team-c": {"title": "What wakes a human at 3 a.m.?",
               "from": "Orbit Corp Head of Operations",
               "detail": "AskIT is live 24x7. There is one on-call engineer. Pick the 3 or 4 alerts that are worth waking someone for, "
                         "and say what is only a dashboard.",
               "evidence": "Tab 2: the 4 failures, each with a different signal (loops, size, missing tool, slow tool).",
               "topic": "Alerts, SLOs and on-call"},
    "team-d": {"title": "A developer changed the prompt on Friday evening",
               "from": "Orbit Corp Head of Quality",
               "detail": "How do we know a prompt or model change did not break AskIT? What must pass before a change goes live, "
                         "and who decides when a check fails?",
               "evidence": "Tab 4: compare prompt v1, v2 and v3 on the same 14 cases. Which categories moved?",
               "topic": "Evals as a release gate and a growing test set"},
}
TRACE_HOME = ["Langfuse Cloud (managed, per-team project)", "Langfuse self-hosted in our own cloud account",
              "AWS CloudWatch (Bedrock logs + GenAI observability)", "OpenTelemetry into the APM we already pay for (Datadog, Dynatrace, Grafana...)"]
ALERTS = ["Runs that hit the step limit (loops)", "Tool latency p95 above target", "Cost per ticket above budget", "Eval pass-rate drop after a change",
          "Error rate of model or tool calls", "Input tokens per run above normal"]
GATES = ["No gate: developers test by hand", "Release only if every risk category passes at least 90% on the eval set",
         "Eval gate AND a human reviews every failing case"]
MODELS = ["One model for everything", "Small model by default, bigger model only for hard or VIP cases", "Biggest model, because quality matters most"]

RUBRIC = [("Decision", "One clear sentence a CFO and a CISO both understand"),
          ("Alternatives", "At least one option rejected, with a real reason"),
          ("See / afford / prove", "Where traces live, what costs how much, what must pass before release"),
          ("Evidence", "Numbers from the lab: cost per ticket, p95, eval pass rates, which failure you found"),
          ("Curveball", "What changed in the design, and what did NOT change")]


def evidence_lines(ev):
    out = []
    if ev.get("cost"):
        c = ev["cost"]
        out.append(f"| Cost run ({c['n']} tickets, {c['model']}) | cost per ticket **US${c['per_ticket']:.5f}** · p50 {c['p50']} ms · p95 {c['p95']} ms · "
                   f"{c['tokens']:.0f} input tokens per ticket |")
    for r in ev.get("evals", []):
        rates = " · ".join(f"{k} {a}/{b}" for k, (a, b) in r["rate"].items())
        out.append(f"| Eval, prompt **{r['prompt']}** | {rates} |")
    if ev.get("mystery") is not None:
        out.append(f"| Find-the-failure | {ev['mystery']} of 4 root causes found |")
    if ev.get("retrieval"):
        out.append(f"| Retrieval check | hit-rate@3 {ev['retrieval']['hit_rate']:.0%} · MRR {ev['retrieval']['mrr']:.2f} |")
    return "| Measurement | Result |\n|---|---|\n" + "\n".join(out) if out else "_Use tabs 2, 3 and 4 first, so your ADR gets real numbers._"


def build_markdown(team, members, trace_home, alerts, gate, model_choice, budget, why, rejected, curveball_answer, ev, model_label):
    cb = CURVEBALLS[team]
    alert_lines = "\n".join(f"- {a}" for a in alerts) or "- ___"
    return f"""# ADR-AskIT-05: How do we see, afford and prove AskIT in production?

**Team:** {team} ({members or 'names'}) · **Date:** {date.today():%d %b %Y} · **Status:** Proposed

## 1. Context
- AskIT now answers, acts and escalates. Runs can loop, grow in cost, pick the wrong tool or be slow, and often nothing crashes.
- **Client curveball ({cb['from']}):** {cb['title']}. {cb['detail']}

## 2. Decision
- **Where traces live:** {trace_home}
- **What wakes a human:**
{alert_lines}
- **Release gate:** {gate}
- **Model strategy:** {model_choice}
- **Budget we promise:** {budget}
- **Why:** {why or '___'}

## 3. Alternatives we rejected
{rejected or '___'}

## 4. How we handle the curveball
{curveball_answer or '___'}

## 5. Evidence from the lab ({model_label})
{evidence_lines(ev)}

## 6. Consequences
- Tracing costs a little time and storage on every run, and the traces themselves hold personal data that must be protected.
- Evals only catch what the test set covers: every real failure we find in production must become a new test case.

## 7. Board verdict (filled by the board)
| Criterion | Score (0-5) |
|---|---|
""" + "\n".join(f"| {k}: {v} | |" for k, v in RUBRIC) + "\n\n**Verdict:** Approved · Approved with conditions · Rejected — Conditions: ___\n"
