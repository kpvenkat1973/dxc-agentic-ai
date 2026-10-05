"""Architecture diagram (SVG) that reflects the live sidebar settings."""
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
    t = title
    badge = (f'<rect x="{x + W_NODE - 46}" y="{y + 8}" width="38" height="20" rx="10" fill="#9AA0A8"/>'
             f'<text x="{x + W_NODE - 27}" y="{y + 22}" class="badge">OFF</text>') if off else ""
    lines = sub if isinstance(sub, list) else [sub]
    subs = "".join(f'<text x="{x + W_NODE/2}" y="{y + 84 + i*16}" class="sub">{escape(s)}</text>' for i, s in enumerate(lines))
    return (f'<g class="{"off" if off else ""}"><rect x="{x}" y="{y}" width="{W_NODE}" height="{H_NODE}" rx="14" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="2"{dash}/>'
            f'<text x="{x + W_NODE/2}" y="{y + 36}" class="ic">{icon}</text>'
            f'<text x="{x + W_NODE/2}" y="{y + 64}" class="tt" fill="{stroke}">{escape(t)}</text>{subs}{badge}</g>')


def arrow(x1, y1, x2, y2):
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" class="ar" marker-end="url(#h)"/>'


def render(cfg, chat_model, embed_model, offline, load_sub=None):
    emb = "offline hash vectors" if offline else embed_model
    llm_name = "offline extractive" if offline else chat_model
    chunk_sub = "by section (§)" if cfg.chunking == "section" else f"fixed {cfg.chunk_size} chars / {cfg.overlap} overlap"
    search_sub = {"keyword": "BM25 keywords", "vector": "cosine similarity", "hybrid": "BM25 + vector (RRF)"}[cfg.search]
    y1, y2, y3 = 92, 346, 530
    s = []
    # lanes
    s.append('<rect x="20" y="40" width="1200" height="200" rx="22" class="lane"/>')
    s.append('<text x="44" y="72" class="lt">① Ingestion pipeline</text><text x="1196" y="72" class="lh" text-anchor="end">offline · runs when KB articles change</text>')
    s.append('<rect x="20" y="290" width="1200" height="408" rx="22" class="lane"/>')
    s.append('<text x="44" y="322" class="lt">② Retrieval, augmentation &amp; generation</text><text x="1196" y="322" class="lh" text-anchor="end">online · runs for every question</text>')
    # ingestion nodes
    ing = [("📄", "Load", load_sub or ["23 KB articles", "data/kb/*.md"]),
           ("🏷️", "Parse + metadata", ["audience · version", "status · effective"]),
           ("✂️", "Chunk", [chunk_sub]),
           ("🔢", "Embed", [emb]),
           ("🗄️", "Index", ["vectors + BM25", "+ metadata"])]
    for i, (ic, t, sub) in enumerate(ing):
        s.append(node(COLS[i], y1, ic, t, sub, "ing"))
        if i:
            s.append(arrow(COLS[i-1] + W_NODE + 4, y1 + H_NODE/2, COLS[i] - 6, y1 + H_NODE/2))
    # retrieval row 1
    r1 = [("👤", "Question", ["user asks", "in plain language"], "ret", False),
          ("🔢", "Embed query", [emb], "ret", cfg.search == "keyword"),
          ("🧭", "Metadata filter", ["current articles only", "user's audience"], "safe", not cfg.metadata_filter),
          ("🔍", "Search", [search_sub, f"candidate pool → top {cfg.top_k}"], "ret", False),
          ("🥇", "Rerank", ["LLM scores 0–10", "keeps the best"], "ret", not cfg.rerank)]
    for i, (ic, t, sub, k, off) in enumerate(r1):
        s.append(node(COLS[i], y2, ic, t, sub, k, off))
        if i:
            s.append(arrow(COLS[i-1] + W_NODE + 4, y2 + H_NODE/2, COLS[i] - 6, y2 + H_NODE/2))
    # retrieval row 2 (right to left)
    r2 = [(4, "🛡️", "Guard", ["enough evidence?", f"threshold {cfg.guard_threshold:.2f}"], "safe", not cfg.guard),
          (3, "🧾", "Augment prompt", [f"top {cfg.top_k} chunks + rules", "+ question"], "llm", False),
          (2, "🧠", "Generate", [llm_name], "llm", False),
          (1, "✅", "Answer", ["with citations [1]", "+ trace record"], "ing", False)]
    for j, (c, ic, t, sub, k, off) in enumerate(r2):
        s.append(node(COLS[c], y3, ic, t, sub, k, off))
        if j:
            s.append(arrow(COLS[c+1] - 4, y3 + H_NODE/2, COLS[c] + W_NODE + 6, y3 + H_NODE/2))
    s.append(arrow(COLS[4] + W_NODE/2, y2 + H_NODE + 4, COLS[4] + W_NODE/2, y3 - 6))
    s.append(f'<text x="{COLS[3] + W_NODE + 26}" y="{y3 + H_NODE/2 - 10}" class="lbl" text-anchor="middle">yes</text>')
    # abstain branch
    s.append(node(COLS[0], y3, "🙋", "I don't know", ["route to human", "no LLM call"], "safe", not cfg.guard))
    gx = COLS[4] + W_NODE/2
    s.append(f'<path d="M{gx} {y3 + H_NODE + 4} V{y3 + H_NODE + 34} H{COLS[0] + W_NODE/2} V{y3 + H_NODE + 8}" class="ar dash" marker-end="url(#h)"/>')
    s.append(f'<text x="{(gx + COLS[0] + W_NODE/2)/2}" y="{y3 + H_NODE + 28}" class="lbl" text-anchor="middle">no · weak evidence</text>')
    # same index connector
    ix = COLS[4] + W_NODE + 6
    s.append(f'<path d="M{ix} {y1 + H_NODE/2} H1206 V270 H{COLS[3] + W_NODE/2} V{y2 - 6}" class="ar link" marker-end="url(#h2)"/>')
    s.append(f'<text x="{(COLS[3] + W_NODE/2 + 1206)/2}" y="263" class="lbl link-t" text-anchor="middle">same index</text>')
    # observe strip
    s.append('<text x="44" y="748" class="lt">③ Observe &amp; improve</text>')
    chips = [("🧾", "Trace record", "every answer"), ("💰", "Usage & cost log", "every API call"),
             ("📊", "Evals dashboard", "golden set, per config"), ("🤖", "Agent + tool boundary", "read · draft · never approve")]
    for i, (ic, t, sub) in enumerate(chips):
        x = 290 + i * 232
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
.dash{{stroke-dasharray:6 5}}
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
<text x="620" y="24" text-anchor="middle" style="font-size:22px;font-weight:700;fill:#17202E">AskIT · RAG architecture</text>
{svg}</svg></div></body></html>"""
