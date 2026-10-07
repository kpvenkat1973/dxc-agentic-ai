"""Architecture diagram (SVG) for the Lab 3 RAG app. Same look as the Lab 4 diagram; follows the sidebar settings."""
from html import escape

W_NODE, H_NODE = 190, 112
COLS = [50, 285, 520, 755, 990]

PAL = {
    "ing": ("#E3F1EE", "#0E7068"),   # teal
    "ret": ("#E2EBF7", "#1F5AA6"),   # blue
    "llm": ("#EEE6F7", "#6A3FA0"),   # plum
    "safe": ("#FBEEDB", "#A8570A"),  # amber
    "off": ("#F1F1F1", "#9AA0A8"),
}


def node(x, y, icon, title, sub, kind="ret", off=False):
    fill, stroke = PAL["off" if off else kind]
    dash = ' stroke-dasharray="6 5"' if off else ""
    badge = (f'<rect x="{x + W_NODE - 46}" y="{y + 8}" width="38" height="20" rx="10" fill="#9AA0A8"/>'
             f'<text x="{x + W_NODE - 27}" y="{y + 22}" class="badge">OFF</text>') if off else ""
    lines = sub if isinstance(sub, list) else [sub]
    subs = "".join(f'<text x="{x + W_NODE/2}" y="{y + 84 + i*16}" class="sub">{escape(s)}</text>' for i, s in enumerate(lines))
    return (f'<g class="{"off" if off else ""}"><rect x="{x}" y="{y}" width="{W_NODE}" height="{H_NODE}" rx="14" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="2"{dash}/>'
            f'<text x="{x + W_NODE/2}" y="{y + 36}" class="ic">{icon}</text>'
            f'<text x="{x + W_NODE/2}" y="{y + 64}" class="tt" fill="{stroke}">{escape(title)}</text>{subs}{badge}</g>')


def arrow(x1, y1, x2, y2):
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" class="ar" marker-end="url(#h)"/>'


def render(chunk_size, overlap, top_k, show_ctx, embed_model, chat_model, fallback):
    overlap = min(overlap, chunk_size // 2)          # the app caps overlap at half the chunk size
    y1, y2, y3 = 92, 346, 530
    s = []
    # lanes
    s.append('<rect x="20" y="40" width="1200" height="200" rx="22" class="lane"/>')
    s.append('<text x="44" y="72" class="lt">① Ingestion pipeline</text><text x="1196" y="72" class="lh" text-anchor="end">runs when you click Load KB or Index documents</text>')
    s.append('<rect x="20" y="290" width="1200" height="408" rx="22" class="lane"/>')
    s.append('<text x="44" y="322" class="lt">② Retrieval, augmentation &amp; generation</text><text x="1196" y="322" class="lh" text-anchor="end">online · runs for every question</text>')
    # ingestion nodes
    ing = [("📄", "Load", ["20 AskIT KB articles", "or your PDF / DOCX / MD"]),
           ("✂️", "Chunk", [f"fixed {chunk_size} chars", f"{overlap} overlap"]),
           ("🔢", "Embed", [embed_model, "one vector per chunk"]),
           ("🗄️", "Store", ["local vector store", "JSON + numpy"])]
    for i, (ic, t, sub) in enumerate(ing):
        s.append(node(COLS[i], y1, ic, t, sub, "ing"))
        if i:
            s.append(arrow(COLS[i-1] + W_NODE + 4, y1 + H_NODE/2, COLS[i] - 6, y1 + H_NODE/2))
    # retrieval row 1
    r1 = [("👤", "Question", ["user asks", "in plain language"], "ret"),
          ("🔢", "Embed query", [embed_model], "ret"),
          ("🔍", "Search", ["cosine similarity", f"top {top_k} chunks"], "ret"),
          ("🧾", "Augment prompt", [f"top {top_k} chunks + rules", "+ question"], "llm"),
          ("🧠", "Generate", [chat_model], "llm")]
    for i, (ic, t, sub, k) in enumerate(r1):
        s.append(node(COLS[i], y2, ic, t, sub, k))
        if i:
            s.append(arrow(COLS[i-1] + W_NODE + 4, y2 + H_NODE/2, COLS[i] - 6, y2 + H_NODE/2))
    # retrieval row 2 (right to left)
    s.append(arrow(COLS[4] + W_NODE/2, y2 + H_NODE + 4, COLS[4] + W_NODE/2, y3 - 6))
    s.append(node(COLS[4], y3, "✅", "Answer", ["cites [file #chunk]", "LLM says \"I don't know\""], "ing"))
    s.append(node(COLS[3], y3, "🔎", "Retrieved chunks", ["with similarity score", "shown under the answer"], "ret", not show_ctx))
    s.append(arrow(COLS[4] - 4, y3 + H_NODE/2, COLS[3] + W_NODE + 6, y3 + H_NODE/2))
    # same store connector (Store -> Search)
    sx, qx = COLS[3] + W_NODE/2, COLS[2] + W_NODE/2
    s.append(f'<path d="M{sx} {y1 + H_NODE + 4} V270 H{qx} V{y2 - 6}" class="ar link" marker-end="url(#h2)"/>')
    s.append(f'<text x="{(sx + qx)/2}" y="263" class="lbl link-t" text-anchor="middle">same store</text>')
    # strip
    s.append('<text x="44" y="748" class="lt">③ Reliability &amp; experiments</text>')
    chips = [("🔁", "Provider fallback", "on · Bedrock → Azure → OpenAI" if fallback else "off · needs 2+ providers"),
             ("🧪", "Mini eval", "12 questions, no LLM cost"),
             ("📝", "Experiments table", "copy into experiment.md")]
    for i, (ic, t, sub) in enumerate(chips):
        x = 400 + i * 232
        s.append(f'<rect x="{x}" y="712" width="218" height="60" rx="16" class="chip"/>'
                 f'<text x="{x + 109}" y="737" class="ct" text-anchor="middle">{ic} <tspan font-weight="700">{escape(t)}</tspan></text>'
                 f'<text x="{x + 109}" y="758" class="cs" text-anchor="middle" font-size="13">{escape(sub)}</text>')
    svg = "".join(s)
    return f"""<!doctype html><html><head><style>
body{{margin:0;font-family:"Segoe UI","Source Sans Pro",system-ui,sans-serif;background:transparent}}
.wrap{{background:#FFFFFF;border:1px solid #E3E6EA;border-radius:18px;padding:10px}}
svg{{width:100%;height:auto;display:block}}
.lane{{fill:#FAFAF7;stroke:#D9D6CE;stroke-width:1.5}}
.lt{{font-size:20px;font-weight:700;fill:#17202E}}
.lh{{font-size:14px;fill:#6B7380}}
.ic{{font-size:28px;text-anchor:middle}}
.tt{{font-size:17px;font-weight:700;text-anchor:middle}}
.sub{{font-size:13px;fill:#4F5866;text-anchor:middle}}
.off .sub,.off .ic{{opacity:.45}}
.badge{{font-size:11px;font-weight:700;fill:#fff;text-anchor:middle}}
.ar{{stroke:#6B7380;stroke-width:2;fill:none}}
.link{{stroke:#1F5AA6;stroke-width:2.2;stroke-dasharray:8 6}}
.link-t{{fill:#1F5AA6;font-weight:600}}
.lbl{{font-size:13px;fill:#6B7380;paint-order:stroke;stroke:#FAFAF7;stroke-width:5px}}
.chip{{fill:#F1F3F6;stroke:#D9DDE3}}
.ct{{font-size:14px;fill:#17202E}}
.cs{{fill:#6B7380}}
</style></head><body><div class="wrap">
<svg viewBox="0 0 1240 790" role="img" aria-label="RAG pipeline architecture">
<defs><marker id="h" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#6B7380"/></marker>
<marker id="h2" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#1F5AA6"/></marker></defs>
<text x="620" y="24" text-anchor="middle" style="font-size:22px;font-weight:700;fill:#17202E">AskIT · RAG Lab architecture</text>
{svg}</svg></div></body></html>"""
