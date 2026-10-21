"""Lab 12 · AskIT Break-it Range  (Streamlit screen).   Start it with:  python run.py

You attack AskIT with 6 attacks, switch 5 defences on and off, and look for the smallest set that stops everything
while normal work still gets done. No code to edit.
Files: range_engine.py (attacks, defences, the run) · naive_model.py (a gullible stand-in model) · guardrail.py (the managed-guardrail layer)
"""
import re
from pathlib import Path

import pandas as pd
import streamlit as st

import model_factory as mf  # noqa: I001  (must load first: it reads the course .env)
import guardrail
import range_engine as E

st.set_page_config(page_title="Lab 12 · AskIT Break-it Range", page_icon="🎯", layout="wide", initial_sidebar_state="expanded")
st.markdown("""<style>
html, body, [class*="css"] {font-size:18px;}
.take{background:rgba(106,63,160,.14);border-left:6px solid #6A3FA0;padding:14px 18px;border-radius:10px;margin:8px 0}
.client{background:rgba(14,112,104,.14);border-left:6px solid #0E7068;padding:14px 18px;border-radius:10px;margin:8px 0}
.lesson{background:linear-gradient(135deg,rgba(245,166,35,.28),rgba(245,166,35,.10));border:3px solid #E08A00;padding:16px 20px;border-radius:14px;margin:14px 0}
.lock{background:rgba(127,127,127,.10);border:2px dashed rgba(127,127,127,.5);padding:12px 16px;border-radius:12px;margin:10px 0;opacity:.85}
.ev{border-radius:10px;padding:8px 14px;margin:5px 0;border:1px solid rgba(127,127,127,.35)}
.ev.user{background:rgba(31,90,166,.12)} .ev.model{background:rgba(106,63,160,.12)} .ev.tool{background:rgba(168,87,10,.14)}
.ev.bad{background:rgba(180,35,24,.22);border:2px solid #B42318} .ev.defence{background:rgba(26,127,55,.18);border:2px solid #1a7f37}
.ev.final{background:rgba(127,127,127,.12);font-weight:600}
.verdict{border-radius:12px;padding:14px 18px;margin:10px 0;font-size:1.1em}
.verdict.bad{background:rgba(180,35,24,.18);border:3px solid #B42318} .verdict.good{background:rgba(26,127,55,.18);border:3px solid #1a7f37}
.card{border:1px solid rgba(127,127,127,.4);border-radius:12px;padding:12px 16px;margin:8px 0}
div[data-baseweb="tab-list"] button:last-child{background:rgba(245,166,35,.28);border-radius:10px 10px 0 0;font-weight:700}
</style>""", unsafe_allow_html=True)

S = st.session_state
for k, v in {"think": {}, "lessons": {}, "history": [], "last": None, "base": None, "prov": "offline"}.items():
    S.setdefault(k, v)

ICON = {"user": "🧑 The user types", "model": "🤖 AskIT (the model)", "tool": "🛠️ A tool runs", "defence": "🛡️ A defence acts", "final": "💬 Final answer", "system": "⚙️ System"}


def lesson_box(text):
    st.markdown(f'<div class="lesson"><b>🎓 Lesson learnt</b><br>{text}</div>', unsafe_allow_html=True)


def thinking(tab, items, lesson):
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


def show_run(r):
    for e in r["events"]:
        cls = "bad" if e.get("bad") else e["who"]
        st.markdown(f'<div class="ev {cls}"><small>{ICON[e["who"]]}</small><br>{e["text"]}</div>', unsafe_allow_html=True)
    it = r["item"]
    if it["id"].startswith("A"):
        if E.got_through(r):
            st.markdown(f'<div class="verdict bad">❌ <b>The attack got through.</b> {it["wins"]}</div>', unsafe_allow_html=True)
        else:
            who = ", ".join(E.DEFENCES[d][0] for d in sorted(r["hits"])) or "the model refused by itself (a real model sometimes does)"
            st.markdown(f'<div class="verdict good">✅ <b>The attack did not get through.</b> Stopped by: {who}</div>', unsafe_allow_html=True)
    else:
        if E.legit_ok(r):
            st.markdown('<div class="verdict good">✅ <b>A normal request still works.</b></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="verdict bad">⚠️ <b>False alarm.</b> A normal request was blocked or broken by your defences. Real users would complain.</div>', unsafe_allow_html=True)


def defence_boxes(prefix, default=()):
    cols = st.columns(5)
    chosen = set()
    for c, (d, (name, desc)) in zip(cols, E.DEFENCES.items()):
        with c:
            if st.checkbox(f"{d} {name}", value=d in default, key=f"{prefix}_{d}", help=desc):
                chosen.add(d)
            st.caption(desc)
    return chosen


# ================================================================================================ sidebar
with st.sidebar:
    st.header("🎯 Lab 12")
    st.markdown("**AI model**")
    stt = mf.status()
    names = [p for p in ("offline", "bedrock", "azure", "openai") if stt[p][0]]
    S.prov = st.selectbox("Model", names, index=names.index(S.prov) if S.prov in names else 0,
                          format_func=lambda p: "Gullible stand-in (everyone sees the same result)" if p == "offline" else mf.LABELS[p], label_visibility="collapsed")
    if S.prov == "offline":
        st.caption("Start here. It is a stand-in that believes everything it reads, so every attack works and every group sees the same grid.")
    else:
        st.warning("A real model may refuse some attacks by itself, and may answer differently each time. That is also a finding.")
    st.markdown(f"**Managed guardrail (D5):** {guardrail.mode()}")

def start_here():
    """The 'Start here' tab: one place of reference for the whole lab."""
    st.markdown("""<style>.mc{border:1px solid rgba(127,127,127,.4);border-radius:12px;padding:12px 16px;height:100%}</style>""", unsafe_allow_html=True)
    st.markdown("### 🏁 Your mission (about 40 minutes, no code to write)")
    c1, c2, c3 = st.columns(3)
    c1.markdown('<div class="mc"><b>The problem</b><br>An agent that can act can be tricked into acting: leaking a secret, obeying an order hidden in a ticket, resetting a VIP password, or running up the bill. A client will ask "is it safe?" and "yes" is not an answer.</div>', unsafe_allow_html=True)
    c2.markdown('<div class="mc"><b>What we do</b><br>Attack our own agent on a practice range: <b>6 attacks</b>, <b>5 defences</b> you switch on and off, and <b>3 normal requests</b> that must still work.</div>', unsafe_allow_html=True)
    c3.markdown('<div class="mc"><b>You leave able to</b><br>Name the 6 risks, explain why no single defence is enough, and show a pass/fail test.</div>', unsafe_allow_html=True)

    st.markdown("### Do these in order")
    st.markdown("""| Tab | What you do | What you will see | What you learn |
|---|---|---|---|
| **1 · Meet the attacks** | Run each attack with **no defences** | All 6 attacks win. The story of each run, step by step | An agent that obeys what it reads can be steered by a user, a ticket or a polite request |
| **2 · Defend one attack** | Tick **one** defence, run **one** attack | A green "defence acts" step where the defence stopped it | Each defence acts at a different place |
| **3 · Full test** | Tick a **set** of defences and run the full test | A grid: 6 attacks and 3 normal requests, stopped or let through | Find the smallest set that stops all 6 and still lets the 3 normal requests through |
| **4 · How it works** | Read where each defence sits | OWASP names and the products clients ask about | Where each defence fits in a real design |
| **🎓 Lessons** | Answer the two thinking questions at the bottom of tabs 1, 2 and 3 | A lesson unlocks for each | Your own summary |

Leave the model on **Gullible stand-in**: every group sees the same result.""")

    st.markdown("### The 6 attacks")
    st.markdown("""| | What the attacker does | Risk (OWASP name) |
|---|---|---|
| **A1** | Asks the agent to print its instructions | Direct prompt injection |
| **A2** | Hides an order inside a ticket; the user only asks for a summary | Indirect prompt injection |
| **A3** | Asks politely for someone's email | Sensitive information disclosure |
| **A4** | Pretends to be an executive assistant | Excessive agency |
| **A5** | Asks for many password resets at once | Excessive agency |
| **A6** | A ticket makes the agent call a tool again and again | Unbounded consumption |""")

    st.markdown("### The 5 defences in one minute")
    st.markdown("Each defence sits at a different place. None sees everything.")
    st.markdown("""| | Defence | What it does | Try it in tab 2 | What you should see | The learning |
|---|---|---|---|---|---|
| **D1** | Input filter | Blocks a message that contains a phrase from a short bad-phrase list | A1 | Blocked before the model runs | Easy to build, but a polite attack passes and a normal request can be blocked by mistake. Check Normal L1 |
| **D2** | Output filter | Hides the secret code and e-mail addresses in the answer | A1, A3 | The secret or e-mail is hidden in the answer | It cleans the answer but does not stop the action. Too late if a password was already reset |
| **D3** | Tool guard (code) | A rule in code in front of the tool: no VIP resets, one change per request | A2, A4, A5 | The tool call is refused | The strongest fix for risky actions: a rule in code, not a request to the model |
| **D4** | Limits | Stops the request after 3 model calls | A6 | The request stops at 3 calls | The only one that protects your bill. It does nothing for secrets or VIPs |
| **D5** | Managed guardrail | A managed service checks the user's text and the answer | A1, A3 | Blocked or hidden, like D1 and D2 but smarter | Catches many ways of saying "ignore your rules". It does **not** see inside tool results or judge whether an action is allowed |""")
    st.markdown("""**What to remember**
1. **No single defence stops all 6 attacks.** Each one covers a different place: input, output, tool, limits.
2. **An attack hidden inside a ticket (A2) never passes through the user's text**, so input filters cannot see it.
3. **Fewer layers = less cost and fewer false alarms.** Always run the 3 normal requests too, not only the attacks.""")
    st.markdown('<div class="take"><b>🏆 Team game:</b> find the smallest set of defences that stops all 6 attacks and still lets the 3 normal requests through. Hint: one defence is a text filter that annoys real users.</div>', unsafe_allow_html=True)

    st.markdown("**Good to know**")
    st.markdown("""- **D5** uses a managed guardrail only if the trainer gives an id. Otherwise it is simulated. The sidebar says which.
- A real model may refuse some attacks by itself, or answer differently each time. Write down what you see: that is a finding, not a bug.
- **Never put AWS keys in files, GitHub, wikis or chat.**""")


_all = st.tabs(["🏁 Start here", "🎯 1 · Meet the attacks", "🛡 2 · Defend one attack", "📊 3 · Full test", "🧩 4 · How it works", "🎓 Lessons learnt"])
tabs = _all[1:]
with _all[0]:
    start_here()


# ================================================================================================ TAB 1
with tabs[0]:
    st.subheader("Six ways to attack the AskIT helpdesk agent")
    st.markdown("First, no defences at all. Pick an attack and press the button. You are the attacker.")
    a = st.selectbox("Attack", E.ATTACKS, format_func=lambda x: f'{x["id"]} · {x["icon"]} {x["name"]}')
    st.markdown(f'<div class="card"><b>{a["icon"]} {a["name"]}</b> · <i>{a["kind"]}</i><br><b>Who attacks:</b> {a["who"]}<br>'
                f'<b>Goal:</b> {a["goal"]}<br><b>The attack wins if:</b> {a["wins"]}</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    if c1.button("▶ Run this attack with NO defences", type="primary"):
        S.last = E.run(a, set(), S.prov)
    if c2.button("▶▶ Run all six with no defences"):
        S.base = E.full_test(set(), S.prov)[:6]
    if S.last and S.last["item"]["id"] == a["id"] and not S.last["defences"]:
        show_run(S.last)
    if S.base:
        st.markdown("**All six, no defences:**")
        st.dataframe(pd.DataFrame([{"Attack": r["id"] + " · " + r["name"], "Result": "❌ got through" if r["bad"] else "✅ failed"} for r in S.base]), hide_index=True, width="stretch")
    thinking("t1", [
        ("In attack 2 the user only asked for a summary. Who gave the harmful order?",
         {"a": "The user.", "b": "Text hidden inside the ticket, which the agent read as if it were an instruction.", "c": "The model's training."}, "b",
         "Anything the agent READS can carry an order: tickets, emails, web pages, files. This is called indirect prompt injection."),
        ("The prompt says 'never reset a VIP password', yet attack 4 worked. What does this show?",
         {"a": "The prompt had a spelling mistake.", "b": "A rule in the prompt is a request, not a guarantee.", "c": "VIPs are not important."}, "b",
         "A model may follow the rule or not, and may do so differently tomorrow. Security cannot depend on the model behaving.")],
        "<b>Anything the agent reads can carry an order</b> (user text, tickets, web pages, files). <b>A rule written in the prompt is a request, not a guarantee.</b> "
        "So security must be built around the model, not inside its instructions.")

# ================================================================================================ TAB 2
with tabs[1]:
    st.subheader("Switch defences on and try one attack")
    st.markdown("Pick an attack, tick one or more defences, press Run. Try each defence on its own first.")
    a2 = st.selectbox("Attack", E.ATTACKS, format_func=lambda x: f'{x["id"]} · {x["icon"]} {x["name"]}', key="a2")
    ds = defence_boxes("t2")
    if st.button("▶ Run with these defences", type="primary"):
        S.last = E.run(a2, ds, S.prov)
    if S.last and S.last["item"]["id"] == a2["id"] and (S.last["defences"] or S.last["item"] is a2):
        show_run(S.last)
    st.markdown('<div class="take"><b>Try this:</b> run attack 2 with only D1. Then only D3. Then attack 1 with only D2. Watch <i>where</i> each defence acts in the story above.</div>', unsafe_allow_html=True)
    thinking("t2", [
        ("Defence 1 (input filter) did not stop attack 2. Why?",
         {"a": "Filters are broken.", "b": "The user's message was clean. The order was inside the ticket, and D1 never reads tool results.", "c": "The ticket was too long."}, "b",
         "Each defence guards ONE place. D1 guards what the user types. An order that arrives inside a tool result walks past it."),
        ("The output filter hid the secret code in attack 1. Is the secret now safe?",
         {"a": "Yes, completely.", "b": "No. The model still read and repeated it. A filter only catches patterns you thought of, so do not put secrets in the prompt.", "c": "Yes, because it is in the logs."}, "b",
         "Filters are a safety net, not a vault. The best protection for a secret is to never give it to the model.")],
        "<b>Each defence guards one place.</b> Input filters miss orders that arrive inside tool results. Output filters catch only patterns you expected. "
        "<b>Only a rule in code in front of the tool can say no to an action</b>, whatever the model decided. And the best way to protect a secret is to keep it out of the prompt.")

# ================================================================================================ TAB 3
with tabs[2]:
    st.subheader("The full test: 6 attacks + 3 normal requests")
    st.markdown("Goal: find the **smallest set of defences** that stops all six attacks **and** lets all three normal requests work.")
    ds3 = defence_boxes("t3")
    if st.button("▶ Run the full test", type="primary"):
        rows = E.full_test(ds3, S.prov)
        stopped = sum(1 for r in rows[:6] if not r["bad"])
        ok = sum(1 for r in rows[6:] if not r["bad"])
        S.history.append({"Defences on": " + ".join(sorted(ds3)) or "none", "Layers": len(ds3), "Attacks stopped": f"{stopped} of 6", "Normal requests OK": f"{ok} of 3",
                          "Perfect?": "🏆" if stopped == 6 and ok == 3 else ""})
        S["rows"] = rows
    rows = S.get("rows")
    if rows:
        st.dataframe(pd.DataFrame([{"": r["id"], "Request": r["name"], "Result": (("❌ got through" if r["bad"] else "✅ stopped") if r["attack"] else ("⚠️ false alarm" if r["bad"] else "✅ works")),
                                    "Defence that acted": ", ".join(r["hits"]) or "–"} for r in rows]), hide_index=True, width="stretch")
        stopped = sum(1 for r in rows[:6] if not r["bad"])
        ok = sum(1 for r in rows[6:] if not r["bad"])
        if stopped == 6 and ok == 3:
            st.success(f"🏆 All six stopped and all normal requests work, with {len(ds3)} layers. Can you do it with fewer?")
        else:
            miss = [r["id"] for r in rows[:6] if r["bad"]]
            fa = [r["id"] for r in rows[6:] if r["bad"]]
            st.info((f"Still getting through: {', '.join(miss)}. " if miss else "") + (f"False alarms on: {', '.join(fa)}. " if fa else "")
                    + "Click one row's attack in tab 2 to see exactly why.")
        with st.expander("Show the story of one request"):
            pick = st.selectbox("Which one?", rows, format_func=lambda r: f'{r["id"]} · {r["name"]}')
            show_run(pick["result"])
    if S.history:
        st.markdown("**Your attempts so far**")
        st.dataframe(pd.DataFrame(S.history[::-1]), hide_index=True, width="stretch")
    thinking("t3", [
        ("Defence 1 stopped attack 1 but broke normal request L1. What is that called?",
         {"a": "A false alarm (a false positive).", "b": "A Python bug.", "c": "A cache miss."}, "a",
         "A crude filter blocks innocent users too. Every defence has a price: measure the attacks stopped AND the normal work that still works."),
        ("No single defence stopped all six attacks. What does that tell you?",
         {"a": "Defences are useless.", "b": "Use layers: each one covers a gap another leaves.", "c": "Buy the most expensive one."}, "b",
         "This is defence in depth. Five attacks arrive at five different places: the user's text, a ticket, the answer, the tool, the bill.")],
        "<b>Defence in depth.</b> No single layer stops everything, and every layer has a price: false alarms, delay, money. "
        "Measure both sides (attacks stopped and normal work still done), and run the whole test again after every change, like the evals on Day 10.")

# ================================================================================================ TAB 4
with tabs[3]:
    st.subheader("How it works")
    svg = """<div style="font-family:Segoe UI,Arial,sans-serif"><svg viewBox="0 0 1150 250" width="100%" style="background:#fff;border-radius:12px">
    <defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5L0 10z" fill="#555"/></marker></defs>
    <g stroke-width="2.2"><rect x="10" y="55" width="150" height="110" rx="12" fill="#E2EBF7" stroke="#1F5AA6"/><rect x="215" y="55" width="150" height="110" rx="12" fill="#E3F1EE" stroke="#1a7f37"/>
    <rect x="420" y="55" width="170" height="110" rx="12" fill="#EEE6F7" stroke="#6A3FA0"/><rect x="645" y="55" width="150" height="110" rx="12" fill="#E3F1EE" stroke="#1a7f37"/>
    <rect x="850" y="55" width="130" height="110" rx="12" fill="#FBEEDB" stroke="#A8570A"/><rect x="1035" y="55" width="105" height="110" rx="12" fill="#E3F1EE" stroke="#1a7f37"/></g>
    <g text-anchor="middle" fill="#161a23" font-size="16"><text x="85" y="95" font-weight="700">🧑 User text</text><text x="85" y="120">+ tickets, files</text>
    <text x="290" y="95" font-weight="700">🛡 In</text><text x="290" y="120">D1 phrases</text><text x="290" y="140">D5 guardrail</text>
    <text x="505" y="95" font-weight="700">🤖 The model</text><text x="505" y="120">decides what to do</text><text x="505" y="140" fill="#6A3FA0">(cannot be trusted)</text>
    <text x="720" y="95" font-weight="700">🔒 Tool guard</text><text x="720" y="120">D3 rules in code</text><text x="720" y="140">D4 limits</text>
    <text x="915" y="95" font-weight="700">🛠 Tools</text><text x="915" y="120">tickets, passwords</text>
    <text x="1087" y="95" font-weight="700">🛡 Out</text><text x="1087" y="120">D2, D5</text></g>
    <g stroke="#555" stroke-width="2.2" fill="none" marker-end="url(#a)"><line x1="162" y1="110" x2="213" y2="110"/><line x1="367" y1="110" x2="418" y2="110"/><line x1="592" y1="110" x2="643" y2="110"/>
    <line x1="797" y1="110" x2="848" y2="110"/><path d="M915 168 Q915 215 590 215 Q520 215 505 168" stroke-dasharray="6 5"/></g>
    <text x="10" y="30" font-size="16" fill="#555">Green boxes are defences. They sit in different places, so each one sees something the others cannot.</text>
    <text x="640" y="238" font-size="14" fill="#555" text-anchor="middle">tool results flow back into the model: that is where the poisoned ticket (attack 2) gets in</text></svg></div>"""
    if hasattr(st, "iframe"):
        st.iframe(svg, height=300)
    else:
        import streamlit.components.v1 as components
        components.html(svg, height=300)
    st.markdown("### Which risk is which (OWASP Top 10 for LLM applications)")
    st.dataframe(pd.DataFrame([
        ["A1, A2", "LLM01 Prompt injection", "Orders from the user or hidden in data", "Treat all text the agent reads as untrusted; limit what a tool can do"],
        ["A3", "LLM02 Sensitive information disclosure", "Personal data in answers", "Return only needed fields from tools; mask output"],
        ["A4, A5", "LLM06 Excessive agency", "The agent can do too much", "Least privilege tools, approval for changes, per-request limits"],
        ["A6", "LLM10 Unbounded consumption", "Loops and runaway bills", "Step limits, cost ceilings, budgets and alarms"]],
        columns=["Attack", "Risk name", "In plain words", "Main fix"]), hide_index=True, width="stretch")
    st.markdown("### Products a client may ask about")
    st.dataframe(pd.DataFrame([
        ["Amazon Bedrock Guardrails", "Managed filters on text going in and out: prompt attacks, denied topics, personal data", "You are on AWS and want a quick managed layer", "Does not judge tool actions or read tool results by default"],
        ["Azure AI Content Safety / Prompt Shields", "Microsoft's managed filters, including prompt-attack detection", "You are on Azure", "Same limit: text filters, not action rules"],
        ["Llama Guard / open-source classifiers", "A model that labels text as safe or unsafe", "You must run it yourself, data cannot leave", "You host and tune it"],
        ["NeMo Guardrails, Guardrails AI", "Open-source rule and flow frameworks around the model", "Custom conversation rules", "You maintain the rules"],
        ["Lakera, Protect AI and similar", "Commercial prompt-attack detection", "A dedicated vendor and support", "Check price, latency and where data goes"],
        ["Policy at the tool door (Gateway + Cedar, Day 12)", "Rules about WHICH TOOL CALL is allowed, outside the model", "Actions that must never happen (VIP resets)", "Rules must be written and tested"]],
        columns=["Option", "What it is", "Good for", "Watch out"]), hide_index=True, width="stretch")
    st.markdown('<div class="client"><b>💼 Say this to a client:</b> "We assume the model can be fooled. So the dangerous things are decided by rules in code and by policy at the tool door, '
                'and text filters are one extra layer. We test it with a red-team set before every release."</div>', unsafe_allow_html=True)

# ================================================================================================ LESSONS
with tabs[4]:
    nm = {"t1": "1 · Meet the attacks", "t2": "2 · Defend one attack", "t3": "3 · Full test"}
    st.subheader("🎓 Lessons learnt")
    st.caption("Each lesson unlocks when you answer the two thinking questions at the bottom of its tab.")
    st.progress(len(S.lessons) / len(nm), text=f"Lessons unlocked: {len(S.lessons)} of {len(nm)}")
    for k, n in nm.items():
        if k in S.lessons:
            st.markdown(f'<div class="lesson"><b>🎓 Tab {n}</b><br>{S.lessons[k]}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="lock">🔒 Tab {n}: not unlocked yet</div>', unsafe_allow_html=True)
    if S.lessons:
        txt = "# My lessons from Lab 12\n\n" + "\n\n".join(f"## Tab {nm[k]}\n" + re.sub(r"<[^>]+>", "", S.lessons[k]) for k in nm if k in S.lessons)
        st.download_button("⬇ Download my lessons (.md)", txt, file_name="lab12_lessons.md")
