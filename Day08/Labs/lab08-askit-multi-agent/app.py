"""Lab 8 · AskIT Multi-Agent Control Room  (Streamlit screen).   Start it with:  python run.py

You do not need to edit any code. Send tickets, approve or reject, crash and resume, compare.
The graph lives in multi_agent.py; the model choice in model_factory.py.
"""
import time
import uuid
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

import model_factory as mf  # noqa: I001  (must load first: it reads the course .env)
import diagram
import multi_agent as ma
import design_decision as dd
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

st.set_page_config(page_title="Lab 8 · AskIT Multi-Agent Control Room", page_icon="🕹️", layout="wide", initial_sidebar_state="expanded")
st.markdown("""<style>
html, body, [class*="css"] {font-size:18px;}
.take{background:rgba(106,63,160,.14);border-left:6px solid #6A3FA0;padding:14px 18px;border-radius:10px;margin:8px 0}
.client{background:rgba(14,112,104,.14);border-left:6px solid #0E7068;padding:14px 18px;border-radius:10px;margin:8px 0}
.step{background:rgba(127,127,127,.12);border:1px solid rgba(127,127,127,.35);padding:10px 14px;border-radius:10px;margin:6px 0}
.approve{background:rgba(183,121,31,.16);border:2px solid #B7791F;padding:14px 18px;border-radius:12px;margin:8px 0}
</style>""", unsafe_allow_html=True)

S = st.session_state
if "cp" not in S:
    S.cp, S.crash = InMemorySaver(), {"armed": False}
    S.run = S.crash_run = S.crash_error = S.compare = None
    S.ticket_text, S.ticket_user = ma.SAMPLES[1]["text"], ma.SAMPLES[1]["user"]

# ================================================================================================ sidebar
with st.sidebar:
    st.header("🕹️ Lab 8 controls")
    stat = mf.status()
    ready = [p for p in ("bedrock", "azure", "openai", "offline") if stat[p][0]]
    provider = st.radio("1 · Model", ready, format_func=lambda p: mf.LABELS[p], index=0,
                        help="Bedrock is the main one. Offline = no AI, just rules, so the lab still runs.")
    st.caption(f"Using: {mf.model_label(provider)}")
    st.divider()
    st.subheader("2 · Client curveball")
    vip_rule = st.toggle("VIP users always go to a human", value=False,
                         help="Switch ON only when the trainer announces the client's new rule.")
    st.caption("VIPs in the data: " + ", ".join(f"{u['name']} ({k})" for k, u in ma.USERS.items() if u["vip"] == "yes"))


@st.cache_resource(show_spinner=False)
def model_for(p):
    return mf.get_model(p)


def graph():
    return ma.build_graph(model_for(provider), S.cp, vip_rule=vip_rule, crash=S.crash)


def view(cfg):
    """Read the saved state of a run: values, what runs next, is it paused, how many checkpoints."""
    g = graph()
    snap = g.get_state(cfg)
    vals = snap.values or {}
    status = {t["node"]: "done" for t in vals.get("trace", [])}
    paused = bool(snap.interrupts)
    for n in snap.next or ():
        status[n] = "wait" if paused else "fail"
    return g, snap, vals, status, paused, len(list(g.get_state_history(cfg)))


def show_graph(status, vals, checkpoints):
    components.html(diagram.lab8(status, vals.get("route"), checkpoints, mf.LABELS[provider], vip_rule), height=600)


def show_trace(vals):
    tr = vals.get("trace", [])
    if tr:
        df = pd.DataFrame(tr)
        st.dataframe(df, hide_index=True)
        st.caption(f"Total: {int(df['llm calls'].sum())} LLM calls · {int(df['tokens'].sum()):,} tokens · "
                   f"{df['seconds'].sum():.1f} s")


# ================================================================================================ header
st.title("🕹️ AskIT Multi-Agent Control Room · Lab 8")
st.markdown("**The question of the day:** when should one AI agent become a **team of agents**, and where must a "
            "**human** stay in control?")
st.info("**Folder:** `C:\\AskIT\\dxc-agentic-ai\\Day08\\Labs\\lab08-askit-multi-agent` · Work through the tabs "
        "**1 → 6** from left to right. You do not need to write any code.")
t1, t2, t3, t4, t5, t6 = st.tabs(["🎫 1 · Route + approve", "💥 2 · Crash + resume", "⚖️ 3 · One agent vs a team",
                                  "🏗️ 4 · How it works", "✅ 5 · Questions + takeaway", "📝 6 · Team design decision"])

# ------------------------------------------------------------------------------------------------ tab 1
with t1:
    st.markdown('<div class="step"><b>Do this:</b> ① Click a sample ticket, then <b>▶ Send to AskIT</b>. Watch which '
                'specialist lights up. ② For <b>🔐 Locked out</b> the graph <b>pauses</b>: read the request, then '
                '<b>Approve</b>. Send it again and <b>Reject</b>. ③ When the trainer announces the curveball, switch the '
                'VIP rule ON in the sidebar and send <b>👑 VIP</b>.</div>', unsafe_allow_html=True)
    cols = st.columns(3)
    for i, smp in enumerate(ma.SAMPLES):
        if cols[i % 3].button(smp["label"], key=f"s{i}"):
            S.ticket_text, S.ticket_user = smp["text"], smp["user"]
            S.run = None
            st.rerun()
    c1, c2 = st.columns([3, 1])
    text = c1.text_area("Ticket text (edit it or write your own)", S.ticket_text, height=90)
    uids = list(ma.USERS)
    user = c2.selectbox("Sent by", uids, index=uids.index(S.ticket_user) if S.ticket_user in uids else 0,
                        format_func=lambda u: f"{ma.USERS[u]['name']}{' 👑 VIP' if ma.USERS[u]['vip'] == 'yes' else ''}")
    if c2.button("▶ Send to AskIT", type="primary"):
        cfg = {"configurable": {"thread_id": f"tkt-{uuid.uuid4().hex[:6]}"}}
        S.ticket_text, S.ticket_user = text, user
        with st.spinner("Router and specialist at work..."):
            try:
                graph().invoke({"ticket": text, "user_id": ma.user_of(text, user), "trace": []}, cfg)
            except Exception as e:
                st.error(f"The run failed: {e}")
        S.run = cfg
    if S.run:
        g, snap, vals, status, paused, n_cp = view(S.run)
        show_graph(status, vals, n_cp)
        if paused:
            req = snap.interrupts[0].value
            st.markdown(f'<div class="approve"><h4>⏸️ The graph is PAUSED, waiting for you</h4>'
                        f'<b>Action requested:</b> <code>{req["action"]}</code> for <b>{req["user_id"]}</b> '
                        f'({ma.USERS.get(req["user_id"], {}).get("name", "unknown user")})<br>'
                        f'<b>Why a human is needed:</b> {req["why"]}<br><b>Draft reply from the specialist:</b> '
                        f'<i>{req["draft_reply"][:300]}</i></div>', unsafe_allow_html=True)
            note = st.text_input("Approver note (optional)", key="note")
            a, r, _ = st.columns([1, 1, 3])
            for btn, decision in ((a, "approve"), (r, "reject")):
                if btn.button("✅ Approve" if decision == "approve" else "❌ Reject", type="primary" if decision == "approve" else "secondary"):
                    g.invoke(Command(resume={"decision": decision, "note": note}), S.run)
                    st.rerun()
            st.caption("In production this card is a Teams / Slack / ServiceNow approval. The graph can wait minutes or "
                       "days: its state sits in the checkpointer, nothing runs while it waits.")
        elif vals.get("final"):
            st.success("**Reply sent to the user**")
            st.markdown(vals["final"])
        st.markdown(f"**Route:** {vals.get('route', '-')} · **Approval:** {vals.get('approval', '-')}")
        with st.expander("📋 Trace: one row per node (who did what, tokens, time)", expanded=True):
            show_trace(vals)
        with st.expander(f"💾 Checkpoints saved for this ticket: {n_cp} (time-travel view)"):
            hist = list(g.get_state_history(S.run))
            st.dataframe(pd.DataFrame([{"checkpoint": len(hist) - i, "next node": ", ".join(h.next) or "END",
                                        "route": h.values.get("route", ""), "approval": h.values.get("approval", "")}
                                       for i, h in enumerate(hist)]), hide_index=True)
            st.caption("Every row is a saved snapshot. LangGraph can resume, replay or branch from any of them.")

# ------------------------------------------------------------------------------------------------ tab 2
with t2:
    st.markdown('<div class="step"><b>Do this:</b> ① Press <b>Run with a crash</b>: the server "dies" at the Policy '
                'step. The picture shows what finished (green) and where it stopped (red). ② Press <b>Resume</b>. '
                'Check the trace: did the router and the specialist run again (and cost tokens again)?</div>',
                unsafe_allow_html=True)
    a, b = st.columns(2)
    if a.button("💥 Run the VPN ticket with a crash", type="primary"):
        S.crash_run = {"configurable": {"thread_id": f"crash-{uuid.uuid4().hex[:6]}"}}
        S.crash["armed"] = True
        try:
            graph().invoke({"ticket": ma.SAMPLES[0]["text"], "user_id": ma.SAMPLES[0]["user"], "trace": []}, S.crash_run)
            S.crash_error = None
        except Exception as e:
            S.crash_error = str(e)
    if b.button("🔄 Resume from the last checkpoint", disabled=not S.crash_run):
        try:
            graph().invoke(None, S.crash_run)                    # None = "carry on from where you stopped"
            S.crash_error = None
        except Exception as e:
            S.crash_error = str(e)
    if S.crash_run:
        g, snap, vals, status, paused, n_cp = view(S.crash_run)
        if S.crash_error:
            st.error(S.crash_error)
        show_graph(status, vals, n_cp)
        if vals.get("final"):
            st.success("Finished after resume. " + vals["final"][:200])
        show_trace(vals)
        st.caption("Resume starts at the failed node. Router and specialist appear ONCE in the trace: their work "
                   "(and their tokens) was saved in the checkpoint, not paid for twice.")

# ------------------------------------------------------------------------------------------------ tab 3
with t3:
    st.markdown('<div class="step"><b>Do this:</b> press the button. The same 6 tickets go to (A) ONE agent that has '
                'all 4 tools, including the write tools, and (B) the multi-agent graph (approvals auto-granted here). '
                'Compare cost, routing and safety.</div>', unsafe_allow_html=True)
    if st.button("⚖️ Run 6 tickets: one agent vs the team", type="primary"):
        rows, bar = [], st.progress(0.0, "Running...")
        single = ma.single_agent(model_for(provider))
        for i, smp in enumerate(ma.SAMPLES):
            try:
                s1 = ma.run_single(single, smp["text"])
            except Exception as e:
                s1 = {"route": "error", "llm calls": 0, "tokens": 0, "seconds": 0, "writes without approval": 0, "answer": str(e)}
            cfg, t0 = {"configurable": {"thread_id": f"cmp-{uuid.uuid4().hex[:6]}"}}, time.time()
            g, asked = graph(), 0
            try:
                out = g.invoke({"ticket": smp["text"], "user_id": smp["user"], "trace": []}, cfg)
                while g.get_state(cfg).interrupts:
                    asked += 1
                    out = g.invoke(Command(resume={"decision": "approve"}), cfg)
                tr = pd.DataFrame(out["trace"])
                m = {"route": out["route"], "llm calls": int(tr["llm calls"].sum()), "tokens": int(tr["tokens"].sum())}
            except Exception as e:
                m = {"route": f"error: {e}", "llm calls": 0, "tokens": 0}
            rows.append({"ticket": smp["label"], "right team": smp["expect"],
                         "ONE agent: team": s1["route"], "ONE agent: LLM calls": s1["llm calls"], "ONE agent: tokens": s1["tokens"],
                         "ONE agent: writes with NO approval": s1["writes without approval"],
                         "TEAM: team": m["route"], "TEAM: LLM calls": m["llm calls"], "TEAM: tokens": m["tokens"],
                         "TEAM: approvals asked": asked})
            bar.progress((i + 1) / len(ma.SAMPLES), f"Ticket {i + 1} of {len(ma.SAMPLES)}")
        S.compare = pd.DataFrame(rows)
    if S.compare is not None:
        df = S.compare
        k = st.columns(4)
        k[0].metric("Right team · ONE", f"{(df['ONE agent: team'] == df['right team']).sum()} / {len(df)}")
        k[1].metric("Right team · TEAM", f"{(df['TEAM: team'] == df['right team']).sum()} / {len(df)}")
        k[2].metric("Tokens · ONE / TEAM", f"{df['ONE agent: tokens'].sum() / 1000:.1f}k / {df['TEAM: tokens'].sum() / 1000:.1f}k")
        k[3].metric("Writes, NO approval · ONE / TEAM", f"{df['ONE agent: writes with NO approval'].sum()} / 0")
        st.dataframe(df, hide_index=True)
        st.bar_chart(df.set_index("ticket")[["ONE agent: tokens", "TEAM: tokens"]], stack=False, height=300)
        st.caption("Read it like an architect: the team usually costs a bit more (one extra router call per ticket) "
                   "but gives you clean routing, smaller prompts per specialist, and a guaranteed human gate on writes.")

# ------------------------------------------------------------------------------------------------ tab 4
with t4:
    st.subheader("The graph you ran (static view)")
    components.html(diagram.lab8({}, None, 0, mf.LABELS[provider], vip_rule), height=600)
    st.subheader("Which code does what")
    st.table(pd.DataFrame([
        ["app.py", "The screen: ticket box, picture, Approve/Reject, compare.", "Your portal / Teams bot / ServiceNow UI"],
        ["multi_agent.py · build_graph()", "Nodes + edges of the StateGraph, compiled with a checkpointer.", "Same code"],
        ["router()", "ONE LLM call: picks Network / Access / Hardware / General.", "Same, or a cheaper classifier model"],
        ["make_specialist()", "A small create_agent per team: own prompt, own READ tools.", "Separate agents, can be owned by different teams"],
        ["policy()", "Plain Python rules: does a human have to approve? (+ VIP rule)", "Policy engine (e.g. Cedar / AgentCore Policy, Day 12)"],
        ["human_approval() · interrupt()", "Pauses the graph and waits for a decision.", "Teams / Slack / ServiceNow approval task"],
        ["act()", "The ONLY place a write tool runs, after a YES.", "Real ITSM / IAM API call with audit log"],
        ["InMemorySaver (checkpointer)", "Saves the state after every node: pause, crash, resume.", "Postgres / DynamoDB checkpointer, AgentCore Runtime"],
    ], columns=["Piece", "What it does here", "What it becomes in production"]))
    st.subheader("The 4 multi-agent patterns (this lab uses Router + Subagents + HITL)")
    st.table(pd.DataFrame([
        ["Router ✅", "An LLM classifies the input and sends it to ONE specialist", "Clear categories (tickets, intents)", "Wrong route = wrong answer; add a fallback"],
        ["Subagents ✅", "A main flow calls specialists like tools; each has its own small context", "Isolation, different owners, parallel work", "More LLM calls; results must be merged"],
        ["Handoffs", "Control passes to another agent, which then talks to the user directly", "Long conversations that change topic", "Harder to trace who said what"],
        ["Skills", "ONE agent loads extra instructions / tools only when needed", "Many small capabilities, one voice", "One big agent still owns everything"],
    ], columns=["Pattern", "How it works", "Use it for", "Watch out"]))
    st.subheader("Frameworks a client may name (concepts only)")
    st.table(pd.DataFrame([
        ["LangGraph (this lab)", "Explicit graph, checkpoints, interrupts, any model", "Most control and visibility", "More code to write"],
        ["CrewAI", "Role-based 'crew' of agents with tasks", "Fast to prototype", "Less control over the exact flow"],
        ["OpenAI Agents SDK", "Agents + handoffs + guardrails, light-weight", "Simple handoff apps", "Best with OpenAI models"],
        ["Claude Agent SDK", "The agent loop behind Claude Code: tools, subagents, skills", "Coding / file / ops agents", "Claude-centric"],
        ["Google ADK", "Agent Development Kit, multi-agent, A2A friendly", "Google Cloud / Gemini shops", "Younger ecosystem"],
        ["AWS Strands + AgentCore", "Model-driven agents; managed runtime, memory, gateway", "AWS-hosted production", "AWS lock-in; check pricing"],
    ], columns=["Framework", "Idea", "Good for", "Watch out"]))

# ------------------------------------------------------------------------------------------------ tab 5
with t5:
    st.markdown("Answer in one or two lines each. Press **Save** and `submission\\lab08_answers.md` is written for you.")
    QS = ["In tab 3, which cost more tokens: one agent or the team? Was the extra cost worth it? Why?",
          "Why does the POLICY node decide on approval in plain code instead of letting the LLM decide?",
          "After the VIP curveball, which node changed, and which parts of the design did NOT need to change?"]
    answers = [st.text_area(f"Q{i + 1}. {q}", key=f"q{i}", height=90) for i, q in enumerate(QS)]
    if st.button("💾 Save my answers", type="primary"):
        out = Path(__file__).resolve().parent / "submission" / "lab08_answers.md"
        out.parent.mkdir(exist_ok=True)
        body = "\n\n".join(f"**Q{i + 1}. {q}**\n\n{a or '<not answered>'}" for i, (q, a) in enumerate(zip(QS, answers)))
        out.write_text(f"# Lab 8 answers\n\nSaved {datetime.now():%Y-%m-%d %H:%M} · model: {mf.LABELS[provider]}\n\n{body}\n",
                       encoding="utf-8")
        st.success(f"Saved to {out}")
    st.markdown('<div class="take"><b>🎯 Takeaway.</b> Go multi-agent only when specialisation, separate ownership or a '
                'human approval point earns the extra calls. The LLM may <b>route</b>; plain-code <b>policy</b> decides '
                'what needs a human; writes happen only <b>after</b> approval; a <b>checkpointer</b> makes pauses and '
                'crashes safe.</div>', unsafe_allow_html=True)
    st.markdown('<div class="client"><b>💼 Say this to a client.</b> "We don\'t let the AI approve its own actions. '
                'It drafts, a policy decides who must sign off, and every step is saved and auditable."</div>',
                unsafe_allow_html=True)

# ------------------------------------------------------------------------------------------------ tab 6
with t6:
    st.markdown('<div class="step"><b>Team task (10 min, one person per team shares this screen):</b> pick your team, read '
                'your curveball, look at the evidence it points to, make 3 choices, write why, press <b>Create</b>. '
                'The app writes <code>teams\\&lt;your team&gt;\\ADR-AskIT-01.md</code> with your lab numbers already in it. '
                'Then pitch it in 2 minutes.</div>', unsafe_allow_html=True)
    c1, c2 = st.columns([1, 2])
    team = c1.selectbox("Your team", list(dd.CURVEBALLS))
    members = c1.text_input("Team members (first names)")
    cb = dd.CURVEBALLS[team]
    c2.markdown(f'<div class="approve"><b>⚡ Curveball from the {cb["from"]}: {cb["title"]}</b><br>{cb["detail"]}<br>'
                f'<b>Evidence in this app:</b> {cb["evidence"]}<br><i>Topic: {cb["topic"]}</i></div>', unsafe_allow_html=True)
    ev = dd.evidence_from(S.compare, lambda i, o: mf.cost_usd(provider, i, o))
    if ev is None:
        st.warning("Run tab 3 (⚖️ One agent vs a team) first, so your ADR gets real numbers.")
    else:
        k = st.columns(4)
        k[0].metric("Right team · ONE / TEAM", f"{ev['one_right']} / {ev['team_right']}")
        k[1].metric("$ per 1,000 tickets · TEAM", f"${ev['team_usd'] * 1000:.2f}", f"ONE ${ev['one_usd'] * 1000:.2f}", delta_color="off")
        k[2].metric("$ per month · TEAM (10k/day)", f"${ev['team_month']:,.0f}")
        k[3].metric("Writes with NO approval · ONE agent", ev["unapproved_writes"])
    st.subheader("Your 3 choices")
    a, b, c = st.columns(3)
    pattern = a.radio("1 · Pattern", dd.PATTERNS)
    approver = b.radio("2 · Who decides that a human must approve?", dd.APPROVERS)
    router_model = c.radio("3 · Router model", dd.ROUTER_MODELS)
    why = st.text_area("Why these choices? (2-3 lines a CIO understands)", height=80)
    rejected = st.text_area("Which alternative did you reject, and why? (1-2 lines)", height=70)
    answer = st.text_area(f"How does your design handle the curveball '{cb['title']}'? What changes, what does NOT change?", height=80)
    st.markdown("**Human approval points** (edit the cells)")
    hitl = st.data_editor(pd.DataFrame([
        {"Action": "Password reset", "Who approves": "Service desk lead", "If nobody answers": "___"},
        {"Action": "___", "Who approves": "___", "If nobody answers": "___"}]), num_rows="dynamic", hide_index=True)
    if st.button("📝 Create our design decision (ADR)", type="primary"):
        md = dd.build_markdown(team, members, pattern, approver, router_model, why, rejected, answer,
                               hitl.to_dict("records"), ev, mf.LABELS[provider])
        out = mf.ROOT / "teams" / team / "ADR-AskIT-01.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(md, encoding="utf-8")
        st.success(f"Saved to {out}. Run SYNC.bat to push it. Now pitch it in 2 minutes.")
        with st.expander("👀 Preview", expanded=True):
            st.markdown(md)
    st.subheader("How the board scores you (0-5 each, 25 points to the leaderboard)")
    st.table(pd.DataFrame(dd.RUBRIC, columns=["Criterion", "What earns full marks"]))
