"""Lab 15 · AskIT Gateway Check  (Streamlit screen).   Start it with:  python run.py

You create a real AgentCore Gateway in the AWS console (steps are in the session page and README.md).
This screen then checks it: what tools does it list, can you call one, and does the SAME agent give the SAME answer through it?
No code to edit. Files: gw_client.py (talks to the Gateway) · gw_agent.py (the agent) · tools_core.py (the 3 tools)
"""
import json
import os
import time
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

import model_factory as mf  # noqa: I001  (must load first: it reads the course .env)
import gw_agent
import gw_client as gc
import tools_core

HERE = Path(__file__).resolve().parent
st.set_page_config(page_title="Lab 15 · AskIT Gateway Check", page_icon="🚪", layout="wide", initial_sidebar_state="expanded")
st.markdown("""<style>
html, body, [class*="css"] {font-size:18px;}
.take{background:rgba(106,63,160,.14);border-left:6px solid #6A3FA0;padding:14px 18px;border-radius:10px;margin:8px 0}
.client{background:rgba(14,112,104,.14);border-left:6px solid #0E7068;padding:14px 18px;border-radius:10px;margin:8px 0}
.lesson{background:linear-gradient(135deg,rgba(245,166,35,.28),rgba(245,166,35,.10));border:3px solid #E08A00;padding:16px 20px;border-radius:14px;margin:14px 0}
.lock{background:rgba(127,127,127,.10);border:2px dashed rgba(127,127,127,.5);padding:12px 16px;border-radius:12px;margin:10px 0;opacity:.85}
.door{border:2px solid rgba(127,127,127,.4);border-radius:14px;padding:12px 16px;margin:6px 0}
.ans{background:rgba(127,127,127,.10);border-radius:10px;padding:10px 14px;margin:6px 0}
div[data-baseweb="tab-list"] button:last-child{background:rgba(245,166,35,.28);border-radius:10px 10px 0 0;font-weight:700}
</style>""", unsafe_allow_html=True)

S = st.session_state
for k, v in {"mode": "practice", "url": gc.load_saved(), "tools": [], "think": {}, "lessons": {}, "last_call": None, "doors": None}.items():
    S.setdefault(k, v)

QUESTIONS = ["Summarise ticket TKT-0004 and tell me the next step.", "Who is employee EMP-1001 and are they a VIP?",
             "Please reset the password for EMP-1002. They are locked out.", "Please reset the password for EMP-1001. They are locked out."]
TICKETS = ["TKT-0004", "TKT-0010", "TKT-0033", "TKT-9999 (does not exist)"]
USERS = ["EMP-1001 (VIP)", "EMP-1002", "EMP-1011", "EMP-9999 (does not exist)"]


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


def gateway():
    return gc.make_gateway(S.mode, S.url)


def discover():
    r = gateway().rpc("tools/list")
    if r.ok:
        S.tools = gc.tools_of(r)
    return r


def specs_from(tools):
    return [{"name": t["name"], "alias": t["name"].split("___")[-1], "description": t.get("description", ""),
             "schema": t.get("inputSchema") or {"type": "object", "properties": {}}} for t in tools]


def provider_now():
    return S.get("prov") or mf.auto_provider()


# ================================================================================================ sidebar
with st.sidebar:
    st.header("🚪 Lab 15")
    st.markdown("**1 · AI model**")
    stt = mf.status()
    names = [p for p in ("bedrock", "azure", "openai", "offline") if stt[p][0]]
    S.prov = st.selectbox("Model", names, index=names.index(mf.auto_provider()), format_func=lambda p: mf.LABELS[p], label_visibility="collapsed")
    st.caption(mf.model_label(S.prov))
    st.markdown("**2 · Which Gateway?**")
    st.caption("Practice = works with no AWS. My Gateway = the one you create in the console.")
    st.markdown(f"Now using: **{gateway().label}**")
    if S.tools:
        st.success(f"{len(S.tools)} tools discovered")

def start_here():
    """The 'Start here' tab: one place of reference for the whole lab."""
    st.markdown("""<style>.mc{border:1px solid rgba(127,127,127,.4);border-radius:12px;padding:12px 16px;height:100%}</style>""", unsafe_allow_html=True)
    st.markdown("### 🏁 Your mission (about 50 minutes, no code to write)")
    c1, c2, c3 = st.columns(3)
    c1.markdown('<div class="mc"><b>The problem</b><br>Companies have many agents and many tools. If every agent is wired to every tool, there is no one place for sign-in, logging or rules, and every change touches every agent.</div>', unsafe_allow_html=True)
    c2.markdown('<div class="mc"><b>What we do</b><br>Put the ticket tools (a small Lambda) <b>behind an AgentCore Gateway</b>. The Gateway shows them as MCP tools at one address. The agent asks "what tools do you have?" and then "run this one".</div>', unsafe_allow_html=True)
    c3.markdown('<div class="mc"><b>You leave able to</b><br>Create a Gateway, see tool discovery and a tool call, and explain why a Gateway beats direct calls.</div>', unsafe_allow_html=True)

    st.markdown("### Part A · Create your Gateway in the AWS console (about 20 minutes)")
    st.markdown("""Region must say **N. Virginia (us-east-1)**. Console names can differ slightly: follow the idea, not the exact word.

| Step | What you do | What you will see |
|---|---|---|
| 1 | Sign in with **your AWS user** from the trainer | Top right shows your user name and N. Virginia |
| 2 | Search **Bedrock AgentCore** → **Gateways** → **Create gateway** | The create form |
| 3 | **Name** `askit-gw-user1xx` (your user number). **Inbound auth: IAM** | |
| 4 | **Service role**: use an existing role → `askit-gateway-role` | The role is in the list |
| 5 | Create it and wait for status **Ready** | A green Ready badge |
| 6 | Open your Gateway → **Targets** → **Add target**. Target protocol **MCP target**. Name **`askit-lambda`**. Target type **Lambda ARN**. Paste the **ARN** the trainer gives you. Tool schema **inline**: paste the whole of `tool_schema.json` (in this folder) | The target is listed under Targets |
| 7 | Copy the **Gateway MCP URL** (it ends with `/mcp`) | Keep it for Part B |

Console warnings about `logs:` permissions can be ignored. Console stuck? Skip to Part B and choose **Practice gateway**: the lesson is the same.""")

    st.markdown("### Part B · Use it from this app (about 30 minutes)")
    st.markdown("""| Tab | What you do | What you will see | What you learn |
|---|---|---|---|
| **1 · Connect** | Choose **Practice gateway** or **My AWS gateway**, paste your MCP URL, press **Connect** | "Connected" and how many milliseconds the Gateway took | Your agent talks to one address, and every request is signed with your AWS keys |
| **2 · Discover** | Look at the tools list | 3 tools named like `askit-lambda___get_ticket` | The agent **discovers** tools. Nobody wired them in |
| **3 · Call a tool** | Call `get_ticket` with `TKT-0004`, then with an id that does not exist | A ticket, then an error with a plain-English hint | Errors come back in a standard shape the agent can read |
| **4 · Two doors** | Press **Run both doors** | The same agent and question answered twice: tools inside the program (Door 1) vs through the Gateway (Door 2) | Same answer. The tool moved to a door a platform team can control |
| **5 · How it works** | Read the diagram | In and out authentication, the products | Where this sits in AWS |
| **🎓 Lessons** | Answer the two thinking questions at the bottom of tabs 2, 3 and 4 | A lesson unlocks for each | Your own summary |""")
    st.markdown("""**Words you will meet**

| Word | Plain meaning |
|---|---|
| **MCP** | A common language between an agent and its tools. Two questions: *what can you do?* (`tools/list`) and *please do this* (`tools/call`) |
| **Gateway** | An AWS service in front of your tools. It shows them as one MCP address, checks who is calling and logs each call |
| **Target** | One tool source behind the Gateway. Ours is the Lambda `askit-lambda` |
| **Tool schema** | The menu of tools and their inputs. It is how the Gateway knows what the Lambda can do |
| **Inbound auth (IAM)** | Who may knock. Every request is signed with your AWS keys |
| **Service role** | The permission the Gateway uses to call the Lambda for you |
| **`___` in a tool name** | The Gateway writes `target name` + `___` + `tool name`, so two targets can never clash |""")
    st.markdown('<div class="client"><b>💼 Say this to a client:</b> "We keep the business logic where it is and put one governed door in front of it. Agents discover the tools; your platform team controls who may use them."</div>', unsafe_allow_html=True)

    st.markdown("**If something goes wrong**")
    st.markdown("""| Problem | Fix |
|---|---|
| 403 / AccessDenied | Your user lacks permission or the region is wrong. Check **us-east-1**. Tell the trainer: *403 on Gateway* |
| 404 | The address is not the Gateway MCP URL. Copy it again (it ends with `/mcp`) |
| "Tool not found" | The target name must be exactly `askit-lambda` |
| "Unsupported protocol version" | The app tries several versions by itself. If it still fails, tell the trainer |
| Anything else | Choose **Practice gateway** and carry on |

**Never put AWS keys in files, GitHub, wikis or chat.** Keys live only in the course `.env` file. **Keep your Gateway:** Session 12 uses it again.""")


_all = st.tabs(["🏁 Start here", "🔌 1 · Connect", "🔍 2 · Discover", "📞 3 · Call a tool", "🤖 4 · Two doors", "🧩 5 · How it works", "🎓 Lessons learnt"])
tabs = _all[1:]
with _all[0]:
    start_here()


# ================================================================================================ TAB 1
with tabs[0]:
    st.subheader("Connect to a Gateway")
    st.markdown("A **Gateway** is a door in front of your tools. First we check that the door opens.")
    choice = st.radio("Which Gateway do you want to use?", ["Practice gateway (no AWS: use this first, or if you are stuck)", "My Gateway on AWS (the one I created in the console)"],
                      index=0 if S.mode == "practice" else 1)
    S.mode = "practice" if choice.startswith("Practice") else "aws"
    if S.mode == "aws":
        url = st.text_input("Paste your Gateway URL (it ends with /mcp)", value=S.url, placeholder="https://askit-gw-user116-xxxx.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp")
        c1, c2 = st.columns(2)
        if c1.button("💾 Save this address"):
            S.url = url.strip()
            gc.save_url(S.url)
            st.success("Saved in this lab folder (never pushed to GitHub).")
        S.url = url.strip()
    if st.button("▶ Test the connection", type="primary"):
        if S.mode == "aws" and not S.url.startswith("https://"):
            st.error("Paste your Gateway URL first. It starts with https:// .")
        else:
            with st.spinner("Asking the Gateway…"):
                r = discover()
            if r.ok:
                st.success(f"✅ Connected. The Gateway answered in {r.ms} ms and lists {len(S.tools)} tools. Go to tab 2.")
            else:
                st.error("❌ " + r.error)
                with st.expander("Checklist if it does not work", expanded=True):
                    st.markdown("1. The URL ends with **/mcp** and was copied from the Gateway page in the console.\n"
                                "2. The Gateway was created with **IAM** as inbound authorization.\n"
                                "3. Your AWS keys are in the course `.env` file (the same keys as Bedrock).\n"
                                "4. Ask the trainer to check your permission. Write: **403 on Gateway**.\n\n"
                                "Stuck for more than 3 minutes? Choose the **Practice gateway** above and keep going: tabs 2 to 4 work the same way.")
    if S.mode == "aws":
        if st.button("Who am I? (shows the AWS user your keys belong to)"):
            try:
                import boto3
                st.code(boto3.client("sts", region_name="us-east-1").get_caller_identity()["Arn"])
            except Exception as e:   # noqa: BLE001
                st.error(f"Could not read your AWS identity: {e}")
    st.markdown('<div class="take"><b>Why a practice gateway?</b> It answers exactly like the real one, so nobody is blocked by a console typo. '
                'Do the real one as well: the point of the lab is to see YOUR gateway work.</div>', unsafe_allow_html=True)

# ================================================================================================ TAB 2
with tabs[1]:
    st.subheader("What tools does the Gateway offer?")
    st.markdown("The agent does not have the tools typed into it. It **asks the Gateway** and reads the answer.")
    if st.button("🔍 Ask: what tools do you have?", type="primary"):
        r = discover()
        S.last_call = ("tools/list", r)
    lc = S.last_call
    if S.tools:
        st.dataframe(pd.DataFrame([{"Full name (what the Gateway calls it)": t["name"], "Short name (what the model sees)": t["name"].split("___")[-1],
                                    "What it does (the model reads this)": t.get("description", ""),
                                    "Inputs": ", ".join((t.get("inputSchema") or {}).get("properties", {}).keys())} for t in S.tools]), hide_index=True, width="stretch")
        st.markdown('<div class="take"><b>Look at the full name.</b> The Gateway adds your <i>target name</i> and three underscores in front: '
                    '<code>askit-lambda___get_ticket</code>. That keeps two targets with the same tool name apart.</div>', unsafe_allow_html=True)
    if lc and lc[0] == "tools/list":
        with st.expander("What was sent and what came back (JSON, for the curious)"):
            st.json(lc[1].request)
            st.json(lc[1].response if lc[1].response is not None else {"error": lc[1].error})
        if not lc[1].ok:
            st.error("❌ " + lc[1].error)
    thinking("t2", [
        ("How did the agent learn that a tool called get_ticket exists?",
         {"a": "We typed its name into the agent.", "b": "It asked the Gateway (tools/list) and got a self-description.", "c": "It guessed from the name."}, "b",
         "The Gateway lists its tools with their descriptions and inputs. The agent never hard-codes them."),
        ("A colleague adds a fourth tool to the Gateway in the console. What must you change in the agent?",
         {"a": "Rewrite the agent.", "b": "Nothing. Ask again and the new tool appears.", "c": "Retrain the model."}, "b",
         "Tools are managed at the Gateway. Every agent that asks gets the new list.")],
        "<b>A Gateway makes tools self-describing.</b> The agent asks what exists and reads the descriptions. Adding or changing a tool happens once, at the Gateway, not inside every agent. "
        "The description is what the model reads, so write it like documentation.")

# ================================================================================================ TAB 3
with tabs[2]:
    st.subheader("Call one tool yourself")
    if not S.tools:
        st.info("First press **🔍 Ask: what tools do you have?** in tab 2.")
    else:
        tool = st.selectbox("Pick a tool", [t["name"] for t in S.tools], format_func=lambda n: n.split("___")[-1])
        short = tool.split("___")[-1]
        if short == "get_ticket":
            val = st.selectbox("Ticket", TICKETS).split(" ")[0]
            args = {"ticket_id": val}
        else:
            val = st.selectbox("Employee", USERS).split(" ")[0]
            args = {"user_id": val}
        c1, c2 = st.columns(2)
        if c1.button("📞 Call it", type="primary"):
            S.last_call = ("call", gateway().rpc("tools/call", {"name": tool, "arguments": args}))
        if c2.button("🚫 Call a tool that does not exist"):
            S.last_call = ("call", gateway().rpc("tools/call", {"name": "askit-lambda___delete_everything", "arguments": {}}))
        lc = S.last_call
        if lc and lc[0] == "call":
            r = lc[1]
            st.markdown(f"**Time:** {r.ms} ms  ·  **Gateway said:** {'OK' if r.ok else 'error'}")
            if r.ok:
                st.json(gc.call_text(r))
            else:
                st.error(r.error)
            with st.expander("What was sent and what came back (JSON)"):
                st.json(r.request)
                st.json(r.response if r.response is not None else {"error": r.error})
    thinking("t3", [
        ("You asked for TKT-9999, which does not exist. What did you see?",
         {"a": "The Gateway crashed.", "b": "A normal reply containing an error message that the model can read.", "c": "Nothing at all."}, "b",
         "A tool error is just a result. The agent can read it and explain it to the user."),
        ("The same call takes ~150 ms on the practice gateway and several hundred on AWS. Where does the extra time go?",
         {"a": "The AI model.", "b": "The trip over the network, signing, and starting the Lambda.", "c": "The ticket data."}, "b",
         "Every call crosses the internet, is signed with your AWS identity, and may wake a sleeping Lambda (a cold start).")],
        "<b>A tool call through a Gateway is a normal web request:</b> signed with your AWS identity, answered in JSON. Errors come back as readable replies, so the agent can explain them. "
        "The price of central control is one network hop on every call.")

# ================================================================================================ TAB 4
with tabs[3]:
    st.subheader("The same agent, through two doors")
    st.markdown("**Door 1** = tools inside your own program (like Days 5 to 9). **Door 2** = tools reached through the Gateway. Same model, same question.")
    q = st.selectbox("Question", QUESTIONS)
    if st.button("▶ Run both doors", type="primary"):
        with st.spinner("Running Door 1 and Door 2…"):
            if not S.tools:
                discover()
            local = tools_core.make(gc._data())

            def door1(name, args):
                t0 = time.time()
                short = name.split("___")[-1]
                try:
                    return local[short](**args), int((time.time() - t0) * 1000)
                except Exception as e:   # noqa: BLE001
                    return {"error": str(e)}, 0

            gw = gateway()

            def door2(name, args):
                r = gw.rpc("tools/call", {"name": name, "arguments": args})
                return gc.call_text(r), r.ms

            prefix_specs = specs_from(S.tools) if S.tools else specs_from(gc.PracticeGateway().rpc("tools/list").data["result"]["tools"])
            local_specs = [dict(s, name=s["alias"]) for s in prefix_specs]
            S.doors = {"q": q, "d1": gw_agent.run(q, S.prov, local_specs, door1), "d2": gw_agent.run(q, S.prov, prefix_specs, door2), "label": gw.label}
    d = S.doors
    if d:
        st.caption(f"Question: {d['q']}  ·  Door 2 = {d['label']}")
        c1, c2 = st.columns(2)
        for col, key, title in ((c1, "d1", "🚪 Door 1 · tools inside the program"), (c2, "d2", "🚪 Door 2 · tools through the Gateway")):
            with col:
                r = d[key]
                st.markdown(f'<div class="door"><b>{title}</b></div>', unsafe_allow_html=True)
                st.markdown(f'<div class="ans">{r["answer"]}</div>', unsafe_allow_html=True)
                st.caption(f"Time {r['ms'] / 1000:.1f} s · tokens {r['tokens_in']}/{r['tokens_out']} · cost ${r['cost_usd']:.6f}")
                st.dataframe(pd.DataFrame([{"Step": s["label"], "ms": s["ms"], "Result": s["out"]} for s in r["steps"]]), hide_index=True, width="stretch")
        if "reset the password for EMP-1001" in d["q"]:
            st.warning("EMP-1001 is a VIP. Both doors reset the password, because no rule exists yet. The Gateway is the right place to add one: that is tomorrow's lab (a Cedar policy).")
    thinking("t4", [
        ("Both doors gave the same answer. What is different?",
         {"a": "The AI model.", "b": "Where the tool lives and who controls it.", "c": "Nothing."}, "b",
         "The agent and the model are the same. The tool moved from inside your program to a shared door that a platform team can control."),
        ("You asked to reset the password of a VIP (EMP-1001) and it worked through the Gateway. Which statement is true?",
         {"a": "The Gateway already blocks VIPs.", "b": "No rule exists yet, and the Gateway is the place to add one.", "c": "The model always blocks VIPs."}, "b",
         "A Gateway does not add rules by itself. It gives you ONE place to add them. Tomorrow: a policy that denies VIP resets.")],
        "<b>Putting a tool behind a Gateway does not change the answer.</b> It changes who owns the tool and where you can add rules, logging and limits. "
        "One door for many agents is how a platform team keeps control. Tomorrow we put a policy on this door.")

# ================================================================================================ TAB 5
with tabs[4]:
    st.subheader("How it works")
    svg = """<div style="font-family:Segoe UI,Arial,sans-serif"><svg viewBox="0 0 1100 270" width="100%" style="background:#fff;border-radius:12px">
    <defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5L0 10z" fill="#555"/></marker></defs>
    <g stroke-width="2.2"><rect x="10" y="50" width="230" height="130" rx="14" fill="#E2EBF7" stroke="#1F5AA6"/><rect x="300" y="50" width="250" height="130" rx="14" fill="#EEE6F7" stroke="#6A3FA0"/>
    <rect x="610" y="50" width="230" height="130" rx="14" fill="#FBEEDB" stroke="#A8570A"/><rect x="900" y="50" width="190" height="130" rx="14" fill="#E3F1EE" stroke="#0E7068"/></g>
    <g text-anchor="middle" fill="#161a23" font-size="17"><text x="125" y="85" font-weight="700" font-size="19">🤖 The agent</text><text x="125" y="112">this app (gw_agent.py)</text><text x="125" y="134">asks, then calls</text>
    <text x="425" y="85" font-weight="700" font-size="19">🚪 AgentCore Gateway</text><text x="425" y="112">checks who you are (IAM)</text><text x="425" y="134">lists the tools · routes the call</text><text x="425" y="156" fill="#6A3FA0">YOU create this in the console</text>
    <text x="725" y="85" font-weight="700" font-size="19">⚙️ Lambda</text><text x="725" y="112">askit-get-ticket</text><text x="725" y="134">plain function, no MCP code</text><text x="725" y="156" fill="#A8570A">trainer deployed it</text>
    <text x="995" y="85" font-weight="700" font-size="19">🗂️ Data</text><text x="995" y="112">tickets, users</text><text x="995" y="134">(inside the Lambda)</text></g>
    <g stroke="#555" stroke-width="2.2" fill="none" marker-end="url(#a)"><line x1="242" y1="100" x2="298" y2="100"/><line x1="552" y1="100" x2="608" y2="100"/><line x1="842" y1="100" x2="898" y2="100"/></g>
    <g text-anchor="middle" fill="#555" font-size="14"><text x="270" y="92">① signed</text><text x="270" y="206" text-anchor="middle"> </text><text x="580" y="92">② invoke</text><text x="870" y="92">③ read</text></g>
    <text x="10" y="225" font-size="15" fill="#555">① POST /mcp  tools/list or tools/call, signed with your AWS keys (SigV4)   ② the Gateway's service role calls the Lambda   ③ the Lambda reads its data</text>
    <text x="10" y="248" font-size="15" fill="#555">Two kinds of "who": INBOUND = who may call the Gateway (IAM, your keys)  ·  OUTBOUND = how the Gateway calls the tool (a service role)</text></svg></div>"""
    if hasattr(st, "iframe"):
        st.iframe(svg, height=320)
    else:
        components.html(svg, height=320)
    st.markdown("### Ways to give an agent a tool")
    st.dataframe(pd.DataFrame([
        ["Own MCP server (Day 9)", "You write and host the server", "Full control, simple for ONE tool set", "You run, secure, scale and patch it"],
        ["Gateway + Lambda (today)", "A plain Lambda becomes an MCP tool", "Existing functions, many agents, central control", "Cold starts, a new AWS service to learn"],
        ["Gateway + existing REST API", "Describe the API (OpenAPI) and the Gateway exposes it", "Hundreds of APIs you already own", "A good API description is needed; auth to the API"],
        ["Gateway + existing MCP server", "The Gateway fronts a server someone else runs", "Vendor MCP servers, one front door", "Another hop; check what auth the server supports"],
        ["Other gateways (Kong, Azure API Management, open-source MCP gateways)", "Same idea outside AWS", "Multi-cloud or already standardised", "Check MCP support level and who operates it"]],
        columns=["Option", "What it is", "Good for", "Watch out"]), hide_index=True, width="stretch")
    with st.expander("💼 Questions a client asks · tap to see a good answer"):
        st.markdown("- **\"Why not call the Lambda directly?\"** You can. A Gateway adds one sign-in, one tool list, logging and rules for every agent, and speaks MCP so any agent framework can use it.\n"
                    "- **\"Who is allowed to call it?\"** Inbound auth: IAM (your AWS identity) or OAuth/JWT from your company login. We used IAM today.\n"
                    "- **\"What does it cost?\"** You pay per use of the Gateway plus the Lambda. Check the AWS price page for the current rates before you quote.\n"
                    "- **\"Can we put limits on what an agent may do?\"** Yes, with policies on the Gateway. That is tomorrow.")
    st.markdown('<div class="client"><b>💼 Say this to a client:</b> "We keep the business logic where it is and put one governed door in front of it. Agents discover the tools; your platform team controls who may use them."</div>', unsafe_allow_html=True)

# ================================================================================================ LESSONS
with tabs[5]:
    names = {"t2": "2 · Discover", "t3": "3 · Call a tool", "t4": "4 · Two doors"}
    st.subheader("🎓 Lessons learnt")
    st.caption("Each lesson unlocks when you answer the two thinking questions at the bottom of its tab.")
    st.progress(len(S.lessons) / len(names), text=f"Lessons unlocked: {len(S.lessons)} of {len(names)}")
    for k, nm in names.items():
        if k in S.lessons:
            st.markdown(f'<div class="lesson"><b>🎓 Tab {nm}</b><br>{S.lessons[k]}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="lock">🔒 Tab {nm}: not unlocked yet</div>', unsafe_allow_html=True)
    if S.lessons:
        import re
        txt = "# My lessons from Lab 15\n\n" + "\n\n".join(f"## Tab {names[k]}\n" + re.sub(r"<[^>]+>", "", S.lessons[k]) for k in names if k in S.lessons)
        st.download_button("⬇ Download my lessons (.md)", txt, file_name="lab15_lessons.md")
