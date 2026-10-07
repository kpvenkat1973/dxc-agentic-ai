"""
AskIT RAG Lab — load the Orbit Corp IT knowledge base, chunk + embed + store it, then chat with it.
Stack: Streamlit | AWS Bedrock (main: Nova chat + Titan embeddings), Azure AI Foundry (GPT / any Foundry deployment) or OpenAI (backup) | numpy + JSON (local vector store)
Run:   streamlit run app.py
"""
import hashlib
import io
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import streamlit as st
from docx import Document
from dotenv import dotenv_values, load_dotenv
from pypdf import PdfReader

# the course .env (AWS keys, Bedrock model id): search upward from this file, then the current folder
_envs = [d / ".env" for d in Path(__file__).resolve().parents if (d / ".env").is_file()]
ENV_FOUND = " + ".join(str(e) for e in _envs)
for _e in reversed(_envs):                      # farthest (course .env) first, nearest last; empty values never win
    for _k, _v in dotenv_values(_e).items():
        if _v:
            os.environ[_k] = _v
load_dotenv()
st.set_page_config(page_title="AskIT RAG Lab", page_icon="🔎", layout="wide")

BEDROCK_EMBED = "amazon.titan-embed-text-v2:0"
OPENAI_EMBED = "text-embedding-3-small"
BEDROCK_MODELS = ["amazon.nova-micro-v1:0", "amazon.nova-lite-v1:0"]   # small = cheap
OPENAI_PREFERRED = ["gpt-5-mini", "gpt-4.1-mini", "gpt-4o-mini"]
DB_PATH = Path(__file__).resolve().parent / "vector_store"   # next to app.py, whatever folder you launch from
MODES = ["Auto (Bedrock → Azure → OpenAI)", "Bedrock only", "Azure Foundry only", "OpenAI only"]

# Azure AI Foundry: key + endpoint come from the course .env (like the AWS keys). Chat model = a *deployment name*.
#   AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT (e.g. https://myres.openai.azure.com  or  https://myres.services.ai.azure.com),
#   AZURE_OPENAI_CHAT_DEPLOYMENTS (comma list, first = default, e.g. gpt-5-mini,gpt-4.1-mini,DeepSeek-V3),
#   AZURE_OPENAI_EMBED_DEPLOYMENT (OPTIONAL: an Azure embedding deployment, e.g. text-embedding-3-small.
#       Leave it empty and embeddings run locally on your laptop with fastembed: nothing to deploy on Azure)
LOCAL_EMBED = os.getenv("LOCAL_EMBED_MODEL", "BAAI/bge-small-en-v1.5")
AZURE_PREFERRED = ["gpt-5-mini", "gpt-4o-mini"]
AZURE_OTHER = "✏️ other (type a deployment name)"

# ---------------------------------------------------------------- Sidebar: keys & mode
def bedrock_status():
    """(ready, reason) - the reason is shown in the sidebar when not ready."""
    try:
        import boto3
    except Exception as e:
        return False, f"boto3 not installed in this Python ({e}). Run: pip install boto3"
    if not ENV_FOUND:
        return False, "no .env file found above this folder"
    if not os.getenv("BEDROCK_SMALL_MODEL_ID"):
        return False, f"BEDROCK_SMALL_MODEL_ID empty in {ENV_FOUND}"
    if boto3.Session().get_credentials() is None:
        return False, f"AWS keys empty in {ENV_FOUND}"
    return True, ""


def bedrock_ready():
    return bedrock_status()[0]


def azure_status():
    """(ready, reason) for Azure AI Foundry."""
    if not os.getenv("AZURE_OPENAI_API_KEY"):
        return False, "AZURE_OPENAI_API_KEY empty" + (f" in {ENV_FOUND}" if ENV_FOUND else " (no .env found)")
    if not os.getenv("AZURE_OPENAI_ENDPOINT"):
        return False, "AZURE_OPENAI_ENDPOINT empty"
    return True, ""


def azure_embed_label():
    d = os.getenv("AZURE_OPENAI_EMBED_DEPLOYMENT")
    return f"Azure · {d}" if d else f"local · {LOCAL_EMBED}"


def azure_chat_deployments():
    raw = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENTS") or os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT") or ""
    return [d.strip() for d in raw.split(",") if d.strip()]


with st.sidebar:
    st.header("🔑 Providers")
    br_ok = bedrock_ready()
    st.caption("🟢 AWS Bedrock ready (main)" if br_ok else "🔴 AWS Bedrock not ready: " + bedrock_status()[1])
    az_ok, az_why = azure_status()
    st.caption("🟢 Azure AI Foundry ready" if az_ok else "⚪ Azure AI Foundry not ready: " + az_why)
    openai_key = st.text_input("OpenAI API key (backup, optional)", value=os.getenv("OPENAI_API_KEY", ""), type="password")
    mode = st.radio("Provider", MODES, index=0)
    if mode.startswith("Auto"):
        st.caption("Auto: the first ready provider (Bedrock → Azure → OpenAI) does everything. The others are used only if it fails, and nothing is sent to them before that.")

use_bedrock = br_ok and mode in (MODES[0], MODES[1])
use_azure = az_ok and mode in (MODES[0], MODES[2])
use_openai = bool(openai_key) and mode in (MODES[0], MODES[3])
# ONE provider does all indexing and retrieval (the "primary"). The others stay dormant: they are used only
# if the primary fails, and their index is then built on demand from the chunks already stored.
ORDER = [p for p, on in (("bedrock", use_bedrock), ("azure", use_azure), ("openai", use_openai)) if on]
primary = ORDER[0] if ORDER else None
providers = [primary] if primary else []
FALLBACKS = ORDER[1:]

if not providers:
    st.title("🔎 AskIT · RAG Lab")
    st.warning("No provider available. Check the course .env (AWS keys + BEDROCK_SMALL_MODEL_ID, or the AZURE_OPENAI_* values), or paste an OpenAI key in the sidebar.")
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
def azure_client(key, endpoint):
    """Azure AI Foundry through its OpenAI-compatible /openai/v1 route (no api-version; the model = deployment name)."""
    from openai import OpenAI
    return OpenAI(base_url=azure_host(endpoint) + "/openai/v1/", api_key=key)


def azure_host(endpoint):
    """Resource root only: pasting the Foundry *project* endpoint (…/api/projects/xyz) or a longer URL still works."""
    import azure_foundry
    return azure_foundry.host(endpoint)


def az():
    return azure_client(os.environ["AZURE_OPENAI_API_KEY"], os.environ["AZURE_OPENAI_ENDPOINT"])


class Store:
    """Tiny local vector store: vectors in memory (numpy), saved to a JSON file. Same idea as Lab 2B's index."""

    def __init__(self, path):
        self.path = Path(path)
        self.ids, self.docs, self.metas, self.vecs = [], [], [], np.zeros((0, 0))
        if self.path.is_file():
            try:
                d = json.loads(self.path.read_text(encoding="utf-8"))
                self.ids, self.docs, self.metas = d["ids"], d["docs"], d["metas"]
                self.vecs = np.array(d["vecs"], dtype=float) if self.ids else np.zeros((0, 0))
            except Exception:
                self.ids, self.docs, self.metas, self.vecs = [], [], [], np.zeros((0, 0))

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({"ids": self.ids, "docs": self.docs, "metas": self.metas,
                                         "vecs": self.vecs.tolist()}), encoding="utf-8")

    def count(self):
        return len(self.ids)

    def add(self, ids, documents, embeddings, metadatas):
        new = np.array(embeddings, dtype=float)
        self.vecs = new if not self.ids else np.vstack([self.vecs, new])
        self.ids += list(ids)
        self.docs += list(documents)
        self.metas += list(metadatas)
        self._save()

    def delete(self, where=None, ids=None):
        drop = set(ids or [])
        keep = [i for i, (cid, m) in enumerate(zip(self.ids, self.metas))
                if cid not in drop and not (where and all(m.get(k) == v for k, v in where.items()))]
        self.ids = [self.ids[i] for i in keep]
        self.docs = [self.docs[i] for i in keep]
        self.metas = [self.metas[i] for i in keep]
        self.vecs = self.vecs[keep] if keep else np.zeros((0, 0))
        self._save()

    def get(self, include=None):
        return {"ids": list(self.ids), "documents": list(self.docs), "metadatas": list(self.metas)}

    def query(self, query_embeddings, n_results):
        q = np.array(query_embeddings[0], dtype=float)
        norms = np.linalg.norm(self.vecs, axis=1) * (np.linalg.norm(q) or 1.0)
        sims = (self.vecs @ q) / np.where(norms == 0, 1.0, norms)
        top = np.argsort(-sims)[:n_results]
        return {"documents": [[self.docs[i] for i in top]], "metadatas": [[self.metas[i] for i in top]],
                "distances": [[float(1 - sims[i]) for i in top]]}   # distance = 1 - cosine


@st.cache_resource
def get_collection(provider):
        # Bedrock, Azure and OpenAI vectors are not compatible: one file each.
    if provider == "azure" and not os.getenv("AZURE_OPENAI_EMBED_DEPLOYMENT"):
        provider = "azure_local"      # local vectors are a different space from Azure-deployment vectors
    return Store(DB_PATH / f"rag_lab_{provider}.json")


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
    azure_model = None
    if use_azure:
        a_opts = list(dict.fromkeys(azure_chat_deployments() or AZURE_PREFERRED))
        pick = st.selectbox("Azure Foundry chat model (deployment)", a_opts + [AZURE_OTHER])
        azure_model = st.text_input("Deployment name", value=a_opts[0]) if pick == AZURE_OTHER else pick
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
@st.cache_resource
def local_embedder():
    try:
        from fastembed import TextEmbedding
    except Exception as e:
        raise RuntimeError(f"fastembed not installed ({e}). Run: pip install fastembed") from e
    return TextEmbedding(LOCAL_EMBED)       # small ONNX model, downloaded once (~130 MB), runs on CPU


def embed(provider, texts, task=None):
    if provider == "azure" and not os.getenv("AZURE_OPENAI_EMBED_DEPLOYMENT"):
        return [v.tolist() for v in local_embedder().embed(texts)]
    if provider == "bedrock":
        def one(t):
            body = json.dumps({"inputText": t[:20000], "dimensions": 512, "normalize": True})
            r = with_retry(lambda: bedrock_client().invoke_model(modelId=BEDROCK_EMBED, body=body))
            return json.loads(r["body"].read())["embedding"]
        with ThreadPoolExecutor(max_workers=4) as pool:   # a few at a time: kind to the shared account
            return list(pool.map(one, texts))
    vectors = []
    for i in range(0, len(texts), 96):  # API batch limit (Cohere: 96)
        batch = texts[i : i + 96]
        if provider == "azure":
            import azure_foundry
            vectors.extend(with_retry(lambda: azure_foundry.embed_batch(
                batch, os.getenv("AZURE_OPENAI_EMBED_DEPLOYMENT"), os.environ["AZURE_OPENAI_API_KEY"],
                os.environ["AZURE_OPENAI_ENDPOINT"], query=(task == "query"))))
        else:
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
            status.append(f"⚠️ {file.name}: {p} indexing failed — {str(e)[:600]}")
    return status


# ---------------------------------------------------------------- Step 5: Retrieve (with fallback)
def ensure_fallback_index(fb):
    """Build a fallback provider's index from the chunks already stored by the primary provider (only when it failed)."""
    src, dst = get_collection(primary), get_collection(fb)
    data = src.get(include=["documents", "metadatas"])
    if not data["ids"]:
        return
    sig = hashlib.md5("".join(data["documents"]).encode()).hexdigest()
    if st.session_state.get(f"fb_sig_{fb}") == sig and dst.count() == len(data["ids"]):
        return
    if dst.count():
        dst.delete(ids=dst.get()["ids"])
    vecs = embed(fb, data["documents"])
    dst.add(ids=data["ids"], documents=data["documents"], embeddings=vecs, metadatas=data["metadatas"])
    st.session_state[f"fb_sig_{fb}"] = sig


def retrieve(question, k):
    errors = []
    for p in providers + FALLBACKS:
        try:
            if p in FALLBACKS:
                ensure_fallback_index(p)
            col = get_collection(p)
            if col.count() == 0:
                continue
            q_vec = embed(p, [question], task="query")[0]
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
    if use_azure:
        chain.append(("azure", azure_model))
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
            client = az() if provider == "azure" else openai_client(openai_key)
            res = with_retry(lambda: client.chat.completions.create(
                model=model, messages=[{"role": "system", "content": SYSTEM_PROMPT},
                                       {"role": "user", "content": prompt}]))
            return res.choices[0].message.content, model
        except Exception as e:
            errors.append(f"{model}: {str(e)[:120]}")
    raise RuntimeError("All models failed. " + " | ".join(errors))


# ---------------------------------------------------------------- UI: Knowledge base
st.title("🔎 AskIT · RAG Lab")
st.caption("Load KB → Chunk → Embed → Store → Retrieve → Generate   ·   Orbit Corp IT helpdesk")

# ---------------------------------------------------------------- UI: Architecture diagram (follows the sidebar settings)
with st.expander("🏗️ Architecture: how this app works (follows your sidebar settings)"):
    try:
        import streamlit.components.v1 as components
        import arch_diagram
        _ad_html = arch_diagram.render(
            chunk_size=chunk_size, overlap=overlap, top_k=top_k, show_ctx=show_ctx,
            embed_model={"bedrock": BEDROCK_EMBED, "azure": azure_embed_label()}.get(primary, OPENAI_EMBED),
            chat_model=chat_chain()[0][1], fallback=bool(FALLBACKS))
        if hasattr(st, "iframe"):
            st.iframe(_ad_html, height=800)
        else:
            components.html(_ad_html, height=800, scrolling=True)
    except Exception as _ad_e:   # the diagram is optional: never break the app
        st.caption(f"Architecture diagram unavailable: {_ad_e}")

with st.sidebar:
    st.divider()
    st.header("📚 AskIT knowledge base")
    kb_folder = find_kb_folder()
    if kb_folder is None:
        st.warning("askit_data/kb not found. Run the app from inside your cloned repo, or upload the KB files below.")
    elif st.button("Load AskIT KB (20 articles)", type="primary", width="stretch"):
        st.session_state.messages = []          # new knowledge = fresh chat
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
        st.session_state.messages = []          # new documents = fresh chat
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
        for p in ("bedrock", "azure", "azure_local", "openai"):
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
if st.button("🧹 Clear chat"):
    st.session_state.messages = []
    st.rerun()
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
                        st.text(doc)   # plain text: chunks start with "# Heading", markdown would render it huge
        except Exception as e:
            reply = f"⚠️ {e}"
            st.error(reply)
    st.session_state.messages.append({"role": "assistant", "content": reply})
