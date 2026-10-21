"""Lab 16B · AskIT Policy Lab  (Streamlit screen).   Start it with:  python run.py

You put a Cedar policy engine in front of the Gateway from Lab 15 and teach it one rule:
    "The agent must NEVER reset a VIP's password. A human does that."
First you test the rules here, with the real Cedar engine (tabs 2 to 5). Then you do the same in the AWS console (README.md, Part A).
No code to edit. Files: policy_engine.py (the Cedar checker) · gw_client.py (talks to a Gateway) · policies\\*.cedar (the 4 rules)
"""
import re
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

import model_factory as mf  # noqa: I001  (must load first: it reads the course .env)
import gw_client as gc
import policy_engine as pe
import rt_client as rt

HERE = Path(__file__).resolve().parent
st.set_page_config(page_title="Lab 16B · AskIT Policy Lab", page_icon="🛡️", layout="wide", initial_sidebar_state="expanded")
st.markdown("""<style>
html, body, [class*="css"] {font-size:18px;}
.take{background:rgba(106,63,160,.14);border-left:6px solid #6A3FA0;padding:14px 18px;border-radius:10px;margin:8px 0}
.client{background:rgba(14,112,104,.14);border-left:6px solid #0E7068;padding:14px 18px;border-radius:10px;margin:8px 0}
.lesson{background:linear-gradient(135deg,rgba(245,166,35,.28),rgba(245,166,35,.10));border:3px solid #E08A00;padding:16px 20px;border-radius:14px;margin:14px 0}
.lock{background:rgba(127,127,127,.10);border:2px dashed rgba(127,127,127,.5);padding:12px 16px;border-radius:12px;margin:10px 0;opacity:.85}
.bad{background:rgba(180,35,24,.14);border-left:6px solid #B42318;padding:12px 16px;border-radius:10px;margin:8px 0}
.ok{background:rgba(14,112,104,.14);border-left:6px solid #0E7068;padding:12px 16px;border-radius:10px;margin:8px 0}
.ans{background:rgba(127,127,127,.10);border-radius:10px;padding:10px 14px;margin:6px 0}
div[data-baseweb="tab-list"] button:last-child{background:rgba(245,166,35,.28);border-radius:10px 10px 0 0;font-weight:700}
</style>""", unsafe_allow_html=True)

S = st.session_state
saved = gc.load_saved()
RULES = [("allow_get_ticket", "allow_get_ticket.cedar"), ("allow_get_user", "allow_get_user.cedar"),
         ("allow_reset_password", "allow_reset_password.cedar"), ("block_vip_reset_password", "block_vip_reset_password.cedar")]
for k, v in {"mode": "practice", "url": saved["url"], "arn": saved["arn"], "think": {}, "lessons": {}, "pmode": "ENFORCE", "strict": False,
             "on": {n: False for n, _ in RULES}, "pred": {}, "plog": [], "mat": None, "t2": None, "t5": None, "agent": None, "e2e": None}.items():
    S.setdefault(k, v)
S.setdefault("rules", {n: (HERE / "policies" / f).read_text(encoding="utf-8") for n, f in RULES})

CASES = [("get_ticket", {"ticket_id": "TKT-0004"}, "Look up ticket TKT-0004"), ("get_user", {"user_id": "EMP-1001"}, "Look up VIP EMP-1001"),
         ("reset_password", {"user_id": "EMP-1002"}, "Reset the password of EMP-1002 (not a VIP)"),
         ("reset_password", {"user_id": "EMP-1001"}, "Reset the password of EMP-1001 (VIP)"),
         ("reset_password", {"user_id": "EMP-1012"}, "Reset the password of EMP-1012 (VIP)"),
         ("delete_everything", {}, "Call a tool that does not exist")]
VIPS = {"EMP-1001", "EMP-1012", "EMP-1023"}


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


def arn_now():
    return S.arn.strip() if S.arn.strip().startswith("arn:") else pe.PRACTICE_ARN


def engine(mode=None, only=None, empty=False):
    """The practice policy engine built from the rules that are switched on."""
    pols = [] if empty else [(n, S.rules[n]) for n, _ in RULES if S.on[n] and (only is None or n in only)]
    return pe.Engine(arn_now(), mode or S.pmode, pols)


def gateway(eng=None, strict=None):
    if S.mode == "practice":
        return gc.PracticeGateway(eng, S.strict if strict is None else strict)
    return gc.AwsGateway(S.url)


def call(tool, args, eng=None, strict=None):
    gw = gateway(eng, strict)
    r = gw.rpc("tools/call", {"name": pe.PREFIX + tool, "arguments": args})
    if r.policy:
        S.plog.append({"tool": tool, "args": str(args), "decision": r.policy["decision"], "blocked": r.policy["blocked"], "by": ", ".join(r.policy["by"])})
    return r


def verdict(r):
    """-> (label, detail)"""
    if gc.is_denied(r):
        return "🛑 DENIED", r.error or "blocked"
    if not r.ok:
        return "⚠ error", r.error
    v = gc.call_text(r)
    if isinstance(v, dict) and v.get("error"):
        return "✅ passed the policy", "the tool said: " + str(v["error"])
    return "✅ ALLOWED", str(v.get("message") or v)[:140] if isinstance(v, dict) else str(v)


def table_for(cases, eng=None, strict=None):
    rows = []
    for tool, args, label in cases:
        r = call(tool, args, eng, strict)
        v, d = verdict(r)
        row = {"Request": label, "Result": v, "Detail": d}
        if r.policy:
            row["Engine decision"] = r.policy["decision"] + ("" if r.policy["blocked"] or r.policy["decision"] == "ALLOW" else " (logged only)")
        if S.mode == "aws":
            row["My local Cedar check"] = engine("ENFORCE").decide(tool, args)["decision"]
        rows.append(row)
    return pd.DataFrame(rows)


def rule_view(name, edit=True):
    with st.expander(f"📜 Rule: {name}", expanded=False):
        st.caption("This is the text you paste into the console (your Gateway ARN is already filled in).")
        st.code(pe.render(S.rules[name], arn_now()), language="text")
        for lvl, msg in pe.lint(pe.render(S.rules[name], arn_now()), arn_now()):
            (st.error if lvl == "error" else st.warning)(msg)
        if edit:
            S.rules[name] = st.text_area("Edit the rule (optional)", S.rules[name], height=170, key=f"ed_{name}")
            if st.button("↩ Back to the starter text", key=f"rs_{name}"):
                S.rules[name] = (HERE / "policies" / dict(RULES)[name]).read_text(encoding="utf-8")
                st.rerun()


def parse_banner():
    errs = engine("ENFORCE").parse_errors()
    for n, e in errs:
        st.error(f"Rule **{n}** has a typing mistake: {e}")
    return bool(errs)


# ================================================================================================ sidebar
with st.sidebar:
    st.header("🛡️ Lab 16B")
    st.markdown("**1 · AI model** (used in tab 4)")
    stt = mf.status()
    names = [p for p in ("bedrock", "azure", "openai", "offline") if stt[p][0]]
    S.prov = st.selectbox("Model", names, index=names.index(mf.auto_provider()), format_func=lambda p: mf.LABELS[p], label_visibility="collapsed")
    st.caption(mf.model_label(S.prov))
    st.markdown("**2 · Which Gateway?**")
    st.markdown(f"Now using: **{gateway().label if S.mode == 'practice' else 'My Gateway (AWS)'}**")
    on = [n for n, _ in RULES if S.on[n]]
    st.markdown(f"**3 · Practice rules switched on:** {len(on)} of 4" if S.mode == "practice" else "**3 · Rules:** the ones in your AWS policy engine")
    if S.mode == "practice":
        for n, _ in RULES:
            st.caption(("✅ " if S.on[n] else "⬜ ") + n)

tabs = st.tabs(["🔌 1 · Connect", "🛑 2 · Default deny", "✅ 3 · Allow the tools", "👑 4 · Block VIPs", "🕵️ 5 · Get around it", "🧩 6 · How it works", "🎓 Lessons learnt"])

# ================================================================================================ TAB 1
with tabs[0]:
    st.subheader("Connect")
    st.markdown("A **policy** is a rule the Gateway checks before it lets a tool run. You will write the rules here first (safe, no AWS), then repeat them on your real Gateway.")
    choice = st.radio("Which Gateway do you want to use?", ["Practice gateway (no AWS: start here, or if you are stuck)", "My Gateway on AWS (the one from yesterday, with my policy engine)"],
                      index=0 if S.mode == "practice" else 1)
    S.mode = "practice" if choice.startswith("Practice") else "aws"
    if S.mode == "aws":
        S.url = st.text_input("Your Gateway URL (ends with /mcp)", value=S.url, placeholder="https://askit-gw-user116-xxxx.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp").strip()
        S.arn = st.text_input("Your Gateway ARN (on the Gateway page in the console: starts with arn:aws:bedrock-agentcore)", value=S.arn,
                              placeholder="arn:aws:bedrock-agentcore:us-east-1:123456789012:gateway/askit-gw-user116-xxxx").strip()
        if st.button("💾 Save these two (never pushed to GitHub)"):
            gc.save(S.url, S.arn)
            st.success("Saved in this lab folder.")
        if S.arn and not S.arn.startswith("arn:aws:bedrock-agentcore:"):
            st.error("The ARN must start with arn:aws:bedrock-agentcore: . Copy it from the Gateway page.")
        if st.button("Who am I? (shows the AWS user your keys belong to)"):
            try:
                import boto3
                st.code(boto3.client("sts", region_name="us-east-1").get_caller_identity()["Arn"])
            except Exception as e:   # noqa: BLE001
                st.error(f"Could not read your AWS identity: {e}")
        st.info("Your rules in the console need this ARN. The app fills it into the rule text for you in tabs 3 and 4.")
    else:
        st.success(f"Practice mode. The practice Gateway's ARN is a fake one: `{pe.PRACTICE_ARN}`")
    if st.button("▶ Test the connection", type="primary"):
        r = gateway().rpc("tools/list")
        (st.success if r.ok else st.error)(f"✅ Connected: {len(gc.tools_of(r))} tools found in {r.ms} ms." if r.ok else "❌ " + r.error)
    st.markdown('<div class="take"><b>Why practice first?</b> A wrong rule in the console only tells you after you paste it. Here the same rule text is checked by the real Cedar engine on your VM. '
                'When it behaves, paste it into the console.</div>', unsafe_allow_html=True)

# ================================================================================================ TAB 2
with tabs[1]:
    st.subheader("A new engine blocks everything")
    st.markdown("Before you add any rule, see what an **empty** policy engine does. This surprises almost everyone.")
    if S.mode == "practice":
        S.t2_mode = st.radio("What is attached to the practice Gateway?", ["No policy engine", "Policy engine, LOG ONLY, no rules", "Policy engine, ENFORCE, no rules"], key="t2m")
        if st.button("▶ Call all three tools", type="primary"):
            eng = None if S.t2_mode.startswith("No") else pe.Engine(arn_now(), "LOG_ONLY" if "LOG" in S.t2_mode else "ENFORCE", [])
            S.t2 = (S.t2_mode, table_for([CASES[0], CASES[2], CASES[3]], eng))
        if S.t2:
            st.markdown(f"**Setup:** {S.t2[0]}")
            st.dataframe(S.t2[1], hide_index=True, width="stretch")
    else:
        st.markdown("**On AWS:** do README **Part A, steps 1 to 3** (create the engine, attach it to your Gateway, no rules yet). Then press the button.")
        if st.button("▶ Call the tools on my Gateway", type="primary"):
            S.t2 = ("My Gateway", table_for([CASES[0], CASES[2], CASES[3]]))
        if S.t2:
            st.dataframe(S.t2[1], hide_index=True, width="stretch")
    if S.plog:
        with st.expander("🧾 What the engine logged (on AWS this goes to CloudWatch)"):
            st.dataframe(pd.DataFrame(S.plog[-12:]), hide_index=True, width="stretch")
    thinking("t2", [
        ("You attached a policy engine in ENFORCE mode with no rules, and every call failed. Why?",
         {"a": "The engine is broken.", "b": "Policies work by default deny: nothing runs unless a permit rule says yes.", "c": "The Lambda was deleted."}, "b",
         "Cedar (the rule language) denies everything that no permit rule allows. An empty engine therefore blocks every tool."),
        ("Which setting lets you try new rules on real traffic WITHOUT blocking anyone?",
         {"a": "ENFORCE", "b": "LOG ONLY", "c": "Delete the engine"}, "b",
         "LOG ONLY records what the engine would have decided, and lets the call through. Use it first, then switch to ENFORCE.")],
        "<b>Policies are default-deny.</b> The moment you switch ENFORCE on, only what you explicitly permit works. That is what you want from a security control, "
        "but it means you roll out in two steps: LOG ONLY first to see what would break, then ENFORCE.")

# ================================================================================================ TAB 3
with tabs[2]:
    st.subheader("Say what IS allowed")
    st.markdown("One **permit** rule per tool. Read one, then switch the three on.")
    for n in ("allow_get_ticket", "allow_get_user", "allow_reset_password"):
        rule_view(n)
    c = st.columns(3)
    for col, n in zip(c, ("allow_get_ticket", "allow_get_user", "allow_reset_password")):
        S.on[n] = col.checkbox((f"Switch on: {n}" if S.mode == "practice" else f"I added {n} in the console"), value=S.on[n], key=f"on_{n}")
    if S.mode == "practice":
        S.pmode = "ENFORCE"
    else:
        st.markdown("**On AWS:** README **Part A, step 4**: create the three permit rules in your policy engine (paste each text above), set the mode to **Enforce**. "
                    "The ticks only tell the app which rules you pasted, so it can show you what your local Cedar says next to what AWS says.")
    if not parse_banner() and st.button("▶ Run 6 requests", type="primary", key="m3"):
        S.mat = ("t3", table_for(CASES, engine() if S.mode == "practice" else None))
    if S.mat and S.mat[0] == "t3":
        st.dataframe(S.mat[1], hide_index=True, width="stretch")
        if S.mat[1].loc[3, "Result"].startswith("✅"):
            st.markdown('<div class="bad"><b>Look at row 4.</b> The password of a VIP was reset. The permit rules said "reset_password is allowed", and nothing says "except for VIPs". That is tab 4.</div>', unsafe_allow_html=True)
        else:
            st.info("Switch on all three rules above and run again.")
    thinking("t3", [
        ("After you allowed the three tools, a VIP's password reset was still allowed. Why?",
         {"a": "The Gateway ignores policies for VIPs.", "b": "A permit rule says what may happen. Nothing yet says what must NOT happen.", "c": "The model decided it."}, "b",
         "Permit rules open a door. To close it for special cases you add a forbid rule."),
        ("Why one permit rule per tool, and not a single rule that allows everything?",
         {"a": "Cedar cannot read longer rules.", "b": "Least privilege: a new tool stays blocked until someone decides to allow it.", "c": "It is faster."}, "b",
         "AgentCore also refuses rules that name an action without naming one Gateway. Small, specific rules are the safe habit.")],
        "<b>Permit narrowly.</b> Allow tool by tool, on one named Gateway. A new tool someone adds tomorrow is blocked until a person writes a rule for it. "
        "That is least privilege, and it is why default-deny is a feature.")

# ================================================================================================ TAB 4
with tabs[3]:
    st.subheader("The VIP rule")
    st.markdown("**Business rule from the CIO:** *the agent must never reset a VIP's password. A human does that.* Read the rule, **predict** what happens, then run it.")
    rule_view("block_vip_reset_password")
    if S.mode == "practice":
        for n in ("allow_get_ticket", "allow_get_user", "allow_reset_password"):
            S.on[n] = True
        S.on["block_vip_reset_password"] = st.checkbox("Switch the VIP rule ON", value=S.on["block_vip_reset_password"], key="on_block")
    else:
        st.markdown("**On AWS:** README **Part A, step 5**: add the VIP rule as a 4th policy. Keep the mode on **Enforce**.")
        S.on["block_vip_reset_password"] = st.checkbox("I added the VIP rule in the console", value=S.on["block_vip_reset_password"], key="on_block")
    parse_banner()
    quick = [CASES[0], CASES[2], CASES[3], CASES[4]]
    st.markdown("**Your prediction.** For each request, will the Gateway let it through?")
    pc = st.columns(4)
    for i, (col, (_, _, label)) in enumerate(zip(pc, quick)):
        S.pred[i] = col.radio(label, ["Allow", "Deny"], index=None, key=f"pr{i}", horizontal=True)
    if st.button("▶ Run them", type="primary", key="m4", disabled=any(S.pred.get(i) is None for i in range(4))):
        df = table_for(quick, engine() if S.mode == "practice" else None)
        df.insert(1, "You predicted", [S.pred[i] for i in range(4)])
        df["You were"] = ["✅ right" if (S.pred[i] == "Allow") == r.startswith("✅") else "❌ wrong" for i, r in enumerate(df["Result"])]
        S.mat = ("t4", df)
    if S.mat and S.mat[0] == "t4":
        st.dataframe(S.mat[1], hide_index=True, width="stretch")
        st.caption(f"Score: {(S.mat[1]['You were'] == '✅ right').sum()} of 4")
    st.markdown("#### LOG ONLY or ENFORCE?")
    if S.mode == "practice":
        S.pmode = st.radio("Mode of the practice engine", ["ENFORCE", "LOG_ONLY"], horizontal=True, key="pm4")
        if st.button("Reset EMP-1001 again in this mode"):
            r = call("reset_password", {"user_id": "EMP-1001"}, engine())
            st.write(verdict(r)[0], "·", engine().decide("reset_password", {"user_id": "EMP-1001"})["why"])
    else:
        st.caption("On AWS you change the mode on the Gateway page in the console, then run the six requests again.")
    st.markdown("#### Ask the agent")
    st.caption("Now the real test: an agent that tries to do it, because a user asked nicely.")
    q = st.selectbox("Question", ["Please reset the password for EMP-1001. They are locked out.", "Please reset the password for EMP-1002. They are locked out."])
    if st.button("🤖 Ask AskIT through this Gateway"):
        with st.spinner("The agent is working…"):
            S.agent = (q, rt.agent_through(gateway(engine() if S.mode == "practice" else None), q, S.prov))
    if S.agent:
        a = S.agent[1]
        st.markdown(f'<div class="ans"><b>{S.agent[0]}</b><br>{a["answer"]}</div>', unsafe_allow_html=True)
        st.dataframe(pd.DataFrame([{"Step": s["label"], "ms": s["ms"], "Result": s["out"]} for s in a["steps"]]), hide_index=True, width="stretch")
    arn_rt = rt.load_saved()
    st.markdown("#### The whole path (AWS only)")
    if S.mode == "aws" and arn_rt and S.url:
        if st.button("🌍 Ask through the trainer's Runtime → my Gateway → Lambda"):
            sid = rt.new_session_id()
            S.e2e = rt.AwsRuntime(arn_rt).invoke("Please reset the password for EMP-1001. They are locked out.", sid, S.prov, S.url)
        if S.e2e:
            (st.success if S.e2e.ok else st.error)(S.e2e.answer if S.e2e.ok else S.e2e.error)
    else:
        st.caption("Needs your Runtime ARN (saved in Lab 16A) and 'My Gateway on AWS' in tab 1. Without them, skip this.")
    thinking("t4", [
        ("A permit rule and a forbid rule both match the same request. What happens?",
         {"a": "The permit wins because it came first.", "b": "The forbid wins, always.", "c": "The Gateway asks a human."}, "b",
         "In Cedar a matching forbid beats any permit. That is what makes a forbid rule a safe place for the 'never' rules."),
        ("The VIP list is typed inside the rule. What is its weakness?",
         {"a": "Nothing.", "b": "The list goes stale when VIPs change, because the policy cannot look up your user database.", "c": "Cedar cannot read lists."}, "b",
         "A policy sees only who is calling, which tool, and the tool's inputs. It cannot ask 'is this person a VIP?'. Keep the list updated, or check inside the tool as well.")],
        "<b>Put the 'never' rules where the model cannot argue with them.</b> A forbid rule in front of the tool is a lock, not a request. "
        "But a policy knows only the request, not your data, so a rule like 'VIPs' needs a list that someone keeps up to date.")

# ================================================================================================ TAB 5
with tabs[4]:
    st.subheader("Can you get around your own rule?")
    st.markdown("A rule compares **text**. Try to reset a VIP's password in a way the rule does not recognise.")
    if S.mode == "practice":
        if not (S.on["block_vip_reset_password"] and all(S.on[n] for n in ("allow_get_ticket", "allow_get_user", "allow_reset_password"))):
            st.warning("Switch all four rules on in tabs 3 and 4 first.")
        S.strict = st.toggle("🔧 Hardened tools: the tool itself refuses ids that are not written exactly EMP-1234", value=S.strict)
    else:
        st.caption("On AWS the result depends on which version of the Lambda the trainer deployed: strict or relaxed. Compare with your neighbour.")
    tries = [("EMP-1001 written in small letters", {"user_id": "emp-1001"}), ("EMP-1001 with a space in front", {"user_id": " EMP-1001"}),
             ("EMP-1001 with a space at the end", {"user_id": "EMP-1001 "}), ("No id at all", {})]
    custom = st.text_input("Your own try (type an id for a VIP, any spelling you like)", "")
    if custom:
        tries.append((f"Your try: {custom!r}", {"user_id": custom}))
    if st.button("▶ Try them all", type="primary", key="m5"):
        rows = []
        for label, args in tries:
            r = call("reset_password", args, engine() if S.mode == "practice" else None)
            v, d = verdict(r)
            uid = str(args.get("user_id", "")).strip().upper()
            reset_done = r.ok and "temporary password" in d and uid in VIPS
            rows.append({"Try": label, "Policy + tool said": v, "Detail": d, "Engine": r.policy["why"] if r.policy else "",
                         "A VIP password was reset?": "⚠ YES, BYPASSED" if reset_done else "no"})
        S.t5 = pd.DataFrame(rows)
    if S.t5 is not None:
        st.dataframe(S.t5, hide_index=True, width="stretch")
        if (S.t5["A VIP password was reset?"].str.contains("YES")).any():
            st.markdown('<div class="bad"><b>The rule was bypassed.</b> The rule compared the text <code>emp-1001</code> with <code>EMP-1001</code> and found them different. '
                        'The tool tidied the text and reset the VIP. Cedar and the tool disagreed about who the user is.</div>', unsafe_allow_html=True)
            st.caption("Idea: add \"emp-1001\" to the list in the rule. Then try a space. You will never list every spelling. Better: switch on the hardened tools above and run again.")
        elif S.t5["Policy + tool said"].str.contains("passed").any() or S.t5["Policy + tool said"].str.contains("ALLOWED").any():
            st.markdown('<div class="ok">No VIP reset happened. The tool refused every spelling it does not recognise: a second lock behind the policy.</div>', unsafe_allow_html=True)
    st.caption("The last try, with no id, shows something else: a Cedar rule that cannot be worked out (the id is missing) is skipped, not applied. Another reason to keep a second check in the tool.")
    thinking("t5", [
        ("Why did 'emp-1001' get past the VIP rule?",
         {"a": "Cedar compares the exact text, and the tool tidies the text itself, so the two disagreed.", "b": "VIPs can use small letters.", "c": "The Gateway was off."}, "a",
         "The policy saw emp-1001, which is not on the list. The tool turned it into EMP-1001 and reset the VIP."),
        ("What is the best extra protection?",
         {"a": "A longer VIP list.", "b": "A check inside the tool too (exact id form, VIP check), so one mistake does not open the door.", "c": "A bigger model."}, "b",
         "Defence in depth: policy at the door, plus a check in the tool. Each covers the other's blind spot.")],
        "<b>One lock is not enough.</b> A policy is only as good as the text it compares. If the tool reads the same text differently, the rule can be walked around. "
        "Put a policy at the Gateway AND a check in the tool, and test both with awkward inputs before you ship.")

# ================================================================================================ TAB 6
with tabs[5]:
    st.subheader("How it works")
    svg = """<div style="font-family:Segoe UI,Arial,sans-serif"><svg viewBox="0 0 1100 330" width="100%" style="background:#fff;border-radius:12px">
    <defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5L0 10z" fill="#555"/></marker></defs>
    <g stroke-width="2.2"><rect x="10" y="40" width="180" height="110" rx="14" fill="#EEE6F7" stroke="#6A3FA0"/><rect x="250" y="40" width="250" height="110" rx="14" fill="#E3F1EE" stroke="#0E7068"/>
    <rect x="560" y="40" width="230" height="110" rx="14" fill="#FBEEDB" stroke="#A8570A"/><rect x="850" y="40" width="240" height="110" rx="14" fill="#E2EBF7" stroke="#1F5AA6"/></g>
    <g text-anchor="middle" fill="#161a23" font-size="17"><text x="100" y="75" font-weight="700" font-size="19">🤖 Agent</text><text x="100" y="102">asks for a tool call</text>
    <text x="375" y="75" font-weight="700" font-size="19">🚪 Gateway</text><text x="375" y="102">asks the policy engine:</text><text x="375" y="124">"may this caller do this?"</text>
    <text x="675" y="75" font-weight="700" font-size="19">🛡️ Policy engine</text><text x="675" y="102">your Cedar rules</text><text x="675" y="124">default deny · forbid wins</text>
    <text x="970" y="75" font-weight="700" font-size="19">⚙️ Lambda tool</text><text x="970" y="102">runs only if allowed</text><text x="970" y="124">and checks its inputs too</text></g>
    <g stroke="#555" stroke-width="2.2" fill="none" marker-end="url(#a)"><line x1="192" y1="95" x2="248" y2="95"/><line x1="502" y1="80" x2="558" y2="80"/><line x1="558" y1="115" x2="502" y2="115"/><line x1="792" y1="95" x2="848" y2="95"/></g>
    <g fill="#161a23" font-size="16"><text x="10" y="200" font-weight="700">What a rule looks like</text>
    <text x="10" y="226" font-family="Consolas,monospace">forbid( principal,  action == AgentCore::Action::"askit-lambda___reset_password",  resource == AgentCore::Gateway::"&lt;arn&gt;" )</text>
    <text x="10" y="248" font-family="Consolas,monospace">when { ["EMP-1001","EMP-1012","EMP-1023"].contains(context.input.user_id) };</text>
    <text x="10" y="284" fill="#555">permit / forbid = the decision · principal = who · action = which tool · resource = which Gateway · when = extra conditions on the tool's inputs</text>
    <text x="10" y="308" fill="#555">Order of thinking: any matching forbid → DENY.  Else any matching permit → ALLOW.  Else → DENY.</text></g></svg></div>"""
    if hasattr(st, "iframe"):
        st.iframe(svg, height=360)
    else:
        components.html(svg, height=360)
    st.markdown("### Where can a rule live?")
    st.dataframe(pd.DataFrame([
        ["In the prompt (Day 11 D1)", "The model only", "Cheap, easy to write", "The model can be talked out of it: a request, not a lock"],
        ["In agent code, in front of the tool (D3/D4)", "Your agent's code", "Runs before the tool; you control it", "Every agent needs its own copy"],
        ["Policy at the Gateway (today)", "Caller, tool, tool inputs", "One place for all agents; audited; model cannot bypass", "Does not know your data (is this a VIP?); text must match exactly"],
        ["Check inside the tool / Lambda", "The tool's own data", "Knows the truth (database)", "Hidden from the platform team; each tool repeats it"],
        ["Lambda interceptor on the Gateway", "The request and reply, with your own code", "Can look up data, edit or redact", "More code to run and secure"],
        ["Bedrock Guardrails", "Text going in and out of the model", "Content filters, PII, topics", "Not about which tool may run"],
        ["IAM", "Which AWS identity may call the Gateway", "Strong and familiar", "Says who, not what they ask for"]],
        columns=["Where", "What it can see", "Good for", "Watch out"]), hide_index=True, width="stretch")
    with st.expander("💼 Questions a client asks · tap to see a good answer"):
        st.markdown("- **\"Can the agent be argued out of the rule?\"** No. The rule is checked by the Gateway, not by the model. The model never sees it.\n"
                    "- **\"How do we know a rule worked?\"** Every decision is logged. Start in LOG ONLY, look at what would have been blocked, then ENFORCE.\n"
                    "- **\"Who writes the rules?\"** A person who understands the business writes it in plain words, the console can draft the Cedar, and a person reviews it. Never paste a generated rule unread.\n"
                    "- **\"What does it cost?\"** About $0.000025 per checked request at the time of writing (that is $25 for a million). Check the AWS price page before you quote.\n"
                    "- **\"Is one rule enough for 'no VIP resets'?\"** Not alone. Add a check in the tool and test awkward inputs (tab 5).")
    st.markdown('<div class="client"><b>💼 Say this to a client:</b> "The model can be fooled, so the \'never\' rules do not live in the model. They live in a policy in front of the tool, written in plain rules, '
                'logged on every decision, and backed by a check inside the tool."</div>', unsafe_allow_html=True)
    st.markdown("**Stretch (if you finish early):** in the console, use **create policy from plain English** to draft the VIP rule. Compare its Cedar with yours. Which is safer? Which would you ship?")

# ================================================================================================ LESSONS
with tabs[6]:
    names = {"t2": "2 · Default deny", "t3": "3 · Allow the tools", "t4": "4 · Block VIPs", "t5": "5 · Get around it"}
    st.subheader("🎓 Lessons learnt")
    st.caption("Each lesson unlocks when you answer the two thinking questions at the bottom of its tab.")
    st.progress(len(S.lessons) / len(names), text=f"Lessons unlocked: {len(S.lessons)} of {len(names)}")
    for k, nm in names.items():
        if k in S.lessons:
            st.markdown(f'<div class="lesson"><b>🎓 Tab {nm}</b><br>{S.lessons[k]}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="lock">🔒 Tab {nm}: not unlocked yet</div>', unsafe_allow_html=True)
    if S.lessons:
        txt = "# My lessons from Lab 16B\n\n" + "\n\n".join(f"## Tab {names[k]}\n" + re.sub(r"<[^>]+>", "", S.lessons[k]) for k in names if k in S.lessons)
        st.download_button("⬇ Download my lessons (.md)", txt, file_name="lab16b_lessons.md")
