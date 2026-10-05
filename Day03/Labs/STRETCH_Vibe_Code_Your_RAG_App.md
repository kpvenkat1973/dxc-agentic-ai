# Stretch: vibe-code your own RAG app (and make it yours)

**For:** anyone who finished Lab 2A/2B and wants to build something they can show off.
**You build:** a Streamlit chat app that answers Orbit Corp IT questions from the KB, shows its sources, and has your own look, name and personality.
**How:** you describe it to your AI coding assistant (Claude, Copilot, whatever your VM has). You review, run, break and fix. You do not type it all by hand.

> Vibe coding does not mean "paste and pray". **You are the reviewer.** If you cannot explain a part of the code in one sentence, ask the AI to explain it before you keep it.

---

## 0. Before you start (3 min)

1. Command Prompt: `cd /d C:\AskIT\dxc-agentic-ai`
2. Make sure the packages are there: `python -m pip install streamlit numpy boto3 python-dotenv`
3. Your `.env` (repo root) must have the AWS keys, `AWS_REGION=us-east-1` and `BEDROCK_SMALL_MODEL_ID` (the trainer shared it). Test: `python Day03\Labs\lab02-naive-rag\lab02a_embeddings.py` runs.
4. Create your own folder so nothing else is touched: `Day03\Labs\my-rag-app\` (put `app.py` in it).

## 1. Pick your identity (2 min)

Fill these in. They go into the prompt below.

| Choice | Your pick (examples) |
|---|---|
| App name | `AskIT Buddy`, `Orbit Oracle`, `HelpBot 3000` |
| Assistant persona | calm senior engineer, pirate captain, cricket commentator, friendly Chennai auto-anna |
| Tone rules | short and funny / formal / Tanglish-light / always ends with a joke |
| Accent colour + theme | teal on dark, saffron on white, neon on black |
| Avatar emoji | 🤖 🦉 🛠️ 🎩 |
| Tagline | "Locked out? I got you." |
| Your name or team (footer) | "Built by Priya, S3 Team 2" |

## 2. The prompt (copy, fill the [BRACKETS], paste to your AI assistant)

```text
You are my pair-programmer. Build a single-file Streamlit app `app.py` in the folder
C:\AskIT\dxc-agentic-ai\Day03\Labs\my-rag-app\ that is a RAG chatbot over the Orbit Corp
IT helpdesk knowledge base. Keep the code simple and readable: I must be able to explain it.
Add short comments saying WHAT each block does and WHY.

CONTEXT (already in my repo, do not rewrite):
- `from askit_core import bedrock, config, data`
  - `bedrock.client()` returns a boto3 bedrock-runtime client (with retries).
  - `data.load_kb()` returns {doc_id: article_text} for 20 markdown KB articles.
  - `config.SMALL_MODEL` is the Bedrock chat model id (Amazon Nova Micro); `config.REGION` the region.
  - Add the repo root to sys.path first:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
- Embeddings: Amazon Titan Text Embeddings v2, modelId "amazon.titan-embed-text-v2:0",
  request body {"inputText": text, "dimensions": 512, "normalize": true}, response JSON key "embedding".
  I wrote my own embed / cosine / chunk_text / build_index / search in
  Day03\Labs\lab02-naive-rag\lab02a_embeddings.py and lab02b_index.py. Reuse the ideas.
  If my versions are not importable, use `from askit_core.rag import embed_text, SimpleIndex`
  (SimpleIndex.build(client, docs, size, overlap) and .search(client, query, k)).
- Chat model: use client.converse(modelId=config.SMALL_MODEL,
  messages=[{"role":"user","content":[{"text": prompt}]}],
  inferenceConfig={"maxTokens": 500, "temperature": 0.2}) and read
  response["output"]["message"]["content"][0]["text"].

CORE FEATURES (must work):
1. On first run, chunk the KB (words, size 80, overlap 20), embed every chunk, keep the index in
   st.session_state or @st.cache_resource so it is NOT rebuilt on every click.
2. A chat box (st.chat_input / st.chat_message). For each question:
   a. embed the question, find the top-K chunks by cosine similarity,
   b. build a grounded prompt: "Answer ONLY from the context. If the answer is not in the context,
      say you do not know and suggest contacting the IT helpdesk. Cite the source ids like [KB-004]."
   c. call the chat model and show the answer.
3. Under every answer show an expander "Sources" listing each retrieved chunk with its doc id,
   similarity score (2 decimals) and the chunk text.
4. A sidebar with: Top-K slider (1-6), chunk size and overlap sliders (with a "Rebuild index" button),
   and a "Clear chat" button.
5. Friendly error messages (no stack traces) if AWS fails: show what to check
   (.env keys, region, Titan access) and let me retry.

MAKE IT MINE (personalisation, all of these):
- App name: [APP NAME]. Page title and icon: [AVATAR EMOJI]. Tagline under the title: "[TAGLINE]".
- Persona: [PERSONA]. Tone rules: [TONE RULES]. Put this in the system/grounding prompt, but the
  answer must still stay grounded in the context and cite sources.
- Theme: accent colour [COLOUR], [DARK or LIGHT] feel. Use st.markdown with a small CSS block
  (custom header banner, rounded chat bubbles, accent-coloured buttons). Use the avatar emoji
  as the assistant avatar in st.chat_message.
- A sidebar "About me" card with: [YOUR NAME / TEAM], the date, and one fun line.
- 4 example-question buttons ("Try me") that fill the chat box: pick questions that suit the KB.
- Footer: "Built by [YOUR NAME] with vibe coding at DevPro Academy".

NICE-TO-HAVE (do these only after the core works, in this order):
- A "Not in KB?" demo button that asks something out of scope (e.g. cafeteria menu) to show the
  app says it does not know.
- Show a small badge on each answer: "grounded" if the best score >= 0.35, else "weak match".
- Download chat as a .md file button.
- A "Mood" toggle (formal / playful) that changes the tone rules.

RULES:
- Never hard-code AWS keys or print them. Settings come from .env through askit_core.config.
- Only touch files in my-rag-app\. Do not edit askit_core or any lab file.
- When done: give me the exact command to run (from C:\AskIT\dxc-agentic-ai):
  python -m streamlit run Day03\Labs\my-rag-app\app.py
  and a 5-line "how it works" summary I can say out loud.
```

## 3. Run it and review (10 min)

1. Run: `python -m streamlit run Day03\Labs\my-rag-app\app.py`. It opens at `http://localhost:8501`.
2. Ask 3 questions: one easy KB question, one that needs a specific fact, one the KB cannot answer.
3. Check every answer: **Open Sources. Does the cited chunk really support the answer?**
4. Read your own code once. Ask the AI: "Explain `search()` and the prompt line by line like I am new to RAG."

## 4. Break it on purpose (5 min)

| Try | What you learn |
|---|---|
| Set Top-K = 1, then 6 | too little context misses answers; too much adds noise |
| Chunk size 30, then 300 (rebuild) | chunking changes what is retrieved |
| Ask the out-of-scope question | does grounding stop the guess? |
| Delete the "answer ONLY from the context" rule | watch the app start to make things up |

Write 3 lines for yourself: what broke, why, and what you changed.

## 5. Finish line

You are done when:
- the app runs, answers from the KB and shows sources,
- it clearly looks and sounds like **you** (name, colour, persona, footer),
- you can explain in 30 seconds: embed, retrieve, ground, answer.

**Show-and-tell:** keep the app running. The trainer picks a few to demo on the screen.

## If something goes wrong

| Symptom | Fix |
|---|---|
| `No module named streamlit` (or numpy, boto3) | `python -m pip install streamlit numpy boto3 python-dotenv` |
| `UnrecognizedClientException` / security token invalid | AWS keys in `.env` are wrong or missing a session token: tell the trainer |
| `AccessDenied` on Titan or Nova | model access not enabled: tell the trainer |
| `Throttling` | wait 30 seconds, click again |
| App rebuilds the index on every question | ask the AI: "cache the index with @st.cache_resource or session_state" |
| AI wrote 400 lines you cannot follow | ask: "simplify, keep it under 150 lines, remove anything I did not ask for" |
