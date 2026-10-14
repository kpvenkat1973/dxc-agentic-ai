"""diagram.py  --  draws the pictures shown in the Lab 10 app (SVG). You do not need to edit this file."""
from html import escape

KIND = {"llm": ("#6A3FA0", "#EEE6F7", "model"), "tool": ("#A8570A", "#FBEEDB", "tool"), "agent": ("#1F5AA6", "#E2EBF7", "run")}


def _wrap(body, w, h):
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
body{{margin:0;font-family:"Aptos Narrow","Segoe UI",system-ui,sans-serif;background:transparent}}
.wrap{{background:#fff;border:1px solid #E3E6EA;border-radius:16px;padding:6px}}
svg{{width:100%;height:auto;display:block}} text{{font-family:"Aptos Narrow","Segoe UI",system-ui,sans-serif}}
</style></head><body><div class="wrap"><svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg">
<defs><marker id="h" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#5a6478"/></marker></defs>
{body}</svg></div></body></html>"""


def waterfall(trace, hilite=None):
    """One bar per span on a time axis. Wide bar = slow. Returns (html, height)."""
    spans = trace["spans"]
    total = max(trace.get("ms", 0), max((s["start_ms"] + s["ms"] for s in spans), default=1), 1)
    W, LEFT, RIGHT, ROW, TOP = 1100, 230, 250, 36, 34
    bar_w = W - LEFT - RIGHT
    H = TOP + ROW * len(spans) + 36
    out = [f'<text x="{LEFT}" y="20" font-size="14" fill="#5a6478">0 ms</text>',
           f'<text x="{LEFT + bar_w}" y="20" font-size="14" fill="#5a6478" text-anchor="end">{total:,} ms</text>',
           f'<line x1="{LEFT}" y1="26" x2="{LEFT + bar_w}" y2="26" stroke="#c9ced8"/>']
    for i, s in enumerate(spans):
        y = TOP + i * ROW
        col, soft, tag = KIND.get(s["kind"], KIND["tool"])
        if s.get("error"):
            col, soft = "#B42318", "#FDE7E7"
        x = LEFT + bar_w * s["start_ms"] / total
        w = max(4, bar_w * s["ms"] / total)
        label = f'{i + 1}. {s["name"]}' + (f' (call {s["repeat"]})' if s.get("repeat", 1) > 1 else "")
        out.append(f'<text x="{LEFT - 10}" y="{y + 22}" font-size="16" text-anchor="end" fill="#141a2a">{escape(label[:30])}</text>')
        out.append(f'<rect x="{LEFT}" y="{y + 4}" width="{bar_w}" height="{ROW - 10}" rx="6" fill="#f6f7fb"/>')
        out.append(f'<rect x="{x:.1f}" y="{y + 4}" width="{w:.1f}" height="{ROW - 10}" rx="6" fill="{soft}" stroke="{col}" stroke-width="2"/>')
        info = f'{s["ms"]:,} ms' + (f' · {s["tokens_in"]:,} in / {s["tokens_out"]:,} out' if s["kind"] == "llm" else "")
        out.append(f'<text x="{LEFT + bar_w + 10}" y="{y + 22}" font-size="15" fill="{col}">{escape(info)}</text>')
    out.append(f'<g font-size="14"><rect x="{LEFT}" y="{H - 22}" width="14" height="14" rx="3" fill="#EEE6F7" stroke="#6A3FA0"/><text x="{LEFT + 20}" y="{H - 10}" fill="#141a2a">model call</text>'
               f'<rect x="{LEFT + 120}" y="{H - 22}" width="14" height="14" rx="3" fill="#FBEEDB" stroke="#A8570A"/><text x="{LEFT + 140}" y="{H - 10}" fill="#141a2a">tool call</text>'
               f'<rect x="{LEFT + 230}" y="{H - 22}" width="14" height="14" rx="3" fill="#FDE7E7" stroke="#B42318"/><text x="{LEFT + 250}" y="{H - 10}" fill="#141a2a">error</text></g>')
    return _wrap("".join(out), W, H), int(H * 0.85) + 24


def _box(x, y, w, h, icon, title, lines, col, soft, dash=False):
    d = ' stroke-dasharray="7 5"' if dash else ""
    sub = "".join(f'<text x="{x + w / 2}" y="{y + 70 + i * 17}" font-size="14" text-anchor="middle" fill="#141a2a">{escape(s)}</text>' for i, s in enumerate(lines))
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" fill="{soft}" stroke="{col}" stroke-width="2.2"{d}/>'
            f'<text x="{x + w / 2}" y="{y + 30}" font-size="24" text-anchor="middle">{icon}</text>'
            f'<text x="{x + w / 2}" y="{y + 54}" font-size="17" font-weight="700" text-anchor="middle" fill="{col}">{escape(title)}</text>{sub}')


def _arrow(x1, y1, x2, y2, label="", dashed=False):
    d = ' stroke-dasharray="6 5"' if dashed else ""
    t = f'<text x="{(x1 + x2) / 2}" y="{(y1 + y2) / 2 - 6}" font-size="13" text-anchor="middle" fill="#5a6478">{escape(label)}</text>' if label else ""
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#5a6478" stroke-width="2"{d} marker-end="url(#h)"/>{t}'


def architecture(has_langfuse=False):
    """The big picture of this lab: the agent, the tracer, and the three places a run can be seen."""
    b = []
    b.append(_box(20, 150, 190, 118, "🧑", "Question", ["from tab 1, 3 or 4"], "#1F5AA6", "#E2EBF7"))
    b.append(_box(270, 130, 230, 158, "🤖", "AskIT agent", ["ops_agent.py", "model call -> tool -> model call", "stops after 6 calls"], "#6A3FA0", "#EEE6F7"))
    b.append(_box(270, 330, 230, 100, "🛠️", "4 AskIT tools", ["askit_core/tools.py"], "#A8570A", "#FBEEDB"))
    b.append(_box(270, 10, 230, 90, "🧾", "Tracer", ["ops_trace.py: a span per step"], "#0E7068", "#E3F1EE"))
    b.append(_box(570, 130, 230, 158, "🧠", "The model", ["model_factory.py", "Bedrock Nova / Azure /", "OpenAI / Offline stand-in"], "#6A3FA0", "#EEE6F7"))
    b.append(_box(870, 10, 220, 100, "📁", "1 · This app", ["submission/traces.jsonl", "waterfall in tab 1"], "#1F5AA6", "#E2EBF7"))
    b.append(_box(870, 150, 220, 118, "🪢", "2 · Langfuse", ["open source, your team's", "project in the cloud"], "#0E7068", "#E3F1EE", dash=not has_langfuse))
    b.append(_box(870, 310, 220, 118, "☁️", "3 · AWS CloudWatch", ["Bedrock logs every call:", "who, tokens, model"], "#A8570A", "#FBEEDB"))
    b += [_arrow(210, 209, 270, 209), _arrow(500, 190, 570, 190, "ask"), _arrow(570, 240, 500, 240, "answer / tool request"),
          _arrow(385, 288, 385, 330, "run tool"), _arrow(385, 130, 385, 100, "records", True),
          _arrow(500, 55, 870, 55, "every span", True), _arrow(500, 80, 870, 190, "live (optional)", True),
          _arrow(800, 250, 870, 340, "Bedrock side: no code", True)]
    return _wrap("".join(b), 1110, 450), 400


def trace_anatomy():
    b = [_box(20, 20, 300, 120, "🧾", "TRACE", ["one question, start to finish", "total time, tokens, cost, answer"], "#0E7068", "#E3F1EE"),
         _box(430, 20, 300, 120, "🧩", "SPAN", ["one step inside the run", "start, duration, input, output"], "#6A3FA0", "#EEE6F7"),
         _box(840, 20, 250, 120, "🔖", "TAGS + SCORES", ["who, team, prompt version", "pass / fail from your evals"], "#A8570A", "#FBEEDB"),
         _arrow(320, 80, 430, 80, "has many"), _arrow(730, 80, 840, 80, "can carry")]
    return _wrap("".join(b), 1110, 160), 150
