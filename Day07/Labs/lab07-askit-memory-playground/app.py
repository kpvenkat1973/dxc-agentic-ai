"""Lab 7 · AskIT Memory Playground  (Streamlit screen).   Start it with:  python run.py

You do not need to edit any code. Play with the sidebar, press the buttons, watch the charts.
The agent logic lives in memory_agent.py; the model choice in model_factory.py.
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
import memory_agent as ma
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore

st.set_page_config(page_title="Lab 7 · AskIT Memory Playground", page_icon="🧠", layout="wide", initial_sidebar_state="expanded")
st.markdown("""<style>
html, body, [class*="css"] {font-size:18px;}
.take{background:rgba(106,63,160,.14);border-left:6px solid #6A3FA0;padding:14px 18px;border-radius:10px;margin:8px 0}
.client{background:rgba(14,112,104,.14);border-left:6px solid #0E7068;padding:14px 18px;border-radius:10px;margin:8px 0}
.step{background:rgba(127,127,127,.12);border:1px solid rgba(127,127,127,.35);padding:10px 14px;border-radius:10px;margin:6px 0}
</style>""", unsafe_allow_html=True)

USERS = {"EMP-1002": "Priya Iyer", "EMP-1003": "Rahul Reddy"}
CHATS_PER_DAY = 10_000
S = st.session_state
if "cp" not in S:
    S.cp, S.store, S.log, S.history = InMemorySaver(), InMemoryStore(), [], []
    S.thread, S.turn, S.compare, S.script_i = f"chat-{uuid.uuid4().hex[:6]}", 0, None, 0
    S.mem_a = S.mem_b = ""

# ================================================================================================ sidebar
with st.sidebar:
    st.header("🧪 Lab 7 controls")
    stat = mf.status()
    ready = [p for p in ("bedrock", "azure", "openai", "offline") if stat[p][0]]
    provider = st.radio("1 · Model", ready, format_func=lambda p: mf.LABELS[p], index=0,
                        help="Bedrock is the main one. Offline = no AI, just rules, so the lab still runs.")
    st.caption(f"Using: {mf.model_label(provider)}")
    st.divider()
    st.subheader("2 · Compaction")
    compaction = st.toggle("Summarise old messages", value=False, key="compaction",
                           help="When the chat reaches the size below, the old part becomes ONE short summary.")
    compact_at = st.slider("Summarise when the chat reaches (tokens)", 800, 4000, 1500, 100, disabled=not compaction)
    keep_last = st.slider("Keep the newest messages word for word", 2, 10, 4, 1, disabled=not compaction)
    st.divider()
    st.subheader("3 · Long-term memory")
    memory = st.toggle("Remember facts across chats", value=True, key="memory",
                       help="Gives the agent save_note and recall_notes tools backed by a store.")
    user_id = st.selectbox("You are", list(USERS), format_func=lambda u: f"{USERS[u]} ({u})")
    st.divider()
    c1, c2 = st.columns(2)
    if c1.button("🆕 New chat", help="Starts an empty chat. Long-term notes stay."):
        S.thread, S.history, S.log, S.turn, S.script_i = f"chat-{uuid.uuid4().hex[:6]}", [], [], 0, 0
        st.rerun()
    if c2.button("🧹 Reset all", help="Clears chats AND long-term notes."):
        for k in list(S.keys()):
            del S[k]
        st.rerun()
    st.caption(f"Chat id (thread_id): `{S.thread}`")


def make_agent(log, comp=None, thread_cp=None):
    return ma.build_agent(mf.get_model(provider), thread_cp or S.cp, log,
                          compaction=compaction if comp is None else comp, compact_at=compact_at, keep_last=keep_last,
                          memory=memory, store=S.store, user_id=user_id)


def send(question):
    agent, meter = make_agent(S.log)
    before = len(S.log)
    t0 = time.time()
    try:
        answer = ma.ask(agent, meter, S.thread, question, S.turn)
    except Exception as e:                                     # show the problem in plain words, keep the app alive
        answer = f"⚠️ The model call failed: {e}. Try again, or pick another model in the sidebar."
    rows = S.log[before:]
    S.history.append({"q": question, "a": answer, "calls": len(rows), "tokens": sum(r["in_tokens"] for r in rows),
                      "tools": sorted({t for r in rows for t in r["tools"]}), "secs": round(time.time() - t0, 1),
                      "summary": any(r["summary"] for r in rows)})
    S.turn += 1


def frame(log):
    rows, prev_summary = [], ""
    for r in log:
        kind = "after a summary" if r["summary"] else "full chat"
        if r["summary"] and r["summary"] != prev_summary:     # a NEW summary was written just before this call
            rows.append({"model call": r["step"] - 0.5, "tokens sent": r["approx_in"] // 2 + mf.approx_tokens(r["summary"]),
                         "what": "summary call (estimate)"})
            prev_summary = r["summary"]
        rows.append({"model call": r["step"], "tokens sent": r["in_tokens"], "what": kind})
    return pd.DataFrame(rows)


def totals(log):
    tin = sum(r["in_tokens"] for r in log)
    tout = sum(r["out_tokens"] for r in log)
    return tin, tout, mf.cost_usd(provider, tin, tout)


# ================================================================================================ header
st.title("🧠 AskIT Memory Playground · Lab 7")
st.markdown("**The question of the day:** every message re-sends the whole chat to the model. "
            "How does an agent keep the facts it needs **without paying more and more for every turn?**")
st.info("**Folder:** `C:\\AskIT\\dxc-agentic-ai\\Day07\\Labs\\lab07-askit-memory-playground` · "
        "Work through the tabs **1 → 5** from left to right. You do not need to write any code.")

t1, t2, t3, t4, t5 = st.tabs(["💬 1 · Chat + context meter", "⚖️ 2 · Compare: compaction OFF vs ON",
                              "🗂️ 3 · Long-term memory", "🏗️ 4 · How it works", "✅ 5 · Questions + takeaway"])

# ------------------------------------------------------------------------------------------------ tab 1
with t1:
    st.markdown('<div class="step"><b>Do this:</b> ① Keep <b>compaction OFF</b>. Press <b>▶ Next script question</b> '
                'about 8 times (or ▶ Play all 8). Watch the bars on the right grow. ② Press <b>🆕 New chat</b> (next to the play buttons), switch '
                '<b>compaction ON</b> in the left sidebar, keep the slider at <b>1500</b>, play again. Watch the bars drop. Open '
                '<b>🗜️ The summary</b> and see what was kept and what was lost.</div>', unsafe_allow_html=True)
    left, right = st.columns([3, 2], gap="large")
    with left:
        b1, b2, b4, b3 = st.columns([3, 2, 2, 3])
        if b4.button("🆕 New chat", key="newchat_tab1", help="Starts an empty chat. Long-term notes stay."):
            S.thread, S.history, S.log, S.turn, S.script_i = f"chat-{uuid.uuid4().hex[:6]}", [], [], 0, 0
            st.rerun()
        nxt = ma.SCRIPT[S.script_i] if S.script_i < len(ma.SCRIPT) else None
        if b1.button("▶ Next script question", disabled=nxt is None):
            with st.spinner("AskIT is thinking..."):
                send(nxt)
                S.script_i += 1
        if b2.button("⏩ Play all 8", disabled=S.script_i > 0):
            bar = st.progress(0.0, "Playing the script...")
            for i, q in enumerate(ma.SCRIPT):
                send(q)
                S.script_i = i + 1
                bar.progress((i + 1) / len(ma.SCRIPT), f"Question {i + 1} of {len(ma.SCRIPT)}")
        b3.caption(f"Next: _{nxt}_" if nxt else "Script finished. Type your own question below.")
        for h in S.history:
            with st.chat_message("user"):
                st.write(h["q"])
            with st.chat_message("assistant", avatar="🤖"):
                st.write(h["a"])
                st.caption(f"{h['calls']} model calls · {h['tokens']:,} tokens sent · tools: "
                           f"{', '.join(h['tools']) or 'none'} · {h['secs']} s" + (" · 🗜️ summary in use" if h["summary"] else ""))
        typed = st.chat_input("Or type your own question to AskIT")
        if typed:
            with st.spinner("AskIT is thinking..."):
                send(typed)
            st.rerun()
    with right:
        st.subheader("📊 Context meter")
        if not S.log:
            st.caption("No model calls yet. Press ▶ Next script question.")
        else:
            tin, tout, usd = totals(S.log)
            m1, m2, m3 = st.columns(3)
            m1.metric("Model calls", len(S.log))
            m2.metric("Tokens sent", f"{tin:,}")
            m3.metric("Cost of this chat", f"${usd:.4f}")
            st.metric(f"If {CHATS_PER_DAY:,} chats like this run every day", f"${usd * CHATS_PER_DAY * 30:,.0f} / month",
                      help="Cost of this chat × 10,000 chats × 30 days, at the list price in model_factory.py")
            df = frame(S.log)
            st.bar_chart(df, x="model call", y="tokens sent", color="what", height=300)
            st.caption("Each bar = what was sent to the model in ONE call. Amber-ish 'summary call' bars are the extra "
                       "cost of writing the summary (estimated).")
            msgs = ma.chat_messages(make_agent([])[0], S.thread)
            with st.expander(f"👀 What the model sees right now ({len(msgs)} messages)"):
                for m in msgs:
                    t = mf.text_of(m) or ("→ calls " + ", ".join(c["name"] for c in getattr(m, "tool_calls", [])))
                    st.markdown(f"**{m.type}** · {t[:160].replace(chr(10), ' ')}{'…' if len(t) > 160 else ''}")
            summ = next((r["summary"] for r in reversed(S.log) if r["summary"]), "")
            with st.expander("🗜️ The summary (appears when compaction kicks in)"):
                st.text(summ.replace(ma.SUMMARY_MARK, "").strip() or "No summary yet. Switch compaction ON and chat more.")
            with st.expander("📋 Step log (one row per model call)"):
                st.dataframe(pd.DataFrame(S.log)[["step", "turn", "messages", "in_tokens", "out_tokens", "tools", "seconds"]],
                             hide_index=True)

# ------------------------------------------------------------------------------------------------ tab 2
with t2:
    st.markdown('<div class="step"><b>Do this:</b> press the button once. The same 8 questions run twice in brand-new '
                'chats: first <b>without</b> compaction, then <b>with</b> it (using your sidebar slider values). '
                'Then try the slider at <b>800</b> and run again: summaries fire almost every call, and the pink summary cost eats the saving.</div>', unsafe_allow_html=True)
    if st.button(f"⚖️ Run the 8-question script twice (compaction at {compact_at} tokens, keep {keep_last})", type="primary"):
        res = {}
        bar = st.progress(0.0, "Running...")
        for j, comp in enumerate((False, True)):
            log = []
            agent, meter = make_agent(log, comp=comp, thread_cp=InMemorySaver())
            answers = []
            for i, q in enumerate(ma.SCRIPT):
                try:
                    answers.append(ma.ask(agent, meter, "cmp", q, i))
                except Exception as e:
                    answers.append(f"⚠️ {e}")
                bar.progress((j * 8 + i + 1) / 16, f"{'WITH' if comp else 'WITHOUT'} compaction · question {i + 1}/8")
            res[comp] = {"log": log, "answers": answers}
        S.compare = {"res": res, "at": compact_at, "keep": keep_last}
    if S.compare:
        res = S.compare["res"]
        off_t, on_t = totals(res[False]["log"]), totals(res[True]["log"])
        saved = 1 - on_t[0] / off_t[0] if off_t[0] else 0
        c1, c2, c3 = st.columns(3)
        c1.metric("Tokens sent · compaction OFF", f"{off_t[0]:,}")
        c2.metric(f"Tokens sent · compaction ON ({S.compare['at']})", f"{on_t[0]:,}", f"{-saved:.0%}", delta_color="inverse")
        c3.metric("Monthly cost at 10,000 chats/day", f"${on_t[2] * CHATS_PER_DAY * 30:,.0f}",
                  f"was ${off_t[2] * CHATS_PER_DAY * 30:,.0f}", delta_color="off")
        line = pd.DataFrame({"model call": [r["step"] for r in res[False]["log"]],
                             "compaction OFF": [r["in_tokens"] for r in res[False]["log"]]}).merge(
            pd.DataFrame({"model call": [r["step"] for r in res[True]["log"]],
                          "compaction ON": [r["in_tokens"] for r in res[True]["log"]]}), on="model call", how="outer")
        st.line_chart(line, x="model call", y=["compaction OFF", "compaction ON"], height=320)
        st.markdown("**Did the agent keep the details?** The last two questions ask for something said in question 1.")
        q1, q2 = st.columns(2)
        for col, comp in ((q1, False), (q2, True)):
            col.markdown(f"**Compaction {'ON' if comp else 'OFF'}**")
            for q, a in list(zip(ma.SCRIPT, res[comp]["answers"]))[-2:]:
                col.markdown(f"🙋 _{q}_  \n🤖 {a}")
        st.caption("Not counted in the line: the extra model call that writes each summary. Compaction is cheaper, not free.")

# ------------------------------------------------------------------------------------------------ tab 3
with t3:
    st.markdown('<div class="step"><b>Do this:</b> ① Press <b>Chat A</b>. ② Press <b>Chat B</b> (a brand-new chat). '
                'Does AskIT know your laptop? ③ Switch <b>long-term memory OFF</b> in the sidebar and press Chat B again. '
                '④ Switch it back ON, change <b>You are</b> to Rahul and press Chat B. ⑤ Press <b>Forget me</b>.</div>',
                unsafe_allow_html=True)
    a, b = st.columns(2)
    if a.button("💬 Chat A: tell AskIT about your laptop"):
        agent, meter = make_agent([], thread_cp=InMemorySaver())
        S.mem_a = ma.ask(agent, meter, f"A-{uuid.uuid4().hex[:4]}", "Please remember: my laptop is a Dell XPS 13 and I work from Bengaluru.")
    if b.button("💬 Chat B (new chat): which laptop do I have?"):
        agent, meter = make_agent([], thread_cp=InMemorySaver())
        S.mem_b = ma.ask(agent, meter, f"B-{uuid.uuid4().hex[:4]}", "Which laptop do I have?")
    a.markdown(f"🤖 {S.mem_a}" if S.mem_a else "")
    b.markdown(f"🤖 {S.mem_b}" if S.mem_b else "")
    st.subheader(f"🗂️ What the store holds for {USERS[user_id]} ({user_id})")
    rows = ma.notes(S.store, user_id)
    st.dataframe(pd.DataFrame(rows) if rows else pd.DataFrame({"note": ["(nothing saved yet)"]}), hide_index=True)
    if st.button("🗑️ Forget me (delete all my notes)"):
        ma.forget_user(S.store, user_id)
        st.rerun()
    st.caption(f"Long-term memory is **{'ON' if memory else 'OFF'}**. Notes are filed per user: namespace ('memories', '{user_id}').")

# ------------------------------------------------------------------------------------------------ tab 4
with t4:
    st.subheader("The flow behind the screen (it follows your sidebar settings)")
    components.html(diagram.lab7(compaction, memory, compact_at, keep_last, mf.LABELS[provider]), height=560)
    st.subheader("Which code does what")
    st.table(pd.DataFrame([
        ["app.py", "The screen: buttons, sliders, charts. Sends your question to the agent.", "Your chat UI / API (FastAPI, Teams bot)"],
        ["memory_agent.py · build_agent()", "Builds the agent with tools, middleware, checkpointer and store.", "Same code"],
        ["SummarizationMiddleware", "Before a model call: if the chat is too big, replace the old part with a summary.", "Same, tuned per use case"],
        ["ContextMeter", "Before/after every model call: records tokens in/out. Feeds the bars.", "Langfuse / CloudWatch traces (Day 10)"],
        ["InMemorySaver (checkpointer)", "Short-term memory: the messages of one chat, by thread_id.", "Postgres / Redis / DynamoDB checkpointer"],
        ["InMemoryStore (store)", "Long-term memory: notes per user, used by save_note / recall_notes.", "AgentCore Memory, Postgres store, Mem0, Zep"],
        ["model_factory.py", "Picks the model: Bedrock Nova → Azure → OpenAI → Offline.", "Model gateway (LiteLLM, Bedrock cross-region)"],
        ["askit_core/tools.py", "The 4 helpdesk tools (2 read, 2 mock write).", "Real ITSM APIs (ServiceNow, Jira) via MCP (Day 9)"],
    ], columns=["Piece", "What it does here", "What it becomes in production"]))
    st.subheader("Trade-offs you will be asked about")
    st.table(pd.DataFrame([
        ["Send the full chat every time", "Simplest, nothing lost", "Cost and latency grow every turn; hits the context limit"],
        ["Trim (drop old messages)", "Free, very fast", "Forgets silently, e.g. the employee id from turn 1"],
        ["Summarise (compaction)", "Big token saving, keeps the gist", "Extra model call; small details can be lost"],
        ["Long-term store", "Facts survive new chats and devices", "Privacy (PII, consent, right to forget), stale or wrong notes"],
        ["Managed memory (AgentCore Memory)", "No servers, built-in extraction and expiry", "AWS lock-in, per-event pricing; check current pricing"],
    ], columns=["Option", "Good", "Watch out"]))

# ------------------------------------------------------------------------------------------------ tab 5
with t5:
    st.markdown("Answer in one or two lines each. Press **Save** and the file `submission\\lab07_answers.md` is written for you.")
    QS = ["In tab 2, how many tokens did compaction save (%), and did AskIT still know your employee id at the end?",
          "A client's helpdesk chats run 40+ turns. Would you switch compaction on? At what size, and what is the risk?",
          "Name one fact that SHOULD go to long-term memory and one that should NOT. Why?"]
    answers = [st.text_area(f"Q{i + 1}. {q}", key=f"q{i}", height=90) for i, q in enumerate(QS)]
    if st.button("💾 Save my answers", type="primary"):
        out = Path(__file__).resolve().parent / "submission" / "lab07_answers.md"
        out.parent.mkdir(exist_ok=True)
        body = "\n\n".join(f"**Q{i + 1}. {q}**\n\n{a or '<not answered>'}" for i, (q, a) in enumerate(zip(QS, answers)))
        out.write_text(f"# Lab 7 answers\n\nSaved {datetime.now():%Y-%m-%d %H:%M} · model: {mf.LABELS[provider]}\n\n{body}\n",
                       encoding="utf-8")
        st.success(f"Saved to {out}")
    st.markdown('<div class="take"><b>🎯 Takeaway.</b> Every turn re-sends the whole chat, so cost grows with chat length. '
                'Compaction trades a little detail for a big saving. Store <b>facts</b> about a user, not transcripts, '
                'and give users a way to delete them.</div>', unsafe_allow_html=True)
    st.markdown('<div class="client"><b>💼 Say this to a client.</b> "Memory is a cost and a compliance decision, not just '
                'a feature. We design what the agent remembers, for how long, and who can delete it."</div>',
                unsafe_allow_html=True)
