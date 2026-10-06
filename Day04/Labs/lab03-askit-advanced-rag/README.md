# Lab 3 — Advanced RAG: make AskIT trustworthy

**AskIT today:** it already answers from the KB. But it can quote an **old** article, mix up **employees and contractors**, and obey text **hidden inside a document**. Today you measure each problem, switch on the fix, and prove the lift with numbers.

| Part | Where | Time | You do |
|---|---|---|---|
| **A** | App → 💬 Ask | 15 min | Compare the baseline with the full pipeline, switch audience |
| **B** | App → 📊 Evals + `rag\evals.py` | 30 min | Challenge 1 (your questions), Challenge 2 (eval evidence) |
| **C** | App → 🧩 Ingestion + `submission\lab03_report.md` | 15 min | Challenge 3 (the poisoned article) |

## Set up (once, ~5 min)
```
cd /d C:\AskIT\dxc-agentic-ai
python -m pip install -r Day04\Labs\lab03-askit-advanced-rag\requirements.txt
cd Day04\Labs\lab03-askit-advanced-rag
python check_setup.py
python -m streamlit run app.py
```
(There is no virtual environment to activate. The `pip install` line installs everything this lab needs, including `pytest`.)
The app opens at http://localhost:8501. **AWS Bedrock is the default**: it uses the same `.env` as the earlier labs (AWS keys + `BEDROCK_SMALL_MODEL_ID`). Nothing to configure.
*Bedrock not working?* In the sidebar choose **OpenAI (backup)** and paste the key the trainer shares. *No keys at all?* **Offline** mode runs with stand-in models: good for exploring, but the numbers will differ.

## The knowledge base (`data\kb\`, 23 articles)
The 20 AskIT articles, plus three on purpose:
- **KB-001** and **KB-004** each have an **old version** (status `superseded`). Old and new disagree.
- **KB-005** is for **contractors only**; **KB-021** is for **employees only**.

Every article has metadata (version, audience, status). The sidebar **Preset** switches features on one by one: metadata filter → section chunks + hybrid search → reranker + "I don't know" guard.

## Part A — Compare
1. 💬 Ask → keep **Compare with baseline** on. Ask: *What is the minimum password length?* Which article did each pipeline use?
2. Sidebar **Who is asking?** → ask *Can I use a personal laptop for VPN access?* as **Employee**, then as **Contractor**.
3. Ask *Which cafeteria serves vegan food on Fridays?* What does each pipeline do?

## Part B — Evals
| # | Do | Test |
|---|---|---|
| Challenge 1 | **TODO-1** in `rag\evals.py`: add 2 questions of your own to `MY_QUESTIONS` (find the answer in `data\kb\`) | `test_challenge_1` |
| Challenge 2 | 📊 Evals dashboard → run **all 4 presets** (Baseline, + Metadata filter, + Section chunks + hybrid, FDE-grade). Then fill section 1 of `submission\lab03_report.md` | `test_challenge_2` |
| ⭐ Stretch | Turn on **LLM-as-judge** and run FDE-grade again. Which questions score below 5, and why? | — |

Restart the app (stop it with Ctrl+C, run it again) after you edit `evals.py`.

## Part C — The poisoned article (security)
1. 🧩 Ingestion → **Load new files** → upload `sample_uploads\KB-022_new_hire_laptop_setup.md` → **Ingest files**. Ask *How long does new-hire laptop setup take?*
2. Upload `sample_uploads\KB-099_printer_update_POISONED.md`. Read the ⚠️ scan message.
3. 💬 Ask *Where did the floor 3 printers move to?* with **Compare with baseline** on.

| # | Do | Test |
|---|---|---|
| Challenge 3 | Fill section 2 of `submission\lab03_report.md`: did each pipeline follow the hidden instruction? What defence would you add? | `test_challenge_3` |
| ⭐ Stretch | In `rag\pipeline.py` delete **rule 6** from `GEN_PROMPT_GROUNDED`, ask again, then put it back. What changed? | — |

## Check yourself
`pytest Day04\Labs\lab03-askit-advanced-rag` → aim for **3 passed**.

## The other tabs
**💰 Usage & cost** shows what every question cost. The two **🔭 Day 5 preview** tabs (agent, RAG vs fine-tuning) are for tomorrow — look, don't do.

## Stuck?
| Symptom | Fix |
|---|---|
| `streamlit` not recognised, or `No module named ...` | Run the `python -m pip install -r ...` line again, and start the app with `python -m streamlit run app.py` |
| Red box "The keys were rejected" / `UnrecognizedClientException` | The AWS keys in the course `.env` are wrong or a session token is missing (key starts with `ASIA`: add `AWS_SESSION_TOKEN`). Fix `.env`, restart the app. Or pick **Offline** in the sidebar |
| Sidebar says Bedrock keys not found | The course `.env` is missing `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` or `BEDROCK_SMALL_MODEL_ID`. Restart the app after fixing it |
| `AccessDeniedException` on Bedrock | The model is not enabled for your user: tell the trainer. Switch to OpenAI (backup) meanwhile |
| `ThrottlingException` | The whole class is calling at once. Wait 30 seconds and retry (retries are automatic) |
| `API call failed: RateLimitError` | The whole class is calling at once — wait 30 s and click again |
| Test 1 fails | Each question needs `q`, `doc` (file name without `.md`), `key` (a phrase inside that article) and `expected` |
| Test 2 fails | Run all 4 presets once (the dashboard saves them to `evals\runs.json`) |
| Test 3 fails | Replace every `TODO` in section 2 of the report |
