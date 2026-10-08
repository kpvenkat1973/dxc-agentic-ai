# Lab 2, Part C: your first RAG app (AskIT)

**AskIT today:** reads the Orbit Corp IT knowledge base, finds the right article for a question, and answers from it, with sources, or "I couldn't find that".
You built embeddings and an index in Parts A and B. This app wires them to an LLM so you can run real experiments.

| Step | Where | Time | You do |
|---|---|---|---|
| **1** | App, with the trainer | 15 min | Load the KB, ask questions, look inside the retrieval |
| **2** | App + `submission\experiment.md` | 25 min | Change chunk size and Top-K, measure with the Mini eval |
| ⭐ Stretch | App | | Out-of-scope questions, your own documents, find a failure |

## Set up (once, 3 minutes)
```
cd C:\AskIT\dxc-agentic-ai
python -m pip install -r Day03\Labs\lab02-askit-rag-app\requirements.txt
cd Day03\Labs\lab02-askit-rag-app
python -m streamlit run app.py
```
The app opens at http://localhost:8501. **AWS Bedrock is the default** (Nova for answers, Titan for embeddings) and uses the same `.env` as the earlier labs.
*Bedrock not working?* Paste an OpenAI key in the sidebar (backup) and choose **OpenAI only**.

## Step 1: Run it
1. In the sidebar click **Load AskIT KB (20 articles)**. Wait for the green message.
2. Pick a sample question → **Ask**. Open **🔍 Retrieved chunks** under the answer.
3. Ask these three and compare the retrieved chunks with the answer:
   - *What is the minimum password length?*
   - *My VPN shows error 809 - what should I try?*
   - *Which cafeteria serves vegan food on Fridays?*  ← not in the KB. What does AskIT say?

## Step 2: Experiment (evidence in `submission\experiment.md`)
1. Open **🧪 Mini eval** → **Run mini eval**. It asks 12 questions and checks whether the right article (**doc hit**) and the answer text (**answer hit**) came back. No LLM cost.
2. Change **one** setting in the sidebar, click **Load AskIT KB** again (it replaces the old chunks), run the Mini eval again.
3. Do this for the 4 settings in the template. The app keeps a table called **Your experiments**: copy it into `submission\experiment.md`.
4. Write one or two sentences: what changed and why?

## ⭐ Stretch (fast movers)
- The two out-of-scope questions still have a **best similarity** score. Why can't a similarity score alone say "not in the KB"?
- Upload one of your own documents (PDF, DOCX, MD) in the sidebar and ask it questions.
- **Break it.** Write 3 questions that this app answers *badly* (wrong, incomplete, or confidently wrong). Add them to the end of `submission\experiment.md`. Day 4 starts from your list.

## Check yourself
`pytest Day03\Labs\lab02-askit-rag-app` → aim for **3 passed** at the end of the lab.

## How it works
| Step | What happens | Code |
|---|---|---|
| Extract | Pull text from the file | `extract_text()` |
| Chunk | Split into overlapping pieces | `chunk_text()` |
| Embed | Turn each chunk into a vector (Titan) | `embed()` |
| Store | Save vectors in a local file (`vector_store\` folder, not pushed) | `ingest()` |
| Retrieve | Embed the question, find the Top-K nearest chunks | `retrieve()` |
| Generate | Send question + chunks to the model with a grounding prompt | `generate()` |

## Stuck?
| Symptom | Fix |
|---|---|
| `streamlit` not recognised | Use `python -m streamlit run app.py` (and run the `python -m pip install` line again) |
| Page says "No provider available" | The course `.env` is missing the AWS keys or `BEDROCK_SMALL_MODEL_ID`. Fix it, restart the app. Or paste an OpenAI key |
| `ThrottlingException` / `429` | The whole class is calling at once. The app retries by itself: wait a few seconds |
| `AccessDeniedException` | The model is not enabled for your user: tell the trainer |
| Mini eval says "Load the AskIT KB first" | Click **Load AskIT KB** in the sidebar |
| Answers look odd after changing chunk size | You forgot to click **Load AskIT KB** again |
| `askit_data/kb not found` | You started the app outside your cloned repo. Use `C:\AskIT\dxc-agentic-ai\Day03\Labs\lab02-askit-rag-app` |
