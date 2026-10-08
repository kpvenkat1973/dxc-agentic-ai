# Lab 4: Agentic RAG with a critic (AskIT)

**Time:** 55 minutes · **Folder:** `Day04\Labs\lab04-askit-agentic-rag` · **Needs:** Lab 3 working (this lab reuses its code and KB)

## The story
AskIT answers easy questions well. But Priya asks: *"I left my laptop at the airport. What will the helpdesk do with it, and how fast will they respond?"* The answer lives in **two** articles. One search finds only one. Your job: add a **critic** that notices what is missing and sends AskIT back to search again.

```
question → ROUTER → retrieve → rerank → CRITIC → not enough? → rewrite query → retrieve again
                                                   enough?     → answer → ANSWER CHECK → answer or human
```

## Setup (2 minutes)
```
cd C:\AskIT\dxc-agentic-ai
python -m pip install -r Day04\Labs\lab03-askit-advanced-rag\requirements.txt
cd Day04\Labs\lab04-askit-agentic-rag
python -m streamlit run app.py
```
(Lab 3 must be in the same `Day04\Labs` folder: this lab reuses its code and KB. No virtual environment to activate.)
It uses **AWS Bedrock** by default (the course `.env`, same as Lab 3). Sidebar: switch to **OpenAI (backup)** and paste a key if Bedrock fails. **Offline** runs with stand-ins.

## Step 1: See the problem (5 min)
Open **Ask**. Pick the first sample question and click **Ask**. The left side is single-pass (Lab 3). The right side is the agentic loop. With the starter code **both are identical**: the loop never runs. That is what you will fix.

## Step 2: Your 3 challenges (30 min), all in `agentic.py`
| # | Function | What you do |
|---|---|---|
| 1 | `parse_critic(text)` | Turn the critic's messy reply into `{"enough": bool, "missing": str}`. A broken reply must never start a loop. |
| 2 | `rewrite_query(...)` | Ask the LLM for a new search query for what is missing. Strip it, log the usage, fall back to the original question. |
| 3 | `should_continue(...)` | Go again only if the critic is not satisfied **and** rounds are left. |

Check yourself any time: `python -m pytest tests` (from this folder). Stuck? See `Day04\Hints\lab04_hints.md`.

## Step 3: Measure it (10 min)
Open **Compare** and click **Run both pipelines**. Then fill `submission\lab04_report.md`: the numbers, one traced loop, and your ship / don't-ship decision. Challenge 4 in `pytest` checks the report and the saved run.

## Step 4: Stretch (fast movers)
- Replace the rule in `route()` with an LLM call that returns `simple` or `complex`.
- Add HyDE: ask the LLM to write a short *fake answer*, then search with it.
- Set **Max retrieval rounds** to 1, 2, 3 in the sidebar. Where does extra effort stop paying off?

## Rules of the loop (already built, read them)
- Never more than `MAX_ROUNDS` rounds. Agents must have a stop.
- If a rewrite does not change the query, stop.
- The answer is checked against its sources. Not grounded → handed to a human.
