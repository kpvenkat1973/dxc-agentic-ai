"""Lab 9 · AskIT MCP Control Room  (Streamlit screen).   Start it with:  python run.py

You do not need to edit any code. Connect, call, break, fix, move to AWS.
The server is askit_server.py; the client + controls are mcp_client.py; the model choice is model_factory.py.
"""
import json
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

import model_factory as mf  # noqa: I001  (must load first: it reads the course .env)
import diagram
import design_decision as dd
import mcp_client as mc
from askit_core import tools as T

HERE = Path(__file__).resolve().parent
st.set_page_config(page_title="Lab 9 · AskIT MCP Control Room", page_icon="🔌", layout="wide", initial_sidebar_state="expanded")
st.markdown("""<style>
html, body, [class*="css"] {font-size:18px;}
.take{background:rgba(106,63,160,.14);border-left:6px solid #6A3FA0;padding:14px 18px;border-radius:10px;margin:8px 0}
.client{background:rgba(14,112,104,.14);border-left:6px solid #0E7068;padding:14px 18px;border-radius:10px;margin:8px 0}
.step{background:rgba(127,127,127,.12);border:1px solid rgba(127,127,127,.35);padding:10px 14px;border-radius:10px;margin:6px 0}
.back{background:rgba(31,90,166,.10);border-left:6px solid #1F5AA6;padding:12px 16px;border-radius:10px;margin:8px 0}
.warn{background:rgba(183,121,31,.16);border:2px solid #B7791F;padding:14px 18px;border-radius:12px;margin:8px 0}
</style>""", unsafe_allow_html=True)

S = st.session_state
DESC = {s["toolSpec"]["name"]: s["toolSpec"]["description"] for s in T.TOOL_SPECS}
TOOL_NAMES = list(DESC)
lam = mc.load_lambda()
for k, v in {"home_kind": "stdio", "lam_url": lam["url"], "lam_key": lam["key"], "calls": [], "probe": {}, "incident": None,
             "last_run": None, "compare": None, "inspected": {}, "raw": None, "scenario": None, "cold": None,
             "ctl_role": "service-desk", "ctl_vip": False, "ctl_redact": False, "ctl_strict": False, "ctl_timeout": 6.0,
             "ctl_retries": 1, "ctl_confirm_on": False, "ctl_confirm_ans": True, "ctl_delay": 0.0, "ctl_flaky": 0,
             "preset": "Good (the original words)"}.items():
    S.setdefault(k, v)
for t in TOOL_NAMES:
    S.setdefault(f"d_{t}", DESC[t])


def controls():
    return mc.Controls(role=S.ctl_role, vip_block=S.ctl_vip, redact=S.ctl_redact, redact_ids=S.ctl_strict and S.ctl_redact,
                       timeout_s=float(S.ctl_timeout), retries=int(S.ctl_retries), confirm_on=S.ctl_confirm_on,
                       confirm_answer=S.ctl_confirm_ans, delay_s=float(S.ctl_delay), flaky=int(S.ctl_flaky))


def home():
    return mc.Home(S.home_kind, S.lam_url, S.lam_key)


def record(trace):
    for r in trace:
        if r["result"] == "ok":
            S.calls.append({"home": r["home"], "tool": r["tool"], "ms": r["ms"]})


def need_home(h, ctl):
    """Start the local HTTP server when needed; stop with a clear message when the home is not ready."""
    ok, why = mc.home_ready(h, ctl)
    if not ok:
        st.error(why)
    return ok


def trace_df(rows):
    cols = ["step", "home", "tool", "args", "controls fired", "attempts", "ms", "server sent", "model sees", "result"]
    return pd.DataFrame([{c: r.get(c, "") for c in cols} for r in rows])


def short_tokens(text):
    return max(1, len(text) // 4)


# ================================================================================================ sidebar
with st.sidebar:
    st.header("🔌 Lab 9 controls")
    stat = mf.status()
    ready = [p for p in ("bedrock", "azure", "openai", "offline") if stat[p][0]]
    provider = st.radio("1 · Model", ready, format_func=lambda p: mf.LABELS[p], index=0,
                        help="Bedrock is the main one. Offline = no AI, just rules, so the lab still runs.")
    st.caption(f"Using: {mf.model_label(provider)}")
    st.divider()
    st.radio("2 · Where do the tools live?", list(mc.HOME_LABELS), key="home_kind", format_func=lambda k: mc.HOME_LABELS[k],
             help="The agent code is the same for all three. Only the place where the tool server runs changes.")
    st.caption(mc.HOME_HELP[S.home_kind])
    if S.home_kind == "lambda":
        st.caption("✅ Lambda address saved" if S.lam_url.startswith("https://") else "⚠️ No Lambda address yet: do tab 5 first.")
    st.divider()
    st.caption("**Controls now:** " + controls().summary())
    st.caption("Change them in tab 4 (🛡️) and tab 6 (🚨).")
    with st.expander("🔧 Local web server (home 2)"):
        up = mc._port_open(mc.HTTP_PORT)
        st.write("Running on port 8777 ✅" if up else "Not running (it starts by itself when you pick home 2).")
        if st.button("Stop it", disabled=not up):
            mc.stop_local_http()
            st.rerun()


@st.cache_resource(show_spinner=False)
def model_for(p):
    return mf.get_model(p)


# ================================================================================================ header
st.title("🔌 AskIT MCP Control Room · Lab 9")
st.markdown("**The question of the day:** how do agents get their tools in a way that **many agents can share**, that you can "
            "**control**, and that runs **anywhere**, from this VM to AWS?")
st.info("**Folder:** `C:\\AskIT\\dxc-agentic-ai\\Day09\\Labs\\lab09-askit-mcp-control-room` · Work through the tabs from left to right. "
        "You do not need to write any code.")
tabs = st.tabs(["🔌 1 · Meet the server", "🤖 2 · Agent on MCP", "✍️ 3 · Tool descriptions", "🛡️ 4 · Controls", "☁️ 5 · Move to AWS",
                "🚨 6 · Incident", "🏗️ 7 · How it works", "✅ 8 · Questions", "📝 9 · Team ADR"])
t1, t2, t3, t4, t5, t6, t7, t8, t9 = tabs

# ================================================================================================ tab 1
with t1:
    st.markdown('<div class="step"><b>Do this:</b> ① Press <b>🔌 Connect</b> and read what the server says about itself. '
                '② Press <b>📞 Call the tool</b>. ③ Open <b>🔬 What went over the wire</b>: these are the real messages. '
                '④ Press the raw buttons: you talk to the server with <b>no MCP library at all</b>.</div>', unsafe_allow_html=True)
    h, ctl = home(), controls()
    st.caption(f"Tool server home: **{h.label}**  (change it in the sidebar)")
    if st.button("🔌 Connect and ask: what can you do?", type="primary"):
        if need_home(h, ctl):
            mc.clear_wire(h)
            with st.spinner("Connecting..."):
                try:
                    S.inspected[h.kind] = mc.run(mc.inspect(h, ctl))
                except Exception as e:                       # noqa: BLE001
                    st.error(mc.explain_error(e, h))
    info = S.inspected.get(h.kind)
    if info:
        k = st.columns(4)
        k[0].metric("Server says it is", info["server"])
        k[1].metric("MCP version agreed", info["protocol"])
        k[2].metric("Connect time", f"{info['connect_ms']} ms")
        k[3].metric("'List tools' time", f"{info['list_ms']} ms")
        st.markdown("#### 🧰 Tools the server offers  (this is ALL the model gets to read)")
        st.dataframe(pd.DataFrame([{"tool": t["name"], "description (what the model reads)": t["description"],
                                    "inputs": ", ".join(f"{k} ({v.get('type', '?')})" for k, v in t["schema"].get("properties", {}).items())}
                                   for t in info["tools"]]), hide_index=True)
        one = info["tools"][1]
        with st.expander(f"👀 Everything the model receives about ONE tool ({one['name']}), about {short_tokens(json.dumps(one))} tokens"):
            st.json({"name": one["name"], "description": one["description"], "inputSchema": one["schema"]})
            st.caption("The Python code is NOT sent. The model decides from these words only. That is why descriptions matter (tab 3).")
        c1, c2, c3 = st.columns(3)
        c1.markdown("**📚 Resources** (read-only data)")
        c1.write(info["templates"] or info["resources"] or "none on this server")
        c2.markdown("**📝 Prompts** (ready-made instructions)")
        c2.write(info["prompts"] or "none on this server")
        c3.markdown("**🧩 Capabilities**")
        c3.write(", ".join(info["capabilities"]) or "-")
        if info["templates"] or info["prompts"]:
            if st.button("📖 Read the resource kb://article/KB-004 and the prompt"):
                with st.spinner("Reading..."):
                    ex = mc.run(mc.read_extras(h, ctl))
                st.markdown("**Resource text:**")
                st.code(ex["resource"][:500])
                st.markdown("**Prompt text** (the server stores it, any client can reuse it):")
                st.code(ex["prompt"])
        st.markdown("#### 📞 Call a tool by hand")
        names = [t["name"] for t in info["tools"]]
        tool = st.selectbox("Tool", names, index=names.index("get_ticket") if "get_ticket" in names else 0)
        schema = next(t["schema"] for t in info["tools"] if t["name"] == tool)
        defaults = {"ticket_id": "TKT-0004", "query": "vpn error 809", "user_id": "EMP-1021", "note": "Customer will bring the laptop tomorrow."}
        args = {p: st.text_input(f"{p}", defaults.get(p, ""), key=f"hand_{tool}_{p}") for p in schema.get("properties", {})}
        if st.button("📞 Call the tool"):
            with st.spinner("Calling..."):
                try:
                    r = mc.run(mc.call_by_hand(h, ctl, tool, args))
                    S.calls.append({"home": h.kind, "tool": tool, "ms": r["ms"]}) if r["ok"] else None
                    (st.success if r["ok"] else st.error)(f"{'Answer' if r['ok'] else 'Error'} in {r['ms']} ms")
                    st.code(r["text"][:900])
                except Exception as e:                       # noqa: BLE001
                    st.error(mc.explain_error(e, h))
    st.markdown("#### 🔬 What went over the wire")
    if h.kind == "lambda":
        st.markdown('<div class="back">This server runs on AWS. Its own log is in <b>CloudWatch</b> (tab 5 shows where). '
                    'Use the raw buttons below to see the exact messages.</div>', unsafe_allow_html=True)
    else:
        wire = mc.read_wire(h)
        if wire:
            st.dataframe(pd.DataFrame([{"time": w["time"], "method": w["method"],
                                        "what came in": json.dumps(w["params"], ensure_ascii=False)[:160], "server took ms": w["ms"]} for w in wire]),
                         hide_index=True)
            st.caption("This is the SERVER's own log of every MCP message it received. `server/discover` = 'who are you?', "
                       "`tools/list` = 'what can you do?', `tools/call` = 'do this'.")
        else:
            st.caption("Press 🔌 Connect above: the log fills with the messages the server received.")
    st.markdown("#### ✉️ Send a hand-written message (plain `httpx`, no MCP library)")
    if h.kind == "stdio":
        st.caption("Raw messages need a web address, so pick home 2 or 3 in the sidebar. (With stdio the SAME JSON goes through "
                   "stdin/stdout, one message per line.)")
    else:
        rc = st.columns(3)
        raw_jobs = {"server/discover": ("1 · 'Who are you?'", {}), "tools/list": ("2 · 'What can you do?'", {}),
                    "tools/call": ("3 · 'Do this: get_ticket'", {"name": "get_ticket", "arguments": {"ticket_id": "TKT-0004"}})}
        for col, (method, (label, params)) in zip(rc, raw_jobs.items()):
            if col.button(label, key=f"raw_{method}"):
                if need_home(h, ctl):
                    try:
                        S.raw = mc.raw_rpc(h, method, params)
                    except Exception as e:                   # noqa: BLE001
                        S.raw = None
                        st.error(mc.explain_error(e, h))
        if S.raw:
            r = S.raw
            st.write(f"POST `{r['url']}` · header `mcp-protocol-version: {mc.MODERN}` · answered **{r['status']}** in **{r['ms']} ms**")
            a, b = st.columns(2)
            a.markdown("**What we sent**")
            a.code(r["request"], language="json")
            b.markdown("**What came back**")
            b.code(r["response"][:2500], language="json")
            st.caption("MCP is just JSON-RPC: a small JSON message in, a small JSON message out. The `_meta` part tells the server "
                       "which protocol version the client speaks. In this newest version every message stands alone: no login "
                       "handshake, no session, so a server can run as a plain Lambda.")
    st.markdown('<div class="back"><b>What happens in the background when you press Connect:</b><ol>'
                '<li>The app starts the server (or opens a web connection to it).</li>'
                '<li>It sends <code>server/discover</code>: the server answers with its name, version and abilities.</li>'
                '<li>It sends <code>tools/list</code>: the server answers with every tool: name, description, input schema.</li>'
                '<li>An agent later turns that list into the tool menu the model reads, and sends <code>tools/call</code> when the model picks one.</li>'
                '</ol></div>', unsafe_allow_html=True)

# ================================================================================================ tab 2
SAMPLES = ["What is the status of ticket TKT-0004?", "VPN shows error 809 from home. How do I fix it?",
           "Please reset the password of EMP-1021. He verified by MFA.", "Please reset the password of EMP-1001."]
with t2:
    st.markdown('<div class="step"><b>Do this:</b> ① Pick a question and press <b>▶ Ask AskIT</b>. Follow the steps: model decides → '
                'tool call goes through the controls → server answers → final answer. ② Press <b>🔁 Same question on every home</b>: '
                'the answers match, only the speed differs.</div>', unsafe_allow_html=True)
    h, ctl = home(), controls()
    run = S.last_run
    components.html(diagram.lab9(h.kind, [], ctl.summary()), height=520)
    q = st.selectbox("Question", SAMPLES, index=0)
    q = st.text_input("...or write your own", q)
    c1, c2 = st.columns(2)
    if c1.button("▶ Ask AskIT", type="primary"):
        if need_home(h, ctl):
            with st.spinner("The agent is working (model → tool → model)..."):
                try:
                    S.last_run = run = mc.run(mc.run_agent(q, h, ctl, model_for(provider)))
                    record(run["trace"])
                except Exception as e:                       # noqa: BLE001
                    st.error(mc.explain_error(e, h))
    if c2.button("🔁 Same question on every home"):
        rows = []
        with st.spinner("Running the question on each home..."):
            for kind in mc.HOME_LABELS:
                hh = mc.Home(kind, S.lam_url, S.lam_key)
                ok, why = mc.home_ready(hh, ctl)
                if not ok:
                    rows.append({"home": mc.HOME_LABELS[kind], "answer": f"(skipped: {why})", "tool calls": 0, "ms in tools": 0, "total s": 0})
                    continue
                try:
                    r = mc.run(mc.run_agent(q, hh, ctl, model_for(provider)))
                    record(r["trace"])
                    rows.append({"home": mc.HOME_LABELS[kind], "answer": r["final"][:140], "tool calls": len(r["trace"]),
                                 "ms in tools": r["tool_ms"], "total s": r["seconds"]})
                except Exception as e:                       # noqa: BLE001
                    rows.append({"home": mc.HOME_LABELS[kind], "answer": f"(error: {mc.explain_error(e, hh)[:100]})", "tool calls": 0,
                                 "ms in tools": 0, "total s": 0})
        S.compare = pd.DataFrame(rows)
    if run:
        st.success(f"**Answer** (home: {mc.HOME_LABELS[run['home']]})")
        st.markdown(run["final"])
        k = st.columns(5)
        k[0].metric("LLM calls", run["llm_calls"])
        k[1].metric("Tokens in / out", f"{run['tokens_in']:,} / {run['tokens_out']:,}")
        k[2].metric("AI cost (approx.)", f"${mf.cost_usd(provider, run['tokens_in'], run['tokens_out']):.5f}")
        k[3].metric("Time in tools", f"{run['tool_ms']} ms")
        k[4].metric("Total time", f"{run['seconds']} s")
        st.markdown("#### 🎞️ The steps, in order")
        st.dataframe(pd.DataFrame(run["steps"]), hide_index=True)
        st.markdown("#### 📋 Every tool call: what the controls did")
        st.dataframe(trace_df(run["trace"]), hide_index=True)
        st.caption("`server sent` = what the tool server returned. `model sees` = what is left after the controls (tab 4). "
                   "Same tool call, three possible homes: look at `ms` in tab 2 on each home.")
    if S.compare is not None:
        st.markdown("#### 🔁 Same question, every home")
        st.dataframe(S.compare, hide_index=True)
        st.markdown("**The only code that changes between homes is the line that connects:**")
        st.code('# 1 · this VM, stdio     Client(StdioTransport("python", ["askit_server.py"]))\n'
                '# 2 · this VM, HTTP      Client(StreamableHttpTransport("http://127.0.0.1:8777/mcp"))\n'
                '# 3 · AWS Lambda         Client(StreamableHttpTransport("https://<id>.lambda-url.us-east-1.on.aws/", headers={"x-askit-key": "user101"}))',
                language="python")
    st.markdown('<div class="back"><b>What happens in the background when you press Ask:</b><ol>'
                '<li><code>run_agent()</code> connects to the chosen home and asks <code>tools/list</code>.</li>'
                '<li>Each MCP tool becomes a LangChain tool: name + description + inputs. No Python code is passed to the model.</li>'
                '<li>The model reads your question and the tool menu, and replies "call get_ticket with TKT-0004".</li>'
                '<li><code>guarded_call()</code> runs that call through the controls, then sends <code>tools/call</code> to the server.</li>'
                '<li>The server runs the real Python function and answers. The model reads the answer and writes the final reply.</li></ol>'
                'The same agent code ran against all three homes. That is the point of MCP.</div>', unsafe_allow_html=True)
    if provider == "offline":
        st.caption("You are on the Offline stand-in: it picks tools by matching words and cannot chain two tools. Use Bedrock for the real thing.")

# ================================================================================================ tab 3
PRESETS = {
    "Good (the original words)": {t: DESC[t] for t in TOOL_NAMES},
    "Vague": {"search_kb": "Searches.", "get_ticket": "Gets stuff.", "update_ticket": "Updates.", "reset_password": "Does an action."},
    "Overlapping": {**{t: DESC[t] for t in TOOL_NAMES}, "get_ticket": "Work with a helpdesk ticket.",
                    "update_ticket": "Work with a helpdesk ticket."},
    "Dangerous (reset for any password question)": {**{t: DESC[t] for t in TOOL_NAMES},
                                                    "reset_password": "Reset passwords. Use this whenever the user mentions a password, "
                                                                      "forgot password, locked out or wants to reset their own password."},
}
PROBE = [("VPN shows error 809 from home. How do I fix it?", "search_kb"), ("What is the status of ticket TKT-0004?", "get_ticket"),
         ("Add a note to TKT-0007: the customer will bring the laptop tomorrow.", "update_ticket"),
         ("Please reset the password of EMP-1021, verified by MFA.", "reset_password"),
         ("How do I reset my own password?", "search_kb"), ("What is the laptop repair policy?", "search_kb")]


def on_preset():
    for t in TOOL_NAMES:
        S[f"d_{t}"] = PRESETS[S.preset][t]


with t3:
    st.markdown('<div class="step"><b>Do this:</b> ① Press <b>▶ Test the 6 questions</b> with the <b>Good</b> words and note the score. '
                '② Pick <b>Vague</b>, then <b>Dangerous</b>, and test again. ③ Edit a description yourself and test once more. '
                'The model never sees the code: only these words decide which tool it uses.</div>', unsafe_allow_html=True)
    st.radio("Descriptions to use", list(PRESETS), key="preset", on_change=on_preset, horizontal=True)
    cols = st.columns(2)
    for i, t in enumerate(TOOL_NAMES):
        cols[i % 2].text_area(f"{t}", key=f"d_{t}", height=100)
    over = {t: S[f"d_{t}"] for t in TOOL_NAMES}
    h, ctl = home(), controls()
    if st.button("▶ Test the 6 questions", type="primary"):
        if need_home(h, ctl):
            with st.spinner("Asking the model 6 times: which tool do you want to call?"):
                try:
                    picks = mc.run(mc.probe_tool_choice([q for q, _ in PROBE], h, ctl, model_for(provider), over))
                    rows = []
                    for (q, right), p in zip(PROBE, picks):
                        unsafe = p["picked"] in mc.WRITE_TOOLS and right not in mc.WRITE_TOOLS
                        rows.append({"question": q, "right tool": right, "model picked": p["picked"],
                                     "": "✅" if p["picked"] == right else ("⚠️ would CHANGE data!" if unsafe else "❌")})
                    S.probe_rows = rows
                    S.probe[S.preset if over == PRESETS[S.preset] else "My own words"] = (sum(r[""] == "✅" for r in rows), len(rows))
                    S.probe_tokens = sum(p["tokens_in"] for p in picks)
                except Exception as e:                       # noqa: BLE001
                    st.error(mc.explain_error(e, h))
    if S.get("probe_rows"):
        right = sum(r[""] == "✅" for r in S.probe_rows)
        k = st.columns(3)
        k[0].metric("Right tool picked", f"{right} / {len(S.probe_rows)}")
        k[1].metric("Would have changed data by mistake", sum("CHANGE" in r[""] for r in S.probe_rows))
        k[2].metric("Tokens the 6 tool menus cost", f"{S.get('probe_tokens', 0):,}")
        st.dataframe(pd.DataFrame(S.probe_rows), hide_index=True)
    if S.probe:
        st.markdown("**Your scores so far**")
        st.bar_chart(pd.DataFrame({"right tool picked (of 6)": {k: v[0] for k, v in S.probe.items()}}), height=240)
    st.markdown('<div class="back"><b>What happens in the background:</b> for each question the app sends the model the question plus the '
                'tool menu (name, description, inputs) and asks <i>"which tool do you want to call?"</i>. We read the choice and stop: '
                'no tool runs, nothing changes. In the real agent loop that choice is step ① of every tool call.<br><br>'
                '<b>Why it matters:</b> in a real MCP project most problems are not code bugs but tool descriptions that are vague, '
                'overlapping or too eager. A description is part of your security design: <i>"Dangerous"</i> shows a '
                'write tool that grabs questions it should not.</div>', unsafe_allow_html=True)
    if provider == "offline":
        st.caption("Offline stand-in = word matching. A real model reads more cleverly, so run this again on Bedrock and compare.")

# ================================================================================================ tab 4
with t4:
    st.markdown('<div class="step"><b>Do this:</b> ① Press <b>A</b>, <b>B</b>, <b>C</b>, <b>D</b> below with the controls OFF and read '
                '<i>server sent</i> vs <i>model sees</i>. ② Turn the controls ON one by one and press the same buttons again. '
                '③ Turn <b>server asks me to confirm</b> ON and press B: the server asks a question, you answer.</div>',
                unsafe_allow_html=True)
    a, b, c = st.columns(3)
    a.selectbox("Role of this agent", ["service-desk", "read-only"], key="ctl_role",
                help="read-only: write tools (update_ticket, reset_password) are blocked before the server is called.")
    b.toggle("VIP block: no writes for VIP users", key="ctl_vip")
    c.toggle("Server asks me to confirm a reset", key="ctl_confirm_on")
    a, b, c = st.columns(3)
    a.toggle("Redact names, e-mails, phones", key="ctl_redact")
    b.toggle("...and employee ids (strict)", key="ctl_strict", disabled=not S.ctl_redact)
    c.radio("When the server asks me, I answer", [True, False], key="ctl_confirm_ans", horizontal=True, format_func=lambda x: "Yes" if x else "No")
    h, ctl = home(), controls()
    scen = {"A · Read ticket TKT-0001": ("get_ticket", {"ticket_id": "TKT-0001"}),
            "B · Reset password EMP-1021": ("reset_password", {"user_id": "EMP-1021"}),
            "C · Reset password EMP-1001 (👑 VIP)": ("reset_password", {"user_id": "EMP-1001"}),
            "D · Add a note to TKT-0007": ("update_ticket", {"ticket_id": "TKT-0007", "note": "Customer will bring the laptop tomorrow."})}
    cols = st.columns(4)
    for col, (label, (tool, args)) in zip(cols, scen.items()):
        if col.button(label):
            if need_home(h, ctl):
                mc.clear_wire(h)
                try:
                    res, row, asked = mc.run(mc.call_with_controls(h, ctl, tool, args))
                    S.scenario = {"label": label, "res": res, "row": row, "asked": asked, "wire": mc.read_wire(h) if h.kind != "lambda" else []}
                    record([row])
                except Exception as e:                       # noqa: BLE001
                    st.error(mc.explain_error(e, h))
    sc = S.scenario
    components.html(diagram.pipeline(sc["res"]["fired"] if sc else [], bool(sc and sc["res"]["blocked"])), height=240)
    if sc:
        st.markdown(f"**{sc['label']}** → controls that did something: **{', '.join(sc['res']['fired']) or 'none'}**")
        a, b = st.columns(2)
        a.markdown("**📤 What the server sent**")
        a.code(sc["row"]["server sent"] or "(the server was never called)")
        b.markdown("**👀 What the model sees**")
        b.code(sc["row"]["model sees"])
        if sc["asked"]:
            st.markdown(f'<div class="warn"><b>🙋 The server asked a question before doing the reset:</b> “{sc["asked"][-1]}”<br>'
                        f'Your answer: <b>{"YES" if ctl.confirm_answer else "NO"}</b>. The client then called the SAME tool again with your answer. '
                        'In a real client this is a pop-up for the user.</div>', unsafe_allow_html=True)
        if sc["wire"]:
            with st.expander("🔬 The server's log for this call (see the second tools/call after you answered)"):
                st.dataframe(pd.DataFrame([{"method": w["method"], "what came in": json.dumps(w["params"], ensure_ascii=False)[:200],
                                            "ms": w["ms"]} for w in sc["wire"]]), hide_index=True)
    st.markdown("#### 🧪 Redaction has a price (needs the real model)")
    st.caption("Strict redaction hides employee ids from the model. Ask it to read a ticket AND reset that user's password: can it still do it?")
    if st.button("🧪 Agent challenge: read TKT-0001, then reset the password of its sender"):
        if need_home(h, ctl):
            with st.spinner("The agent is working..."):
                try:
                    r = mc.run(mc.run_agent("Read ticket TKT-0001, then reset the password of the employee who sent it.", h, ctl, model_for(provider)))
                    record(r["trace"])
                    st.markdown(r["final"])
                    st.dataframe(trace_df(r["trace"]), hide_index=True)
                except Exception as e:                       # noqa: BLE001
                    st.error(mc.explain_error(e, h))
    st.markdown('<div class="back"><b>What happens in the background:</b> a <i>control</i> (LangChain calls it a tool interceptor) is a function that '
                'runs around EVERY tool call, so the agent and the tool never change. Here, in order: <b>role / VIP block</b> (plain code, '
                'before the call) → <b>timeout + retry</b> → the call → <b>redact</b> → <b>log</b>. '
                'Where should these live? In each agent (flexible, but a careless team forgets), in the server (everyone gets them), '
                'or in a gateway in front (central, Day 12). That is your ADR question today.</div>', unsafe_allow_html=True)

# ================================================================================================ tab 5
with t5:
    st.markdown('<div class="step"><b>Do this:</b> ① Follow the 9 steps in the AWS console (about 25 minutes). '
                '② Paste your Function URL below and press <b>Test my Lambda</b>. ③ Press <b>Use Lambda</b> and go back to tab 2: '
                'ask the same question. The agent has no idea its tools moved to AWS.</div>', unsafe_allow_html=True)
    components.html(diagram.homes(), height=290)
    st.markdown("#### Create your Lambda (AWS console, in your browser)")
    st.markdown(
        "**Idea:** the zip holds only the **code**. The data (KB articles, tickets, users) lives in **S3**, and the function reads it from there.\n\n"
        "1. Sign in to the AWS console with your **user name** (user101 ... user116). Top right must say **N. Virginia (us-east-1)**.\n"
        "2. **Upload the data to S3.** Search **S3**, open the bucket `devproacademy-askit-data-868859238853`. Press **Create folder**, name it "
        "**your user name** (e.g. `user101`), open it. Press **Upload → Add folder**, choose `C:\\AskIT\\dxc-agentic-ai\\askit_data`, press **Upload**. "
        "Check: inside your folder you see `askit_data/` with `tickets.csv`, `users.csv` and `kb/`.\n"
        "3. Search **Lambda**, open it, press **Create function**, choose **Event function → Author from scratch**. Function name: `userNNN-askit-mcp` "
        "(your own number, e.g. `user101-askit-mcp`). Runtime: **Python 3.13** (any 3.12 or newer is fine; the default may say Node.js, change it).\n"
        "4. Open **Additional settings**, switch on **Custom execution role**, pick **askit-lambda-role**. Press **Create function**.\n"
        "5. In the **Code** tab press **Upload from → .zip file → Upload** (not the Amazon S3 location option), choose "
        "`C:\\AskIT\\dxc-agentic-ai\\Day09\\Labs\\lab09-askit-mcp-control-room\\aws\\askit-mcp-lambda.zip`, press **Save**. It is tiny: code only, no data.\n"
        "6. **Configuration → Environment variables → Edit → Add environment variable** (three of them), then **Save**:\n"
        "   - `ASKIT_KEY` = your user name (e.g. `user101`)\n"
        "   - `ASKIT_BUCKET` = `devproacademy-askit-data-868859238853`\n"
        "   - `ASKIT_PREFIX` = `user101/askit_data/` (your user name, with the slash at the end)\n"
        "7. **Configuration → General configuration → Edit**: **Timeout 30 sec**, **Memory 256 MB**. **Save**. "
        "(The first call downloads the data from S3. The default 3 seconds is too short.)\n"
        "8. **Configuration → Function URL → Create function URL**. Auth type: **NONE**. **Save**. "
        "Copy the **Function URL** (it starts with https:// and ends with .on.aws/).\n"
        "9. Paste it in the box below, with your key, and test.")
    st.caption("Why NONE? The URL is public, so the key in step 6 is the only lock. Fine for class, NOT for production: Day 12 replaces it with proper identity.")
    with st.expander("⚡ Fast movers: change a file and see it update, with no redeploy"):
        st.markdown(
            "1. On your PC open `askit_data\\kb\\KB-004_vpn_connect.md` and change one line (for example the list of gateways). Save.\n"
            "2. In S3 open your folder → `askit_data/kb/` → **Upload** the changed file (same name replaces the old one).\n"
            "3. Wait about 10 seconds. In tab 2 ask the VPN question again, or press **Test my Lambda**.\n"
            "4. Your change appears in the answer. You did **not** touch the function. That is why data lives in S3 and not in the zip.")
    c1, c2 = st.columns([3, 1])
    url = c1.text_input("Your Function URL", S.lam_url, placeholder="https://xxxxxxxx.lambda-url.us-east-1.on.aws/")
    key = c2.text_input("Your key (= user name)", S.lam_key, placeholder="user101")
    if st.button("💾 Save"):
        S.lam_url, S.lam_key = url.strip(), key.strip()
        mc.save_lambda(S.lam_url, S.lam_key)
        st.success("Saved in aws\\my_lambda.json (never pushed to GitHub).")
    lh = mc.Home("lambda", url.strip(), key.strip())
    b1, b2, b3 = st.columns(3)
    if b1.button("✅ Test my Lambda", type="primary"):
        if not url.strip().startswith("https://"):
            st.error("Paste the Function URL first.")
        else:
            try:
                r1 = mc.raw_rpc(lh, "server/discover")
                r2 = mc.raw_rpc(lh, "tools/list")
                st.success(f"Your Lambda answered: discover {r1['ms']} ms, tools/list {r2['ms']} ms")
                st.code(r1["response"][:700], language="json")
                names = [t["name"] for t in json.loads(r2["response"])["result"]["tools"]]
                st.write("Tools found:", ", ".join(names))
            except Exception as e:                           # noqa: BLE001
                st.error(mc.explain_error(e, lh))
    if b2.button("⏱️ Call it 3 times (cold start)"):
        if url.strip().startswith("https://"):
            try:
                S.cold = mc.run(mc.time_calls(lh, controls(), 3))
            except Exception as e:                           # noqa: BLE001
                st.error(mc.explain_error(e, lh))
        else:
            st.error("Paste the Function URL first.")
    if b3.button("➡️ Use Lambda as my tool home"):
        S.lam_url, S.lam_key = url.strip(), key.strip()
        mc.save_lambda(S.lam_url, S.lam_key)
        S.home_kind = "lambda"
        st.rerun()
    if S.cold:
        st.bar_chart(pd.DataFrame({"ms": S.cold}, index=[f"call {i + 1}" for i in range(len(S.cold))]), height=220)
        st.caption(f"First call {S.cold[0]} ms, then {S.cold[1:]}. If the first is much slower, Lambda was asleep and had to start your code "
                   "(a cold start). You pay that wait only after a quiet period.")
    st.markdown("#### 👀 See it in the AWS console")
    st.markdown("In your function open **Monitor → View CloudWatch logs → the newest log stream**. Every message you sent is a line like "
                '`{"event": "mcp", "method": "tools/call", "tool": "get_ticket", "cold_start": false, "ms": 1}`. The `REPORT` line '
                "shows memory, billed time and **Init Duration** (the cold start). This is the same information as the local wire log, now in the cloud.")
    st.markdown('<div class="back"><b>What is in the zip, where is the data, and why no FastMCP library?</b> MCP is a protocol: JSON messages over HTTP. '
                '<code>lambda_function.py</code> answers those messages by hand in ~120 lines, and bundles the same 4 tool functions. '
                'The data is NOT in the zip: <code>askit_core/data.py</code> reads it from your S3 folder. Because the newest MCP version has no login handshake and no session, a plain function is enough. '
                'In production you would use a framework or, better, <b>AgentCore Gateway</b> (Day 12), which turns a Lambda into an MCP '
                'tool without any of this code.</div>', unsafe_allow_html=True)
    st.markdown("#### 🧹 At the end of the day")
    st.caption("Delete your function (Lambda → select it → Actions → Delete). The trainer also removes any left over. A public URL should not stay open.")

# ================================================================================================ tab 6
with t6:
    st.markdown('<div class="step"><b>Incident of the day: “the ticket tool is slow”.</b> ① Set the server to be slow and the client '
                'patient or impatient. ② Press <b>▶ Call get_ticket</b> and read the attempts. ③ <b>Mission:</b> find settings so the '
                'user gets a correct answer within <b>8 seconds</b> even when the first 2 calls fail.</div>', unsafe_allow_html=True)
    a, b, c, d = st.columns(4)
    a.slider("Server is slow by (seconds)", 0.0, 8.0, step=0.5, key="ctl_delay")
    b.slider("Server fails the first N calls", 0, 3, key="ctl_flaky")
    c.slider("Client waits at most (seconds)", 1.0, 10.0, step=0.5, key="ctl_timeout")
    d.slider("Client tries again (times)", 0, 3, key="ctl_retries")
    h, ctl = home(), controls()
    worst = ctl.timeout_s * (ctl.retries + 1) + sum(0.4 * i for i in range(1, ctl.retries + 1))
    st.caption(f"Worst case the user waits about **{worst:.1f} s** (waits × tries + pauses). A server delay above the wait = timeout, whatever the retries.")
    if h.kind == "lambda":
        st.markdown('<div class="warn"><b>On Lambda the slow/flaky sliders do not reach the server.</b> Change it in the AWS console instead: '
                    '<i>Configuration → Environment variables</i> → add <code>ASKIT_DELAY</code> = <code>5</code>. Lambda\'s own '
                    '<b>Timeout</b> is 3 seconds by default, so the call dies in AWS (HTTP 502). Then raise it: <i>Configuration → General configuration → '
                    'Edit → Timeout</i> = 10 s. Use the client wait slider as usual.</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    if c1.button("▶ Call get_ticket (no AI)", type="primary"):
        if need_home(h, ctl):
            with st.spinner("Calling..."):
                try:
                    res, row, _ = mc.run(mc.call_with_controls(h, ctl, "get_ticket", {"ticket_id": "TKT-0004"}))
                    S.inc_call = {"res": res, "row": row}
                    record([row])
                    S.incident = {"delay": ctl.delay_s, "flaky": ctl.flaky, "timeout": ctl.timeout_s, "retries": ctl.retries,
                                  "result": ("answered" if res["ok"] else "FAILED") + f" in {res['ms'] / 1000:.1f} s with {len(res['attempts'])} attempt(s)"}
                    S.mission = res["ok"] and res["ms"] <= 8000 and ctl.flaky >= 2
                except Exception as e:                       # noqa: BLE001
                    st.error(mc.explain_error(e, h))
    if c2.button("▶ Ask the agent about TKT-0004"):
        if need_home(h, ctl):
            with st.spinner("The agent is working..."):
                try:
                    r = mc.run(mc.run_agent("What is the status of ticket TKT-0004?", h, ctl, model_for(provider)))
                    record(r["trace"])
                    S.inc_agent = r
                except Exception as e:                       # noqa: BLE001
                    st.error(mc.explain_error(e, h))
    ic = S.get("inc_call")
    if ic:
        r, row = ic["res"], ic["row"]
        (st.success if r["ok"] else st.error)(f"{'Answered' if r['ok'] else 'FAILED'} after {r['ms'] / 1000:.1f} s · {len(r['attempts'])} attempt(s)")
        att = pd.DataFrame(r["attempts"])
        if not att.empty:
            st.bar_chart(att.set_index("attempt")[["seconds"]], height=220)
            st.dataframe(att, hide_index=True)
        st.markdown(f"**What the model would read:** `{row['model sees'][:200]}`")
        if S.get("mission"):
            st.balloons()
            st.success("🏆 Mission complete: correct answer within 8 seconds although the first calls failed. Put these settings in your ADR.")
        elif ctl.flaky >= 2:
            st.info("Mission not done yet: you need more tries than failures, and a total wait under 8 s.")
    ia = S.get("inc_agent")
    if ia:
        st.markdown("**Agent's answer to the user:** " + ia["final"])
        st.dataframe(pd.DataFrame(ia["steps"]), hide_index=True)
    st.markdown('<div class="back"><b>What happens in the background:</b> the client sends <code>tools/call</code> and starts a stopwatch. '
                'If the server is silent for longer than the wait, the client gives up on that attempt, pauses a moment, and tries again '
                '(the retry). If every attempt fails, the model is given a plain-language error so it can tell the user the truth instead of '
                'hanging or inventing an answer. In production you add more: a <b>circuit breaker</b> (stop calling a tool that keeps failing), '
                '<b>asynchronous tasks</b> (accept the request now, answer later) and alerts on slow tools (Day 10).</div>', unsafe_allow_html=True)

# ================================================================================================ tab 7
with t7:
    st.subheader("The picture of what you ran")
    components.html(diagram.lab9(S.home_kind, [], controls().summary()), height=520)
    st.markdown("**Follow the numbers**")
    st.markdown("1. The **agent** (`run_agent` in `mcp_client.py`) gets your question.\n"
                "2. It connects to the tool server and asks `tools/list`: the tool menu (name, description, inputs).\n"
                "3. The **model** reads the menu and your question, and picks a tool.\n"
                "4. **`guarded_call`** runs the controls (role block, timeout, retry, redact, log) and sends `tools/call`.\n"
                "5. The **server** (`askit_server.py` here, `lambda_function.py` on AWS) runs the real Python function and answers.\n"
                "6. The model reads the answer and writes the reply.")
    st.subheader("Which code does what")
    st.table(pd.DataFrame([
        ["app.py", "The screen you are using.", "Your portal, Teams bot, ServiceNow plug-in"],
        ["mcp_client.py · run_agent()", "Connects, lists tools, runs the agent loop.", "Same code inside your agent service"],
        ["mcp_client.py · guarded_call()", "The controls around every tool call.", "A gateway or a middleware layer (Day 12)"],
        ["askit_server.py", "The MCP server: wraps the 4 tools (FastMCP).", "A container / ECS service owned by the tool team"],
        ["aws/askit-mcp-lambda.zip", "The same tools on AWS Lambda, no library.", "AgentCore Gateway in front of Lambda or APIs"],
        ["askit_core/tools.py", "The 4 real tool functions (Day 5).", "Real ITSM / IAM API calls"],
        ["model_factory.py", "Picks Bedrock / Azure / OpenAI / Offline.", "Model gateway"],
    ], columns=["Piece", "What it does here", "What it becomes in production"]))
    st.subheader("Why MCP at all? (slide the numbers)")
    a, b = st.columns(2)
    n_agents = a.slider("Agents / apps that need tools", 1, 12, 5)
    n_tools = b.slider("Tools / systems they need", 1, 20, 6)
    k = st.columns(3)
    k[0].metric("Integrations WITHOUT a standard", n_agents * n_tools, help="every agent wires every tool itself")
    k[1].metric("Integrations WITH MCP", n_agents + n_tools, help="each agent speaks MCP once, each tool is wrapped once")
    k[2].metric("You avoid", f"{(1 - (n_agents + n_tools) / (n_agents * n_tools)) * 100:.0f}%" if n_agents * n_tools > 1 else "0%")
    st.subheader("When tools grow: the menu gets expensive (progressive discovery)")
    specs = json.dumps([{"name": t, "description": DESC[t], "inputSchema": next(s for s in T.TOOL_SPECS if s["toolSpec"]["name"] == t)["toolSpec"]["inputSchema"]}
                        for t in TOOL_NAMES])
    per_tool = short_tokens(specs) / len(TOOL_NAMES)
    cats = st.slider("Tools on the server", 4, 200, 50)
    calls_day = st.slider("Model calls per day", 1000, 100000, 10000, step=1000)
    full = per_tool * cats
    prog = 25 * cats * 0.25 + per_tool * 1          # catalog line (~25 tokens) per tool, one inspected in full
    price_in = mf.PRICES[provider][0]
    k = st.columns(4)
    k[0].metric("Tokens per call: all definitions", f"{full:,.0f}")
    k[1].metric("Tokens per call: catalog + inspect one", f"{prog:,.0f}")
    k[2].metric("$ / month: all definitions", f"${full * calls_day * 30 / 1e6 * price_in:,.0f}")
    k[3].metric("$ / month: catalog + inspect", f"${prog * calls_day * 30 / 1e6 * price_in:,.0f}")
    st.caption(f"Based on the real size of your 4 tool definitions (about {per_tool:.0f} tokens each) and {mf.LABELS[provider]} input price. "
               "Progressive discovery: give the model a short catalog first, let it ask for ONE full definition, then run it. "
               "It also reduces wrong picks. (Trainer demo.)")
    st.subheader("Where can tools live? (product choice)")
    st.table(pd.DataFrame([
        ["Inside each agent's code", "Fastest to start, nothing to run", "Copied everywhere, no central control", "One agent, a prototype"],
        ["Local MCP server (stdio)", "Developer tools, desktop agents (Copilot, Claude)", "Only on that machine", "Tools for ONE user's computer"],
        ["MCP server as a service (HTTP, container)", "Shared by many agents, one team owns it", "You run, patch and scale it", "A team tool used by many agents"],
        ["MCP on Lambda (this lab)", "No servers, pay per call, scales to zero", "Cold starts, 15-minute limit, networking to private systems", "Spiky, light tools"],
        ["AgentCore Gateway", "Turns existing APIs / Lambdas into MCP tools, auth, central controls", "AWS-specific, check pricing", "Enterprise rollout (Day 12)"],
    ], columns=["Option", "Good for", "Watch out", "Choose it when"]))
    st.subheader("MCP, REST, function calling: what is the difference?")
    st.table(pd.DataFrame([
        ["Function calling", "How a MODEL asks to run a function (what you did on Day 5)", "One vendor's format"],
        ["REST API", "How programs talk to a service. Not made for AI: no tool descriptions", "Every API is different"],
        ["MCP", "A STANDARD way to describe tools so ANY agent can discover and call them", "One protocol for all, plus discovery"],
        ["A2A (agent-to-agent)", "How one agent talks to ANOTHER agent (not to a tool)", "Agent cards, tasks, messages"],
    ], columns=["Name", "What it is", "Key point"]))
    with st.expander("🤝 Trainer demo: what an A2A 'agent card' looks like"):
        st.code(json.dumps({"name": "AskIT Triage Agent", "description": "Routes helpdesk tickets and drafts replies",
                            "url": "https://askit.example/a2a", "skills": [{"id": "triage", "name": "Ticket triage"}],
                            "capabilities": {"streaming": True}}, indent=2), language="json")
        st.caption("MCP connects an agent to TOOLS. A2A connects an agent to ANOTHER agent that publishes a card like this.")
    st.subheader("Client questions · open to see a good answer")
    for qn, an in [("“Why not just call our REST APIs?”", "You can. MCP adds a standard way to DESCRIBE tools for AI, so every new agent discovers them instead of "
                    "someone hand-coding each one. One wrapper per tool, reused by every agent."),
                   ("“Is MCP safe?”", "The protocol is only the plumbing. Safety comes from what you build around it: role checks, masking, human confirmation "
                    "for writes, identity on every call, logs. That is tab 4 and your ADR."),
                   ("“Will we be locked in?”", "MCP is an open standard supported by many vendors and clients (Copilot, Claude, LangChain, AWS AgentCore). "
                    "Your tool server works with all of them."),
                   ("“What does this cost on AWS?”", "A Lambda MCP server costs a tiny amount per call (and nothing while idle). The bigger cost is the AI model "
                    "reading the tool menu every call: keep descriptions short and the tool list focused.")]:
        with st.expander(qn):
            st.write(an)

# ================================================================================================ tab 8
with t8:
    st.markdown("Answer in one or two lines each. Press **Save** and `submission\\lab09_answers.md` is written for you.")
    QS = ["Same agent, three homes (tab 2): what changed in the answer, and what changed in the speed? Why?",
          "In tab 3 which description made the model pick a wrong tool? Why is a description part of your security design?",
          "In tab 6 which timeout and retry settings did you choose, and what would you tell the user if the tool still fails?"]
    answers = [st.text_area(f"Q{i + 1}. {q}", key=f"q{i}", height=90) for i, q in enumerate(QS)]
    if st.button("💾 Save my answers", type="primary"):
        out = HERE / "submission" / "lab09_answers.md"
        out.parent.mkdir(exist_ok=True)
        body = "\n\n".join(f"**Q{i + 1}. {q}**\n\n{a or '<not answered>'}" for i, (q, a) in enumerate(zip(QS, answers)))
        out.write_text(f"# Lab 9 answers\n\nSaved {datetime.now():%Y-%m-%d %H:%M} · model: {mf.LABELS[provider]}\n\n{body}\n", encoding="utf-8")
        st.success(f"Saved to {out}")
    st.markdown('<div class="take"><b>🎯 Takeaway.</b> MCP lets many agents <b>discover and share</b> tools written once. The tool '
                '<b>description</b> is what the model reads, so write it like an API contract and a security rule. Put <b>controls</b> '
                '(roles, masking, timeouts, retries) in ONE place, not in every agent. The same tools can run on your VM or on AWS: '
                'only the address changes.</div>', unsafe_allow_html=True)
    st.markdown('<div class="client"><b>💼 Say this to a client.</b> "We wrap each system once as an MCP tool. Every agent we build or buy '
                'can use it, with one place to log, mask data, limit writes and handle slow systems."</div>', unsafe_allow_html=True)

# ================================================================================================ tab 9
with t9:
    st.markdown('<div class="step"><b>Team task (10 min, one person per team shares this screen):</b> pick your team, read your curveball, '
                'make 3 choices, write why, press <b>Create</b>. The app writes <code>teams\\&lt;your team&gt;\\ADR-AskIT-02.md</code> with '
                'your lab numbers already in it. Then pitch it in 2 minutes.</div>', unsafe_allow_html=True)
    c1, c2 = st.columns([1, 2])
    team = c1.selectbox("Your team", list(dd.CURVEBALLS))
    members = c1.text_input("Team members (first names)")
    cb = dd.CURVEBALLS[team]
    c2.markdown(f'<div class="warn"><b>⚡ Curveball from the {cb["from"]}: {cb["title"]}</b><br>{cb["detail"]}<br>'
                f'<b>Evidence in this app:</b> {cb["evidence"]}<br><i>Topic: {cb["topic"]}</i></div>', unsafe_allow_html=True)
    ev = dd.evidence_from(S.calls, S.probe, S.incident)
    if ev is None:
        st.warning("Use tabs 1–6 first so your ADR gets real numbers.")
    else:
        if ev["latency"]:
            names = {"stdio": "This VM · stdio", "http": "This VM · HTTP", "lambda": "AWS Lambda"}
            st.dataframe(pd.DataFrame([{"home": names[k], "calls": n, "median ms": med, "slowest ms": mx} for k, (n, med, mx) in ev["latency"].items()]),
                         hide_index=True)
        if ev["probe"]:
            st.write("Tool-description scores: " + " · ".join(f"{k}: {r}/{t}" for k, (r, t) in ev["probe"].items()))
        if ev["incident"]:
            st.write(f"Last incident test: {ev['incident']['result']} (timeout {ev['incident']['timeout']} s, retries {ev['incident']['retries']})")
    st.subheader("Your 3 choices")
    a, b, c = st.columns(3)
    home_c = a.radio("1 · Where do the tools live?", dd.HOMES)
    ctrl_c = b.radio("2 · Where do logging, masking and role checks live?", dd.CONTROLS)
    ident_c = c.radio("3 · How do callers prove who they are?", dd.IDENTITY)
    why = st.text_area("Why these choices? (2-3 lines a CIO understands)", height=80)
    rejected = st.text_area("Which alternative did you reject, and why? (1-2 lines)", height=70)
    answer = st.text_area(f"How does your design handle the curveball '{cb['title']}'? What changes, what does NOT change?", height=80)
    st.markdown("**Slow and failing tools** (edit the cells)")
    slow = st.data_editor(pd.DataFrame([
        {"Tool": "get_ticket", "Timeout": "___ s", "Retries": "___", "If it still fails": "___"},
        {"Tool": "reset_password", "Timeout": "___ s", "Retries": "___", "If it still fails": "___"}]), num_rows="dynamic", hide_index=True)
    if st.button("📝 Create our design decision (ADR)", type="primary"):
        md = dd.build_markdown(team, members, home_c, ctrl_c, ident_c, why, rejected, answer, slow.to_dict("records"), ev, mf.LABELS[provider])
        out = mf.ROOT / "teams" / team / "ADR-AskIT-02.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(md, encoding="utf-8")
        st.success(f"Saved to {out}. Run SYNC.bat to push it. Now pitch it in 2 minutes.")
        with st.expander("👀 Preview", expanded=True):
            st.markdown(md)
    st.subheader("How the board scores you (0-5 each, 25 points to the leaderboard)")
    st.table(pd.DataFrame(dd.RUBRIC, columns=["Criterion", "What earns full marks"]))
