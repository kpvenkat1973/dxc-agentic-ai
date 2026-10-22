"""Lab 16 · AskIT goes to production  (Day 12, Streamlit screen).   Start it with:  python run.py

One story, six tabs. The SAME AskIT agent you built on Day 5:
  1 on your VM  ->  2 deployed by YOU to AgentCore Runtime  ->  3 sessions  ->  4 version 2 with Gateway tools
  ->  5 an incident you find in CloudWatch  ->  6 a policy that blocks a risky action, and the wrap-up.
No code to edit. Files: cloud.py (AWS calls) · gw_agent.py + gw_client.py + tools_core.py (the local agent and its tools)
"""
import re

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

import model_factory as mf  # noqa: I001  (must load first: it reads the course .env)
import cloud
import gw_agent
import gw_client as gc

st.set_page_config(page_title="Lab 16 · AskIT goes to production", page_icon="🚀", layout="wide", initial_sidebar_state="expanded")
st.markdown("""<style>
html, body, [class*="css"] {font-size:18px;}
.hero{background:linear-gradient(120deg,#0b1f3a,#1F5AA6 60%,#0E7068);color:#fff;padding:18px 22px;border-radius:16px;margin:0 0 10px}
.hero h2{margin:0 0 4px;color:#fff}.hero p{margin:0;opacity:.9}
.board{display:flex;flex-wrap:wrap;gap:8px;margin:10px 0 4px}
.gap{padding:8px 14px;border-radius:999px;font-weight:700;font-size:15px;border:2px solid}
.gap.open{background:rgba(180,35,24,.10);border-color:#B42318;color:#B42318}
.gap.closed{background:rgba(14,112,104,.16);border-color:#0E7068;color:#0E7068}
.bridge{background:rgba(31,90,166,.10);border-left:6px solid #1F5AA6;padding:10px 16px;border-radius:10px;margin:6px 0 12px}
.todo{background:rgba(245,166,35,.12);border:2px solid #E08A00;padding:14px 18px;border-radius:12px;margin:10px 0}
.lesson{background:linear-gradient(135deg,rgba(106,63,160,.20),rgba(106,63,160,.06));border:2px solid #6A3FA0;padding:14px 18px;border-radius:14px;margin:12px 0}
.client{background:rgba(14,112,104,.12);border-left:6px solid #0E7068;padding:12px 16px;border-radius:10px;margin:8px 0}
.ans{background:rgba(127,127,127,.10);border-radius:10px;padding:12px 16px;margin:6px 0;font-size:19px}
.cold{background:rgba(31,90,166,.14);border-left:6px solid #1F5AA6;padding:8px 14px;border-radius:10px;margin:6px 0}
.warm{background:rgba(224,138,0,.14);border-left:6px solid #E08A00;padding:8px 14px;border-radius:10px;margin:6px 0}
.alarm{background:rgba(180,35,24,.14);border:3px solid #B42318;padding:14px 18px;border-radius:12px;margin:8px 0;font-weight:600}
</style>""", unsafe_allow_html=True)

S = st.session_state
for k, v in {"gaps": {}, "pred": {}, "lessons": {}, "calls": [], "sid": {k: cloud.new_session_id() for k in "PABX"},
             "rt": None, "who": None, "vals": None, "last": {}, "use_backup": False, "listed": False}.items():
    S.setdefault(k, v)
for _k in "PABX":                                                             # older sessions (before an app update) may miss a key
    S.sid.setdefault(_k, cloud.new_session_id())

GAPS = [("host", "🏠 Hosting"), ("scale", "👥 Scale & isolation"), ("tools", "🧰 Enterprise tools"), ("ops", "🔎 Troubleshooting"), ("gov", "🛡️ Governance")]
Q_TICKET = "Summarise ticket TKT-0004 and tell me the next step."
Q_VIP = "Who is employee EMP-1012 and are they a VIP?"
Q_KB = "How do I fix VPN error 809?"
Q_RESET_OK = "Please reset the password for EMP-1002. They are locked out."
Q_RESET_VIP = "Please reset the password for EMP-1012. They are locked out."


# ============================================================================================ helpers
def close_gap(key):
    if key not in S.gaps:
        S.gaps[key] = True
        st.toast(f"Gap closed: {dict(GAPS)[key]} ✅", icon="🎉")
        st.rerun()                                                            # redraw the scoreboard at the top


def board():
    chips = "".join(f'<span class="gap {"closed" if S.gaps.get(k) else "open"}">{"✅" if S.gaps.get(k) else "⛔"} {label}</span>' for k, label in GAPS)
    return f'<div class="board">{chips}</div>'


def bridge(text):
    st.markdown(f'<div class="bridge">🔗 <b>Remember?</b> {text}</div>', unsafe_allow_html=True)


def todo(html):
    st.markdown(f'<div class="todo">{html}</div>', unsafe_allow_html=True)


def lesson(key, text, client):
    S.lessons[key] = (text, client)
    st.markdown(f'<div class="lesson">🎓 <b>Lesson learnt</b><br>{text}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="client">💼 <b>Say this to a client:</b> “{client}”</div>', unsafe_allow_html=True)


def predict(key, question, options, right, why):
    """Predict first: the run button below stays locked until you pick an answer."""
    st.markdown(f"#### 🤔 Predict first: {question}")
    pick = st.radio("prediction", options, index=None, key=f"pr_{key}", label_visibility="collapsed")
    if pick is not None:
        S.pred[key] = (pick, right, why)
    return pick is not None


def reveal(key):
    if key in S.pred:
        pick, right, why = S.pred[key]
        (st.success if pick == right else st.info)(("✅ You predicted right. " if pick == right else f"You predicted “{pick}”. The answer: **{right}**. ") + why)


def need_aws():
    if S.who is None:
        try:
            S.who = cloud.whoami()
            S.vals = cloud.class_values(S.who[1])
        except Exception as e:                                                # noqa: BLE001
            st.error(f"Cannot read your AWS identity: {cloud.explain(e)}")
            return False
    return True


def refresh_runtime():
    try:
        S.rt = cloud.find_runtime(S.who[0])
        S.listed = True
    except Exception as e:                                                    # noqa: BLE001
        st.error(cloud.explain(e))


def target():
    """-> (arn, gateway_url_to_send, label).  Your Runtime, or the class backup Runtime."""
    if S.use_backup or not S.rt:
        return S.vals["backup_arn"], S.vals["gateway_url"], "Class backup Runtime"
    return S.rt["arn"], None, f"My Runtime {S.rt['name']} (v{S.rt['version']})"


def ask(prompt, label="A"):
    arn, gw, where = target()
    r = cloud.invoke(arn, prompt, S.sid[label], gw)
    r["where"], r["label"], r["q"] = where, label, prompt
    if r.get("ok"):
        sess = r.get("session", {})
        S.calls.append({"#": len(S.calls) + 1, "Session": label, "Sandbox id": sess.get("boot_id", "?"), "Turn": sess.get("turn", "?"),
                        "Cold start?": "yes 🧊" if sess.get("cold") else "no 🔥", "Seconds": round(r["ms"] / 1000, 1), "Runtime": where,
                        "q": prompt, "a": r.get("answer", "")})
    return r


def show(r):
    if not r:
        return
    if not r.get("ok"):
        st.error("❌ " + r.get("error", "failed"))
        return
    sess = r.get("session", {})
    c = st.columns(5)
    c[0].metric("Where it ran", "AWS Runtime")
    c[1].metric("Sandbox id", sess.get("boot_id", "?"))
    c[2].metric("Turn", sess.get("turn", "?"))
    c[3].metric("Tools it has", len(r.get("tools") or []))
    c[4].metric("Time", f"{r['ms'] / 1000:.1f} s")
    st.markdown(f'<div class="{"cold" if sess.get("cold") else "warm"}">' + ("🧊 <b>Cold start:</b> new session, so AWS started a fresh sandbox first."
                if sess.get("cold") else "🔥 <b>Warm:</b> this session's sandbox was already running.") + "</div>", unsafe_allow_html=True)
    st.markdown(f'<div class="ans">💬 {r.get("answer", "")}</div>', unsafe_allow_html=True)
    if r.get("steps"):
        with st.expander("🔍 What the agent did, step by step", expanded=False):
            st.dataframe(pd.DataFrame([{"Step": s.get("label"), "ms": s.get("ms"), "Result": s.get("out")} for s in r["steps"]]), hide_index=True, width="stretch")


def tool_failed(r):
    return bool(r and r.get("ok") and any(s.get("kind") == "tool" and '"error"' in str(s.get("out", "")) for s in r.get("steps", [])))


# ============================================================================================ header + sidebar
st.markdown('<div class="hero"><h2>🚀 AskIT goes to production</h2><p>The CIO: “Great demo. Can 50,000 employees use it on Monday, securely, '
            'and will you know when it breaks?” Close all five gaps to say yes.</p></div>', unsafe_allow_html=True)
st.markdown(board(), unsafe_allow_html=True)
st.progress(len(S.gaps) / 5, text=f"Production gaps closed: {len(S.gaps)} of 5")

with st.sidebar:
    st.header("🚀 Lab 16")
    if need_aws():
        st.markdown(f"**You are:** `{S.who[0]}`")
        st.markdown(f"**Your Runtime name:** `askit_{S.who[0]}`")
        if S.rt:
            st.success(f"Runtime found · {S.rt['status']} · version {S.rt['version']} · Gateway {'set ✅' if S.rt['gateway_set'] else 'not set'}")
        elif S.listed:
            st.warning("No Runtime yet (tab 2)")
        if st.button("🔄 Refresh my Runtime"):
            refresh_runtime()
            st.rerun()
        S.use_backup = st.toggle("Stuck? Use the class backup Runtime", value=S.use_backup,
                                 help="Only if your own deploy failed. You still do every other step.")
    st.divider()
    st.markdown("**Model for tab 1 (your VM)**")
    stt = mf.status()
    names = [p for p in ("bedrock", "azure", "openai", "offline") if stt[p][0]]
    S.prov = st.selectbox("Model", names, index=names.index(mf.auto_provider()), format_func=lambda p: mf.LABELS[p], label_visibility="collapsed")

tabs = st.tabs(["🖥️ 1 · On my VM", "☁️ 2 · Deploy it", "👥 3 · Two users", "🧰 4 · Gateway (v2)", "🛡️ 5 · Run it safely", "🏗️ 6 · Architect it"])

# ============================================================================================ TAB 1  local
with tabs[0]:
    st.subheader("Step 1 · AskIT as it is today: on your VM")
    bridge("Day 5: you built the agent loop (ask the model, it picks a tool, run the tool, answer). Days 3–4: the knowledge-base search. This is that agent.")
    st.markdown("**Ask AskIT.** It runs **here, on your VM**, and its tools are **Python functions on your VM**.")
    q = st.radio("Question", [Q_TICKET, Q_VIP, Q_KB], horizontal=False, key="q1")
    if st.button("▶ Ask the agent on my VM", type="primary"):
        with st.spinner("Your VM is running the agent…"):
            g = gc.PracticeGateway()
            tools = gc.tools_of(g.rpc("tools/list"))
            specs = [{"name": t["name"], "alias": t["name"].split("___")[-1], "description": t.get("description", ""),
                      "schema": t.get("inputSchema") or {"type": "object", "properties": {}}} for t in tools]
            try:
                S.last["local"] = gw_agent.run(q, S.prov, specs, lambda n, a: (gc.call_text(g.rpc("tools/call", {"name": n, "arguments": a})), 0))
            except Exception as e:                                            # noqa: BLE001
                S.last["local"] = {"answer": f"Model error: {e}. Pick 'Offline stand-in' in the sidebar and try again.", "steps": [], "ms": 0}
    loc = S.last.get("local")
    if loc:
        st.markdown(f'<div class="ans">💬 {loc["answer"]}</div>', unsafe_allow_html=True)
        st.caption(f"{loc.get('ms', 0) / 1000:.1f} s · tools used: " + (", ".join(s["label"].split("(")[0].split("___")[-1] for s in loc["steps"] if s.get("kind") == "tool") or "none"))
        st.divider()
        st.markdown("### 🧯 Now imagine 50,000 employees use this. What is missing?")
        st.caption("Tick every gap you agree with. These five go on the scoreboard at the top. We close one in each step today.")
        gap_text = {"host": "It runs on MY VM. When I close VS Code, AskIT is gone. Nobody else can use it.",
                    "scale": "500 users at once? One VM, one process, everyone shares the same memory.",
                    "tools": "The tools are Python functions copied into this program. Every new agent copies them again.",
                    "ops": "If it breaks at 3 am, where are the logs and traces? Only on my VM, and only if I am watching.",
                    "gov": "Nothing stops the agent from resetting the CEO's password."}
        ticked = [k for k, _ in GAPS if st.checkbox(gap_text[k], key=f"gapck_{k}")]
        if len(ticked) == 5:
            lesson("t1", "<b>The agent works. It is not production-ready.</b> Same code, but no hosting, no isolation, no shared tools, no visibility, no guardrails. "
                   "AgentCore closes these five gaps without rewriting the agent.",
                   "Your prototype logic is fine. What we add now is how it runs: hosting, shared tools, monitoring and policy.")

# ============================================================================================ TAB 2  deploy
with tabs[1]:
    st.subheader("Step 2 · Deploy YOUR AskIT to AgentCore Runtime")
    bridge("Day 9: you created a Lambda in the AWS console. Today you do the same for the whole agent: same idea, a bigger thing to host.")
    if need_aws():
        v = S.vals
        if predict("servers", "after you deploy, how many servers will you manage?", ["One EC2 server", "One per user", "Zero"], "Zero",
                   "AgentCore Runtime starts a sandbox when a request arrives and stops it when idle. You never see a server."):
            todo(f"""<b>🖐️ Your turn in the AWS console (5 minutes). Sign in as <code>{S.who[0]}</code>, region <b>N. Virginia (us-east-1)</b>.</b><br><br>
            1. Search <b>Amazon Bedrock AgentCore</b>. Left menu: <b>Runtime</b>. Click <b>Create runtime</b> (or <b>Host agent</b>).<br>
            2. <b>Name</b>: copy from the box below. Leave <b>Runtime platform V1</b> and <b>Compute type microVMs</b> as they are.<br>
            3. <b>Agent source</b>: <b>S3 Source</b>. Under <b>S3 configuration</b> choose <b>Choose from an existing S3 bucket</b>
               ⚠️ <i>not</i> “Start with a template”. Paste the S3 URI from the box below.<br>
            4. <b>Agent entry point</b>: <code>main.py</code>. <b>Python version</b>: as in the box below.<br>
            5. <b>Permissions</b>: <b>Use an existing service role</b> → <code>askit-runtime-role</code>. Leave everything else. Click <b>Create</b>.<br>
            6. Wait about 1 minute, then click <b>Check my Runtime</b> below. A grey note “Update your IAM execution role…” is normal: ignore it.""")
            c1, c2 = st.columns(2)
            with c1:
                st.caption("📋 Hover a grey box and click the copy icon ⧉, then paste in the AWS console.")
                st.markdown("**Name**")
                st.code(f"askit_{S.who[0]}", language=None)
                st.markdown("**S3 URI** (Choose from an existing S3 bucket)")
                st.code(v["s3_uri"], language=None)
            with c2:
                st.markdown("**Agent entry point**")
                st.code("main.py", language=None)
                st.markdown("**Python version**")
                st.code(str(v["runtime"]).replace("PYTHON_", "Python ").replace("_", "."), language=None)
                st.markdown("**Permissions → Use an existing service role**")
                st.code(v["role"], language=None)
            st.caption("No environment variables yet. That is on purpose: this is version 1.")
            if st.button("🔎 Check my Runtime", type="primary"):
                refresh_runtime()
            if S.listed and not S.rt:
                st.warning(f"No Runtime called askit_{S.who[0]} yet. Check the name (small letters, underscore) and the region, then click again.")
            if S.rt:
                st.success(f"✅ Found **{S.rt['name']}** · status **{S.rt['status']}** · version **{S.rt['version']}** · role {S.rt['role']}")
                if str(S.rt["status"]).upper() != "READY":
                    st.info("Not Ready yet. Wait 30 seconds and click Check my Runtime again.")
                elif st.button("👋 Say hello to my Runtime (ping)"):
                    with st.spinner("First call: AWS is starting a sandbox for you…"):
                        r = ask("ping", "P")
                    S.last["ping"] = r
                show(S.last.get("ping"))
                if S.last.get("ping", {}).get("ok"):
                    close_gap("host")
                    reveal("servers")
                    lesson("t2", "<b>Same code, zero servers.</b> You gave AWS a zip and a role. AgentCore Runtime runs it on demand, in a sandbox, "
                           "and you pay for the time it works, not for idle machines. The CLI does the same in one command; the console shows every setting.",
                           "We host your existing agent on a managed runtime. No servers to patch, it scales with use, and you pay per use.")

# ============================================================================================ TAB 3  sessions
PEOPLE = {"A": ("👩", "Priya", [Q_TICKET, "Is employee EMP-1002 a VIP?", "What was my first question?"]),
          "B": ("👨", "Rahul", ["What did the other employee ask you?"])}


def chat_column(label):
    icon, name, _ = PEOPLE[label]
    rows = [c for c in S.calls if c["Session"] == label]
    st.markdown(f"### {icon} {name}")
    if not rows:
        st.caption("Has not asked anything yet.")
        return
    st.markdown(f"🖥️ **{name}'s private computer (sandbox) id:** `{rows[-1]['Sandbox id']}`")
    for c in rows:
        st.markdown(f"**{icon} {name}:** {c['q']}")
        badge = "🧊 <b>slow first answer</b>: AWS started a private computer for " + name if c["Cold start?"].startswith("yes") else "🔥 <b>fast</b>: same private computer, already running"
        st.markdown(f'<div class="ans">🤖 {c["a"]}<br><small>{badge} · {c["Seconds"]} s</small></div>', unsafe_allow_html=True)


with tabs[2]:
    st.subheader("Step 3 · Two employees use AskIT at the same time")
    bridge("Day 7: memory and context. On your VM everyone would share one program and one memory. On AgentCore each person gets a private computer.")
    if need_aws() and (S.rt or S.use_backup):
        st.markdown("Two employees, **Priya** and **Rahul**, chat with **your** AskIT on AWS. Each conversation is called a **session**. "
                    "Watch two things: **which private computer** answers each person, and **how fast**.")
        if predict("sessions", "Priya asks 3 questions, Rahul asks 1. How many private computers (sandboxes) will AWS start?",
                   ["1 (they share one)", "2 (one per person)", "4 (one per question)"], "2 (one per person)",
                   "One private computer per session (per person's conversation). Priya's 3 questions reuse hers; Rahul gets his own."):
            c1, c2, c3 = st.columns(3)
            if c1.button("👩 Priya asks 3 questions", type="primary"):
                with st.spinner("Priya is chatting…"):
                    for qq in PEOPLE["A"][2]:
                        r = ask(qq, "A")
                        if r.get("ok") and S.calls:
                            S.calls[-1]["q"], S.calls[-1]["a"] = qq, r.get("answer", "")
                        elif not r.get("ok"):
                            st.error("❌ " + r.get("error", ""))
                            break
            if c2.button("👨 Rahul asks 1 question", type="primary"):
                with st.spinner("Rahul is chatting…"):
                    qq = PEOPLE["B"][2][0]
                    r = ask(qq, "B")
                    if r.get("ok") and S.calls:
                        S.calls[-1]["q"], S.calls[-1]["a"] = qq, r.get("answer", "")
                    elif not r.get("ok"):
                        st.error("❌ " + r.get("error", ""))
            if c3.button("🔁 Start again (new conversations)"):
                S.sid.update({"A": cloud.new_session_id(), "B": cloud.new_session_id()})
                S.calls = [c for c in S.calls if c["Session"] not in ("A", "B")]
                st.rerun()
            left, right = st.columns(2)
            with left:
                chat_column("A")
            with right:
                chat_column("B")
            pa = [c for c in S.calls if c["Session"] == "A"]
            pb = [c for c in S.calls if c["Session"] == "B"]
            if pa and pb and pa[-1]["Sandbox id"] != pb[-1]["Sandbox id"]:
                st.markdown('<div class="todo"><b>👀 What you just saw</b><br>'
                            f"• Priya's 3 answers came from <b>one</b> private computer (<code>{pa[-1]['Sandbox id']}</code>). Rahul got a <b>different</b> one (<code>{pb[-1]['Sandbox id']}</code>).<br>"
                            "• The <b>first</b> answer for each person was slower (AWS started their computer). Later answers were fast.<br>"
                            "• Priya's agent <b>remembered</b> her first question. Rahul's agent knows <b>nothing</b> about Priya: no data leaks between users.<br>"
                            "• Look at Priya's ticket answer: version 1 has <b>no tools</b>. The Python tools stayed on your VM. Step 4 fixes that.</div>",
                            unsafe_allow_html=True)
                close_gap("scale")
                reveal("sessions")
                lesson("t3", "<b>Every user gets a private computer (sandbox).</b> Same conversation: same sandbox, memory kept, fast after the first answer. "
                       "Another user: another sandbox, nothing shared. The first answer is slower (a cold start). And notice: the agent moved to AWS, but its tools did not come along.",
                       "Each conversation runs in its own isolated sandbox, so one user's data never reaches another's.")
    else:
        st.info("Finish step 2 first (or switch on the backup Runtime in the sidebar).")

# ============================================================================================ TAB 4  gateway v2
with tabs[3]:
    st.subheader("Step 4 · Version 2: give your agent enterprise tools through the Gateway")
    bridge("Day 9: an MCP server on Lambda. Day 11: the Gateway put MCP in front of that Lambda. Today your deployed agent plugs into it.")
    if need_aws() and (S.rt or S.use_backup):
        st.markdown("Version 1 has **0 tools**. The class Gateway offers 4 tools: `get_ticket`, `get_user`, `reset_password`, `search_kb` (the RAG search over the 20 KB articles).")
        if predict("tools", "your agent has 0 tools now. You add ONE setting: the Gateway's address. How many tools will it have?",
                   ["Still 0 (the code must change)", "1 (one address, one tool)", "4 (every tool behind the Gateway)"], "4 (every tool behind the Gateway)",
                   "The agent asks the Gateway for its tool list (MCP tools/list) on every run. One address gives it every tool behind the Gateway."):
            todo("""<b>🖐️ Your turn: everything happens in the AWS console (3 minutes).</b><br><br>
            <b>A. Find the Gateway's address</b><br>
            1. AgentCore → left menu <b>Gateways</b> → click <b>askit-gw-user116</b> (the class Gateway).<br>
            2. Copy its <b>Gateway URL</b> (it ends with <code>/mcp</code>). Look at its <b>Targets</b>: one Lambda with 4 tools.<br><br>
            <b>B. Give that address to YOUR agent</b><br>
            3. AgentCore → <b>Runtime</b> → click your Runtime → <b>Update runtime</b> (top right).<br>
            4. <b>Environment variables</b> (expand <i>Advanced configurations</i> if hidden) → <b>Add</b>. Key: <code>GATEWAY_URL</code>. Value: paste the Gateway URL.<br>
            5. <b>Update</b>. AWS makes <b>Version 2</b> and points the DEFAULT endpoint to it. Wait for <b>Ready</b>, then click <b>Check version</b> below.""")
            with st.expander("Can't find the Gateway URL? Open this"):
                st.code(S.vals["gateway_url"], language=None)
            if st.button("🔎 Check version", type="primary"):
                refresh_runtime()
                S.sid["X"] = cloud.new_session_id()     # a new version needs a new session
            if S.rt and not S.use_backup:
                (st.success if S.rt["gateway_set"] else st.warning)(f"Version **{S.rt['version']}** · GATEWAY_URL **{'set ✅' if S.rt['gateway_set'] else 'not set yet'}** · {S.rt['status']}")
            q4 = st.radio("Ask (in a new session)", [Q_TICKET, Q_KB, Q_VIP], key="q4")
            not_ready = bool(S.rt and not S.use_backup and str(S.rt["status"]).upper() != "READY")
            if not_ready:
                st.info("⏳ Your Runtime is still updating. Wait about 1 minute, then click Check version again.")
            if st.button("▶ Ask version 2", disabled=not_ready):
                ver = S.rt["version"] if S.rt else "backup"
                if S.get("sid_ver") != ver:                                   # a running sandbox keeps its old version: new version, new session
                    S.sid["X"], S["sid_ver"] = cloud.new_session_id(), ver
                with st.spinner("The agent lists its tools at the Gateway, then works…"):
                    S.last["v2"] = ask(q4, "X")
            r = S.last.get("v2")
            show(r)
            if r and r.get("ok") and len(r.get("tools") or []) >= 4:
                st.markdown("**Tools your agent found:** " + " · ".join(f"`{t}`" for t in r["tools"]))
                close_gap("tools")
                reveal("tools")
                lesson("t4", "<b>Tools live in one place; agents plug in.</b> The agent code did not change. The Gateway turned a Lambda into MCP tools, IAM signs every call, "
                       "and every agent in the company can reuse them. A new setting made a new version, so you could roll back to version 1 in a click.",
                       "Your systems (tickets, HR, knowledge base) are exposed once, securely, and every agent reuses them. No copy-pasted integrations.")
    else:
        st.info("Finish step 2 first (or switch on the backup Runtime in the sidebar).")

# ============================================================================================ TAB 5  incident
def mini_trace(r):
    """The run as a simple trace: one row per step, the failing step in red."""
    rows = []
    for st_ in r.get("steps", []):
        out = str(st_.get("out", ""))
        bad = st_.get("kind") == "tool" and '"error"' in out
        icon = {"model": "🤖 Model", "tool": "🧰 Tool", "gateway": "🚪 Gateway"}.get(st_.get("kind"), "•")
        label = str(st_.get("label", "")).split("___")[-1]
        txt = out.replace("<", "&lt;")[:160]
        style = "background:rgba(180,35,24,.16);border-left:6px solid #B42318" if bad else "background:rgba(127,127,127,.08);border-left:6px solid #0E7068"
        rows.append(f'<div style="{style};padding:8px 12px;border-radius:8px;margin:4px 0">'
                    f'<b>{"❌ " if bad else "✅ "}{icon}</b> · <code>{label}</code> · {st_.get("ms", 0)} ms<br><small>{txt}</small></div>')
    st.markdown("".join(rows), unsafe_allow_html=True)


with tabs[4]:
    st.subheader("Step 5 · Run it safely: when it breaks, and when it must say no")
    if need_aws() and (S.rt or S.use_backup):
        # ---------------------------------------------------------------- 5A incident
        st.markdown("## 🚨 5A · Something breaks")
        bridge("Day 10: a trace shows every step of an agent run. AgentCore records that trace for every request, automatically.")
        st.markdown("**When the trainer says “Production is down”**, click the button.")
        if predict("rootcause", "AskIT gives a strange answer about a ticket. Where is the problem most likely?",
                   ["The AI model", "The agent code", "A tool behind the Gateway"], "A tool behind the Gateway",
                   "The trace shows it: the model and the Gateway were fine; the get_ticket tool failed (ticket system timeout, 503)."):
            if st.button("▶ Ask: " + Q_TICKET, type="primary", key="inc_btn"):
                S.sid["X"] = cloud.new_session_id()                           # fresh conversation: the agent must call the tool, not answer from memory
                with st.spinner("Asking…"):
                    S.last["inc"] = ask(Q_TICKET, "X")
            r = S.last.get("inc")
            if r and not r.get("ok"):
                st.error("❌ " + r.get("error", ""))
            if r and r.get("ok"):
                st.markdown(f'<div class="ans">💬 {r.get("answer", "")}</div>', unsafe_allow_html=True)
                if not tool_failed(r):
                    st.info("Looks normal. Wait for the trainer to break production, then click again.")
                else:
                    st.markdown("#### 🔎 The trace of this run (one row per step; the failed step is red)")
                    mini_trace(r)
                    close_gap("ops")
                    reveal("rootcause")
                    lesson("t5a", "<b>Never debug an agent from its answer.</b> The answer sounded fine. The trace showed which step failed (get_ticket), why (ticket system timeout), "
                           "and that the model was fine. AgentCore keeps this trace for every run in CloudWatch, with no extra code.",
                           "Every agent run is traced end to end, so when something breaks we see which step failed in minutes, not days.")
        st.divider()
        # ---------------------------------------------------------------- 5B policy (explainer, no AWS calls)
        st.markdown("## 🛡️ 5B · It must say no")
        bridge("Day 11: guardrails lived inside your app. AgentCore Policy puts the rule in the Gateway, outside the agent, for every agent at once.")
        st.markdown("The security team's rule: **never reset the password of a VIP** (EMP-1001, EMP-1012, EMP-1023).")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**In plain English**")
            st.markdown('<div class="ans">⛔ <b>Forbid</b> the tool <code>reset_password</code> on our Gateway<br>'
                        '<b>when</b> the user id is EMP-1001, EMP-1012 or EMP-1023.<br><br>'
                        '✅ <b>Permit</b> each tool (get_ticket, get_user, reset_password, search_kb) for our own AWS users.<br><br>'
                        '🔒 Anything not permitted is denied (<b>default deny</b>). A forbid always wins.</div>', unsafe_allow_html=True)
        with c2:
            st.markdown("**The same rule in Cedar** (the policy language AgentCore uses)")
            st.code('forbid(\n  principal is AgentCore::IamEntity,\n  action == AgentCore::Action::"askit-lambda___reset_password",\n'
                    '  resource == AgentCore::Gateway::"<class gateway>"\n)\nwhen {\n  ["EMP-1001", "EMP-1012", "EMP-1023"]\n    .contains(context.input.user_id)\n};',
                    language="text")
        st.markdown("**Where it sits:** Agent → 🚪 Gateway → **🛡️ Policy engine decides allow / deny** → tool. The agent never talks to the tool directly.")
        if predict("policy", "the security team adds this rule. Must the developers change or redeploy the agent?",
                   ["Yes, the agent code must check for VIPs", "No, the Gateway enforces it for every agent"], "No, the Gateway enforces it for every agent",
                   "The Gateway asks the policy engine before every tool call. The agent cannot go around it, even if the model is tricked by a prompt."):
            what = st.radio("An agent tries: reset_password for EMP-1012. What happens?", ["The tool runs", "The Gateway denies the call; the agent tells the user it is not allowed"],
                            index=None, key="pol_q")
            if what:
                (st.success if what.startswith("The Gateway") else st.warning)(
                    "Denied at the Gateway, logged, and the agent gets a clear 'not allowed' message. The Lambda never runs." if what.startswith("The Gateway")
                    else "No: the forbid matches EMP-1012, so the Gateway blocks it before the Lambda runs.")
                close_gap("gov")
                reveal("policy")
                lesson("t5b", "<b>Security owns the rules; developers own the agent.</b> The policy sits in the Gateway and checks every tool call. "
                       "Default deny, explicit permits, and a forbid always wins. No redeploy, every decision logged, and it holds even if the model is tricked.",
                       "Your security team writes the rules once, at the gateway, and every agent obeys them, whatever the model decides.")
    else:
        st.info("Finish step 2 first (or switch on the backup Runtime in the sidebar).")

# ============================================================================================ TAB 6  architect it
PIECES = {
    "Runtime": "🏠 hosts the agent, a private sandbox per session, pay per use",
    "Gateway": "🚪 turns company APIs / Lambdas into MCP tools, IAM or OAuth in front",
    "Identity": "🪪 who the user is (company login) and the agent's own keys to other systems",
    "Memory": "🧠 short-term (this chat) and long-term (facts across chats) memory",
    "Observability": "🔎 a trace of every run: steps, time, tokens, errors",
    "Policy": "🛡️ rules (Cedar) on which tool calls are allowed",
    "Browser": "🌐 the agent uses websites like a person",
    "Code Interpreter": "🧮 the agent runs code safely (data, charts, files)",
    "Evaluations": "📏 scores answers (correct, faithful, safe) on live traffic",
}
CASES = {
    "🏦 AskBank Ops": {"story": "A bank wants an agent that resets passwords and grants system access for 8,000 staff. Auditors will check every action.",
                       "must": {"Runtime", "Gateway", "Identity", "Policy", "Observability"}, "nice": {"Memory", "Evaluations"},
                       "go": "Pilot (with human approval for access grants)",
                       "why": "Actions on accounts = Policy (never reset privileged users) + Identity (bank login, who asked). Audit = Observability. "
                              "Tools to the identity system via Gateway. Start as a pilot with human approval; no fully automatic access grants yet."},
    "🛒 StoreHelp": {"story": "A retailer wants a shopping assistant for its website. Traffic is 20× on sale days. It checks stock and prices.",
                     "must": {"Runtime", "Gateway", "Memory", "Observability"}, "nice": {"Evaluations", "Identity"},
                     "go": "Go (after a peak-load test and a cost alarm)",
                     "why": "Spiky traffic = Runtime (scales per session, pay per use; plan for cold start). Stock and price APIs via Gateway. "
                            "Memory for the shopping chat. Observability plus a cost alarm for sale days. Go, after a peak test."},
    "🏥 LabDoc": {"story": "A hospital wants summaries of lab reports for doctors. Reports contain patient data.",
                  "must": {"Runtime", "Gateway", "Identity", "Policy", "Observability", "Evaluations"}, "nice": {"Memory"},
                  "go": "No-go for now (pilot on non-patient reports first)",
                  "why": "Patient data = Identity (which doctor may see which report) + Policy + redaction. A wrong summary is dangerous, so Evaluations "
                         "(is it faithful?) and a human sign-off. No-go until redaction and evaluation are proven."},
}


def arch_svg(chosen):
    """A small reference architecture showing the pieces the participant picked."""
    def box(x, y, w, h, title, on, color):
        op = "1" if on else ".18"
        return (f'<g opacity="{op}"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="{color}" fill-opacity=".14" stroke="{color}" stroke-width="2"/>'
                f'<text x="{x + w / 2}" y="{y + h / 2 + 6}" text-anchor="middle" font-size="16" font-weight="700" fill="#1b2230">{title}</text></g>')
    c = chosen
    return f"""<svg viewBox="0 0 980 300" width="100%" style="background:#fff;border-radius:12px;font-family:Segoe UI,Arial">
    <defs><marker id="m" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5L0 10z" fill="#888"/></marker></defs>
    {box(10, 120, 140, 60, "👥 Users", True, "#1F5AA6")}
    {box(190, 120, 140, 60, "🪪 Identity", "Identity" in c, "#6A3FA0")}
    {box(370, 100, 200, 100, "🏠 Runtime (agent)", "Runtime" in c, "#6A3FA0")}
    {box(370, 20, 95, 60, "🧠 Memory", "Memory" in c, "#6A3FA0")}
    {box(475, 20, 95, 60, "🤖 Model", True, "#E08A00")}
    {box(370, 220, 95, 60, "🌐 Browser", "Browser" in c, "#6A3FA0")}
    {box(475, 220, 95, 60, "🧮 Code", "Code Interpreter" in c, "#6A3FA0")}
    {box(620, 120, 140, 60, "🚪 Gateway", "Gateway" in c, "#0E7068")}
    {box(620, 30, 140, 60, "🛡️ Policy", "Policy" in c, "#B42318")}
    {box(810, 120, 160, 60, "🏢 Systems", True, "#0E7068")}
    {box(620, 220, 160, 60, "🔎 Observability", "Observability" in c, "#1F5AA6")}
    {box(810, 220, 160, 60, "📏 Evaluations", "Evaluations" in c, "#1F5AA6")}
    <g stroke="#888" stroke-width="2" marker-end="url(#m)"><line x1="150" y1="150" x2="188" y2="150"/><line x1="330" y1="150" x2="368" y2="150"/>
    <line x1="570" y1="150" x2="618" y2="150"/><line x1="760" y1="150" x2="808" y2="150"/><line x1="690" y1="118" x2="690" y2="92"/></g></svg>"""


with tabs[5]:
    st.subheader("Step 6 · Architect it: design AgentCore for a client")
    bridge("Everything from 11 days, as a client solution. This is the conversation you will have in a sales or architecture call.")
    case = st.radio("Pick a client", list(CASES), horizontal=True, key="case")
    cs = CASES[case]
    st.markdown(f'<div class="todo">📞 <b>The client says:</b> {cs["story"]}</div>', unsafe_allow_html=True)
    picked = st.multiselect("Which AgentCore pieces would you propose?", list(PIECES), key=f"pick_{case}",
                            format_func=lambda k: f"{k}: {PIECES[k]}")
    go = st.radio("Your recommendation", ["Go", "Pilot (with human approval for access grants)", "Go (after a peak-load test and a cost alarm)",
                                          "No-go for now (pilot on non-patient reports first)"], index=None, key=f"go_{case}")
    components.html(arch_svg(set(picked)), height=320)
    if st.button("✅ Compare with the reference design", type="primary", disabled=not picked or go is None):
        S.last[f"arch_{case}"] = True
    if S.last.get(f"arch_{case}"):
        must, nice = cs["must"], cs["nice"]
        missed, extra = must - set(picked), set(picked) - must - nice
        c1, c2, c3 = st.columns(3)
        c1.metric("Must-haves you picked", f"{len(must & set(picked))} of {len(must)}")
        c2.metric("Missed", len(missed))
        c3.metric("Not needed", len(extra))
        if missed:
            st.warning("Missed: " + ", ".join(f"**{m}** ({PIECES[m][2:]})" for m in sorted(missed)))
        if extra:
            st.info("Not needed here (cost and complexity): " + ", ".join(sorted(extra)))
        (st.success if go == cs["go"] else st.info)(f"Reference recommendation: **{cs['go']}**")
        st.markdown(f'<div class="lesson">🏗️ <b>Reference design</b><br>{cs["why"]}</div>', unsafe_allow_html=True)
        components.html(arch_svg(must | nice), height=320)
        st.caption("Reference architecture: must-haves plus nice-to-haves.")
        S.lessons[f"arch {case}"] = (cs["why"], "We start from the risks and the users, then pick only the AgentCore pieces that close them.")

    st.divider()
    st.markdown("### ⚖️ AgentCore or build it yourself? (the question every client asks)")
    st.markdown("""
| Need | Build it yourself (Days 1–11) | AgentCore |
|---|---|---|
| Run the agent | Your VM / containers: you patch and scale | **Runtime**: sandbox per session, pay per use |
| Connect tools | MCP server you host (Day 9) | **Gateway**: APIs → MCP, IAM/OAuth in front |
| See inside | Langfuse / LangSmith (Day 10) | **Observability** in CloudWatch |
| Rules on actions | Guardrails in code (Day 11) | **Policy** at the Gateway, no redeploy |
| Memory | Your own store (Day 7) | **Memory**, managed |

**LangGraph / LangChain / MCP decide *how the agent thinks*. AgentCore decides *how it runs*.** They work together.
""")
    st.divider()
    st.markdown(board(), unsafe_allow_html=True)
    if len(S.gaps) == 5:
        st.success("🏆 All five gaps closed. You can answer the CIO: yes.")
    st.markdown("### 🧹 Before you leave: delete your Runtime")
    st.markdown(f"AgentCore → Runtime → select **askit_{S.who[0] if S.who else 'userNNN'}** → **Delete**. Then click below.")
    if st.button("🔎 Check it is deleted"):
        refresh_runtime()
        st.success("Deleted. Clean exit ✅") if S.rt is None else st.warning("Still there. Delete it in the console, then check again.")
    if S.lessons:
        txt = "# My lessons from Day 12: AskIT goes to production\n\n" + "\n\n".join(
            f"## {k}\n{re.sub(r'<[^>]+>', '', a)}\n\nClient line: {c}" for k, (a, c) in S.lessons.items())
        st.download_button("⬇ Download my lessons and client lines (.md)", txt, file_name="day12_lessons.md")
