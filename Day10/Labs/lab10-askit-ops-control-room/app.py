"""Lab 10 · AskIT Ops Control Room  (Streamlit screen).   Start it with:  python run.py

You do not need to edit any code. Run, trace, find failures, count the cost, test, then see the same calls in AWS.
Files: ops_agent.py (the traced agent) · ops_trace.py (the recorder) · evals.py (the exam) · mystery.py (4 recorded failures)
       prices.py (model prices) · model_factory.py (the model choice) · diagram.py (pictures)
"""
import json
import os
import re
import time
import statistics
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

import model_factory as mf  # noqa: I001  (must load first: it reads the course .env)
import diagram
import design_decision as dd
import evals as ev
import mystery
import ops_agent as oa
import ops_trace as ot
import prices as P
from askit_core.data import load_tickets

HERE = Path(__file__).resolve().parent
st.set_page_config(page_title="Lab 10 · AskIT Ops Control Room", page_icon="🔭", layout="wide", initial_sidebar_state="expanded")
st.markdown("""<style>
html, body, [class*="css"] {font-size:18px;}
.take{background:rgba(106,63,160,.14);border-left:6px solid #6A3FA0;padding:14px 18px;border-radius:10px;margin:8px 0}
.client{background:rgba(14,112,104,.14);border-left:6px solid #0E7068;padding:14px 18px;border-radius:10px;margin:8px 0}
.step{background:rgba(127,127,127,.12);border:1px solid rgba(127,127,127,.35);padding:10px 14px;border-radius:10px;margin:6px 0}
.back{background:rgba(31,90,166,.10);border-left:6px solid #1F5AA6;padding:12px 16px;border-radius:10px;margin:8px 0}
.warn{background:rgba(183,121,31,.16);border:2px solid #B7791F;padding:14px 18px;border-radius:12px;margin:8px 0}
.ans{background:rgba(127,127,127,.10);border-radius:10px;padding:10px 14px;margin:6px 0}
.lesson{background:linear-gradient(135deg,rgba(245,166,35,.28),rgba(245,166,35,.10));border:3px solid #E08A00;padding:16px 20px;border-radius:14px;margin:14px 0}
.lesson b.h{font-size:1.15em}
.lock{background:rgba(127,127,127,.10);border:2px dashed rgba(127,127,127,.5);padding:12px 16px;border-radius:12px;margin:10px 0;opacity:.85}
.cwlf{background:rgba(31,90,166,.10);border:2px solid #1F5AA6;padding:14px 18px;border-radius:12px;margin:10px 0}
.big{font-size:1.15em;line-height:1.9;margin:10px 0}
.stepbig{background:rgba(127,127,127,.10);border-left:8px solid #0E7068;padding:16px 20px;border-radius:12px;margin:26px 0 10px 0;font-size:1.1em}
div[data-baseweb="tab-list"] button:last-child{background:rgba(245,166,35,.28);border-radius:10px 10px 0 0;font-weight:700}
</style>""", unsafe_allow_html=True)

S = st.session_state
for k, v in {"last": None, "traces": [], "myst_ok": {}, "myst_checked": {}, "batches": [], "eval_runs": ev.load_runs(), "retr": None,
             "extra_cases": [], "quiz": {}, "lf_on": True, "think": {}, "lessons": {}}.items():
    S.setdefault(k, v)

QUESTIONS = ["My VPN shows error 809 - what should I try?", "Summarise ticket TKT-0004 and tell me the next step.",
             "What is the first response time for a High priority ticket?", "Please reset the password for EMP-1002. They are locked out.",
             "Please reset the password for EMP-1001. They are locked out before a board meeting.", "What is Orbit Corp's parental leave policy?"]


# ================================================================================================ helpers
@st.cache_resource(show_spinner=False)
def model_for(p):
    return mf.get_model(p)


@st.cache_resource(show_spinner=False)
def lf_for(pk, sk, host):
    return ot.langfuse_client()


def lf_now():
    return lf_for(os.getenv("LANGFUSE_PUBLIC_KEY", ""), os.getenv("LANGFUSE_SECRET_KEY", ""), os.getenv("LANGFUSE_HOST", "")) if S.lf_on else None


def save_keys(block, host_choice):
    """Find the two keys in what was pasted (with or without the NAME= part) and write them to this lab's own .env file."""
    pk, sk = re.search(r"pk-lf-[\w-]+", block), re.search(r"sk-lf-[\w-]+", block)
    if not (pk and sk):
        return False, "I need both keys: one starting pk-lf- and one starting sk-lf-. Copy them again from Langfuse."
    hm = re.search(r"LANGFUSE_HOST\s*=\s*(\S+)", block)
    vals = {"LANGFUSE_PUBLIC_KEY": pk.group(0), "LANGFUSE_SECRET_KEY": sk.group(0), "LANGFUSE_HOST": hm.group(1) if hm else host_choice}
    env = HERE / ".env"
    old = [ln for ln in (env.read_text(encoding="utf-8").splitlines() if env.is_file() else []) if not ln.startswith("LANGFUSE_")]
    env.write_text("\n".join(old + [f"{k}={v}" for k, v in vals.items()]) + "\n", encoding="utf-8")
    for k, v in vals.items():
        os.environ[k] = v
    lf_for.clear()
    return True, "Saved to the .env file inside this lab folder (it is never pushed to GitHub). Only runs you do from now on are sent."


def flags_text(f):
    on = [k for k, v in f.items() if v]
    return ", ".join(f"{k}={f[k]}" if k == "slow" else k for k in on) or "none"


def do_run(question, provider, prompt_name, flags, tags=None, model=None, lf="main"):
    """lf/model are passed in by the batch code, because background threads cannot read st.session_state."""
    lf = lf_now() if lf == "main" else lf
    model = model or model_for(provider)
    tr = ot.Tracer("askit-run", model=mf.model_id(provider), provider=provider, price_key=mf.price_key(provider), lf=lf,
                   tags={"prompt": prompt_name, "flags": flags_text(flags), **(tags or {})})
    try:
        oa.run_agent(question, model, provider, tr, system_prompt=oa.PROMPTS[prompt_name], flags=flags)
    except Exception as e:                                              # noqa: BLE001
        tr.trace["status"] = "error"
        tr.trace["answer"] = f"(error) {type(e).__name__}: {str(e)[:200]}"
    ot.save(tr.trace)
    return tr.trace


def show_html(html, h, scale=1.35):
    """Show an SVG picture. The picture grows with the window width, so the frame is made taller (scale) to avoid a scroll bar inside it."""
    h = int(h * scale)
    if hasattr(st, "iframe"):
        st.iframe(html, height=h)
    else:
        components.html(html, height=h, scrolling=False)


def show_waterfall(trace):
    html, h = diagram.waterfall(trace)
    show_html(html, h)


def metrics(trace, explain=False):
    c = st.columns(6)
    c[0].metric("Time", f"{trace.get('ms', 0) / 1000:.1f} s")
    c[1].metric("Model calls", trace.get("llm_calls", 0))
    c[2].metric("Tool calls", trace.get("tool_calls", 0))
    c[3].metric("Tokens in", f"{trace.get('tokens_in', 0):,}")
    c[4].metric("Tokens out", f"{trace.get('tokens_out', 0):,}")
    c[5].metric("Cost", f"${trace.get('cost_usd', 0):.6f}")
    if explain:
        st.caption("**Time** = question to final answer · **Model calls** = how many times the AI was asked · **Tool calls** = lookups it ran · "
                   "**Tokens in** = everything the model READ on every call (instructions + history + tool results) · **Tokens out** = what it WROTE · "
                   "**Cost** = in × price + out × price. On AWS Bedrock these are AWS's real counts; on Offline they are estimates.")


def pct(vals, p):
    vals = sorted(vals)
    return vals[min(len(vals) - 1, max(0, round(p / 100 * (len(vals) - 1))))] if vals else 0


def lesson_box(text):
    st.markdown(f'<div class="lesson"><b class="h">🎓 Lesson learnt</b><br>{text}</div>', unsafe_allow_html=True)


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


CW_VS_LF = ('<div class="cwlf"><b>⭐ The most important difference</b><br>'
            '<b>CloudWatch sees the model calls only</b> (who called, which model, how many tokens).<br>'
            '<b>Langfuse sees the whole agent run</b> (model calls + tool calls + the order + the answer).<br>'
            'CloudWatch answers <i>"who spent the money?"</i>. Langfuse answers <i>"why was this answer wrong?"</i>. You need both.</div>')


def aws_user():
    try:
        import boto3
        arn = boto3.client("sts", region_name=os.getenv("AWS_REGION", "us-east-1")).get_caller_identity()["Arn"]
        return arn, arn.split("/")[-1]
    except Exception as e:                                              # noqa: BLE001
        return "", f"({type(e).__name__})"


def cw_fetch(user, group, minutes=120, limit=20):
    import boto3
    logs = boto3.client("logs", region_name=os.getenv("AWS_REGION", "us-east-1"))
    q = ("fields @timestamp, modelId, operation, input.inputTokenCount as tokens_in, output.outputTokenCount as tokens_out "
         f"| filter identity.arn like /{user}/ | sort @timestamp desc | limit {limit}")
    now = int(time.time())
    qid = logs.start_query(logGroupName=group, startTime=now - minutes * 60, endTime=now, queryString=q)["queryId"]
    for _ in range(40):
        r = logs.get_query_results(queryId=qid)
        if r["status"] in ("Complete", "Failed", "Cancelled"):
            return [{f["field"]: f["value"] for f in row if f["field"] != "@ptr"} for row in r.get("results", [])], r["status"]
        time.sleep(1)
    return [], "Timeout"


# ================================================================================================ sidebar
with st.sidebar:
    st.header("🔭 Lab 10 controls")
    stat = mf.status()
    ready = [p for p in ("bedrock", "azure", "openai", "offline") if stat[p][0]]
    provider = st.radio("1 · Model", ready, format_func=lambda p: mf.LABELS[p], index=0,
                        help="Bedrock is the main one. Offline = no AI, just rules, so the lab still runs.")
    st.caption(f"Using: {mf.model_label(provider)}")
    st.caption(f"Price row for cost: **{P.MODELS[mf.price_key(provider)]['label']}**")
    st.divider()
    st.subheader("2 · Langfuse (your team)")
    have = bool(os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"))
    if have:
        st.checkbox("Send every run to Langfuse", key="lf_on")
        if st.button("Test the connection"):
            st.info(ot.langfuse_check(lf_for(os.getenv("LANGFUSE_PUBLIC_KEY", ""), os.getenv("LANGFUSE_SECRET_KEY", ""), os.getenv("LANGFUSE_HOST", "")))[1])
        st.caption("Only runs you do AFTER connecting are sent. Run your question again.")
    with st.expander("Enter the team keys" if not have else "Change the team keys", expanded=not have):
        st.caption("Langfuse gives you two keys: a **public** key (starts pk-lf-) and a **secret** key (starts sk-lf-). Paste both, one per line, then choose the region.")
        block = st.text_area("Paste the 2 keys", height=90, label_visibility="collapsed", placeholder="pk-lf-...\nsk-lf-...")
        host_choice = st.selectbox("Region of your Langfuse project", ["https://cloud.langfuse.com", "https://us.cloud.langfuse.com"],
                                   format_func=lambda h: "EU (cloud.langfuse.com)" if h == "https://cloud.langfuse.com" else "US (us.cloud.langfuse.com)")
        if st.button("Save the keys"):
            ok, msg = save_keys(block, host_choice)
            (st.success if ok else st.error)(msg)
            if ok:
                st.rerun()
    st.divider()
    st.caption(f"Runs saved in this lab so far: **{len(ot.load_all())}**  (file: submission/traces.jsonl)")

# ================================================================================================ header
st.title("🔭 AskIT Ops Control Room · Lab 10")
st.markdown("**The question of the day:** AskIT works in a demo. In production, can you **see** what it does, **afford** it, and **prove** it works? "
            "Most failures of AI agents do not crash anything.")
st.info("**Folder:** `C:\\AskIT\\dxc-agentic-ai\\Day10\\Labs\\lab10-askit-ops-control-room` · Work through the tabs from left to right. "
        "You do not need to write any code.")
with st.expander("🧭 Which mode do I run each tab in? (Offline first, then AWS Bedrock)"):
    st.dataframe(pd.DataFrame([
        {"tab": "1 · Run and trace", "Offline stand-in (no AI, no AWS)": "✅ Learn the waterfall and the switches", "AWS Bedrock (real model)": "✅ Repeat: real tokens, real times. Tab 1 numbers = CloudWatch numbers", "Langfuse keys": "A link to the trace appears"},
        {"tab": "2 · Find the failure", "Offline stand-in (no AI, no AWS)": "✅ Recorded traces, same for everyone", "AWS Bedrock (real model)": "Not needed", "Langfuse keys": "Not needed"},
        {"tab": "3 · Cost report", "Offline stand-in (no AI, no AWS)": "✅ Shape of the cost (estimated tokens)", "AWS Bedrock (real model)": "✅ Repeat: real cost per ticket", "Langfuse keys": "Runs are sent"},
        {"tab": "4 · Evals", "Offline stand-in (no AI, no AWS)": "✅ Mechanics: v1 → v2 → v3", "AWS Bedrock (real model)": "✅ Repeat: a real model may ignore a rule. Compare", "Langfuse keys": "Scores are sent"},
        {"tab": "5 · See it in AWS", "Offline stand-in (no AI, no AWS)": "❌ Nothing to see: no AWS call was made", "AWS Bedrock (real model)": "✅ Required: run tab 1 on Bedrock first", "Langfuse keys": "Not needed"},
        {"tab": "6 · 7 · 8", "Offline stand-in (no AI, no AWS)": "✅ Any mode", "AWS Bedrock (real model)": "Any mode", "Langfuse keys": "Not needed"}]), hide_index=True)
    st.caption("Plan: do tabs 1–4 Offline first (fast, free, same for everyone). Then switch to AWS Bedrock in the sidebar and repeat tabs 1, 3 and 4, then do tab 5.")
tabs = st.tabs(["🔭 1 · Run and trace", "🕵️ 2 · Find the failure", "💰 3 · Cost report", "✅ 4 · Evals", "☁️ 5 · See it in AWS",
                "🏗️ 6 · How it works", "❓ 7 · Questions + products", "📝 8 · Team ADR", "🎓 Lessons learnt"])
t1, t2, t3, t4, t5, t6, t7, t8, t9 = tabs

# ================================================================================================ tab 1
with t1:
    st.markdown('<div class="step"><b>Do this:</b> ① Pick a question and press <b>▶ Run AskIT</b>. ② Read the <b>waterfall</b>: every bar is one step '
                '(purple = model call, orange = tool call), a wide bar is a slow step. ③ Tick <b>one failure switch</b>, run the SAME question again, '
                'and compare the two rows in the table at the bottom.</div>', unsafe_allow_html=True)
    c1, c2 = st.columns([3, 2])
    q_pick = c1.selectbox("Question", QUESTIONS + ["(type my own)"])
    q = c1.text_input("Your own question", "How do I connect to the VPN from a hotel?") if q_pick == "(type my own)" else q_pick
    prompt_name = c2.selectbox("Instructions given to the agent", list(oa.PROMPTS), help="v2 adds a rule for VIP users, v3 adds a not-found rule. Tab 4 compares them.")
    st.markdown("**Failure switches** (tick one, run, look at the trace):")
    f1, f2, f3, f4 = st.columns(4)
    loop = f1.checkbox("🔁 Ticket system stuck", help="The ticket tool answers 'still syncing, call me again' forever. Use with a ticket question.")
    bloat = f2.checkbox("🐘 Huge search results", help="search_kb returns all 20 articles in full. Use with a how-to question.")
    slow = f3.selectbox("🐌 Slow ticket system", [0, 3, 8], format_func=lambda x: "off" if x == 0 else f"+{x} seconds")
    pad = f4.checkbox("📚 Padded instructions", help="Adds 6 pages of policy text to the system prompt. Every model call pays for it.")
    flags = {"loop": loop, "bloat": bloat, "slow": slow, "pad": pad}
    if st.button("▶ Run AskIT", type="primary"):
        with st.spinner("AskIT is working..."):
            S.last = do_run(q, provider, prompt_name, flags)
            S.traces.append({"question": q, "flags": flags_text(flags), **{k: S.last.get(k) for k in ("ms", "llm_calls", "tool_calls", "tokens_in", "cost_usd", "status")}})
    t = S.last
    if t is None:
        st.caption("No run yet. Press Run AskIT.")
    else:
        metrics(t, explain=True)
        if t["status"] != "ok":
            st.markdown(f'<div class="warn"><b>Status: {t["status"]}.</b> The run did not end normally. Find the step in the waterfall that explains why.</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="ans"><b>Question:</b> {t["question"]}<br><b>Answer:</b> {t["answer"]}</div>', unsafe_allow_html=True)
        show_waterfall(t)
        with st.expander("📋 Every step as a table (tokens, cost, what went in and out)"):
            st.dataframe(pd.DataFrame(ot.span_rows(t)), hide_index=True)
        with st.expander("🧾 The raw trace (this is what is saved and sent)"):
            st.json(t)
        st.subheader("Where can you see this run?")
        a, b, c = st.columns(3)
        a.markdown("**1 · This app**  \nAlways. The waterfall above and the file `submission/traces.jsonl`.")
        if t.get("langfuse_url"):
            b.markdown(f"**2 · Langfuse**  \n✅ Sent. [Open this trace in Langfuse]({t['langfuse_url']})  \nOpen **Tracing** and click your run: the same steps, plus filters, users, scores.")
        elif os.getenv("LANGFUSE_PUBLIC_KEY"):
            b.markdown("**2 · Langfuse**  \nKeys are set, but this run was not sent (check the box in the sidebar, or the connection test).")
        else:
            b.markdown("**2 · Langfuse**  \nNot connected yet. Enter your team keys in the sidebar (left).")
        c.markdown("**3 · AWS CloudWatch**  \nBedrock logs each **model call** on its own (not your tools). Go to tab 5 to find yours.")
        st.markdown(CW_VS_LF, unsafe_allow_html=True)
    if S.traces:
        st.subheader("Compare your runs")
        plain = {}
        for r in S.traces:
            if r["flags"] == "none":
                plain.setdefault(r["question"], r)
        rows = []
        for r in S.traces[-8:]:
            b0 = plain.get(r["question"])
            if b0 is r:
                vs = "plain run (reference)"
            elif b0 and b0.get("tokens_in") and b0.get("cost_usd"):
                vs = f"tokens ×{(r['tokens_in'] or 0) / b0['tokens_in']:.1f} · cost ×{(r['cost_usd'] or 0) / b0['cost_usd']:.1f}"
            else:
                vs = "run this question with no switch first"
            rows.append({"question": r["question"][:42], "switch ticked": r["flags"], "time s": round((r["ms"] or 0) / 1000, 1), "model calls": r["llm_calls"],
                         "tool calls": r["tool_calls"], "tokens in": r["tokens_in"], "cost $": r["cost_usd"], "vs plain run": vs, "status": r["status"]})
        st.dataframe(pd.DataFrame(rows), hide_index=True)
        st.caption("Each switch hurts a different question: 🔁 stuck and 🐌 slow hit the ticket question, 🐘 huge results hits the how-to question, 📚 padded hits every question. "
                   "Compare a run only with a plain run of the SAME question.")
    st.markdown('<div class="take"><b>🎯 Takeaway.</b> A trace is a flight recorder. Without it you only know that the answer was bad; with it you know '
                '<i>which step</i> made it bad. Switch on one failure, then read the two things that change: the <b>shape</b> of the waterfall and the '
                '<b>tokens</b>.</div>', unsafe_allow_html=True)
    st.markdown('<div class="client"><b>💼 Say this to a client.</b> "Before go-live we record every step of every run: what the AI was asked, which tool it used, '
                'how long and how many tokens each step took. That is how we find problems no alarm would catch."</div>', unsafe_allow_html=True)
    thinking("t1", [
        ("You tick 🐘 Huge search results and ask the VPN question. Which number jumps the most?",
         {"a": "Tool calls", "b": "Tokens in of the NEXT model call (it must read the huge result)", "c": "Tokens out", "d": "Nothing changes"}, "b",
         "The tool result is pasted into the history, and the model reads the whole history again on its next call."),
        ("A user complains 'AskIT is slow', yet its final answer is correct. What does the final answer tell you about WHY it was slow?",
         {"a": "Which step was slow: the final answer shows it", "b": "That the model is too small", "c": "Nothing. Only the trace shows which step was slow", "d": "That the network is down"}, "c",
         "A correct answer can hide a slow tool, a retry or a loop. Only the step-by-step trace shows where the time went."),
    ], "<b>You cannot diagnose an agent from the complaint or from the final answer.</b> Only the trace shows which step (a model call or a tool call) caused the problem. "
       "That is why we record every step.")

# ================================================================================================ tab 2
with t2:
    st.markdown('<div class="step"><b>Do this:</b> Four runs went wrong in production. They were <b>recorded</b>, so everyone sees the same trace. For each one: '
                '① read the complaint, ② look at the waterfall and the table, ③ pick the root cause, ④ press <b>Check my answer</b> and read the fix. About 4 minutes each.</div>', unsafe_allow_html=True)
    cases = mystery.cases()
    done = sum(1 for v in S.myst_ok.values() if v)
    st.progress(done / 4, text=f"Root causes found: {done} of 4")
    pick = st.radio("Which failure?", [f"{c['id']} · {c['title']}" for c in cases], horizontal=False)
    c = next(x for x in cases if pick.startswith(x["id"]))
    st.markdown(f'<div class="warn"><b>The complaint:</b> {c["complaint"]}</div>', unsafe_allow_html=True)
    metrics(c["trace"])
    show_waterfall(c["trace"])
    with st.expander("📋 The same trace as a table"):
        st.dataframe(pd.DataFrame(ot.span_rows(c["trace"])), hide_index=True)
    st.write(f"**Per 1,000 runs this would cost about ${c['trace']['cost_usd'] * 1000:.2f}** (Nova Lite prices).")
    shown = [f"{k.upper()} · {v}" for k, v in c["options"].items()]
    ans = st.radio("What is the root cause?", shown, key=f"m_{c['id']}", index=None)
    if st.button("Check my answer", key=f"mb_{c['id']}", disabled=ans is None):
        S.myst_checked[c["id"]] = True
        S.myst_ok[c["id"]] = (ans[0].lower() == c["right"])
    if S.myst_checked.get(c["id"]):
        if S.myst_ok.get(c["id"]):
            st.success("✅ Yes.")
        else:
            st.error(f"Not quite. The root cause is **{c['right'].upper()} · {c['options'][c['right']]}**.")
        st.markdown(f'<div class="back"><b>Why:</b> {c["why"]}<br><b>The signal to look for:</b> {c["signal"]}<br><b>The fix:</b> {c["fix"]}</div>', unsafe_allow_html=True)
    if done == 4:
        st.balloons()
        st.success("All four found. Now make them yourself: go to tab 1, tick a failure switch and run it.")
    st.markdown('<div class="take"><b>🎯 Takeaway.</b> Four different failures, four different signals: <b>repeated spans</b> (loop), <b>one huge input</b> (bloat), '
                'a <b>missing span</b> (wrong tool, no error at all), a <b>wide tool bar</b> (slow dependency). Nobody got an error message. '
                'You only find these if you look at traces.</div>', unsafe_allow_html=True)
    st.markdown('<div class="client"><b>💼 Say this to a client.</b> "When someone says the AI is slow or wrong, the first thing we open is the trace. '
                'It tells us in a minute whether to fix the prompt, the tool, the data or the model, instead of guessing and paying for a bigger model."</div>', unsafe_allow_html=True)
    thinking("t2", [
        ("The answer was wrong and the trace has NO error and NO red bar. What is the first thing to look at?",
         {"a": "The AWS bill", "b": "Which tool spans are there, and which one is missing", "c": "The colour of the bars", "d": "The VM memory"}, "b",
         "A silent failure shows as a missing or wrong tool span. Nothing crashes, so you only see it by reading the steps."),
        ("Two complaints say 'it is slow'. In one trace the WIDE bar is a model call, in the other it is a tool call. Who do you talk to?",
         {"a": "Same person for both: the prompt writer", "b": "Model call wide → check the prompt size / model. Tool call wide → the owner of that system", "c": "Nobody, slowness is normal", "d": "Always buy a bigger model"}, "b",
         "The same complaint has different root causes. The shape of the waterfall tells you whose problem it is."),
    ], "<b>The same complaint ('slow', 'wrong') can have four different root causes</b>: a loop, a huge input, a missing tool, a slow system. Each leaves a different signal in the trace "
       "and has a different owner. Read the shape of the trace, not the answer.")

# ================================================================================================ tab 3
with t3:
    st.markdown('<div class="step"><b>Do this:</b> ① Press <b>Run the batch</b> (10 tickets). Read the cost per ticket and the slowest 5% of runs. '
                '② Tick <b>Padded instructions</b> and run it again: what does a long prompt cost? ③ In part C, move the sliders and see what happens to the monthly bill for each model.</div>', unsafe_allow_html=True)
    st.subheader("A · Cost per ticket (measured)")
    a1, a2, a3 = st.columns(3)
    n = a1.selectbox("How many tickets", [5, 10, 20], index=1)
    b_pad = a2.checkbox("📚 Padded instructions", key="b_pad")
    b_bloat = a3.checkbox("🐘 Huge search results", key="b_bloat")
    if st.button("▶ Run the batch", type="primary"):
        tick = load_tickets()[:n]
        flags = {"pad": b_pad, "bloat": b_bloat}
        prog = st.progress(0.0, text="Running...")
        res = []
        mdl, lfc = model_for(provider), lf_now()

        def work(tk):
            return do_run(f"Summarise ticket {tk['ticket_id']} and tell me the next step.", provider, "v1 · plain", flags, tags={"batch": "cost"}, model=mdl, lf=lfc)

        with ThreadPoolExecutor(max_workers=3) as ex:
            futs = [ex.submit(work, tk) for tk in tick]
            for f in futs:
                res.append(f.result())
                prog.progress(min(1.0, sum(1 for x in futs if x.done()) / len(futs)), text=f"{sum(1 for x in futs if x.done())} of {len(futs)} done")
        prog.empty()
        ms = [r["ms"] for r in res]
        S.batches.append({"label": f"#{len(S.batches) + 1} " + ("padded" if b_pad else "normal") + (" + huge results" if b_bloat else ""), "n": n,
                          "model": mf.model_label(provider), "price_key": mf.price_key(provider),
                          "cost_per_ticket": sum(r["cost_usd"] for r in res) / n, "p50": round(pct(ms, 50)), "p95": round(pct(ms, 95)),
                          "tokens_in": sum(r["tokens_in"] for r in res) / n, "tokens_out": sum(r["tokens_out"] for r in res) / n,
                          "calls": sum(r["llm_calls"] for r in res) / n, "not_ok": sum(1 for r in res if r["status"] != "ok"),
                          "per_call": [statistics.mean([r["spans"][i]["tokens_in"] for r in res if len(r["spans"]) > i and r["spans"][i]["kind"] == "llm"] or [0]) for i in (0, 2)]})
    if S.batches:
        df = pd.DataFrame([{"batch": b["label"], "tickets": b["n"], "cost per ticket $": round(b["cost_per_ticket"], 7), "p50 ms": b["p50"], "p95 ms": b["p95"],
                            "tokens in / ticket": round(b["tokens_in"]), "tokens out / ticket": round(b["tokens_out"]), "model calls / ticket": round(b["calls"], 1),
                            "runs not ok": b["not_ok"]} for b in S.batches])
        st.dataframe(df, hide_index=True)
        st.bar_chart(df.set_index("batch")["cost per ticket $"])
        last = S.batches[-1]
        st.markdown(f"**Where the input tokens go** (last batch): model call 1 reads about **{last['per_call'][0]:.0f}** tokens, model call 2 reads about **{last['per_call'][1]:.0f}** "
                    "(it re-reads everything, plus the tool result). Every extra step re-sends the whole history, so cost grows faster than steps.")
        if st.button("💾 Save this table to submission/cost_report.csv"):
            df.to_csv(HERE / "submission" / "cost_report.csv", index=False)
            st.success("Saved. SYNC.bat will push it.")
    st.subheader("B · Why a long prompt is expensive")
    st.markdown('<div class="back">You pay for <b>input tokens on every model call</b>. A 3-page policy in the system prompt is paid again at call 1, call 2, call 3... '
                'and for every ticket. <b>Prompt caching</b> lets the provider re-use a repeated prefix at about a tenth of the input price; '
                'it only works for a stable prefix (system prompt + tool list come first, the changing question last).</div>', unsafe_allow_html=True)
    st.subheader("C · What would it cost per month? (what-if)")
    base = S.batches[-1] if S.batches else {"tokens_in": 650.0, "tokens_out": 70.0}
    w1, w2, w3, w4 = st.columns(4)
    vol = w1.number_input("Tickets per month", 1000, 500000, 20000, step=1000)
    share = w2.slider("Share of input served from cache", 0, 90, 0, step=10, format="%d%%")
    cut = w3.slider("Shorter prompts / trimmed tool results", 0, 80, 0, step=10, format="%d%%")
    budget = w4.number_input("Monthly budget US$", 1.0, 100000.0, 50.0, step=10.0)
    tin = base["tokens_in"] * (1 - cut / 100)
    rows = []
    for k, m in P.MODELS.items():
        mc = P.cost(k, tin, base["tokens_out"], cached_in=tin * share / 100) * vol
        rows.append({"model": m["label"], "US$ per month": round(mc, 2), "US$ per ticket": round(mc / vol, 6), "inside budget": "✅" if mc <= budget else "❌", "note": m["note"]})
    cdf = pd.DataFrame(rows)
    cheapest = max(cdf["US$ per month"].min(), 0.0001)
    cdf["times the cheapest"] = (cdf["US$ per month"] / cheapest).round(1)
    st.dataframe(cdf, hide_index=True)
    st.bar_chart(cdf.set_index("model")["US$ per month"])
    st.caption(f"Based on **{base['tokens_in']:.0f} input and {base['tokens_out']:.0f} output tokens per ticket** "
               f"({'your last batch' if S.batches else 'a typical default: run a batch above to use your own numbers'}). Prices checked {P.PRICES_DATE}: always re-check the vendor page. "
               "Different models count tokens differently, and a cheaper model may need more steps or fail more often: cost per ticket is only half the story, "
               "the other half is the eval pass rate (tab 4).")
    st.markdown('<div class="take"><b>🎯 Takeaway.</b> Cost is <b>(tokens in + tokens out) × price × tickets</b>. The big levers are, in order: <b>fewer tokens</b> '
                '(trim prompts and tool results, stop loops), <b>caching</b>, then <b>the right model for the job</b>. Switching to a bigger model is the LAST lever, not the first.</div>', unsafe_allow_html=True)
    st.markdown('<div class="client"><b>💼 Say this to a client.</b> "We give you cost per ticket, measured on your own data, and what it becomes at your volume with each model. '
                'We also set a budget alarm and a step limit, so a loop cannot turn into a surprise invoice."</div>', unsafe_allow_html=True)
    thinking("t3", [
        ("Why does each extra step in a run cost MORE than the step before it?",
         {"a": "The model gets tired", "b": "Prices go up during a run", "c": "Every call re-sends the whole history (prompt + earlier results) as input tokens", "d": "Tools are charged per second"}, "c",
         "Input tokens are paid on every call, and the history only grows. That is why loops and long tool results are so expensive."),
        ("A model costs 10× less per token but needs 3× more steps and fails more tests. Is it the cheaper choice?",
         {"a": "Yes, always: 10× is bigger than 3×", "b": "Not necessarily: compare cost per SUCCESSFUL ticket, with the pass rate from tab 4", "c": "No, cheap models are always worse", "d": "Price does not matter"}, "b",
         "Cost per ticket is only half the story. A cheap model that fails the exam costs you in rework."),
    ], "<b>Cost = tokens × price × tickets.</b> Every step re-sends the whole history, so long prompts, big tool results and loops multiply the bill. "
       "Cut tokens first (trim, stop loops, cache). Choose a different model last, and judge it by cost per <i>successful</i> ticket.")

# ================================================================================================ tab 4
with t4:
    st.markdown('<div class="step"><b>Do this:</b> ① Press <b>Run the exam</b> with prompt <b>v1</b>. Look at the red ❌ rows. ② Pick prompt <b>v2</b> (adds a VIP rule) and run again. '
                '③ Pick <b>v3</b> and run again. ④ Read the comparison table: which risk category moved, and did anything get worse?</div>', unsafe_allow_html=True)
    st.markdown("Each test question is checked for the risks that apply to it. **Every check is PASS or FAIL**, done by plain code, so the result is the same every time. "
                "The risks come from failures we saw in tabs 1–2: wrong tool, runaway loop, answer not grounded in the knowledge base, unsafe write, over budget.")
    st.markdown('<div class="back"><b>This exam is a golden set:</b> a fixed list of questions with known right behaviour (which tool, which article, what must NOT happen). '
                'Because it never changes, a difference between two runs can only come from the one thing you changed.</div>', unsafe_allow_html=True)
    with st.expander("📖 What do the numbers mean? (pass %, hit rate, MRR, regression)"):
        st.markdown("""
- **Pass % (per risk):** of the questions where this risk applies, how many passed the check. `7/9` = 78%. Every check is PASS or FAIL, done by code.
- **Hit rate @3:** for each knowledge-base question, is the right article among the **top 3** search results? 10 of 10 → **100%**. It tests the *search*, not the AI.
- **MRR (mean reciprocal rank):** how *high* the right article is. Rank 1 scores 1.0, rank 2 scores 0.5, rank 3 scores 0.33, not found scores 0. Then take the average. **0.93** means almost always rank 1.
- **Regression:** a number that was fine before your change and got worse after it. Finding regressions before users do is the whole point of an exam.
- **Golden set:** the fixed list of test questions. Change ONE thing (the prompt, the model), run the same list, compare.
- **AI judge:** a second model call that reads the answer and says PASS/FAIL. It costs tokens and can be wrong, so use it only for what code cannot check (tone, helpfulness).
""")
    with st.expander("📋 The test questions"):
        st.dataframe(pd.DataFrame([{"id": c[0], "question": c[1], "should use first": c[2] or "(no write allowed for VIP)", "article": c[3], "kind": c[4]} for c in ev.CASES + S.extra_cases]), hide_index=True)
    e1, e2, e3 = st.columns([2, 1, 1])
    pname = e1.radio("Instructions given to the agent", list(oa.PROMPTS), horizontal=False)
    use_judge = e2.checkbox("Add an AI judge", help="A second model call reads each answer and says PASS or FAIL. Costs extra tokens. Use it to see its limits.")
    if e3.button("▶ Run the exam", type="primary"):
        prog = st.progress(0.0, text="Running the questions...")
        
        summary = ev.run_eval(model_for(provider), provider, pname, lf=lf_now(), use_judge=use_judge, workers=3, cases=ev.CASES + S.extra_cases,
                              progress=lambda d, t: prog.progress(d / t, text=f"{d} of {t} done"))
        prog.empty()
        S.eval_runs = ev.load_runs()
        S.eval_last = summary
    last = S.get("eval_last")
    if last:
        st.subheader(f"Result · prompt {last['prompt']}")
        rate = pd.DataFrame([{"risk": ev.CAT_TEXT[k], "passed": a, "of": b, "pass %": round(100 * a / b) if b else 0} for k, (a, b) in last["rate"].items()])
        r1, r2 = st.columns([1, 1])
        r1.dataframe(rate, hide_index=True)
        r2.bar_chart(rate.set_index("risk")["pass %"])
        sym = {True: "✅", False: "❌", None: "–"}
        keys = list(last["rate"])
        mat = pd.DataFrame([{"case": r["case"], "question": r["question"][:60], **{ev.CAT_TEXT[k]: sym[r["checks"].get(k)] for k in keys},
                             "tools used": " → ".join(r["tools"]) or "(none)"} for r in last["rows"]])
        st.dataframe(mat, hide_index=True)
        bad = [r for r in last["rows"] if any(v is False for v in r["checks"].values())]
        with st.expander(f"🔎 Look at the {len(bad)} failing cases (what the agent actually answered)"):
            for r in bad:
                fails = ", ".join(ev.CAT_TEXT[k] for k, v in r["checks"].items() if v is False)
                st.markdown(f"**{r['case']}** · {r['question']}  \n❌ {fails}  \n_Answer:_ {r['answer'][:300]}  \n_Tools:_ {' → '.join(r['tools']) or '(none)'}" + (f"  \n_Judge:_ {r['judge_reason']}" if r.get("judge_reason") else ""))
        st.caption(f"This exam cost about US${last['cost_usd']:.5f}. " + ("Scores were also sent to Langfuse (open a trace: they show next to it)." if lf_now() else ""))
    if len(S.eval_runs) > 0:
        st.subheader("Compare all exams you ran")
        cmp = []
        for r in S.eval_runs[-8:]:
            row = {"run": r["run_id"], "prompt": r["prompt"], "model": r["model"].split("·")[0].strip()}
            for k, (a, b) in r["rate"].items():
                row[ev.CAT_TEXT[k]] = f"{a}/{b}"
            row["cost $"] = r["cost_usd"]
            cmp.append(row)
        st.dataframe(pd.DataFrame(cmp), hide_index=True)
        st.caption("Rule: change ONE thing, run again, compare. If a number you did not expect to move got worse, you found a regression before your users did.")
        ignored = [r for r in S.eval_runs if r["prompt"][:2] in ("v2", "v3") and "stand-in" not in r["model"].lower() and "offline" not in r["model"].lower()
                   and r["rate"].get("safe") and r["rate"]["safe"][0] < r["rate"]["safe"][1]]
        if ignored:
            st.markdown('<div class="warn"><b>⚠️ A rule in the prompt is a request, not a guarantee.</b> Prompt v2 told the model never to touch a VIP account, yet at least one VIP case still failed '
                        'with this real model. Only the exam showed it. What would you do? ① a stronger model for VIP cases, ② stricter wording, ③ <b>a guard in the code</b> '
                        '(the tool itself refuses VIP changes). For safety rules, ③ is the one that always works.</div>', unsafe_allow_html=True)
    st.subheader("Retrieval check (no AI needed)")
    st.markdown("Before blaming the model, check the search: does the right article come back in the top 3? (RAG tools call this *context recall* / *hit rate*.)")
    if st.button("Check the search on 10 knowledge-base questions"):
        S.retr = ev.retrieval_scores()
    if S.retr:
        m1, m2 = st.columns(2)
        m1.metric("Hit rate @3", f"{S.retr['hit_rate']:.0%}", help="Is the right article in the top 3 results? 100% = every time.")
        m2.metric("MRR (higher = right article nearer the top)", f"{S.retr['mrr']:.2f}", help="Average of 1/rank of the right article. 1.0 = always first.")
        st.caption("If hit rate is high but answers are still wrong, the search is fine: look at the prompt or the model.")
    with st.expander("➕ Stretch: add a test question of your own"):
        x1, x2, x3 = st.columns(3)
        nq = x1.text_input("Your question", "Can I use my own phone for email?")
        ntag = x2.selectbox("Kind", ["kb", "unknown", "ticket"])
        ndoc = x3.text_input("Right article (KB-009) or NONE", "KB-009")
        if st.button("Add it to the exam"):
            S.extra_cases.append((f"X{len(S.extra_cases) + 1:02d}", nq, "get_ticket" if ntag == "ticket" else "search_kb", "NONE" if ntag == "unknown" else ndoc, ntag))
            st.success("Added. It is part of the next exam you run.")
    st.markdown('<div class="take"><b>🎯 Takeaway.</b> An eval is a <b>unit test for AI behaviour</b>. Pass or fail per risk, a fixed set of questions, and one change at a time. '
                'Every failure you find in production becomes a new test question, so the exam grows with the product. Libraries like RAGAS and DeepEval compute '
                'the same kinds of checks; you saw how the idea works with no library at all.</div>', unsafe_allow_html=True)
    st.markdown('<div class="client"><b>💼 Say this to a client.</b> "We do not say it works because the demo looked good. We keep a test set from your real tickets, '
                'it runs on every change, and nothing goes live if a risk category drops below the agreed pass rate."</div>', unsafe_allow_html=True)
    thinking("t4", [
        ("Hit rate @3 is 100%, but some answers are still wrong. Where do you look next?",
         {"a": "The prompt and the model: the search already finds the right article", "b": "The search: it must be broken", "c": "The VM", "d": "Nowhere, 100% means done"}, "a",
         "Hit rate only says the right article was retrieved. What the model does with it is a different step, and a different check."),
        ("Prompt v3 fixes the not-found case, but a VIP case that passed in v2 now fails. What is this called, and what do you do?",
         {"a": "A regression: do not release v3 until it is fixed", "b": "Bad luck: ignore it", "c": "Overfitting: add more questions and release", "d": "Latency: buy a faster model"}, "a",
         "A change that fixes one thing and breaks another is a regression. The exam exists to catch it before the users do."),
    ], "<b>An eval is a unit test for AI behaviour:</b> a fixed golden set, PASS/FAIL checks, change one thing, compare. "
       "<b>A rule in a prompt is a request, not a guarantee.</b> Only the exam tells you if the model obeyed it, and a safety rule belongs in code too.")

# ================================================================================================ tab 5
with t5:
    arn, user = S.get("who") or ("", "user1xx")
    st.markdown(CW_VS_LF, unsafe_allow_html=True)
    st.markdown('<div class="stepbig"><b>Step 0 · Make some calls first (in THIS app, 2 minutes)</b><br>'
                '① Sidebar: choose <b>AWS Bedrock</b> (Offline makes no AWS call, so there is nothing to see).<br>'
                '② Tab 1: pick <b>Summarise ticket TKT-0004</b>, press <b>Run AskIT</b>. Write down <b>Tokens in</b>.<br>'
                '③ Wait about 1–2 minutes: AWS delivers the log a little later.</div>', unsafe_allow_html=True)
    if st.button("Who am I in AWS?"):
        S.who = aws_user()
        arn, user = S.who
    if S.get("who"):
        arn, user = S.who
        st.write(f"AWS says you are **{user}**" if arn else f"Could not reach AWS: {user}. Check your keys in the course .env file.")
    uname = user if S.get("who") and arn else "user1xx"
    group = os.getenv("ASKIT_BEDROCK_LOG_GROUP", "/aws/bedrock/askit-invocations")
    query = ("fields @timestamp, modelId, input.inputTokenCount as tokens_in, output.outputTokenCount as tokens_out\n"
             f"| filter identity.arn like /{uname}/\n| sort @timestamp desc\n| limit 20")
    st.markdown("**Steps in the AWS console** (about 10 minutes)")
    st.markdown(f"""1. Open the AWS console and check the top right says **N. Virginia (us-east-1)**. Logs live in one region only: if you are in another region the log group will not be there.
2. Quick way: open  `https://us-east-1.console.aws.amazon.com/cloudwatch/home?region=us-east-1#logsV2:logs-insights`
   Or by menu: search **CloudWatch** → left menu **Logs** → **Log Analytics** → the **Logs Insights** query box.
3. Under *Select log group(s)* choose **{group}**. Set the time range (top right) to **1h**.
4. Replace the query box with the text below, then click **Run query**.""")
    st.code(query, language="text")
    st.markdown("""5. Look at the rows. **One row = one model call**, so your Step 0 run shows **2 rows**: call 1 asked for a tool, call 2 wrote the answer. Add the two `tokens_in` values: it should match *Tokens in* in tab 1.
6. Now open **CloudWatch → GenAI Observability → Model invocations** (left menu). These charts show every user's calls: count, latency, tokens. This is the team view an operations group would watch.
7. **Your Day 9 Lambda:** Lambda → your function → **Monitor** tab → **View CloudWatch Logs**. Same idea for the tool side: AWS logs what it runs.""")
    st.caption("No rows? Wait another minute and run the query again. Still nothing: check the region (step 1) and that you ran tab 1 with AWS Bedrock, not Offline.")
    st.subheader("Or fetch it here")
    if st.button("Fetch my last Bedrock calls from CloudWatch"):
        try:
            rows, status = cw_fetch(uname, group)
            S.cw = rows
            st.caption(f"Query status: {status}")
        except Exception as e:                                          # noqa: BLE001
            st.error(f"Could not read the logs: {type(e).__name__}: {str(e)[:200]}. Use the console steps above (same query).")
    if S.get("cw"):
        st.dataframe(pd.DataFrame(S.cw), hide_index=True)
        tin_aws = sum(int(r.get("tokens_in", 0)) for r in S.cw[:2])
        st.caption(f"Newest 2 calls from AWS add up to {tin_aws} input tokens. Your last local trace says {S.last['tokens_in'] if S.last else '—'}.")
    elif S.get("cw") == []:
        st.info("The query ran but returned no rows yet.")
    st.subheader("The same run, three views")
    st.dataframe(pd.DataFrame([
        {"": "What it records", "This app (own tracer)": "Every step: model + tool + timing + cost", "Langfuse": "Every step, nested, with scores and users", "AWS CloudWatch (Bedrock)": "Every model call only: who, model, tokens, status (and prompt/answer text if the account setting is on)"},
        {"": "Sees your tools?", "This app (own tracer)": "Yes", "Langfuse": "Yes", "AWS CloudWatch (Bedrock)": "No. It cannot see which tool ran or why. That is why you also trace in the app"},
        {"": "Who can read it", "This app (own tracer)": "You, on this VM", "Langfuse": "Your team in the project", "AWS CloudWatch (Bedrock)": "Anyone with IAM rights to the log group: security can audit it centrally"},
        {"": "Setup effort", "This app (own tracer)": "Written for you in this lab", "Langfuse": "Keys + 1 decorator or integration", "AWS CloudWatch (Bedrock)": "One account setting; no code change"},
        {"": "Best for", "This app (own tracer)": "Learning how it works", "Langfuse": "Debugging and improving agents; evals; prompt versions", "AWS CloudWatch (Bedrock)": "Audit, usage and cost by user; one team view; alarms"}]), hide_index=True)
    st.markdown('<div class="take"><b>🎯 Takeaway.</b> AWS gives you <b>one side for free</b>: who called which model, with how many tokens. It does not know your agent\'s steps. '
                'Production teams use <b>both</b>: the cloud log for audit, usage and billing, and an agent-level tracer for debugging. '
                '"Which team spent the money?" is answered here. "Why did this answer go wrong?" is answered by the trace.</div>', unsafe_allow_html=True)
    st.markdown('<div class="client"><b>💼 Say this to a client.</b> "On AWS you get an audit trail of every model call in your own account, with no extra vendor. '
                'We add agent-level tracing on top, and we can send both to the monitoring tool you already use."</div>', unsafe_allow_html=True)
    thinking("t5", [
        ("Your agent calls get_ticket 6 times in a row. Can the CloudWatch Bedrock log show you that?",
         {"a": "Yes, it lists every tool", "b": "No: it only sees the model calls, not your tools", "c": "Only if you pay extra", "d": "Yes, as an error"}, "b",
         "Bedrock logs sit at the model API. Tool calls run in your code, so only an agent-level trace (Langfuse, your tracer) shows them."),
        ("The finance team asks 'which team spent how much on models last week?' Which view answers it best?",
         {"a": "Langfuse trace of one run", "b": "The waterfall in tab 1", "c": "CloudWatch invocation log: who called, which model, how many tokens", "d": "The prompt"}, "c",
         "Usage and cost by caller is the cloud log's job. Debugging one wrong answer is the trace's job."),
    ], "<b>CloudWatch sees the model calls only; Langfuse sees the whole agent run.</b> CloudWatch tells you who called which model and how many tokens (audit, usage, billing). "
       "Langfuse shows every step, tool and decision (debugging). You need both.")

# ================================================================================================ tab 6
with t6:
    st.markdown('<div class="step"><b>Read this once (3 minutes).</b> The picture shows what each file in this lab does. Nothing here needs editing.</div>', unsafe_allow_html=True)
    pic1, pic2 = st.tabs(["🧩 The pieces of this lab", "🔬 Inside one trace"])
    with pic1:
        html, h = diagram.architecture(has_langfuse=bool(os.getenv("LANGFUSE_PUBLIC_KEY")))
        show_html(html, h)
    with pic2:
        html, h = diagram.trace_anatomy()
        show_html(html, h, scale=1.5)
    st.dataframe(pd.DataFrame([
        {"file": "app.py", "what it does": "The screen: tabs, buttons, tables. Calls the others."},
        {"file": "ops_agent.py", "what it does": "The AskIT agent loop: model call, tool call, repeat, with a limit of 6. Applies the failure switches."},
        {"file": "ops_trace.py", "what it does": "The recorder. One span per step; saves traces; sends them to Langfuse when keys are set."},
        {"file": "evals.py", "what it does": "The 14 test questions and the PASS/FAIL checks. Also the retrieval check."},
        {"file": "mystery.py", "what it does": "The four recorded failures of tab 2."},
        {"file": "prices.py", "what it does": "Model prices (with date) for the cost tab."},
        {"file": "model_factory.py", "what it does": "Gives the app a model: Bedrock, Azure, OpenAI or the Offline stand-in."},
        {"file": "diagram.py · design_decision.py", "what it does": "Draws the pictures · builds your team ADR."},
        {"file": "submission/", "what it does": "Your evidence: traces.jsonl, eval_runs.json, cost_report.csv, your ADR. Pushed to GitHub by SYNC.bat."}]), hide_index=True)
    st.markdown('<div class="back"><b>In production</b> the same pieces exist, with other names: the tracer becomes an SDK (Langfuse, OpenTelemetry) inside your agent, '
                'the store becomes a service with retention and access control, evals run in your CI pipeline, and alerts watch the numbers you saw in tabs 1–3.</div>', unsafe_allow_html=True)
    thinking("t6", [
        ("Which file records every step of a run (the flight recorder)?",
         {"a": "app.py", "b": "prices.py", "c": "mystery.py", "d": "ops_trace.py"}, "d",
         "ops_trace.py creates one span per model call and tool call, saves them and sends them to Langfuse."),
        ("You want to add a new failure switch, for example 'rate limit'. Which file applies the switches in front of the tools?",
         {"a": "ops_agent.py", "b": "evals.py", "c": "diagram.py", "d": "design_decision.py"}, "a",
         "run_tool() in ops_agent.py is where the switches (loop, bloat, slow, pad) are applied before the real tool runs."),
    ], "<b>Tracing is a small piece inside your agent.</b> Everything else in production is about what happens to the traces: where they live, who may read them, "
       "how long they stay, and who gets woken when the numbers go wrong.")

# ================================================================================================ tab 7
with t7:
    st.subheader("Quick questions")

    def quiz(qid, text, opts, right, why):
        st.markdown(f"**{text}**")
        a = st.radio("answer", [f"{k.upper()} · {v}" for k, v in opts.items()], key=f"q_{qid}", index=None, label_visibility="collapsed")
        if st.button("Check", key=f"qb_{qid}", disabled=a is None):
            S.quiz[qid] = a[0].lower() == right
        if qid in S.quiz:
            (st.success if S.quiz[qid] else st.error)(("✅ " if S.quiz[qid] else f"The answer is {right.upper()}. ") + why)

    quiz("1", "The same tool appears 5 times in a row in a trace. What is the most likely cause?",
         {"a": "The model is too small", "b": "Nothing stops the agent repeating a call", "c": "The knowledge base is too big", "d": "Tracing is switched on"}, "b",
         "Repeated identical spans mean a loop. A step limit and a 'same call twice' stop rule are the fix.")
    quiz("2", "Why must a pass/fail check be binary rather than a score out of 10?",
         {"a": "Nobody can act on 7.3, but everybody can fix a FAIL", "b": "Scores are not allowed in tests", "c": "Models cannot give numbers", "d": "Binary is cheaper to store"}, "a",
         "A FAIL on one risk tells you what to fix; a vague score does not.")
    quiz("3", "The answer was wrong but there is no error anywhere in the trace. What do you check first?",
         {"a": "The VM memory", "b": "Which tools ran, and which one is missing", "c": "The font of the answer", "d": "The AWS bill"}, "b",
         "Silent failures show up as a missing or wrong tool span, as in mystery M3.")
    quiz("4", "Which change usually saves the MOST money first?",
         {"a": "A bigger model", "b": "Fewer tokens: trim prompts and tool results, stop loops", "c": "A second VM", "d": "A new logo"}, "b",
         "You pay per token, so cut tokens before you change the model.")
    quiz("5", "What can AWS's Bedrock invocation log NOT tell you?",
         {"a": "Which tool your agent ran", "b": "Who made the call", "c": "How many tokens were used", "d": "Which model was called"}, "a",
         "It sits at the model API. Your agent's tool calls happen in your code, so you need app-level tracing too.")
    quiz("6", "A developer edits the prompt. What should happen before it goes live?",
         {"a": "Ask a friend to try it", "b": "Run the eval set and compare with the last run", "c": "Nothing, prompts are not code", "d": "Raise the temperature"}, "b",
         "Prompts are code. Run the same exam, change one thing, compare, and only then release.")

    st.subheader("Which product? (the question clients ask)")
    st.markdown("**Tracing and observability**")
    st.dataframe(pd.DataFrame([
        {"option": "Langfuse", "what it is": "Open-source tracing, prompts, datasets, evals. Cloud or self-hosted", "strong when": "Any framework or model; you want the data in your own cloud; mixed stack", "watch out for": "You run and secure it if self-hosted", "cost model": "Free self-hosted; cloud plans by volume"},
        {"option": "LangSmith", "what it is": "LangChain's managed tracing and evals", "strong when": "You are all-in on LangChain/LangGraph", "watch out for": "Closed source, vendor-hosted data", "cost model": "Per seat + trace volume"},
        {"option": "AWS CloudWatch GenAI + AgentCore Observability", "what it is": "Logs, metrics and traces inside your AWS account", "strong when": "Everything runs on AWS; security wants one audit place", "watch out for": "Less 'debug this answer' polish than agent-first tools", "cost model": "Log ingestion + storage + queries"},
        {"option": "OpenTelemetry + your APM (Datadog, Dynatrace, Grafana)", "what it is": "Vendor-neutral standard; send agent spans to tools you already own", "strong when": "A platform team already runs the monitoring", "watch out for": "LLM-specific views (tokens, prompts) vary by vendor", "cost model": "Whatever your APM charges"}]), hide_index=True)
    st.markdown("**Evaluation**")
    st.dataframe(pd.DataFrame([
        {"option": "Plain code checks (this lab)", "strong when": "Rules you can write down: right tool, no loop, cited source", "watch out for": "Cannot judge open-ended quality"},
        {"option": "AI judge (LLM as judge)", "strong when": "Tone, helpfulness, faithfulness to the sources", "watch out for": "Costs tokens, can be wrong or biased: spot-check it by hand"},
        {"option": "RAGAS / DeepEval", "strong when": "Ready-made RAG and agent metrics, run in CI", "watch out for": "Most metrics are AI-judged, so they cost tokens and vary; pin versions"},
        {"option": "Langfuse datasets / AWS Bedrock + AgentCore Evaluations", "strong when": "Managed runs over saved datasets and production traces", "watch out for": "You still must write good test cases"}]), hide_index=True)
    st.subheader("Client questions, with an answer you can give")
    qa = {
        "Do traces put our employees' data at risk?": "They can, because they store questions and tool results. Decide where traces live (your own account or self-hosted), mask names and ids before sending, set a retention period, and limit who can open them. This is exactly a CISO curveball in the ADR.",
        "Does tracing slow the agent down?": "Very little: the SDK sends spans in the background. A model call takes hundreds of milliseconds; recording it takes about a millisecond. Measure it once in your own setup.",
        "Why not just use CloudWatch?": "CloudWatch sees the model call, not the agent's decisions or tools. Use it for audit, usage and billing; add agent-level traces to debug wrong answers.",
        "Which model should we start with?": "The smallest one that passes your eval set. Start small, run the exam, move up only for the categories that fail. Never pick a model by brand.",
        "Can we cap the spend?": "Yes, in layers: a step limit in the agent, a cost-per-ticket alert, budgets and alarms in the cloud account, and (Day 11–12) a gateway that enforces limits per team.",
        "How big should the test set be?": "Start with 20–50 real cases covering happy paths, past failures and tricky inputs. Every production failure adds a case. Quality of cases beats quantity.",
    }
    for k, v in qa.items():
        with st.expander(k):
            st.write(v)

# ================================================================================================ tab 8
with t8:
    st.markdown('<div class="stepbig"><b>📝 Team exercise · breakout room · 10 minutes, then a 90-second pitch</b><br>'
                'You will write a one-page <b>design decision (ADR)</b>: <i>"we chose X, not Y, because of these numbers."</i> '
                'Do the steps below <b>in order, top to bottom</b>. Do not skip ahead: the client curveball comes in Step 5.</div>', unsafe_allow_html=True)
    st.markdown('<div class="big"><b>Who does what</b> (decide in 30 seconds)<br>'
                '👤 <b>Driver</b>: shares the screen and types<br>'
                '📖 <b>Reader</b>: reads each step aloud to the team<br>'
                '🤔 <b>Challenger</b>: asks "why not the other option?" at every choice<br>'
                '🎤 <b>Presenter</b>: gives the 90-second pitch</div>', unsafe_allow_html=True)

    st.markdown('<div class="stepbig"><b>Step 1 · Your team</b> (1 min)<br>Pick your team name and type your first names.</div>', unsafe_allow_html=True)
    c1, c2 = st.columns([1, 1])
    team = c1.selectbox("Your team", list(dd.CURVEBALLS))
    members = c2.text_input("Team members (first names)")
    cb = dd.CURVEBALLS[team]

    st.markdown('<div class="stepbig"><b>Step 2 · Look at your lab numbers</b> (1 min)<br>These come from tabs 2, 3 and 4. They are the <b>evidence</b> for your decision. '
                'If the box is empty, go back and do those tabs first.</div>', unsafe_allow_html=True)
    evd = {"mystery": sum(1 for v in S.myst_ok.values() if v) if S.myst_checked else None, "retrieval": S.retr, "evals": [], "cost": None}
    seen = {}
    for r in S.eval_runs:
        seen[r["prompt"]] = r
    evd["evals"] = list(seen.values())
    if S.batches:
        bt = S.batches[-1]
        evd["cost"] = {"n": bt["n"], "model": bt["model"].split("·")[0].strip(), "per_ticket": bt["cost_per_ticket"], "p50": bt["p50"], "p95": bt["p95"], "tokens": bt["tokens_in"]}
    if not (evd["cost"] or evd["evals"] or evd["mystery"] is not None):
        st.warning("Use tabs 2, 3 and 4 first, so your ADR gets real numbers.")
    else:
        st.markdown(dd.evidence_lines(evd))

    st.markdown('<div class="stepbig"><b>Step 3 · The basic design: make 3 choices</b> (3 min)<br>Read each question aloud. Discuss. The Challenger asks "why not the others?" before you click.</div>', unsafe_allow_html=True)
    th = st.radio("**Choice 1 · Where do traces live?**", dd.TRACE_HOME)
    st.write("")
    gate = st.radio("**Choice 2 · What must pass before a change goes live?**", dd.GATES)
    st.write("")
    mdl = st.radio("**Choice 3 · Model strategy**", dd.MODELS)
    st.write("")
    alerts = st.multiselect("**Choice 4 · What wakes a human at 3 a.m.?** (pick 3 or 4)", dd.ALERTS, default=dd.ALERTS[:3])
    st.write("")
    bud = st.text_input("**Choice 5 · The budget we promise.** For example: under US$0.01 per ticket, alarm at 80% of US$500 a month", "")

    st.markdown('<div class="stepbig"><b>Step 4 · Explain your choices</b> (2 min)<br>Two or three short lines each. Write so that a CFO and a CISO both understand. Use a number from Step 2.</div>', unsafe_allow_html=True)
    why = st.text_area("**Why these choices?** (2–3 lines)", height=90)
    rej = st.text_area("**Which option did you reject, and why?** (1–2 lines)", height=80)

    st.markdown('<div class="stepbig"><b>Step 5 · The client curveball</b> (3 min)<br>Only now, tick the box. The client has changed the rules. '
                'Decide: what in your design <b>changes</b>, and what does <b>NOT</b> change?</div>', unsafe_allow_html=True)
    show_cb = st.checkbox("⚡ Reveal the curveball", key=f"cb_{team}")
    ans = ""
    if show_cb:
        st.markdown(f'<div class="warn"><b>⚡ Curveball from the {cb["from"]}: {cb["title"]}</b><br>{cb["detail"]}<br>'
                    f'<b>Evidence in this app:</b> {cb["evidence"]}<br><i>Topic: {cb["topic"]}</i></div>', unsafe_allow_html=True)
        ans = st.text_area(f"**How does your design handle '{cb['title']}'?** What changes, what does NOT change?", height=100)

    st.markdown('<div class="stepbig"><b>Step 6 · Create the ADR</b> (30 seconds)<br>Press the button. The app writes the file for you with your lab numbers inside.</div>', unsafe_allow_html=True)
    if st.button("📝 Create our design decision (ADR)", type="primary"):
        md = dd.build_markdown(team, members, th, alerts, gate, mdl, bud, why, rej, ans, evd, mf.LABELS[provider])
        out = mf.ROOT / "teams" / team / "ADR-AskIT-05.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(md, encoding="utf-8")
        S.lessons["t8"] = ("<b>A design decision names the option you rejected and the number that proves your choice.</b> "
                           "The client curveball changes part of the design, not all of it: say clearly which part.")
        st.success(f"Saved to {out}. Run SYNC.bat to push it.")
        with st.expander("👀 Preview", expanded=True):
            st.markdown(md)
    st.markdown('<div class="stepbig"><b>Step 7 · Pitch in 90 seconds</b><br>The Presenter says four things: ① <b>our decision</b> ② <b>one number that proves it</b> ③ <b>what we rejected and why</b> ④ <b>how the curveball changed us</b>.</div>', unsafe_allow_html=True)
    st.subheader("How the board scores you (0-5 each, 25 points to the leaderboard)")
    st.table(pd.DataFrame(dd.RUBRIC, columns=["Criterion", "What earns full marks"]))
    st.info("📚 Bonus reading after class: `Day10\\Content\\Eval_Harness_FDE_Guide.html` (how a forward-deployed engineer builds an eval harness for a client).")
    if S.lessons.get("t8"):
        lesson_box(S.lessons["t8"])

# ================================================================================================ tab 9
with t9:
    st.markdown("## 🎓 Lessons learnt")
    st.caption("Each lesson unlocks when you answer the two thinking questions at the bottom of its tab (tab 8: when you create your ADR). Tab 7 has no lesson.")
    names = {"t1": "1 · Run and trace", "t2": "2 · Find the failure", "t3": "3 · Cost report", "t4": "4 · Evals", "t5": "5 · See it in AWS", "t6": "6 · How it works", "t8": "8 · Team ADR"}
    st.progress(len(S.lessons) / len(names), text=f"Lessons unlocked: {len(S.lessons)} of {len(names)}")
    for k, nm in names.items():
        if k in S.lessons:
            st.markdown(f'<div class="lesson"><b class="h">🎓 Tab {nm}</b><br>{S.lessons[k]}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="lock">🔒 Tab {nm}: not unlocked yet. Do the tab, then answer its two questions.</div>', unsafe_allow_html=True)
    if S.lessons:
        txt = "# My lessons from Lab 10\n\n" + "\n\n".join(f"## Tab {names[k]}\n" + re.sub(r"<[^>]+>", "", S.lessons[k]) for k in names if k in S.lessons)
        st.download_button("⬇ Download my lessons (.md)", txt, file_name="lab10_lessons.md")
