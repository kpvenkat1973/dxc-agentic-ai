"""Lab 16A · AskIT Runtime Room  (Streamlit screen).   Start it with:  python run.py

AskIT's agent code runs NOT on your VM but on AWS, inside AgentCore Runtime (the trainer deployed it once; you call it).
You talk to it, watch how SESSIONS behave (private sandbox, cold start, memory), see it in the AWS console, and work out what it costs.
No code to edit. Files: rt_client.py (calls the Runtime) · gw_client.py + gw_agent.py + tools_core.py (the practice agent and its tools)
"""
import re
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

import model_factory as mf  # noqa: I001  (must load first: it reads the course .env)
import gw_client as gc
import prices as P
import rt_client as rt

HERE = Path(__file__).resolve().parent
st.set_page_config(page_title="Lab 16A · AskIT Runtime Room", page_icon="🏠", layout="wide", initial_sidebar_state="expanded")
st.markdown("""<style>
html, body, [class*="css"] {font-size:18px;}
.take{background:rgba(106,63,160,.14);border-left:6px solid #6A3FA0;padding:14px 18px;border-radius:10px;margin:8px 0}
.client{background:rgba(14,112,104,.14);border-left:6px solid #0E7068;padding:14px 18px;border-radius:10px;margin:8px 0}
.lesson{background:linear-gradient(135deg,rgba(245,166,35,.28),rgba(245,166,35,.10));border:3px solid #E08A00;padding:16px 20px;border-radius:14px;margin:14px 0}
.lock{background:rgba(127,127,127,.10);border:2px dashed rgba(127,127,127,.5);padding:12px 16px;border-radius:12px;margin:10px 0;opacity:.85}
.ans{background:rgba(127,127,127,.10);border-radius:10px;padding:10px 14px;margin:6px 0}
.cold{background:rgba(180,35,24,.14);border-left:6px solid #B42318;padding:10px 14px;border-radius:10px;margin:6px 0}
.warm{background:rgba(14,112,104,.14);border-left:6px solid #0E7068;padding:10px 14px;border-radius:10px;margin:6px 0}
div[data-baseweb="tab-list"] button:last-child{background:rgba(245,166,35,.28);border-radius:10px 10px 0 0;font-weight:700}
</style>""", unsafe_allow_html=True)

S = st.session_state
saved = gc.load_saved()
for k, v in {"mode": "practice", "arn": rt.load_saved(), "url": saved["url"], "think": {}, "lessons": {}, "prt": rt.PracticeRuntime(), "calls": [],
             "sid": {"A": rt.new_session_id(), "B": rt.new_session_id()}, "last": None, "sess_table": None}.items():
    S.setdefault(k, v)

QUESTIONS = ["Summarise ticket TKT-0004 and tell me the next step.", "Who is employee EMP-1002 and are they a VIP?",
             "Please reset the password for EMP-1002. They are locked out.", "Summarise ticket TKT-0010 and tell me the next step.",
             "How do I fix VPN error 809?", "What is the minimum password length?"]


def lesson_box(text):
    st.markdown(f'<div class="lesson"><b>🎓 Lesson learnt</b><br>{text}</div>', unsafe_allow_html=True)


def thinking(tab, items, lesson):
    """Two thinking questions per tab. Answering both unlocks the lesson, which is also collected in the last tab."""
    st.divider()
    st.markdown("### 🧠 Think before you move on")
    for i, (text, opts, right, why) in enumerate(items):
        key = f"{tab}_{i}"
        st.markdown(f"**{i + 1}. {text}**")
        a = st.radio("answer", [f"{k.upper()} · {v}" for k, v in opts.items()], key=f"th_{key}", index=None, label_visibility="collapsed")
        if st.button("Check", key=f"thb_{key}", disabled=a is None):
            S.think[key] = a[0].lower() == right
        if key in S.think:
            (st.success if S.think[key] else st.error)(("✅ " if S.think[key] else f"The answer is {right.upper()}. ") + why)
    if all(f"{tab}_{i}" in S.think for i in range(len(items))):
        S.lessons[tab] = lesson
        lesson_box(lesson)
    else:
        st.markdown('<div class="lock">🔒 Answer both questions to unlock the lesson for this tab.</div>', unsafe_allow_html=True)


def invoke(prompt, label="A"):
    """One call to the Runtime (practice or AWS), logged for the charts."""
    sid = S.sid[label]
    if S.mode == "practice":
        r = S.prt.invoke(prompt, sid, S.prov, gc.PracticeGateway())
    else:
        r = rt.AwsRuntime(S.arn).invoke(prompt, sid, S.prov, S.url)
    if r.ok:
        S.calls.append({"#": len(S.calls) + 1, "Session": label, "Turn": r.session.get("turn", "?"), "Cold start?": "yes" if r.session.get("cold") else "no",
                        "Sandbox (boot id)": r.session.get("boot_id", "?"), "Time (ms)": r.ms, "Where": "practice" if S.mode == "practice" else "AWS"})
    S.last = r
    return r


def show(r):
    if not r.ok:
        st.error("❌ " + r.error)
        return
    sess = r.session
    c = st.columns(5)
    c[0].metric("Session", sess.get("id", "?")[-6:] if sess.get("id") else "?")
    c[1].metric("Sandbox (boot id)", sess.get("boot_id", "?"))
    c[2].metric("Turn in this session", sess.get("turn", "?"))
    c[3].metric("Cold start?", "yes" if sess.get("cold") else "no")
    c[4].metric("Total time", f"{r.ms / 1000:.1f} s")
    st.markdown(f'<div class="{"cold" if sess.get("cold") else "warm"}">'
                + ("🧊 <b>Cold start:</b> this session had no sandbox yet, so AWS started one before running the agent." if sess.get("cold")
                   else "🔥 <b>Warm:</b> the sandbox for this session was already running.") + "</div>", unsafe_allow_html=True)
    st.markdown(f'<div class="ans">{r.answer}</div>', unsafe_allow_html=True)
    if r.steps:
        st.dataframe(pd.DataFrame([{"Step": s["label"], "ms": s["ms"], "Result": s["out"]} for s in r.steps]), hide_index=True, width="stretch")
    if r.cost:
        st.caption(f"Tokens {r.tin}/{r.tout} · model cost ${r.cost:.6f}")


# ================================================================================================ sidebar
with st.sidebar:
    st.header("🏠 Lab 16A")
    st.markdown("**1 · AI model** (practice runtime only)")
    stt = mf.status()
    names = [p for p in ("bedrock", "azure", "openai", "offline") if stt[p][0]]
    S.prov = st.selectbox("Model", names, index=names.index(mf.auto_provider()), format_func=lambda p: mf.LABELS[p], label_visibility="collapsed")
    st.caption(mf.model_label(S.prov))
    st.markdown("**2 · Which Runtime?**")
    st.markdown(f"Now using: **{S.prt.label if S.mode == 'practice' else rt.AwsRuntime.label}**")
    st.markdown("**3 · My sessions**")
    for k, v in S.sid.items():
        st.caption(f"Session {k}: …{v[-8:]}")
    if S.calls:
        st.caption(f"Calls so far: {len(S.calls)}")

tabs = st.tabs(["🔌 1 · Connect", "💬 2 · Talk to it", "🧪 3 · Sessions", "👀 4 · See it in AWS", "🧩 5 · How it works and cost", "🎓 Lessons learnt"])

# ================================================================================================ TAB 1
with tabs[0]:
    st.subheader("Connect to the Runtime")
    st.markdown("Until now AskIT's agent ran on **your VM**. Today it runs **on AWS**, in **AgentCore Runtime**. You send a question, AWS runs the agent, and the answer comes back.")
    choice = st.radio("Which Runtime do you want to use?", ["Practice runtime (no AWS: start here, or if you are stuck)", "The trainer's Runtime on AWS"], index=0 if S.mode == "practice" else 1)
    S.mode = "practice" if choice.startswith("Practice") else "aws"
    if S.mode == "aws":
        S.arn = st.text_input("Runtime ARN (the trainer gives it to you)", value=S.arn, placeholder="arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/askit_agent-xxxxxxxxxx").strip()
        S.url = st.text_input("Your Gateway URL from yesterday (the agent in the Runtime will call it; leave empty to use the trainer's shared one)", value=S.url,
                              placeholder="https://askit-gw-user116-xxxx.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp").strip()
        if st.button("💾 Save the ARN (never pushed to GitHub)"):
            rt.save(S.arn)
            st.success("Saved in this lab folder.")
        if st.button("Who am I? (shows the AWS user your keys belong to)"):
            try:
                import boto3
                st.code(boto3.client("sts", region_name="us-east-1").get_caller_identity()["Arn"])
            except Exception as e:   # noqa: BLE001
                st.error(f"Could not read your AWS identity: {e}")
    if st.button("▶ Say hello (ping)", type="primary"):
        with st.spinner("Calling the Runtime…"):
            show(invoke("ping", "A"))
    st.markdown('<div class="take"><b>What to notice:</b> the first call is slower than the next ones. Hold that thought for tab 3.</div>', unsafe_allow_html=True)
    if S.mode == "practice":
        st.caption("The practice runtime copies how the real one behaves: a private sandbox for each session id, a slow first call, a new sandbox after quiet time.")

# ================================================================================================ TAB 2
with tabs[1]:
    st.subheader("Ask AskIT, running on the Runtime")
    q = st.selectbox("Question", QUESTIONS)
    c1, c2 = st.columns(2)
    if c1.button("▶ Ask (session A)", type="primary"):
        with st.spinner("The agent is working…"):
            invoke(q, "A")
    if c2.button("🆕 Start a new session A"):
        S.sid["A"] = rt.new_session_id()
        st.success("New session id made. Your next question starts a fresh sandbox.")
    if S.last:
        show(S.last)
    st.markdown('<div class="take"><b>Try a knowledge question</b> (the last two in the list). The agent calls the tool <b>search_kb</b> through the Gateway. '
                'That is the <b>RAG</b> step: find the best help article, then answer from it. In the steps table, find <b>search_kb</b> and read its <b>mode</b>: '
                '<i>titan-embed-text-v2</i> means it matched by meaning on AWS; <i>keyword</i> means it matched words.</div>', unsafe_allow_html=True)
    thinking("t2", [
        ("Where did the agent's code run for this answer?",
         {"a": "On my VM.", "b": "In a managed sandbox on AWS that is private to my session.", "c": "Inside the AI model."}, "b",
         "You sent a prompt and a session id. AWS ran the agent code for you and returned the result. Nothing ran on your VM except this screen."),
        ("Who decides the session id?",
         {"a": "AWS decides it for you.", "b": "The caller (this app). A new id means a new, empty sandbox.", "c": "The model."}, "b",
         "You choose it. Same id means the same session. That is why each user needs their own id.")],
        "<b>A Runtime is a place to run your agent code, hosted by AWS.</b> It is the same agent code you ran on your VM in earlier days. What changed is the home: "
        "AWS now starts, isolates and stops it for you, and you pay for the time it actually works.")

# ================================================================================================ TAB 3
with tabs[2]:
    st.subheader("Sessions: one private sandbox per session id")
    st.markdown("Run the three experiments in order. Watch the **Sandbox (boot id)**, the **Turn** and the **Cold start?** columns.")

    def run3(label, prompts):
        with st.spinner(f"Session {label}: asking {len(prompts)} question(s)…"):
            for p in prompts:
                invoke(p, label)

    c1, c2, c3 = st.columns(3)
    if c1.button("1 · Session A: ask 3 questions"):
        run3("A", [QUESTIONS[0], QUESTIONS[1], QUESTIONS[3]])
    if c2.button("2 · Session B: ask 1 question"):
        run3("B", [QUESTIONS[0]])
    if S.mode == "practice":
        if c3.button("3 · Session A goes quiet for 90 s, then asks again"):
            S.prt.make_idle(S.sid["A"])
            run3("A", [QUESTIONS[0]])
    else:
        if c3.button("3 · Ask session A again (try it again after the break)"):
            run3("A", [QUESTIONS[0]])
    if S.calls:
        df = pd.DataFrame(S.calls[-12:])
        st.dataframe(df, hide_index=True, width="stretch")
        st.bar_chart(df.set_index("#")["Time (ms)"], height=220)
        cold = [c["Time (ms)"] for c in S.calls if c["Cold start?"] == "yes"]
        warm = [c["Time (ms)"] for c in S.calls if c["Cold start?"] == "no"]
        if cold and warm:
            st.markdown(f'<div class="take">Average <b>cold</b> call: {sum(cold) / len(cold) / 1000:.1f} s · average <b>warm</b> call: {sum(warm) / len(warm) / 1000:.1f} s. '
                        f'The difference is the time to start a sandbox.</div>', unsafe_allow_html=True)
    if S.mode == "practice":
        st.caption("In the practice runtime the quiet-time limit is 90 seconds so you can see it. On AWS it is much longer (minutes) and you can set it.")
    thinking("t3", [
        ("Questions 1 to 3 in session A showed the same boot id. Session B showed a different one. What does that mean?",
         {"a": "Each session has its own private sandbox.", "b": "The boot id is random noise.", "c": "Session B used a different model."}, "a",
         "Same session id means the same running sandbox. A new id means a new sandbox, with nothing carried over from session A."),
        ("The first call in a session is slower than the next ones. Why?",
         {"a": "The model needs to warm up.", "b": "The sandbox has to be started first (a cold start). Later calls reuse it.", "c": "The network gets faster."}, "b",
         "A cold start is the price of not paying for idle machines. Plan for it: show progress on the screen, or keep a session warm for busy users.")],
        "<b>A session is a private computer that lives for a while.</b> Same session id: same sandbox, remembers the conversation, fast after the first call. "
        "New id or too long quiet: fresh sandbox, empty memory, one cold start. Give every user their own session id, and never share one between people.")

# ================================================================================================ TAB 4
with tabs[3]:
    st.subheader("See it in the AWS console (trainer shows first, then you)")
    st.markdown("Ask one question in tab 2 first, so there is something to find. Copy your session id from the sidebar of tab 2 (the last 8 characters are enough).")
    if S.calls:
        df = pd.DataFrame(S.calls)
        a, b, c = st.columns(3)
        a.metric("Calls made", len(df))
        a2 = df[df["Cold start?"] == "yes"]["Time (ms)"]
        b2 = df[df["Cold start?"] == "no"]["Time (ms)"]
        b.metric("Avg cold call", f"{a2.mean() / 1000:.1f} s" if len(a2) else "none yet")
        c.metric("Avg warm call", f"{b2.mean() / 1000:.1f} s" if len(b2) else "none yet")
    st.markdown("""
**On AWS (names may differ a little in your console, follow the idea):**
1. Search **CloudWatch**. In the left menu open **GenAI Observability**, then **Bedrock AgentCore**.
2. Choose **Agents** and open **askit_agent** (the trainer's Runtime).
3. Open **Sessions** and find the id you copied. Open it: one row per question you asked.
4. Open one **trace**: you see the steps of that single run, in order, with the time each took.
5. Find the **cold start**: the first question of a session has a longer first step.
6. (Trainer) In **Logs** look at the runtime's log group: the agent's own print lines are there.
""")
    st.markdown('<div class="take"><b>Remember Day 10.</b> The Bedrock model log shows the <i>model</i> calls only. A trace shows the <i>agent</i>: every tool call and the order. '
                'On a Runtime you want the trace, the logs and an alarm, all three.</div>', unsafe_allow_html=True)
    thinking("t4", [
        ("A user says: 'the first answer every morning is slow'. What do you check first?",
         {"a": "The AI model's quality.", "b": "Whether the first call of a new session is a cold start.", "c": "The ticket data."}, "b",
         "A slow first answer and fast next ones is the signature of a cold start. The trace shows it as a longer first step."),
        ("You want to see which tools one agent run called, and in what order. Where do you look?",
         {"a": "In the agent trace for that session.", "b": "Only in the Bedrock model invocation log.", "c": "In IAM."}, "a",
         "The model log knows model calls only. The trace follows the whole run, including tool calls.")],
        "<b>Run it, then watch it.</b> Hosting the agent on a Runtime gives you sessions, traces and logs in one place. Looking at one trace tells you more than any complaint: "
        "which step was slow, which tool was called, whether it was a cold start.")

# ================================================================================================ TAB 5
with tabs[4]:
    st.subheader("How it works")
    svg = """<div style="font-family:Segoe UI,Arial,sans-serif"><svg viewBox="0 0 1100 330" width="100%" style="background:#fff;border-radius:12px">
    <defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5L0 10z" fill="#555"/></marker></defs>
    <g stroke-width="2.2"><rect x="10" y="90" width="170" height="110" rx="14" fill="#E2EBF7" stroke="#1F5AA6"/>
    <rect x="260" y="20" width="360" height="270" rx="18" fill="#F5F5F0" stroke="#999" stroke-dasharray="7 5"/>
    <rect x="285" y="60" width="150" height="90" rx="12" fill="#EEE6F7" stroke="#6A3FA0"/><rect x="285" y="170" width="150" height="90" rx="12" fill="#EEE6F7" stroke="#6A3FA0"/>
    <rect x="690" y="90" width="170" height="110" rx="14" fill="#E3F1EE" stroke="#0E7068"/><rect x="920" y="90" width="170" height="110" rx="14" fill="#FBEEDB" stroke="#A8570A"/></g>
    <g text-anchor="middle" fill="#161a23" font-size="16"><text x="95" y="125" font-weight="700" font-size="18">🖥️ Your screen</text><text x="95" y="150">this app or</text><text x="95" y="172">the Front Desk</text>
    <text x="440" y="46" font-weight="700" font-size="18">🏠 AgentCore Runtime</text>
    <text x="360" y="98" font-weight="700">Session A</text><text x="360" y="122">own sandbox</text><text x="360" y="244" font-weight="700">Session B</text><text x="360" y="212">own sandbox</text>
    <text x="360" y="266" fill="#555" font-size="13"> </text><text x="535" y="130">agent code:</text><text x="535" y="152">ask model, pick tool,</text><text x="535" y="174">call tool, answer</text>
    <text x="775" y="125" font-weight="700" font-size="18">🚪 Gateway</text><text x="775" y="150">tools + policy</text><text x="775" y="172">(Lab 15, 16B)</text>
    <text x="1005" y="125" font-weight="700" font-size="18">⚙️ Lambda</text><text x="1005" y="150">the tools</text></g>
    <g stroke="#555" stroke-width="2.2" fill="none" marker-end="url(#a)"><line x1="182" y1="130" x2="283" y2="105"/><line x1="182" y1="165" x2="283" y2="215"/><line x1="622" y1="145" x2="688" y2="145"/><line x1="862" y1="145" x2="918" y2="145"/></g>
    <g fill="#555" font-size="14"><text x="10" y="300">invoke_agent_runtime(agentRuntimeArn, runtimeSessionId, payload) · signed with your AWS identity</text>
    <text x="10" y="320">Idle sessions are stopped; you pay for the time the agent is actually working, not for waiting machines.</text></g></svg></div>"""
    if hasattr(st, "iframe"):
        st.iframe(svg, height=360)
    else:
        components.html(svg, height=360)
    st.markdown("### Where can an agent live?")
    st.dataframe(pd.DataFrame([
        ["AgentCore Runtime", "Managed, one private sandbox per session; any framework; scales to zero", "Agents with sessions, tools, long waits", "Cold starts; AgentCore-specific; check regions and limits"],
        ["AWS Lambda", "Short functions, no sessions of their own", "Quick stateless tasks and tools (like our Lambda)", "Time limit per call; you keep the conversation state yourself"],
        ["ECS / Fargate / EKS (containers)", "Your container, always on or scaled by you", "Full control, existing platform, steady traffic", "You run, patch and scale it; you pay while it idles"],
        ["Bedrock Agents (configure, not code)", "Managed agents set up in the console", "Simple agents, little code", "Less control of the loop; check what is current"],
        ["Another cloud's agent service (Azure AI Foundry Agent Service, Google Vertex AI Agent Engine)", "The same idea on another cloud", "Customer is already on that cloud", "Different tools and prices; check each one's limits"],
        ["Your own VM / laptop", "What we did on Days 1 to 11", "Learning, prototypes", "Nobody else can use it; nothing scales; you are on call"]],
        columns=["Option", "What it is", "Good for", "Watch out"]), hide_index=True, width="stretch")

    st.markdown("### What will it cost? (try the numbers)")
    with st.expander("Prices used (AWS price page, 20 Oct 2026). Always re-check before you quote a client."):
        pc1, pc2, pc3, pc4 = st.columns(4)
        p_cpu = pc1.number_input("Runtime $ per vCPU-hour", value=0.0895, format="%.4f")
        p_mem = pc2.number_input("Runtime $ per GB-hour", value=0.00945, format="%.5f")
        p_gw = pc3.number_input("Gateway $ per 1,000 calls", value=0.005, format="%.4f")
        p_pol = pc4.number_input("Policy $ per request", value=0.000025, format="%.6f")
    k1, k2, k3, k4 = st.columns(4)
    per_day = k1.number_input("Questions per day", 100, 200000, 2000, step=100)
    wall = k2.number_input("Seconds per question (wall clock)", 1, 300, 12)
    share = k3.slider("Share of those seconds the CPU really works", 5, 100, 25, help="While the agent waits for the model or a tool, the CPU is idle and is not billed.") / 100
    mem = k4.number_input("Memory (GB)", 0.5, 8.0, 1.0, step=0.5)
    k5, k6, k7, k8 = st.columns(4)
    model_key = k5.selectbox("Model", list(P.MODELS), index=1, format_func=lambda m: P.MODELS[m]["label"])
    tin = k6.number_input("Tokens in per question", 200, 100000, 3000, step=200)
    tout = k7.number_input("Tokens out per question", 20, 20000, 300, step=20)
    calls = k8.number_input("Gateway calls per question", 0, 20, 3)
    pol_on = st.checkbox("Policy engine switched on", value=True)
    n = per_day * 30
    parts = {"Runtime CPU": n * wall * share * 1 / 3600 * p_cpu, "Runtime memory": n * wall * mem / 3600 * p_mem, "Gateway": n * calls * p_gw / 1000,
             "Policy checks": n * calls * p_pol if pol_on else 0.0, "Model tokens": n * P.cost(model_key, tin, tout)}
    total = sum(parts.values())
    m1, m2, m3 = st.columns(3)
    m1.metric("Per month", f"${total:,.2f}")
    m2.metric("Per question", f"${total / n:.5f}")
    m3.metric("Biggest line", max(parts, key=parts.get))
    st.bar_chart(pd.Series(parts, name="US$ per month"), height=240)
    st.caption("Assumptions: 1 vCPU; memory counted for the whole time of the question; no free tier; Observability (CloudWatch) and data transfer not included.")
    with st.expander("💼 Questions a client asks · tap to see a good answer"):
        st.markdown("- **\"Why not just run it on a server?\"** You can. A server costs money while idle and you patch and scale it. A Runtime gives each user a private sandbox and bills the work done.\n"
                    "- **\"Is my data safe between users?\"** Each session runs in its own isolated sandbox. You must still give every user their own session id.\n"
                    "- **\"What if it is slow in the morning?\"** That is the cold start: show progress, or keep a session warm for busy users.\n"
                    "- **\"Do we have to rewrite the agent?\"** No. Your existing agent code is wrapped in a small entry function and deployed.\n"
                    "- **\"Can we leave AWS later?\"** The agent is ordinary code and the tools speak MCP, so the moving cost is the hosting and deployment, not the agent.")
    st.markdown('<div class="client"><b>💼 Say this to a client:</b> "Your agent runs in its own private sandbox for each conversation, starts when someone asks and stops when they leave. '
                'You pay for the work, you see every step, and the same agent code runs elsewhere if you ever need it to."</div>', unsafe_allow_html=True)
    thinking("t5", [
        ("In the cost table, which line is usually the biggest for an AskIT-style agent?",
         {"a": "The model tokens.", "b": "The Gateway calls.", "c": "The memory."}, "a",
         "Try bigger token counts and a bigger model. Tokens dominate. Hosting is cheap by comparison."),
        ("Questions per day double and nothing else changes. What happens to the monthly bill?",
         {"a": "It stays the same.", "b": "It roughly doubles, because you pay per use and nothing sits idle.", "c": "It goes down."}, "b",
         "Pay-per-use scales with use. There is no big fixed fee for an idle server.")],
        "<b>Hosting is the small number.</b> The model's tokens usually cost more than the Runtime, the Gateway and the policy checks together. "
        "So the biggest cost lever is still the one from Day 10: fewer steps, fewer tokens, a right-sized model.")

# ================================================================================================ LESSONS
with tabs[5]:
    names = {"t2": "2 · Talk to it", "t3": "3 · Sessions", "t4": "4 · See it in AWS", "t5": "5 · How it works and cost"}
    st.subheader("🎓 Lessons learnt")
    st.caption("Each lesson unlocks when you answer the two thinking questions at the bottom of its tab.")
    st.progress(len(S.lessons) / len(names), text=f"Lessons unlocked: {len(S.lessons)} of {len(names)}")
    for k, nm in names.items():
        if k in S.lessons:
            st.markdown(f'<div class="lesson"><b>🎓 Tab {nm}</b><br>{S.lessons[k]}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="lock">🔒 Tab {nm}: not unlocked yet</div>', unsafe_allow_html=True)
    if S.lessons:
        txt = "# My lessons from Lab 16A\n\n" + "\n\n".join(f"## Tab {names[k]}\n" + re.sub(r"<[^>]+>", "", S.lessons[k]) for k in names if k in S.lessons)
        st.download_button("⬇ Download my lessons (.md)", txt, file_name="lab16a_lessons.md")
