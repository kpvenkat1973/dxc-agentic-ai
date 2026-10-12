"""diagram.py  --  draws the architecture picture shown in the app (an SVG). You do not need to edit this file."""
from html import escape

W, H = 200, 118
PAL = {
    "ui": ("#E2EBF7", "#1F5AA6"),      # blue   - screen / user
    "agent": ("#EEE6F7", "#6A3FA0"),   # plum   - agent / LLM
    "mem": ("#E3F1EE", "#0E7068"),     # teal   - memory / state
    "tool": ("#FBEEDB", "#A8570A"),    # amber  - tools / actions
    "human": ("#FDE7E7", "#B42318"),   # red    - human / approval
    "off": ("#F1F1F1", "#9AA0A8"),
    "done": ("#DCF5E3", "#1B7F3B"),
    "wait": ("#FFF4CC", "#B7791F"),
    "fail": ("#FDE2E1", "#C0362C"),
}


def node(x, y, icon, title, lines, kind="ui", file="", off=False, w=W, h=H, pulse=False, badge_text="OFF"):
    fill, stroke = PAL["off" if off else kind]
    dash = ' stroke-dasharray="7 5"' if off else ""
    cls = "n off" if off else ("n pulse" if pulse else "n")
    sub = "".join(f'<text x="{x + w/2}" y="{y + 74 + i*16}" class="sub">{escape(s)}</text>' for i, s in enumerate(lines))
    f = (f'<text x="{x + w/2}" y="{y + h - 9}" class="file">{escape(file)}</text>') if file else ""
    badge = (f'<rect x="{x + w - 46}" y="{y + 8}" width="38" height="20" rx="10" fill="#9AA0A8"/>'
             f'<text x="{x + w - 27}" y="{y + 22}" class="badge">{badge_text}</text>') if off else ""
    return (f'<g class="{cls}"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" fill="{fill}" stroke="{stroke}" '
            f'stroke-width="2.2"{dash}/><text x="{x + w/2}" y="{y + 32}" class="ic">{icon}</text>'
            f'<text x="{x + w/2}" y="{y + 56}" class="tt" fill="{stroke}">{escape(title)}</text>{sub}{f}{badge}</g>')


def arrow(x1, y1, x2, y2, label="", dashed=False, lx=None, ly=None):
    d = ' stroke-dasharray="6 5"' if dashed else ""
    t = ""
    if label:
        tx = lx if lx is not None else (x1 + x2) / 2
        ty = ly if ly is not None else (y1 + y2) / 2 - 7
        t = f'<text x="{tx}" y="{ty}" class="lbl" text-anchor="middle">{escape(label)}</text>'
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" class="ar"{d} marker-end="url(#h)"/>{t}'


def path(d, label="", lx=0, ly=0, dashed=False):
    da = ' stroke-dasharray="6 5"' if dashed else ""
    t = f'<text x="{lx}" y="{ly}" class="lbl" text-anchor="middle">{escape(label)}</text>' if label else ""
    return f'<path d="{d}" class="ar"{da} marker-end="url(#h)"/>{t}'


def lane(x, y, w, h, title, hint=""):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="20" class="lane"/>'
            f'<text x="{x + 20}" y="{y + 28}" class="lt">{escape(title)}</text>'
            + (f'<text x="{x + w - 18}" y="{y + 28}" class="lh" text-anchor="end">{escape(hint)}</text>' if hint else ""))


def page(svg_body, width, height):
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
body{{margin:0;font-family:"Aptos Narrow","Segoe UI",system-ui,sans-serif;background:transparent}}
.wrap{{background:#fff;border:1px solid #E3E6EA;border-radius:18px;padding:8px}}
svg{{width:100%;height:auto;display:block}}
.lane{{fill:#FAFAF7;stroke:#D9D6CE;stroke-width:1.4}}
.lt{{font-size:18px;font-weight:700;fill:#17202E}} .lh{{font-size:13px;fill:#6B7380}}
.ic{{font-size:26px;text-anchor:middle}} .tt{{font-size:17px;font-weight:700;text-anchor:middle}}
.sub{{font-size:13px;fill:#3F4855;text-anchor:middle}} .file{{font-size:12px;fill:#6B7380;text-anchor:middle;font-family:Consolas,monospace}}
.off .sub,.off .ic,.off .file{{opacity:.45}} .badge{{font-size:11px;font-weight:700;fill:#fff;text-anchor:middle}}
.ar{{stroke:#6B7380;stroke-width:2;fill:none}}
.lbl{{font-size:12.5px;fill:#4F5866;paint-order:stroke;stroke:#fff;stroke-width:5px}}
.pulse rect{{animation:p 1.2s ease-in-out infinite}} @keyframes p{{50%{{stroke-width:5}}}}
</style></head><body><div class="wrap"><svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
<defs><marker id="h" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
<path d="M0 0L10 5L0 10z" fill="#6B7380"/></marker></defs>{svg_body}</svg></div></body></html>"""


# ------------------------------------------------------------------------------------------------ Lab 7 picture
def lab7(compaction=True, memory=True, compact_at=1500, keep_last=4, provider="Bedrock Nova"):
    X = [20, 262, 504, 746, 988]
    y1, y2 = 70, 330
    s = [lane(5, 10, 1200, 225, "① One question, end to end", "runs for every message you send"),
         lane(5, 265, 1200, 230, "② The three memory pieces the agent uses", "dashed = switched off in the sidebar")]
    s.append(node(X[0], y1, "👤", "You", ["type a question or", "press ▶ Play script"], "ui"))
    s.append(node(X[1], y1, "🖥️", "Streamlit screen", ["chat, sliders, charts", "sends to the agent"], "ui", "app.py"))
    s.append(node(X[2], y1, "🤖", "AskIT agent", ["create_agent(...) loop:", "think → tool → answer"], "agent", "memory_agent.py"))
    s.append(node(X[3], y1, "🧩", "Middleware", [f"Compaction: {'ON at ' + str(compact_at) if compaction else 'OFF'}",
                                                 "Context meter (bars)"], "agent", "SummarizationMiddleware"))
    s.append(node(X[4], y1, "🧠", "LLM", [provider, "paid per token sent"], "agent", "model_factory.py"))
    for i in range(4):
        s.append(arrow(X[i] + W + 3, y1 + H/2, X[i+1] - 5, y1 + H/2))
    s.append(node(X[1], y2, "🧵", "Short-term memory", ["checkpointer keeps", "ONE chat (thread_id)"], "mem", "InMemorySaver"))
    s.append(node(X[2], y2, "🛠️", "Tools", ["search_kb · get_ticket", "update · reset (mock)"], "tool", "askit_core/tools.py"))
    s.append(node(X[3], y2, "🗜️", "Compacted chat", [f"old part → 1 summary", f"newest {keep_last} kept word for word"],
                  "mem", "summary message", off=not compaction))
    s.append(node(X[4], y2, "🗂️", "Long-term memory", ["store: notes per user", "save_note · recall_notes"], "mem",
                  "InMemoryStore", off=not memory))
    a = X[2] + W/2
    s.append(path(f"M{a-50} {y1+H+3} V{y1+H+40} H{X[1]+W/2} V{y2-5}", "loads / saves the chat", X[1]+W/2+70, y1+H+33))
    s.append(arrow(a, y1 + H + 3, a, y2 - 5, "calls", lx=a + 24, ly=y1 + H + 70))
    s.append(path(f"M{X[3]+W/2} {y1+H+3} V{y2-5}", "rewrites the chat", X[3]+W/2+60, y1+H+70, dashed=not compaction))
    s.append(path(f"M{a+50} {y1+H+3} V{y1+H+48} H{X[4]+W/2} V{y2-5}", "new chat? read notes", X[4]+W/2-60, y1+H+41,
                  dashed=not memory))
    return page("".join(s), 1210, 505)


# ------------------------------------------------------------------------------------------------ Lab 8 picture
def lab8(status=None, route=None, checkpoints=0, provider="Bedrock Nova", vip_rule=False):
    """status: {node_name: 'done' | 'wait' | 'fail'} from the last run. route: the specialist the router picked."""
    status = status or {}
    w, h = 158, 112
    X = [12, 192, 372, 562, 742, 922, 1102]
    y = 95

    def k(name, base):
        return status.get(name, base)

    def kind_of(name, base):
        st = status.get(name)
        return st if st in ("done", "wait", "fail") else base

    s = [lane(2, 8, 1268, 420, "① The multi-agent graph (LangGraph StateGraph)",
              "green = ran · amber = waiting for a human · red = crashed · dashed = skipped this time")]
    s.append(node(X[0], y + 80, "🎫", "Ticket", ["from the user", "+ who sent it"], "ui", "app.py", w=w, h=h))
    s.append(node(X[1], y + 80, "🧭", "Router", ["LLM picks ONE team", f"→ {route}" if route else "Network/Access/..."],
                  kind_of("router", "agent"), "router()", w=w, h=h))
    specs = [("network_agent", "🌐", "Network"), ("access_agent", "🔐", "Access"),
             ("hardware_agent", "💻", "Hardware"), ("general_agent", "📦", "General")]
    sy = [40, 132, 224, 316]
    for (name, ic, title), yy in zip(specs, sy):
        skipped = bool(route) and route != title
        s.append(node(X[2], yy, ic, f"{title} agent", [f"{name} · READ tools"], kind_of(name, "agent"), "",
                      off=skipped and name not in status, w=w + 30, h=84, badge_text="SKIP"))
        s.append(arrow(X[1] + w + 3, y + 80 + h/2, X[2] - 5, yy + 42, dashed=skipped))
        s.append(arrow(X[2] + w + 33, yy + 42, X[3] - 5, y + 80 + h/2, dashed=skipped))
    s.append(node(X[3], y + 80, "📏", "Policy", ["plain code, NO LLM", "VIP rule ON" if vip_rule else "approval needed?"],
                  kind_of("policy", "tool"), "policy()", w=w, h=h))
    s.append(node(X[4], y + 80, "🙋", "Human approval", ["graph PAUSES", "interrupt()"], kind_of("human_approval", "human"),
                  "human_approval()", w=w, h=h, pulse=status.get("human_approval") == "wait"))
    s.append(node(X[5], y + 80, "⚙️", "Act", ["the ONLY write", "reset_password"], kind_of("act", "tool"), "act()", w=w, h=h))
    s.append(node(X[6], y + 80, "✉️", "Respond", ["reply to the user", "no LLM"], kind_of("respond", "ui"), "respond()",
                  w=w - 4, h=h))
    s.append(arrow(X[0] + w + 3, y + 80 + h/2, X[1] - 5, y + 80 + h/2))
    for a, b in ((3, 4), (4, 5), (5, 6)):
        s.append(arrow(X[a] + w + 3, y + 80 + h/2, X[b] - 5, y + 80 + h/2))
    s.append(path(f"M{X[3] + w/2} {y + 80 + h + 3} V{y + 80 + h + 52} H{X[6] + w/2 - 2} V{y + 80 + h + 5}",
                  "no approval needed → straight to Respond", (X[3] + X[6] + w) / 2, y + 80 + h + 46, dashed=True))
    s.append(lane(2, 442, 1268, 92, "② Under every node", ""))
    chips = [("💾", "Checkpointer", f"state saved after every node · {checkpoints} saved so far"),
             ("🧠", "LLM", f"{provider} · used only by router + specialists"),
             ("🛠️", "Tools", "askit_core/tools.py · write tool only in Act")]
    for i, (ic, t, sub) in enumerate(chips):
        x = 230 + i * 345
        s.append(f'<rect x="{x}" y="470" width="330" height="54" rx="14" fill="#F1F3F6" stroke="#D9DDE3"/>'
                 f'<text x="{x + 165}" y="492" text-anchor="middle" font-size="15" font-weight="700">{ic} {escape(t)}</text>'
                 f'<text x="{x + 165}" y="512" text-anchor="middle" font-size="12.5" fill="#4F5866">{escape(sub)}</text>')
    return page("".join(s), 1272, 540)
