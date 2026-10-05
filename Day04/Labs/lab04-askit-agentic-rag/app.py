"""Lab 4 - AskIT Agentic RAG: watch the critic loop work.
Run:  streamlit run app.py     (from this folder, with the same .venv as Lab 3)"""
import os
from pathlib import Path

import pandas as pd
import streamlit as st

import agentic
import eval_agentic as ev
from rag import pipeline
from rag.ingest import chunk_documents, load_documents
from rag.llm import LLM, UsageLog, bedrock_ready

HERE = Path(__file__).resolve().parent
try:
    from dotenv import load_dotenv
    load_dotenv(HERE.parents[2] / ".env")   # the course .env (AWS keys, Bedrock model id)
    load_dotenv()                            # or a .env in this folder
except Exception:
    pass

st.set_page_config(page_title="AskIT Agentic RAG", page_icon="🔁", layout="wide")
ss = st.session_state
ss.setdefault("log", UsageLog())

with st.sidebar:
    st.header("Connection")
    br_ok = bedrock_ready()
    env_key = os.getenv("OPENAI_API_KEY", "")
    label = st.radio("Provider", ["AWS Bedrock (main)", "OpenAI (backup)", "Offline"],
                     index=0 if br_ok else (1 if env_key else 2))
    api_key, provider = "", "offline"
    if label.startswith("AWS") and br_ok:
        provider = "bedrock"
        st.caption(f"🟢 Live: AWS Bedrock · {os.getenv('BEDROCK_SMALL_MODEL_ID')}")
    elif label.startswith("OpenAI"):
        key_in = st.text_input("OpenAI API key", value="", type="password",
                               placeholder="Loaded from .env" if env_key else "sk-...")
        api_key = key_in or env_key
        provider = "openai" if api_key else "offline"
    if label.startswith("AWS") and not br_ok:
        st.error("AWS keys or BEDROCK_SMALL_MODEL_ID not found in .env: offline mode.")
    if provider == "offline":
        st.caption("🟠 Offline mode: stand-in models, no API calls")
    audience = st.radio("Audience", ["Employee", "Contractor"])
    max_rounds = st.slider("Max retrieval rounds", 1, 4, agentic.MAX_ROUNDS)
    st.caption("Rounds = 1 means no loop: the same as Lab 3.")


@st.cache_resource(show_spinner="Building the index...")
def get_index(provider, key):
    llm = LLM(key or None, log=ss.log, cache_dir=str(HERE / ".cache"), provider=provider)
    docs = load_documents(str(agentic.LAB3 / "data" / "kb"))
    return pipeline.Index(chunk_documents(docs, "section"), llm)


index = get_index(provider, api_key)
st.title("🔁 AskIT Agentic RAG")
st.caption("Single pass: retrieve → answer.  Agentic: retrieve → critic → rewrite → retrieve again → answer → answer check.")

tab_ask, tab_cmp, tab_how = st.tabs(["Ask (watch the loop)", "Compare", "How it works"])

with tab_ask:
    samples = [x["q"] for x in ev.QUESTIONS]
    pick = st.selectbox("Sample question", ["(type my own)"] + samples)
    q = st.text_input("Question", value="" if pick == "(type my own)" else pick)
    who = next((x["audience"] for x in ev.QUESTIONS if x["q"] == q), audience)   # a sample question carries its own audience
    if q and who != audience:
        st.caption(f"This sample question is asked as a **{who}**.")
    if st.button("Ask", type="primary") and q.strip():
        audience = who
        left, right = st.columns(2)
        single = agentic.run_single(index, q, audience)
        agent_res = agentic.run(index, q, audience, max_rounds)
        with left:
            st.subheader("Single pass (Lab 3)")
            st.write(single.answer)
            st.caption(f"Sources: {agentic._docs(single.hits)} · LLM calls {agentic.llm_calls(single)} · ${single.cost:.4f}")
        with right:
            st.subheader("Agentic loop")
            for t in agent_res.trace:
                st.markdown(f"{t['icon']} **{t['title']}** — {t['detail']}")
            st.divider()
            st.write(agent_res.answer)
            st.caption(f"Rounds {agent_res.rounds} · Sources: {agentic._docs(agent_res.hits)} · "
                       f"LLM calls {agentic.llm_calls(agent_res)} · ${agent_res.cost:.4f}")

with tab_cmp:
    st.write("8 questions: 5 multi-part, 3 simple. A question passes when the final evidence holds **every** article the answer needs.")
    if st.button("Run both pipelines"):
        bar = st.progress(0.0)
        for i, cfg in enumerate(ev.CONFIGS):
            rows = ev.evaluate(index, cfg, max_rounds, lambda p, i=i: bar.progress((i + p) / len(ev.CONFIGS), text=cfg))
            ev.save_run(ev.summarize(cfg, rows, "offline" if index.llm.offline else index.llm.chat_model))
            ss[f"rows_{i}"] = rows
        bar.empty()
    runs = ev.load_runs()
    if runs:
        st.dataframe(pd.DataFrame([{k: v for k, v in r.items() if k != "questions"} for r in runs]), width="stretch", hide_index=True)
    for i, cfg in enumerate(ev.CONFIGS):
        if f"rows_{i}" in ss:
            with st.expander(f"Per question: {cfg}"):
                st.dataframe(pd.DataFrame(ss[f"rows_{i}"]).drop(columns=["answer"]), width="stretch", hide_index=True)

with tab_how:
    st.markdown("""
**Router** – a simple question takes one pass. A multi-part question enters the loop.
**Critic** – reads the passages and says: enough to answer *every* part? If not, what is missing? *(your TODO-1)*
**Rewrite** – turns "what is missing" into a new search query. *(your TODO-2)*
**Loop control** – go again only if the critic is not satisfied and rounds are left. *(your TODO-3)*
**Answer check** – a second critic checks the answer against its sources. If it is not grounded, AskIT hands over to a human.
""")
