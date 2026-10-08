import json
import sys
from pathlib import Path

import numpy as np
import streamlit as st
from pypdf import PdfReader

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from askit_core import bedrock, config

st.set_page_config(page_title="Doc Oracle", page_icon="🦉", layout="wide")

st.markdown(
    """
    <style>
    .block-container { padding-top: 1rem; }
    .title { color: #14b8a6; font-weight: 800; }
    .tagline { color: #64748b; font-size: 1.05rem; margin-bottom: 1.2rem; }
    .card { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 0.8rem 1rem; margin: 0.6rem 0 1rem; }
    .stChatMessage { border-radius: 18px; }
    .stButton > button { border-radius: 999px; background: linear-gradient(135deg, #14b8a6, #0ea5e9); color: white; border: none; }
    .stDownloadButton > button { border-radius: 999px; background: #0f172a; color: white; border: none; }
    .footer { text-align: center; color: #64748b; font-size: 0.82rem; margin-top: 1.2rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

APP_NAME = "Doc Oracle"
PERSONALITY = "calm senior engineer"
STYLE = "short, practical, friendly"

st.title(f"{APP_NAME} 🦉")
st.caption("Upload. Ask. Done.")

with st.sidebar:
    st.markdown("<div class='card'><b>About me</b><br>Built by Team 2<br>Today: " + __import__("datetime").datetime.now().strftime("%d %b %Y") + "<br>Fun line: I can debug any PDF by lunch.</div>", unsafe_allow_html=True)
    top_k = st.slider("Top-K", 1, 6, 3)
    chunk_size = st.slider("Chunk size", 80, 200, 120)
    overlap = st.slider("Chunk overlap", 10, 60, 30)
    clear = st.button("Clear chat")
    if clear:
        st.session_state.pop("messages", None)

if "messages" not in st.session_state:
    st.session_state.messages = []

if "index" not in st.session_state:
    st.session_state.index = None

uploaded = st.file_uploader("Upload a PDF", type="pdf")
if uploaded is not None and st.session_state.get("uploaded_name") != uploaded.name:
    st.session_state.index = None
    st.session_state.messages = []
    st.session_state.uploaded_name = uploaded.name

if config.SMALL_MODEL == "":
    st.warning("AWS is not configured yet. Check .env keys, region, and the Bedrock model access, then retry.")
    st.stop()


def chunk_text(text: str, size: int, overlap: int):
    words = text.split()
    if not words:
        return []
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + size, len(words))
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start = max(start + size - overlap, end - overlap)
    return chunks


def embed_many(texts):
    client = bedrock.client()
    vectors = []
    for i in range(0, len(texts), 4):
        batch = texts[i : i + 4]
        payload = [{"inputText": t, "dimensions": 512, "normalize": True} for t in batch]
        body = json.dumps({"inputText": batch[0], "dimensions": 512, "normalize": True}) if len(batch) == 1 else json.dumps({"inputText": batch})
        # Titan v2 accepts a single inputText; batch with four calls is safer and stays under the shared AWS limit.
        items = []
        for text in batch:
            resp = client.invoke_model(modelId="amazon.titan-embed-text-v2:0", body=json.dumps({"inputText": text, "dimensions": 512, "normalize": True}))
            data = json.loads(resp["body"].read())
            items.append(data["embedding"])
        vectors.extend(items)
    return np.array(vectors, dtype=float)


def build_index(file):
    reader = PdfReader(file)
    page_texts = []
    for page_no, page in enumerate(reader.pages, 1):
        text = (page.extract_text() or "").replace("\xa0", " ").strip()
        if text:
            page_texts.append((page_no, text))
    if not page_texts:
        st.warning("No text found in this PDF. Please upload a searchable PDF with selectable text.")
        return False

    chunks = []
    for page_no, text in page_texts:
        for part in chunk_text(text, chunk_size, overlap):
            chunks.append({"page": page_no, "text": part.strip()})

    with st.spinner("Building the vector index..."):
        progress = st.progress(0)
        vectors = []
        for i in range(0, len(chunks), 4):
            batch = [c["text"] for c in chunks[i : i + 4]]
            vectors.extend(embed_many(batch))
            progress.progress((i + len(batch)) / max(len(chunks), 1))

    st.session_state.index = {"chunks": chunks, "vectors": np.array(vectors, dtype=float)}
    st.success(f"Built index from {len(page_texts)} pages and {len(chunks)} chunks.")
    return True


def retrieve(question):
    index = st.session_state.index
    qv = embed_many([question])[0]
    rows = index["vectors"]
    qn = np.linalg.norm(qv)
    norms = np.linalg.norm(rows, axis=1)
    sims = (rows @ qv) / np.maximum((norms * qn), 1e-9)
    order = np.argsort(sims)[::-1][: top_k]
    top = [(int(index["chunks"][i]["page"]), float(sims[i]), index["chunks"][i]["text"]) for i in order]
    return top


def answer_question(question):
    if st.session_state.index is None:
        st.warning("Build the PDF index first.")
        return

    hits = retrieve(question)
    context = "\n".join(f"[p.{page}] {text}" for page, _, text in hits)
    persona = f"You are {PERSONALITY}. Talk in {STYLE}. Answer ONLY from the context below. If the answer is not in the PDF, say 'I could not find that in the PDF.' Cite the page like [p.3].\n\nContext:\n{context}"

    try:
        response = bedrock.client().converse(
            modelId=config.SMALL_MODEL,
            messages=[{"role": "user", "content": [{"text": persona}]}],
            inferenceConfig={"maxTokens": 500, "temperature": 0.2},
        )
        answer = response["output"]["message"]["content"][0]["text"]
    except Exception:
        st.error("AWS request failed. Check your .env keys, AWS region, and Titan/Nova model access, then retry.")
        return

    best = hits[0][1] if hits else 0.0
    badge = "grounded" if best >= 0.35 else "weak match"
    st.session_state.messages.append({"role": "user", "content": question})
    st.session_state.messages.append({"role": "assistant", "content": answer, "badge": badge, "sources": hits})

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant":
            st.caption(message.get("badge", "grounded"))
            with st.expander("Sources"):
                for page, score, text in message.get("sources", []):
                    st.markdown(f"- [p.{page}] · score {score:.2f}\n{text}")

if uploaded is not None:
    if st.button("Build index"):
        build_index(uploaded)

    if st.button("Not in my PDF?"):
        st.session_state["pending_question"] = "Who won the last cricket world cup?"

    pending = st.session_state.pop("pending_question", None)
    if pending:
        answer_question(pending)

    user_input = st.chat_input("Ask about the PDF")
    if user_input:
        answer_question(user_input)

else:
    st.info("Upload a PDF to start.")

chat_text = "\n\n".join(
    f"## {m['role'].title()}\n{m['content']}\n" + (
        "\nSources:\n" + "\n".join(f"- [p.{p}] score {s:.2f}: {t}" for p, s, t in m.get("sources", [])) if m["role"] == "assistant" else ""
    )
    for m in st.session_state.messages
)

st.download_button(
    label="Download chat as .md",
    data=chat_text or "# Chat\n",
    file_name="chat.md",
    mime="text/markdown",
)

st.markdown('<div class="footer">Built by Team 2 with vibe coding at DevPro Academy</div>', unsafe_allow_html=True)
