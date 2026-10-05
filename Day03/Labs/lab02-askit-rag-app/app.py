"""
AskIT RAG Lab — load the Orbit Corp IT knowledge base, chunk + embed + store it, then chat with it.
Stack: Streamlit | AWS Bedrock (main: Nova chat + Titan embeddings) or OpenAI (backup) | ChromaDB (local vector store)
Run:   streamlit run app.py
"""
import hashlib
import io
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import chromadb
import streamlit as st
from docx import Document
from dotenv import load_dotenv
from pypdf import PdfReader

load_dotenv(Path(__file__).resolve().parents[3] / ".env")   # the course .env (AWS keys, Bedrock model id)
load_dotenv()
st.set_page_config(page_title="AskIT RAG Lab", page_icon="🔎", layout="wide")

BEDROCK_EMBED = "amazon.titan-embed-text-v2:0"
OPENAI_EMBED = "text-embedding-3-small"
BEDROCK_MODELS = ["amazon.nova-micro-v1:0", "amazon.nova-lite-v1:0"]   # small = cheap
OPENAI_PREFERRED = ["gpt-5-mini", "gpt-4.1-mini", "gpt-4o-mini"]
DB_PATH = "chroma_db"
MODES = ["Auto (Bedrock → OpenAI)", "Bedrock only", "OpenAI only"]

# ---------------------------------------------------------------- Sidebar: keys & mode
def bedrock_ready():
    try:
        import boto3
        return bool(os.getenv("BEDROCK_SMALL_MODEL_ID")) and boto3.Session().get_credentials() is not None
    except Exception:
        return False


with st.sidebar:
    st.header("🔑 Providers")
    br_ok = bedrock_ready()
    st.caption("🟢 AWS Bedrock ready (main)" if br_ok else "🔴 AWS Bedrock: keys or BEDROCK_SMALL_MODEL_ID missing in the course .env")
    openai_key = st.text_input("OpenAI API key (backup, optional)", value=os.getenv("OPENAI_API_KEY", ""), type="password")
    mode = st.radio("Provider", MODES, index=0)
    if mode.startswith("Auto"):
        st.caption("Auto: Bedrock does everything. OpenAI is used only if Bedrock fails, and nothing is sent to it before that.")

use_bedrock = br_ok and mode != "OpenAI only"
use_openai = bool(openai_key) and mode != "Bedrock only"
# ONE provider does all indexing and retrieval (the "primary"). In Auto mode OpenAI stays dormant: it is only
# used if Bedrock fails, and its index is then built on demand from the chunks already stored.
primary = "bedrock" if use_bedrock else ("openai" if use_openai else None)
providers = [primary] if primary else []
FALLBACK = "openai" if (use_bedrock and use_openai) else None

if not providers:
    st.title("🔎 AskIT · RAG Lab")
    st.warning("No provider available. Check the course .env (AWS keys + BEDROCK_SMALL_MODEL_ID), or paste an OpenAI key in the sidebar.")
    st.stop()


# ---------------------------------------------------------------- Clients & model lists
@st.cache_resource
def bedrock_client():
    import boto3
    from botocore.config import Config
    return boto3.client("bedrock-runtime", region_name=os.getenv("AWS_REGION", "us-east-1"),
                        config=Config(retries={"max_attempts": 8, "mode": "adaptive"}, read_timeout=120, connect_timeout=10))


@st.cache_resource
def openai_client(key):
    from openai import OpenAI
    return OpenAI(api_key=key)


@st.cache_resource
def get_collection(provider):
    # One collection per embedding provider: Bedrock and OpenAI vectors are not compatible.
    db = chromadb.PersistentClient(path=DB_PATH)
    return db.get_or_create_collection(f"rag_lab_{provider}", metadata={"hnsw:space": "cosine"})


SKIP = ("tts", "image", "live", "audio", "embedding", "realtime", "transcribe", "search", "native")


@st.cache_data(ttl=3600, show_spinner=False)
def openai_models(key):
    try:
        ids = [m.id for m in openai_client(key).models.list()]
        return sorted([i for i in ids if i.startswith("gpt") and not any(s in i for s in SKIP)], reverse=True)
    except Exception:
        return []


def model_picker(label, options, preferred):
    if not options:
        return st.text_input(label, value=preferred[0])
    idx = next((options.index(p) for p in preferred if p in options), 0)
    return st.selectbox(label, options, index=idx)


with st.sidebar:
    st.header("⚙️ Settings")
    o_models = openai_models(openai_key) if use_openai else []
    b_opts = list(dict.fromkeys([os.getenv("BEDROCK_SMALL_MODEL_ID", BEDROCK_MODELS[1])] + BEDROCK_MODELS))
    bedrock_model = st.selectbox("Bedrock chat model (small = cheap)", b_opts) if use_bedrock else None
    openai_model = model_picker("OpenAI chat model", o_models, OPENAI_PREFERRED) if use_openai else None
    chunk_size = st.slider("Chunk size (characters)", 100, 2000, 800, 50)
    overlap = st.slider("Chunk overlap (characters)", 0, 400, 150, 50)
    top_k = st.slider("Top-K chunks to retrieve", 1, 10, 4)
    show_ctx = st.checkbox("Show retrieved chunks", value=True)
    if overlap > chunk_size // 2:
        st.caption(f"⚠️ Overlap is capped at half the chunk size ({chunk_size // 2}).")


# ---------------------------------------------------------------- AskIT data
# The 12 test questions of the Orbit Corp helpdesk (same as askit_data/rag_questions.csv).
# expected = the KB article that holds the answer (NONE = not in the KB, AskIT should say "I don't know")
# key      = a short phrase that must be inside a retrieved chunk for the answer to be findable
QUESTIONS = [
    ("How many failed sign-ins lock my account and when does it unlock?", "KB-002", "5 failed"),
    ("What is the minimum password length?", "KB-001", "14 characters"),
    ("Can contractors use their personal laptop on VPN?", "KB-005", "Personal devices"),
    ("My VPN shows error 809 - what should I try?", "KB-004", "switch gateway"),
    ("How long can I restore deleted OneDrive files?", "KB-013", "93 days"),
    ("I lost my phone with the authenticator app. What happens now?", "KB-003", "temporary access code"),
    ("What is the first response time for a High priority ticket?", "KB-016", "1 hour"),
    ("Who approves access to a shared mailbox?", "KB-010", "mailbox owner"),
    ("I clicked a phishing link and typed my password. What priority is this?", "KB-019", "priority Critical"),
    ("Can I get permanent admin rights on my laptop?", "KB-008", "never granted permanently"),
    ("What is Orbit Corp's parental leave policy?", "NONE", ""),
    ("Which cafeteria serves vegan food on Fridays?", "NONE", ""),
]


def find_kb_folder():
    here = Path(__file__).resolve()
    for p in (here.parents[3] / "askit_data" / "kb", Path("askit_data") / "kb"):
        if p.is_dir():
            return p
    return None


class LocalFile(io.BytesIO):
    """Lets a file on disk go through the same ingest() code as an uploaded file."""
    def __init__(self, path):
        super().__init__(Path(path).read_bytes())
        self.name = Path(path).name


# ---------------------------------------------------------------- Retry helper (handles 503 / 429)
def is_transient(e):
    s = str(e)
    return any(x in s for x in ("503", "429", "500", "Throttling", "ServiceUnavailable", "overloaded", "Rate limit"))


def with_retry(fn, tries=3):
    for i in range(tries):
        try:
            return fn()
        except Exception as e:
            if i == tries - 1 or not is_transient(e):
                raise
            time.sleep(2 ** i)  # 1s, 2s back-off


# ---------------------------------------------------------------- Step 1: Extract
def extract_text(file) -> str:
    name = file.name.lower()
    if name.endswith(".pdf"):
        return "\n".join(page.extract_text() or "" for page in PdfReader(file).pages)
    if name.endswith(".docx"):
        return "\n".join(p.text for p in Document(file).paragraphs)
    return file.read().decode("utf-8", errors="ignore")  # .txt / .md


# ---------------------------------------------------------------- Step 2: Chunk
def chunk_text(text: str, size: int, overlap: int) -> list[str]:
    overlap = min(overlap, size // 2)  # guard: overlap close to the chunk size would create thousands of chunks
    text = " ".join(text.split())
    chunks, start = [], 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):  # avoid cutting a word in half
            space = text.rfind(" ", start, end)
            if space > start + size // 2:
                end = space
        chunks.append(text[start:end].strip())
        if end == len(text):
            break
        start = max(end - overlap, start + 1)
    return [c for c in chunks if c]


# ---------------------------------------------------------------- Step 3: Embed
def embed(provider, texts, task=None):
    if provider == "bedrock":
        def one(t):
            body = json.dumps({"inputText": t[:20000], "dimensions": 512, "normalize": True})
            r = with_retry(lambda: bedrock_client().invoke_model(modelId=BEDROCK_EMBED, body=body))
            return json.loads(r["body"].read())["embedding"]
        with ThreadPoolExecutor(max_workers=4) as pool:   # a few at a time: kind to the shared account
            return list(pool.map(one, texts))
    vectors = []
    for i in range(0, len(texts), 100):  # API batch limit
        batch = texts[i : i + 100]
        res = with_retry(lambda: openai_client(openai_key).embeddings.create(model=OPENAI_EMBED, input=batch))
        vectors.extend(d.embedding for d in res.data)
    return vectors


# ---------------------------------------------------------------- Step 4: Store
def ingest(file):
    chunks = chunk_text(extract_text(file), chunk_size, overlap)
    if not chunks:
        return [f"❌ {file.name}: no text found"]
    doc_id = hashlib.md5(file.name.encode()).hexdigest()[:8]
    status = []
    for p in providers:
        try:
            vecs = embed(p, chunks)
            col = get_collection(p)
            col.delete(where={"source": file.name})  # re-upload replaces old version
            col.add(ids=[f"{doc_id}-{i}" for i in range(len(chunks))], documents=chunks, embeddings=vecs,
                    metadatas=[{"source": file.name, "chunk": i} for i in range(len(chunks))])
            status.append(f"✅ {file.name}: {len(chunks)} chunks → {p}")
        except Exception as e:
            status.append(f"⚠️ {file.name}: {p} indexing failed — {str(e)[:150]}")
    return status


# ---------------------------------------------------------------- Step 5: Retrieve (with fallback)
def ensure_fallback_index():
    """Build the OpenAI index from the chunks already stored by the primary provider (only when Bedrock failed)."""
    src, dst = get_collection(primary), get_collection(FALLBACK)
    data = src.get(include=["documents", "metadatas"])
    if not data["ids"]:
        return
    sig = hashlib.md5("".join(data["documents"]).encode()).hexdigest()
    if st.session_state.get("fb_sig") == sig and dst.count() == len(data["ids"]):
        return
    if dst.count():
        dst.delete(ids=dst.get()["ids"])
    vecs = embed(FALLBACK, data["documents"])
    dst.add(ids=data["ids"], documents=data["documents"], embeddings=vecs, metadatas=data["metadatas"])
    st.session_state.fb_sig = sig


def retrieve(question, k):
    errors = []
    for p in providers + ([FALLBACK] if FALLBACK else []):
        try:
            if p == FALLBACK:
                ensure_fallback_index()
            col = get_collection(p)
            if col.count() == 0:
                continue
            q_vec = embed(p, [question])[0]
            res = col.query(query_embeddings=[q_vec], n_results=min(k, col.count()))
            return list(zip(res["documents"][0], res["metadatas"][0], res["distances"][0])), p
        except Exception as e:
            errors.append(f"{p}: {str(e)[:150]}")
    raise RuntimeError("Retrieval failed. " + " | ".join(errors) if errors else "No indexed documents.")


# ---------------------------------------------------------------- Step 6: Generate (with fallback)
SYSTEM_PROMPT = (
    "You are AskIT, the IT helpdesk assistant of Orbit Corp. Answer ONLY from the provided context. "
    "Cite sources inline like [filename #chunk]. Keep answers short. "
    "If the answer is not in the context, say: \"I couldn't find that in the AskIT knowledge base. I will route this to a human agent.\""
)


def chat_chain():
    chain = []
    if use_bedrock:
        chain.append(("bedrock", bedrock_model))
    if use_openai:
        chain.append(("openai", openai_model))
    return chain


def generate(question, hits):
    context = "\n\n".join(f"[{m['source']} #{m['chunk']}]\n{doc}" for doc, m, _ in hits)
    prompt = f"Context:\n{context}\n\nQuestion: {question}"
    errors = []
    for provider, model in chat_chain():
        try:
            if provider == "bedrock":
                res = with_retry(lambda: bedrock_client().converse(
                    modelId=model, system=[{"text": SYSTEM_PROMPT}],
                    messages=[{"role": "user", "content": [{"text": prompt}]}],
                    inferenceConfig={"maxTokens": 800, "temperature": 0.2}))
                return "".join(b.get("text", "") for b in res["output"]["message"]["content"]), model
            res = with_retry(lambda: openai_client(openai_key).chat.completions.create(
                model=model, messages=[{"role": "system", "content": SYSTEM_PROMPT},
                                       {"role": "user", "content": prompt}]))
            return res.choices[0].message.content, model
        except Exception as e:
            errors.append(f"{model}: {str(e)[:120]}")
    raise RuntimeError("All models failed. " + " | ".join(errors))


# ---------------------------------------------------------------- UI: Knowledge base
st.title("🔎 AskIT · RAG Lab")
st.caption("Load KB → Chunk → Embed → Store → Retrieve → Generate   ·   Orbit Corp IT helpdesk")

with st.sidebar:
    st.divider()
    st.header("📚 AskIT knowledge base")
    kb_folder = find_kb_folder()
    if kb_folder is None:
        st.warning("askit_data/kb not found. Run the app from inside your cloned repo, or upload the KB files below.")
    elif st.button("Load AskIT KB (20 articles)", type="primary", width="stretch"):
        paths = sorted(kb_folder.glob("*.md"))
        bar = st.progress(0.0, text="Indexing…")
        problems = []
        for i, path in enumerate(paths, 1):
            lines = ingest(LocalFile(path))
            problems += [l for l in lines if not l.startswith("✅")]
            bar.progress(i / len(paths), text=f"Indexing {path.name}")
        bar.empty()
        if problems:
            for l in problems:
                st.write(l)
        else:
            st.success(f"Indexed {len(paths)} articles (chunk {chunk_size}, overlap {overlap}).")
    st.caption("Changed chunk size or overlap? Click **Load AskIT KB** again: it replaces the old chunks.")
    files = st.file_uploader("…or upload your own documents", type=["pdf", "txt", "md", "docx"], accept_multiple_files=True)
    if files and st.button("Index documents", type="primary", width="stretch"):
        for f in files:
            with st.spinner(f"Indexing {f.name}…"):
                for line in ingest(f):
                    st.write(line)

    for p in providers:
        metas = get_collection(p).get(include=["metadatas"])["metadatas"]
        st.metric(f"Chunks stored ({p})", len(metas))
        for s in sorted({m["source"] for m in metas}):
            st.write(f"• {s}")
    if st.button("Clear knowledge base", width="stretch"):
        for p in ("bedrock", "openai"):
            col = get_collection(p)
            if col.count():
                col.delete(ids=col.get()["ids"])
        st.session_state.messages = []
        st.rerun()

# ---------------------------------------------------------------- UI: Mini eval (how good is my retrieval?)
if "messages" not in st.session_state:
    st.session_state.messages = []
if "experiments" not in st.session_state:
    st.session_state.experiments = []

with st.expander("🧪 Mini eval — how good is my retrieval? (12 AskIT questions, no LLM cost)"):
    st.caption("For each question: did the right KB article come back (doc hit)? Did a chunk that contains the "
               "answer come back (answer hit)? Change chunk size / overlap / Top-K, re-load the KB, run again.")
    if st.button("Run mini eval", key="run_eval"):
        rows, errs = [], None
        bar = st.progress(0.0, text="Asking 12 questions…")
        for i, (q, exp, key) in enumerate(QUESTIONS, 1):
            try:
                hits, _prov = retrieve(q, top_k)
            except Exception as e:
                errs = str(e)
                break
            arts = [m["source"].split("_")[0] for _, m, _ in hits]
            best = max((1 - d) for _, _, d in hits)
            if exp == "NONE":
                rows.append({"question": q, "expected": "NONE", "retrieved": ", ".join(arts),
                             "doc hit": "n/a", "answer hit": "n/a", "best similarity": round(best, 3)})
            else:
                rows.append({"question": q, "expected": exp, "retrieved": ", ".join(arts),
                             "doc hit": "✅" if exp in arts else "❌",
                             "answer hit": "✅" if any(key.lower() in doc.lower() for doc, _, _ in hits) else "❌",
                             "best similarity": round(best, 3)})
            bar.progress(i / len(QUESTIONS), text=f"Question {i} of {len(QUESTIONS)}")
        bar.empty()
        if errs:
            st.error(f"Mini eval stopped: {errs}. Load the AskIT KB first.")
        else:
            scored = [r for r in rows if r["doc hit"] != "n/a"]
            doc_hits = sum(r["doc hit"] == "✅" for r in scored)
            ans_hits = sum(r["answer hit"] == "✅" for r in scored)
            st.session_state.eval_rows = rows
            st.session_state.experiments.append({"chunk size": chunk_size, "overlap": overlap, "top-K": top_k,
                                                 "doc hit": f"{doc_hits}/{len(scored)}",
                                                 "answer hit": f"{ans_hits}/{len(scored)}"})
    if st.session_state.get("eval_rows"):
        st.dataframe(st.session_state.eval_rows, hide_index=True, width="stretch")
        st.caption("Questions with expected NONE are not in the KB. Look at their best similarity: the retriever "
                   "still returns its closest chunks, so the LLM must be the one to say \"I don't know\".")
    if st.session_state.experiments:
        st.markdown("**Your experiments** (copy these into `submission/experiment.md`)")
        st.dataframe(st.session_state.experiments, hide_index=True, width="stretch")

# ---------------------------------------------------------------- UI: Chat
st.markdown("**Try a sample question**")
sq1, sq2 = st.columns([5, 1])
sample = sq1.selectbox("Sample question", [q for q, _, _ in QUESTIONS], label_visibility="collapsed")
if sq2.button("Ask", width="stretch"):
    st.session_state.pending_q = sample

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

typed = st.chat_input("Ask AskIT a question")
question = st.session_state.pop("pending_q", None) or typed
if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        try:
            with st.spinner("Retrieving and thinking…"):
                hits, retr_provider = retrieve(question, top_k)
                reply, used_model = generate(question, hits)
            st.markdown(reply)
            st.caption(f"Retrieved with {retr_provider} embeddings · answered by {used_model}")
            if show_ctx:
                with st.expander("🔍 Retrieved chunks"):
                    for doc, m, dist in hits:
                        st.markdown(f"**{m['source']} #{m['chunk']}** — similarity {1 - dist:.3f}")
                        st.caption(doc)
        except Exception as e:
            reply = f"⚠️ {e}"
            st.error(reply)
    st.session_state.messages.append({"role": "assistant", "content": reply})
