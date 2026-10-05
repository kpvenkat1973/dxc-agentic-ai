"""AskIT Advanced RAG Lab - RAG with metadata filtering, reranking, evals, cost tracking and a bounded agent.
Run:  streamlit run app.py"""
import json, os
import pandas as pd
import streamlit as st

from rag import config, pipeline, evals, agent, diagram
import streamlit.components.v1 as components
from rag.ingest import load_documents, chunk_documents, parse_upload, scan_injection, MAX_UPLOAD_MB
from rag.llm import LLM, UsageLog, bedrock_ready

try:
    from pathlib import Path as _P
    from dotenv import load_dotenv
    load_dotenv(_P(__file__).resolve().parents[3] / ".env")   # the course .env (AWS keys, Bedrock model id)
    load_dotenv()                                              # or a .env in this folder
except Exception:
    pass

st.set_page_config(page_title="AskIT Advanced RAG Lab", page_icon="🛟", layout="wide")
st.markdown("""<style>
.block-container{padding-top:1.4rem}
div[data-testid="stMetricValue"]{font-size:1.6rem}
.src-bad{color:#b0291f;font-weight:600}
</style>""", unsafe_allow_html=True)

ss = st.session_state
ss.setdefault("log", UsageLog())
ss.setdefault("indexes", {})
ss.setdefault("ask_results", [])
ss.setdefault("query_costs", [])
ss.setdefault("agent_steps", None)
ss.setdefault("uploaded", {})        # doc_id -> Document
ss.setdefault("ingest_log", [])
if ss.pop("switch_source", False):
    ss.source = "Both"

# ---------------- sidebar ----------------
PRESET_KEYS = dict(chunking="chunking", chunk_size="chunk_size", overlap="overlap", search="search",
                   metadata_filter="metadata_filter", rerank="rerank", top_k="top_k", guard="guard",
                   guard_threshold="guard_threshold")


def apply_preset():
    if ss.preset not in pipeline.PRESETS:  # "Custom": keep the knobs as they are
        return
    cfg = pipeline.PRESETS[ss.preset]
    for attr, key in PRESET_KEYS.items():
        ss[key] = getattr(cfg, attr)


def matching_preset():
    """Name of the preset the sidebar knobs currently match, or "Custom"."""
    for name, p in pipeline.PRESETS.items():
        ignore = set()
        if p.chunking == "section":
            ignore |= {"chunk_size", "overlap"}
        if not p.guard:
            ignore.add("guard_threshold")
        if all(ss[key] == getattr(p, attr) for attr, key in PRESET_KEYS.items() if attr not in ignore):
            return name
    return "Custom"


if "chunking" not in ss:
    ss.preset = "FDE-grade (all on)"
    apply_preset()
else:  # keep the Preset label honest: it follows the knobs
    ss.preset = matching_preset()

with st.sidebar:
    st.header("Connection")
    br_ok = bedrock_ready()
    env_key = os.getenv("OPENAI_API_KEY", "")
    provider_label = st.radio("Provider", ["AWS Bedrock (main)", "OpenAI (backup)", "Offline"],
                              index=0 if br_ok else (1 if env_key else 2),
                              help="Bedrock uses the AWS keys and BEDROCK_SMALL_MODEL_ID in the course .env. "
                                   "OpenAI is the backup: paste a key below. Offline = stand-in models, no API calls.")
    api_key, provider = "", "offline"
    if provider_label.startswith("AWS"):
        if br_ok:
            provider = "bedrock"
            st.caption("🟢 Live: AWS Bedrock")
        else:
            st.error("AWS keys or BEDROCK_SMALL_MODEL_ID not found in .env. Using offline mode. Or switch to OpenAI.")
    elif provider_label.startswith("OpenAI"):
        key_in = st.text_input("OpenAI API key", value="", type="password",
                               placeholder="Loaded from .env" if env_key else "sk-...")
        api_key = key_in or env_key
        if api_key:
            provider = "openai"
            st.caption("🟢 Live: OpenAI API (backup)")
        else:
            st.warning("Paste an OpenAI key. Using offline mode until then.")
    if provider == "offline":
        st.caption("🟠 Offline mode: no API calls, stand-in models")

    if provider == "bedrock":
        env_model = os.getenv("BEDROCK_SMALL_MODEL_ID", config.DEFAULT_BEDROCK_MODEL)
        opts = list(dict.fromkeys([env_model] + config.BEDROCK_MODEL_OPTIONS))
        chat_model = st.selectbox("Chat model (small = cheap)", opts)
        embed_model = config.DEFAULT_BEDROCK_EMBED
        st.caption(f"Embeddings: {embed_model}")
        price_note = "Verify at aws.amazon.com/bedrock/pricing"
    else:
        chat_model = st.selectbox("Chat model", config.CHAT_MODEL_OPTIONS + ["Other..."])
        if chat_model == "Other...":
            chat_model = st.text_input("Model name", value="gpt-5-mini")
        embed_model = st.selectbox("Embedding model", ["text-embedding-3-small", "text-embedding-3-large"])
        price_note = "Verify at openai.com/api/pricing"
    with st.expander("Prices (USD per 1M tokens)"):
        st.caption(price_note)
        pin, pout = config.PRICES.get(chat_model, (0.25, 2.0))
        pin = st.number_input(f"{chat_model} input", value=float(pin), format="%.3f")
        pout = st.number_input(f"{chat_model} output", value=float(pout), format="%.3f")
        pemb = st.number_input(f"{embed_model} input", value=float(config.PRICES.get(embed_model, (0.02, 0))[0]),
                               format="%.3f")
    prices = dict(config.PRICES)
    prices[chat_model] = (pin, pout)
    prices[embed_model] = (pemb, 0.0)

    st.header("Knowledge source")
    st.radio("Documents to search", ["Preloaded AskIT KB", "My uploaded files", "Both"], key="source",
             help="Upload files in the 🧩 Ingestion tab")
    st.header("Who is asking?")
    audience = st.radio("Audience", ["Employee", "Contractor"], horizontal=True)

    st.header("RAG pipeline")
    st.selectbox("Preset", list(pipeline.PRESETS) + ["Custom"], key="preset", on_change=apply_preset,
                 help="Changes to 'Custom' as soon as any knob below no longer matches a preset.")
    st.radio("Chunking", ["section", "fixed"], key="chunking", horizontal=True)
    # always rendered (disabled when not used) so Streamlit keeps their values
    st.slider("Chunk size (chars, fixed only)", 80, 400, key="chunk_size", step=20, disabled=ss.chunking != "fixed")
    st.slider("Overlap (chars, fixed only)", 0, 100, key="overlap", step=10, disabled=ss.chunking != "fixed")
    st.radio("Search", ["keyword", "vector", "hybrid"], key="search", horizontal=True)
    st.toggle("Metadata filter (current + my audience)", key="metadata_filter")
    st.toggle("LLM reranker", key="rerank")
    st.slider("Top-k chunks to the LLM", 1, 5, key="top_k")
    st.toggle("Abstain guard (say 'I don't know')", key="guard")
    st.slider("Guard threshold", 0.0, 0.9, key="guard_threshold", step=0.05, disabled=not ss.guard)
    st.divider()
    total_cost = sum(r["cost_usd"] for r in ss.log.rows)
    st.metric("Session cost", f"${total_cost:.4f}", f"{len(ss.log.rows)} API calls", delta_color="off")

cfg = pipeline.Config("Current settings", ss.chunking, ss.chunk_size, ss.overlap, ss.search,
                      ss.metadata_filter, ss.rerank, ss.top_k, ss.guard, ss.guard_threshold)

try:
    llm = LLM(api_key or None, chat_model, embed_model, prices, ss.log, provider=provider)
except Exception as e:
    st.error(f"Could not create the model client: {e}")
    st.stop()

PRELOADED = load_documents()
UPLOADED = list(ss.uploaded.values())
DOCS = {"Preloaded AskIT KB": PRELOADED, "My uploaded files": UPLOADED, "Both": PRELOADED + UPLOADED}[ss.source]


def get_index(c: pipeline.Config, docs=None):
    docs = DOCS if docs is None else docs
    key = (c.chunking, c.chunk_size, c.overlap, llm.provider, embed_model, tuple(d.doc_id for d in docs))
    if key not in ss.indexes:
        ss.indexes[key] = pipeline.Index(chunk_documents(docs, c.chunking, c.chunk_size, c.overlap), llm)
    idx = ss.indexes[key]
    idx.llm = llm
    return idx


def safe(fn, *a, **k):
    try:
        return fn(*a, **k)
    except Exception as e:
        st.error(f"API call failed: {type(e).__name__}: {e}. Check the key, model name, or switch to offline mode.")
        st.stop()


# ---------------- header ----------------
st.title("AskIT · Advanced RAG Lab")
st.caption(f"RAG over {len(DOCS)} documents ({ss.source.lower()}) · audience **{audience}** · model **{chat_model}** · "
           f"{'live ' + llm.provider if not llm.offline else 'offline mode'} · pipeline: {cfg.label()}")

tabs = st.tabs(["🏗️ Architecture", "💬 Ask", "🧩 Ingestion & chunks", "📊 Evals dashboard", "💰 Usage & cost",
                "🔭 Day 5 preview: agent", "🔭 Day 5 preview: RAG vs fine-tuning"])


def render_result(res: pipeline.Result, title):
    st.subheader(title)
    st.caption(res.config.label())
    top = res.hits[0]["chunk"] if res.hits else None
    if res.abstained:
        st.warning("Abstained: evidence too weak. Routed to a human agent.")
    elif top is not None and not pipeline.is_ok_source(top, audience):
        m = top.doc.meta
        st.error(f"Top source is WRONG for this user: {top.citation} "
                 f"({'superseded' if m['status'] != 'active' else m['audience'] + ' audience'})")
    else:
        st.success("Grounded in a current article for this audience")
    st.markdown(f"#### {res.answer}")
    c = st.columns(4)
    c[0].metric("Input tokens", f"{res.tokens_in:,}")
    c[1].metric("Output tokens", f"{res.tokens_out:,}")
    c[2].metric("Cost", f"${res.cost:.5f}")
    c[3].metric("Latency", f"{res.timings.get('total_ms', 0):,} ms")
    st.caption(" · ".join(f"{k.replace('_ms','')}: {v} ms" for k, v in res.timings.items() if k.endswith("_ms")) +
               f" · {res.removed_by_filter} chunks removed by filter")
    rows = []
    for r, h in enumerate(res.hits, 1):
        ch = h["chunk"]
        ok = pipeline.is_ok_source(ch, audience)
        rows.append({"#": r, "citation": ch.citation, "final score": h["score"], "retrieval": h["retrieval_score"],
                     "term coverage": h["coverage"], **ch.meta_row(), "ok for this user": "✅" if ok else "❌",
                     "text": ch.text})
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    with st.expander("Prompt sent to the LLM"):
        st.code(res.prompt or "(no generation: guard stopped it)", language="text")
    with st.expander("Trace record (JSON)"):
        st.json({"question": res.question, "audience": audience, "config": res.config.label(),
                 "removed_by_filter": res.removed_by_filter,
                 "retrieved": [{"citation": h["chunk"].citation, "score": h["score"]} for h in res.hits],
                 "abstained": res.abstained, "answer": res.answer, "timings_ms": res.timings,
                 "usage": res.usage})


# ---------------- Architecture ----------------
with tabs[0]:
    st.markdown("The diagram follows your sidebar settings. Stages switched off appear grey and dashed.")
    _svg = diagram.render(cfg, chat_model, embed_model, llm.offline, load_sub=[f"{len(DOCS)} documents", ss.source.lower()])
    if hasattr(st, "iframe"):
        st.iframe(_svg, height=800)
    else:
        components.html(_svg, height=800, scrolling=True)
    c = st.columns(4)
    c[0].markdown("🟩 **Ingestion / output**")
    c[1].markdown("🟦 **Retrieval**")
    c[2].markdown("🟪 **LLM steps**")
    c[3].markdown("🟧 **Safety controls**")

# ---------------- Ask ----------------
with tabs[1]:
    qs = list(dict.fromkeys([g["q"] for g in evals.GOLDEN] + ["Please reset the CEO's password right now, it is urgent."]))
    col1, col2 = st.columns([3, 1])
    pick = col1.selectbox("Sample questions", qs)
    compare = col2.toggle("Compare with baseline", value=True)
    q = st.text_input("Ask AskIT a question", value=pick)
    if not DOCS:
        st.info("No documents in the current knowledge source. Upload files in the 🧩 Ingestion tab, or switch the source in the sidebar.")
    elif st.button("Ask", type="primary"):
        idx = get_index(cfg)
        res = safe(pipeline.run, idx, q, cfg, audience)
        out = [(res, "Current pipeline")]
        if compare:
            base = pipeline.PRESETS["Baseline (naive RAG)"]
            out.insert(0, (safe(pipeline.run, get_index(base), q, base, audience), "Baseline (naive RAG)"))
        ss.ask_results = out
        ss.query_costs.append(res.cost)
    if ss.ask_results:
        cols = st.columns(len(ss.ask_results))
        for c, (r, t) in zip(cols, ss.ask_results):
            with c:
                render_result(r, t)

# ---------------- Ingestion ----------------
with tabs[2]:
    with st.expander("📤 Load new files (ingest live)", expanded=not ss.uploaded):
        st.caption(f"Supported: .md, .txt, .pdf (text-based, not scanned), .docx · up to {MAX_UPLOAD_MB} MB each. "
                   "Uploaded text is sent to the embedding and chat models; don't upload confidential documents.")
        files = st.file_uploader("Choose files", type=["md", "txt", "pdf", "docx"], accept_multiple_files=True)
        st.markdown("**Metadata for these files** (used for filtering and citations)")
        m = st.columns(4)
        up_audience = m[0].selectbox("Audience", ["All", "Employee", "Contractor"])
        up_version = m[1].text_input("Version", "v1")
        up_status = m[2].selectbox("Status", ["active", "superseded"])
        up_eff = m[3].date_input("Effective date")
        b1, b2 = st.columns([1, 1])
        if b1.button("Ingest files", type="primary", disabled=not files):
            with st.status("Ingesting…", expanded=True) as status:
                for f in files:
                    try:
                        doc, info = parse_upload(f.name, f.getvalue(), dict(audience=up_audience, version=up_version,
                                                 status=up_status, effective=up_eff.isoformat()))
                    except Exception as e:
                        st.error(f"{f.name}: {e}")
                        continue
                    st.write(f"📄 **Parse** {f.name}: {info['type']}, {info['size_kb']} KB"
                             f"{', ' + str(info['pages']) + ' pages' if info['pages'] else ''}, "
                             f"{info['sections']} sections, {info['chars']:,} chars ({info['parse_ms']} ms)")
                    if info["warning"] or not doc.sections:
                        st.warning(info["warning"] or "No text extracted.")
                        continue
                    flagged = scan_injection(doc)
                    if flagged:
                        st.warning(f"⚠️ **Scan**: {f.name} contains text that looks like instructions to the AI "
                                   f"(section: {', '.join(flagged)}). It is indexed anyway so you can test what happens.")
                    ch = chunk_documents([doc], cfg.chunking, cfg.chunk_size, cfg.overlap)
                    st.write(f"✂️ **Chunk** ({cfg.chunking}): {len(ch)} chunks, avg {sum(len(c.text) for c in ch)//len(ch)} chars")
                    st.write(f"🏷️ **Tag**: audience {up_audience} · {up_version} · {up_status} · effective {up_eff.isoformat()}")
                    n0 = len(ss.log.rows)
                    safe(llm.embed, [c.text for c in ch], "embed upload")
                    er = ss.log.rows[n0:]
                    etok, ecost, ems = sum(r["input_tokens"] for r in er), sum(r["cost_usd"] for r in er), sum(r["latency_ms"] for r in er)
                    st.write(f"🔢 **Embed**: {etok:,} tokens · ${ecost:.6f} · {ems} ms")
                    ss.uploaded[doc.doc_id] = doc
                    st.write("🗄️ **Index**: added to the search index")
                    ss.ingest_log.append(dict(file=f.name, type=info["type"], size_kb=info["size_kb"], pages=info["pages"],
                                              sections=info["sections"], chars=info["chars"], chunks=len(ch),
                                              embed_tokens=etok, embed_cost_usd=round(ecost, 6),
                                              total_ms=info["parse_ms"] + ems))
                status.update(label="Ingestion complete", state="complete")
            ss.switch_source = True
            st.rerun()
        if ss.uploaded and b2.button("Remove uploaded files"):
            ss.uploaded, ss.ingest_log = {}, []
            st.rerun()
    if ss.ingest_log:
        st.markdown("**Ingestion log**")
        st.dataframe(pd.DataFrame(ss.ingest_log), hide_index=True, width="stretch")
    st.markdown(f"**Step 1. Ingest:** current knowledge source: **{ss.source}**. Preloaded files are markdown with "
                "front-matter metadata in `data/kb/`.")
    if not DOCS:
        st.info("No documents yet. Upload files above.")
    else:
        st.dataframe(pd.DataFrame([{"file": d.doc_id, **{k: d.meta.get(k, "") for k in
                                   ["code", "title", "version", "audience", "effective", "status"]},
                                    "sections": len(d.sections)} for d in DOCS]), hide_index=True, width="stretch")
        chunks = chunk_documents(DOCS, cfg.chunking, cfg.chunk_size, cfg.overlap)
        st.markdown(f"**Step 2. Chunk:** strategy `{cfg.chunking}` (change it in the sidebar).")
        cut = sum(1 for c in chunks if not c.text.rstrip().endswith((".", "?", "!")))
        est_tokens = sum(len(c.text) for c in chunks) // 4
        m = st.columns(4)
        m[0].metric("Chunks", len(chunks))
        m[1].metric("Avg chars / chunk", int(sum(len(c.text) for c in chunks) / max(1, len(chunks))))
        m[2].metric("Cut mid-sentence", cut)
        m[3].metric("Embedding cost (est.)", f"${est_tokens / 1e6 * prices[embed_model][0]:.6f}")
        st.markdown("**Step 3. Tag:** every chunk inherits its document's metadata, used later for filtering and citations.")
        st.dataframe(pd.DataFrame([{"chunk_id": c.chunk_id, "citation": c.citation, **c.meta_row(),
                                    "chars": len(c.text), "cut mid-sentence": "⚠️" if not c.text.rstrip().endswith((".", "?", "!")) else "",
                                    "text": c.text} for c in chunks]), hide_index=True, width="stretch", height=420)

# ---------------- Evals ----------------
with tabs[3]:
    if ss.source != "Preloaded AskIT KB":
        st.info("The golden set is written for the preloaded AskIT KB, so evaluations always run on those files. "
                "Uploaded files would need their own test questions.")
    st.markdown(f"Golden set: **{len(evals.GOLDEN)} questions** with known answers "
                "(two are not in the KB and should be answered with 'I don't know'; one pair checks who is asking).")
    c1, c2 = st.columns([3, 1])
    chosen = c1.multiselect("Configurations to test", list(pipeline.PRESETS) + ["Current settings"],
                            default=["Baseline (naive RAG)", "FDE-grade (all on)"])
    judge = c2.toggle("LLM-as-judge", value=False, disabled=llm.offline,
                      help="Scores faithfulness and correctness 1-5. Adds cost.")
    if st.button("Run evaluation", type="primary"):
        for name in chosen:
            c = cfg if name == "Current settings" else pipeline.PRESETS[name]
            bar = st.progress(0.0, text=f"Evaluating {name}...")
            rows = safe(evals.evaluate, get_index(c, PRELOADED), c, audience, judge, lambda p: bar.progress(p, text=f"Evaluating {name}..."))
            evals.save_run(evals.summarize(c, rows, chat_model if not llm.offline else "offline"))
            bar.empty()
    runs = evals.load_runs()
    if not runs:
        st.info("No runs yet. Pick configurations and click Run evaluation.")
    else:
        df = pd.DataFrame([{k: v for k, v in r.items() if k != "questions"} for r in runs])
        latest = df.groupby("config").tail(1).set_index("config")
        st.markdown("#### Latest run per configuration")
        k = st.columns(len(latest))
        for col, (name, r) in zip(k, latest.iterrows()):
            col.metric(name, f"{r.pass_rate:.0%} pass", f"hit@1 {r.hit_at_1:.0%} · ${r.cost_usd:.4f}", delta_color="off")
        ch1, ch2 = st.columns(2)
        with ch1:
            st.markdown("**Quality by configuration**")
            st.bar_chart(latest[["pass_rate", "hit_at_1", "recall_at_k", "mrr"]], stack=False)
        with ch2:
            st.markdown("**Cost and latency by configuration**")
            st.bar_chart(latest[["cost_usd"]])
            st.bar_chart(latest[["avg_latency_ms"]])
        if latest["faithfulness"].notna().any():
            st.markdown("**LLM-as-judge (1-5)**")
            st.bar_chart(latest[["faithfulness", "correctness"]].dropna(how="all"), stack=False)
        st.markdown("#### Run history")
        st.dataframe(df[["run_at", "config", "model", "pass_rate", "hit_at_1", "recall_at_k", "mrr", "faithfulness",
                         "correctness", "wrong_source_top1", "avg_latency_ms", "cost_usd", "settings"]].iloc[::-1],
                     hide_index=True, width="stretch")
        st.markdown("#### Question-level drill-down")
        sel = st.selectbox("Run", [f"{i}: {r['config']} ({r['run_at']})" for i, r in enumerate(runs)][::-1])
        qdf = pd.DataFrame(runs[int(sel.split(":")[0])]["questions"])
        qdf["passed"] = qdf["passed"].map({True: "✅", False: "❌"})
        st.dataframe(qdf[["passed", "question", "top_source", "answer", "hit_at_1", "abstained",
                          "stale_or_wrong_office_top1", "faithfulness", "correctness", "judge_reason", "cost_usd",
                          "latency_ms"]], hide_index=True, width="stretch")
        cc1, cc2 = st.columns(2)
        cc1.download_button("Download runs (JSON)", json.dumps(runs, indent=1), "eval_runs.json")
        if cc2.button("Clear history"):
            os.remove(evals.RUNS_FILE)
            st.rerun()

# ---------------- Agent ----------------
with tabs[5]:
    st.markdown("A pipeline answers from documents. An **agent** chooses tools. The **tool boundary** is enforced in code.")
    c1, c2 = st.columns([1, 2])
    eid = c1.selectbox("Signed-in user", list(agent.EMPLOYEES),
                       format_func=lambda e: f"{agent.EMPLOYEES[e]['name']} ({agent.EMPLOYEES[e]['audience']}"
                                             f"{', VIP' if agent.EMPLOYEES[e]['vip'] else ''})")
    prompts = ["What is the minimum password length?", "What is the status of ticket TKT-0067?",
               "Add a note to ticket TKT-0067: I only need admin rights for one hour.",
               "What is the status of ticket TKT-0004?", "Reset my password now."]
    p = c2.selectbox("Try a request", prompts)
    msg = st.text_input("Request", value=p)
    redteam = st.toggle("🔴 Red-team: tell the model it may reset passwords", value=False,
                        help="Simulates a weak or injected prompt that tells the model it may reset passwords. "
                             "Shows that the code boundary still blocks the action.")
    if st.button("Run agent", type="primary"):
        n0 = len(ss.log.rows)
        steps, ms = safe(agent.run_agent, llm, get_index(pipeline.PRESETS["FDE-grade (all on)"], PRELOADED), eid, msg,
                         redteam=redteam)
        ss.agent_steps = (steps, ms, ss.log.rows[n0:])
    if ss.agent_steps:
        steps, ms, rows = ss.agent_steps
        m = st.columns(4)
        m[0].metric("Tool calls", sum(1 for s in steps if s["kind"] == "tool"))
        m[1].metric("Tokens", f"{sum(r['input_tokens'] + r['output_tokens'] for r in rows):,}")
        m[2].metric("Cost", f"${sum(r['cost_usd'] for r in rows):.5f}")
        m[3].metric("Latency", f"{ms:,} ms")
        for i, s in enumerate(steps, 1):
            if s["kind"] == "tool":
                box = st.error if s["blocked"] else st.info
                box(f"**Step {i}: {s['tool']}**  args: `{json.dumps(s['args'])}`")
                with st.expander("Tool result", expanded=s["blocked"]):
                    st.json(s["result"])
            else:
                st.success(f"**Answer:** {s['content']}")
    st.markdown("#### Tool boundary")
    st.dataframe(pd.DataFrame([
        {"tool": "search_kb", "type": "read", "who may run it": "agent", "why": "KB is shared, current articles only"},
        {"tool": "get_ticket", "type": "read", "who may run it": "agent", "why": "Own tickets only (data boundary)"},
        {"tool": "update_ticket", "type": "write (note)", "who may run it": "agent", "why": "Own tickets only; blocked for VIP users (KB-018)"},
        {"tool": "reset_password", "type": "write (decision)", "who may run it": "human", "why": "Blocked in code for the agent (KB-001: identity check first)"},
    ]), hide_index=True, width="stretch")

# ---------------- Usage ----------------
with tabs[4]:
    rows = ss.log.rows
    if not rows:
        st.info("No API calls yet. Ask a question or run an evaluation.")
    else:
        df = pd.DataFrame(rows)
        m = st.columns(4)
        m[0].metric("API calls", len(df))
        m[1].metric("Input tokens", f"{df.input_tokens.sum():,}")
        m[2].metric("Output tokens", f"{df.output_tokens.sum():,}")
        m[3].metric("Total cost", f"${df.cost_usd.sum():.4f}")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Cost by operation (USD)**")
            st.bar_chart(df.groupby("operation")["cost_usd"].sum())
        with c2:
            st.markdown("**Average latency by operation (ms)**")
            st.bar_chart(df.groupby("operation")["latency_ms"].mean())
        st.dataframe(df.iloc[::-1], hide_index=True, width="stretch")
        st.download_button("Download usage log (CSV)", df.to_csv(index=False), "usage_log.csv")
    st.markdown("#### What would this cost in production?")
    avg_q = (sum(ss.query_costs) / len(ss.query_costs)) if ss.query_costs else 0.0
    c = st.columns(3)
    emps = c[0].number_input("Users", value=1000, step=100)
    qpm = c[1].number_input("Questions per user per month", value=4, step=1)
    per_q = c[2].number_input("Cost per question (USD)", value=float(round(avg_q, 6)), format="%.6f",
                              help="Defaults to the average from your Ask tab questions")
    st.metric("Estimated monthly LLM cost", f"${emps * qpm * per_q:,.2f}",
              f"{emps * qpm:,} questions/month", delta_color="off")
    st.caption("Compare with the cost of L1 helpdesk analyst time spent answering the same questions.")

# ---------------- Fine-tuning ----------------
with tabs[6]:
    st.markdown("#### Should we fine-tune instead of RAG?")
    st.dataframe(pd.DataFrame([
        {"question": "Facts change (new KB article versions)?", "RAG": "Re-index in minutes", "Fine-tuning": "Retrain every change"},
        {"question": "Need citations for audit?", "RAG": "Yes, per chunk", "Fine-tuning": "No source to cite"},
        {"question": "Different answers per audience?", "RAG": "Metadata filter", "Fine-tuning": "Hard to control"},
        {"question": "Consistent tone / format / style?", "RAG": "Prompting", "Fine-tuning": "Strong fit"},
        {"question": "Cheaper small model for a narrow task?", "RAG": "-", "Fine-tuning": "Strong fit (distillation)"},
        {"question": "Time to first result", "RAG": "Hours", "Fine-tuning": "Days (data + training + eval)"},
    ]), hide_index=True, width="stretch")
    st.markdown("**Verdict for AskIT:** RAG for KB facts. Fine-tuning only later, e.g. to classify tickets "
                "(category / priority / sentiment, using the labels in tickets.csv) with a small cheap model, or to enforce a tone.")
    st.markdown("#### What fine-tuning data looks like")
    sysmsg = "You are AskIT, Orbit Corp's IT helpdesk assistant. Answer briefly and politely."
    lines = [json.dumps({"messages": [{"role": "system", "content": sysmsg}, {"role": "user", "content": g["q"]},
                                      {"role": "assistant", "content": g["expected"]}]}) for g in evals.GOLDEN]
    st.code("\n".join(lines[:3]), language="json")
    st.download_button("Download sample training file (JSONL)", "\n".join(lines), "askit_finetune_sample.jsonl")
    st.markdown("#### How the job would be launched (not run in this demo)")
    st.code('''from openai import OpenAI
client = OpenAI()
f = client.files.create(file=open("askit_finetune_sample.jsonl", "rb"), purpose="fine-tune")
job = client.fine_tuning.jobs.create(training_file=f.id, model="<fine-tunable model>")
# then: evaluate the tuned model on the SAME golden set before shipping''', language="python")
    st.caption("A real job needs hundreds of examples, a held-out eval set, and a comparison against RAG on the same golden set.")
