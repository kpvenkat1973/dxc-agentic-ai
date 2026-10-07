# Stretch: Build your own "Chat with my PDF" app (using vibe coding)

**For:** anyone who has finished Lab 2A and 2B and wants to build something to show others.

**What you will build:** a small web app (Streamlit) where you **upload your own PDF** and **ask questions about it**. The app answers only from your PDF and tells you the page number it used. You also give the app your own name, colour and personality.

**How:** you do not write the code by hand. You tell your AI assistant (Claude, Copilot, or whatever is on your VM) what you want, using the prompt in Step 2. The AI writes the code. **You run it, test it, break it and fix it.**

> Vibe coding does not mean "paste and pray". **You are the reviewer.** If you cannot explain a part of the code in one sentence, ask the AI to explain it before you keep it.

**Time needed:** about 40 minutes.

---

## Simple words used in this lab

| Word | Meaning |
|---|---|
| **PDF text** | The words inside your PDF. Scanned PDFs (photos of paper) have no text, so they will not work. |
| **Chunk** | A small piece of the PDF text (a few lines). We cut the whole PDF into many chunks. |
| **Embedding** | A list of numbers that represents the meaning of a chunk. Similar meaning = similar numbers. |
| **Top-K** | How many best-matching chunks we pick to answer a question. |
| **Grounded answer** | An answer that comes only from your PDF, not from the AI's imagination. |

---

## Step 0. Get ready (5 minutes)

1. Open **Command Prompt** and go to your project folder:

   ```
   cd /d C:\AskIT\dxc-agentic-ai
   ```

2. Install the packages (copy and paste, press Enter, wait till it finishes):

   ```
   python -m pip install streamlit numpy boto3 python-dotenv pypdf
   ```

3. Check that your AWS access is working. This should run without any red error:

   ```
   python Day03\Labs\lab02-naive-rag\lab02a_embeddings.py
   ```

   If you see an error, check the "If something goes wrong" table at the end, or call the trainer.

4. **Pick one PDF** to use for your demo. Keep it ready on your desktop.
   - Good choices: your college syllabus, your resume, a company policy, a user manual, notes of any subject.
   - Must have **selectable text** (try selecting a line with your mouse). Scanned PDFs will not work.
   - Keep it **under 30 pages** so the app is fast.
   - Do not use PDFs with confidential or personal data (Aadhaar, bank details, etc.).

> You do **not** need to create any folder or file yourself. Your AI assistant will create the folder `my-rag-app` and the file `app.py` for you (the prompt below tells it to).

---

## Step 1. Choose your identity (2 minutes)

Fill this table. You will paste these choices into the prompt in Step 2.

| Choice | Your pick (examples) |
|---|---|
| App name | `PDF Buddy`, `Doc Oracle`, `AskMyPDF` |
| Personality | calm senior engineer, cricket commentator, friendly Chennai auto-anna, polite teacher |
| Style of talking | short and funny / formal / English with a little Tanglish / always ends with a joke |
| Colour and theme | teal on dark, saffron on white, neon on black |
| Avatar emoji | 🤖 🦉 🛠️ 🎩 |
| Tagline | "Upload. Ask. Done." |
| Your name or team (for footer) | "Built by Priya, Team 2" |

---

## Step 2. The prompt (copy, fill the [BRACKETS], paste into your AI assistant)

Replace every `[BRACKET]` with your choice from Step 1. Do not change anything else.

```text
You are my pair-programmer. I am a fresher and new to RAG, so keep the code simple.

TASK
Create a new folder C:\AskIT\dxc-agentic-ai\Day03\Labs\my-rag-app\ and inside it create ONE file, app.py.
It is a Streamlit app: the user uploads a PDF and chats with it (RAG). Keep the code simple and
readable, under 200 lines. Add short comments saying WHAT each block does and WHY.

WHAT IS ALREADY AVAILABLE IN MY REPO (do not rewrite these)
- Add the repo root to sys.path first:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
- `from askit_core import bedrock, config`
    - bedrock.client() gives a boto3 bedrock-runtime client.
    - config.SMALL_MODEL is the chat model id (Amazon Nova Micro).
- Embeddings: Amazon Titan Text Embeddings v2, modelId "amazon.titan-embed-text-v2:0",
  request body {"inputText": text, "dimensions": 512, "normalize": true},
  response JSON key "embedding".
- Chat: client.converse(modelId=config.SMALL_MODEL,
  messages=[{"role":"user","content":[{"text": prompt}]}],
  inferenceConfig={"maxTokens": 500, "temperature": 0.2})
  and read response["output"]["message"]["content"][0]["text"].
- Read the PDF with the pypdf package (already installed).
- Write my own small functions for chunking, embedding and cosine similarity in app.py using numpy.

MUST-HAVE FEATURES
1. The app has ONLY ONE way to give data: a PDF upload box (st.file_uploader, type pdf).
   There is no built-in knowledge base.
2. After upload, show a button "Build index". It does these steps and shows a progress bar:
   a. read the text page by page (remember the page number of every piece of text),
   b. cut the text into chunks (by words, size 120, overlap 30),
   c. embed every chunk (do 4 at a time at most, the AWS account is shared),
   d. keep chunks + vectors in st.session_state so nothing is rebuilt on every click.
   Show how many pages and how many chunks were created.
   If the PDF has no text (scanned PDF), show a friendly message and stop.
   Uploading a new PDF must replace the old one and clear the chat.
3. Chat box (st.chat_input and st.chat_message). For each question:
   a. embed the question and find the top-K chunks by cosine similarity,
   b. build a prompt: "Answer ONLY from the context. If the answer is not in the context, say you
      could not find it in the PDF. Cite the page like [p.3]."
   c. call the chat model and show the answer.
4. Under every answer, an expander "Sources" listing each chunk used with: page number,
   similarity score (2 decimals) and the chunk text.
5. Sidebar: Top-K slider (1 to 6), chunk size and overlap sliders (changing them needs
   "Build index" again), and a "Clear chat" button.
6. If AWS fails, show a simple message (no stack trace) saying what to check: .env keys, region,
   Titan model access. Let me retry.

MAKE IT MINE
- App name: [APP NAME]. Page title icon: [AVATAR EMOJI]. Tagline under the title: "[TAGLINE]".
- Personality: [PERSONALITY]. Style of talking: [STYLE]. Put this in the prompt to the chat model,
  but the answer must still come only from the PDF and must still cite pages.
- Theme: [COLOUR AND THEME]. Use a small CSS block with st.markdown (coloured header, rounded
  chat bubbles, coloured buttons). Use the avatar emoji as the assistant avatar.
- Sidebar "About me" card with: [YOUR NAME OR TEAM], today's date and one fun line.
- Footer: "Built by [YOUR NAME OR TEAM] with vibe coding at DevPro Academy".

ONLY AFTER THE MUST-HAVE FEATURES WORK, add (in this order):
- A "Not in my PDF?" button that asks a question from outside the PDF (for example "Who won the
  last cricket world cup?") to show the app says it does not know.
- A small badge on each answer: "grounded" if the best score is 0.35 or more, else "weak match".
- A button to download the chat as a .md file.

RULES
- Never write AWS keys in the code or print them. Settings come from .env through askit_core.config.
- Create and change files ONLY inside my-rag-app\. Do not edit askit_core or any lab file.
- When done, tell me the exact command to run from C:\AskIT\dxc-agentic-ai:
    python -m streamlit run Day03\Labs\my-rag-app\app.py
  and give me a 5-line "how it works" summary that I can say out loud.
```

---

## Step 3. Run it and check (10 minutes)

1. Run the command the AI gave you (from `C:\AskIT\dxc-agentic-ai`):

   ```
   python -m streamlit run Day03\Labs\my-rag-app\app.py
   ```

   The app opens in your browser at `http://localhost:8501`.

2. Upload your PDF and click **Build index**. Wait for the progress bar.
3. Ask **3 questions**:
   - one easy question (answer is clearly written in the PDF),
   - one question that needs a specific fact (a number, a date, a name),
   - one question that is **not** in your PDF.
4. For every answer, **open "Sources" and check the page**. Does that chunk really support the answer?
5. Read your code once. Ask the AI: *"Explain the search function and the prompt line by line, like I am new to RAG."*

---

## Step 4. Break it on purpose (5 minutes)

| Try this | What you learn |
|---|---|
| Top-K = 1, then Top-K = 6 | Too little context misses the answer. Too much adds noise. |
| Chunk size very small (30), then very big (300), then Build index again | Chunk size changes what is found. |
| Ask a question that is not in your PDF | Does the app say "not found" or does it guess? |
| Delete the line "Answer ONLY from the context" and ask again | See how the AI starts making up answers. |

Write 3 lines for yourself: **what broke, why it broke, what you changed.**

---

## Step 5. Finish line and demo

You are done when:
- you can upload your own PDF and the app answers from it with page numbers,
- the app looks and sounds like **you** (name, colour, personality, footer),
- you can explain in 30 seconds: **read PDF, cut into chunks, embed, find best chunks, answer from them only.**

**Show and tell:** keep the app open. The trainer will pick a few participants to demo on the big screen. In your demo: upload your PDF, ask one question, show the Sources, then ask one question that is not in the PDF.

---

## If something goes wrong

| What you see | What to do |
|---|---|
| `No module named streamlit` (or numpy, boto3, pypdf) | Run: `python -m pip install streamlit numpy boto3 python-dotenv pypdf` |
| `UnrecognizedClientException` or "security token invalid" | AWS keys in `.env` are wrong or expired. Tell the trainer. |
| `AccessDenied` for Titan or Nova | Model access is not enabled. Tell the trainer. |
| `Throttling` | Too many requests together. Wait 30 seconds and click again. |
| "No text found in this PDF" | Your PDF is a scanned image. Use another PDF where you can select the text. |
| Building the index takes very long | Your PDF is too big. Use a PDF under 30 pages. |
| App builds the index again on every question | Tell the AI: "keep the index in st.session_state so it is not rebuilt on every click". |
| The AI wrote 400 lines and you cannot follow | Tell the AI: "simplify, keep it under 200 lines, remove anything I did not ask for". |
