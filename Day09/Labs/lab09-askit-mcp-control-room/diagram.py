"""diagram.py  --  draws the pictures shown in the Lab 9 app (SVG). You do not need to edit this file."""
from html import escape

W, H = 200, 118
PAL = {
    "ui": ("#E2EBF7", "#1F5AA6"),      # blue   - screen / user
    "agent": ("#EEE6F7", "#6A3FA0"),   # plum   - agent / LLM
    "mem": ("#E3F1EE", "#0E7068"),     # teal   - memory / state
    "tool": ("#FBEEDB", "#A8570A"),    # amber  - tools / actions
    "human": ("#FCE7F3", "#BE185D"),   # pink   - human / approval (red is kept for crashes only)
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



# ------------------------------------------------------------------------------------------------ Lab 9 pictures
HOME_NODES = {"stdio": ("🖥️", "This VM · stdio", ["child process", "stdin / stdout"], "askit_server.py"),
              "http": ("🌐", "This VM · HTTP", ["web service", "127.0.0.1:8777"], "askit_server.py --http"),
              "lambda": ("☁️", "AWS Lambda", ["Function URL", "https, public + key"], "aws/askit-mcp-lambda.zip")}


def lab9(active="stdio", fired=None, ctl_summary=""):
    """The main picture: ONE agent on the left, three possible homes for the tool server on the right."""
    fired = fired or []
    s = [lane(5, 10, 1250, 470, "The same agent, three possible homes for its tools", "only the connect line changes")]
    s.append(node(25, 130, "🙋", "Question", ["from the user"], "ui", "app.py"))
    s.append(node(255, 130, "🧠", "Agent", ["LLM + tool list", "same code always"], "agent", "run_agent()", pulse=True))
    s.append(node(485, 130, "🛡️", "MCP client + controls", ["role · timeout · retry", "redact · log"], "tool", "guarded_call()", w=220,
                  pulse=bool(fired)))
    s.append(arrow(228, 189, 252, 189)); s.append(arrow(458, 189, 482, 189, "tool call", lx=470, ly=170))
    ys = {"stdio": 45, "http": 190, "lambda": 335}
    for kind, (ic, title, lines, f) in HOME_NODES.items():
        on = kind == active
        s.append(node(810, ys[kind], ic, title, lines, "mem" if on else "off", f, w=230, h=118, off=not on, badge_text="OFF"))
        s.append(arrow(708, 189, 807, ys[kind] + 59, "JSON messages" if on else "", dashed=not on, lx=770, ly=(189 + ys[kind] + 59) / 2 - 6))
    s.append(node(1080, 190, "🛠️", "4 tools", ["search_kb · get_ticket", "update_ticket ·", "reset_password"], "tool", "tools.py", w=170, h=132))
    for kind in ys:
        s.append(arrow(1043, ys[kind] + 59, 1077, 249, dashed=kind != active))
    s.append(f'<text x="30" y="440" class="lbl" style="font-size:15px" text-anchor="start">Controls now: {escape(ctl_summary)}</text>')
    return page("".join(s), 1260, 490)


def pipeline(fired=None, blocked=False):
    """The controls pipeline around ONE tool call. `fired` = names of controls that did something."""
    fired = " ".join(fired or []).lower()
    stages = [("🧑‍⚖️", "Role / VIP block", ["plain code,", "before the call"], "role" in fired or "vip" in fired, "tool"),
              ("⏱️", "Timeout + retry", ["wait N seconds,", "try again"], "retry" in fired or "timeout" in fired, "tool"),
              ("🔌", "Tool server", ["runs the tool"], not blocked, "mem"),
              ("🙋", "Server asks you", ["“are you sure?”", "(elicitation)"], "server asked" in fired, "human"),
              ("🕶️", "Redact", ["mask names,", "emails, phones"], "redact" in fired, "tool"),
              ("🧠", "Model sees", ["only what is left"], True, "agent")]
    s = [lane(5, 10, 1250, 190, "One tool call, left to right", "highlighted = this control did something")]
    x = 20
    for i, (ic, t, lines, on, kind) in enumerate(stages):
        s.append(node(x, 55, ic, t, lines, kind, "", w=185, h=118, off=not on and kind not in ("mem", "agent"), badge_text="idle"))
        if i:
            s.append(arrow(x - 22, 114, x - 3, 114))
        x += 207
    return page("".join(s), 1260, 210)


def homes():
    """Static picture for tab 5: where each home can reach and who can reach it."""
    s = [lane(5, 10, 1250, 250, "Three homes, one protocol", "")]
    rows = [("stdio", 60, "Only this app can talk to it", "Reaches: files on this VM, the internet if the VM can"),
            ("http", 135, "Any program on this VM can call it", "Reaches: same as above. Also: other VMs if you open the port"),
            ("lambda", 210, "Anyone with URL + key, from anywhere", "Reaches: AWS services (IAM) and the internet; NOT your office network, unless VPC / PrivateLink")]
    for kind, y, who, reach in rows:
        ic, title, lines, f = HOME_NODES[kind]
        s.append(node(25, y - 10, ic, title, [], "mem", "", w=210, h=62))
        s.append(f'<text x="260" y="{y + 12}" class="tt" style="font-size:16px;text-anchor:start" fill="#3F4855">{escape(who)}</text>')
        s.append(f'<text x="260" y="{y + 34}" class="sub" style="text-anchor:start">{escape(reach)}</text>')
    return page("".join(s), 1260, 270)
