# Lab 10: AskIT Ops Control Room

**Session 10 · Observability, cost and evaluation: can you see it, afford it, prove it?** · about 2 hours in 4 parts · **no code to write**

| What we do | Why | Outcome | How |
|---|---|---|---|
| Record every step of the AskIT agent as a **trace**, find four hidden failures in recorded traces, measure **cost per ticket**, run an **exam** (evals) on 14 questions, and find your own model calls in **AWS CloudWatch**. | Clients ask "how do we know it works?", "what will it cost?" and "who can see what it did?". An agent that does not crash can still be wrong, slow or expensive. | You can read a trace, name the root cause of a failure, quote a cost per ticket, run a pass/fail exam before a release, and show the same call in your own tracer, Langfuse and AWS. You also run the exam as a **LangSmith experiment** and compare two prompt versions side by side. | One command opens an app. Then buttons, and 6 clicks in the AWS console. |

---

## STEP 0. Open the right folder (do this first)

**We are doing Lab 10 · AskIT Ops Control Room now (`lab10-askit-ops-control-room`).**

1. Open **VS Code**.
2. Click **File** → **Open Folder**.
3. Paste this path and click **Select Folder**:

```
C:\AskIT\dxc-agentic-ai\Day10\Labs\lab10-askit-ops-control-room
```

4. Click **Terminal** → **New Terminal**. The prompt must end with **lab10-askit-ops-control-room**.

Folder not there? In File Explorer open `C:\AskIT\dxc-agentic-ai` and double-click **SYNC.bat**. Then repeat step 2.

## STEP 1. Start the app

Is the Lab 9 app still running? Click in its terminal and press **Ctrl+C** first.

In the VS Code terminal, type this line and press Enter:

```
python run.py
```

The first time it installs packages (a few minutes). The browser opens the app. If it does not, open:

```
http://localhost:8501
```

Keep the terminal open. In the sidebar (left) leave **1 · Model** on **AWS Bedrock** (or **Offline stand-in** if Bedrock shows a problem).

## STEP 2. Connect Langfuse (2 minutes, optional but recommended)

**Langfuse** is an open-source website where traces are stored and searched. Your trainer gives your team **two keys**: a **public key** (starts `pk-lf-`) and a **secret key** (starts `sk-lf-`). Do not put them in GitHub.

1. In the app sidebar open **2 · Langfuse (your team)** → **Enter the team keys**.
2. Paste both keys into the box, one per line. Choose the **region** of your project in the list below it (EU or US). Click **Save the keys**.
3. Click **Test the connection**. You should see "Connected to Langfuse".
4. Run a question in tab 1 **again**. Only runs you do after connecting are sent. Then click **Open this trace in Langfuse**.

**CloudWatch vs Langfuse (remember this):** CloudWatch sees the **model calls only**. Langfuse sees the **whole agent run** (model calls, tool calls, order, answer).

The test fails? Skip this. Everything in the lab still works; you only miss the Langfuse view in tab 1.

---

## The big picture (read once, 2 minutes)

```
Question -> AskIT agent -> model call -> tool call -> model call -> answer
                 |             every step is recorded as a SPAN by the tracer
                 +--> 1. this app (submission/traces.jsonl)
                 +--> 2. Langfuse (your team's project)
                 +--> 3. AWS CloudWatch (Bedrock logs each model call by itself)
```

- A **trace** is one run of the agent. A **span** is one step inside it: a model call or a tool call. Each span has start time, duration, input, output, tokens and cost.
- **Tokens** are the pieces of text a model reads and writes. You pay per token, for every model call.
- An **eval** is an exam for the agent: fixed questions, each checked PASS or FAIL for a named risk.

---

## Which mode for which tab?

Tabs 1–4 first in **Offline stand-in** (fast, free, same for everyone: you learn the mechanics). Then choose **AWS Bedrock** in the sidebar and repeat tabs 1, 3 and 4 (real tokens, real cost, a real model that may behave differently). Tab 5 needs Bedrock. Tabs 6–8 work in any mode. The same table is at the top of the app. At the bottom of every tab answer the **two thinking questions**: they unlock a lesson, and all lessons are collected in the last tab **🎓 Lessons learnt**.

## Part A · Tabs 1 and 2 (40 min)

**Tab 1 · Run and trace**
1. Choose the question *My VPN shows error 809 - what should I try?* and click **▶ Run AskIT**.
2. Read the **waterfall**: each bar is one step. Purple is a model call, orange is a tool call. A wide bar is a slow step.
3. Under **Failure switches**, tick **🔁 Ticket system stuck**. Change the question to *Summarise ticket TKT-0004 and tell me the next step.* Click **▶ Run AskIT** again. What do you see in the waterfall? What happened to the status line?
4. Untick it. Tick **🐘 Huge search results**, choose the VPN question, run again. Which number changed most?
5. Look at **Compare your runs** at the bottom: your runs side by side.
6. If Langfuse is connected, click **Open this trace in Langfuse**. Find the same steps there.

**Tab 2 · Find the failure**
Four failures were recorded in production. For each: read the complaint, look at the waterfall, pick the root cause, click **Check my answer**, read the fix. About 4 minutes each. Which one had no error at all?

## Part B · Tab 3 (25 min)

1. Click **▶ Run the batch** (10 tickets). Read **cost per ticket**, **p50** (typical run time) and **p95** (the slowest 5% of runs).
2. Tick **📚 Padded instructions** and run the batch again. How many times more does a ticket cost?
3. Part C of the tab: type your monthly volume, move the **cache** slider to 60% and the **shorter prompts** slider to 30%. Which model fits a US$50 budget? Which one would you NOT recommend even if it fits, and why?
4. Click **💾 Save this table** (your evidence for GitHub).

## Part C · Tabs 4 and 5 (30 min)

**Tab 4 · Evals**
1. Prompt **v1**, click **▶ Run the exam**. Look for ❌. Which risk category fails most? Open **Look at the failing cases**.
2. Prompt **v2** (adds a VIP rule), run again. Which category changed?
3. Prompt **v3** (adds a not-found rule), run again. Read **Compare all exams you ran**. Did anything get worse?
4. Click **Check the search on 10 knowledge-base questions**: is the search or the model the problem?
5. Stretch: open **Add a test question of your own**, add one, run again.

**Tab 5 · See it in AWS** (needs **AWS Bedrock** in the sidebar, not Offline)
1. In the sidebar choose **AWS Bedrock**. In tab 1 run **Summarise ticket TKT-0004** once and write down *Tokens in*. Wait 1–2 minutes.
2. Open the AWS console (region **N. Virginia**, top right) → **CloudWatch** → **Logs** → **Log Analytics** (the Logs Insights query box). Choose the log group named in the tab. Paste the query from the tab (it already contains your user name). **Run query**.
3. Find your calls: **one row per model call**, so 2 rows for that question. Do the two `tokens_in` add up to tab 1?
4. Open **CloudWatch → GenAI Observability → Model invocations** to see the team view.
5. Open your Day 9 Lambda → **Monitor** → **View CloudWatch Logs**.

## Part D · LangSmith: the same exam as an experiment (25 min)

| What we do | Why | Outcome | How |
|---|---|---|---|
| Upload our 14 questions to your own free **LangSmith** account, run the exam for prompt **v1** and prompt **v3**, and compare the two experiments in the browser. | Real teams keep the exam (a *dataset*) in a tool, run it on every change (an *experiment*), and look at the two runs side by side before they release. | You can show which risks v3 fixed, spot any question that got worse (a *regression*), and open the trace of one failing answer. | Two commands, then about 5 clicks in LangSmith. |

You will use a **second terminal**. The app keeps running in the first one.

1. **Before this part** (during the break): sign up free at `https://smith.langchain.com`. Can the page not open? Tell the trainer; the trainer will show it on screen.
2. In VS Code: **Terminal → New Terminal**. The prompt must end with **lab10-askit-ops-control-room**.
3. Connect your account (2 minutes). Type, press Enter, then follow the 4 steps it prints:

```
python langsmith_setup.py
```

Paste your API key when asked (nothing shows while you paste: that is normal). You should see **OK Connected to LangSmith.**
The script tries all 4 LangSmith regions (US, EU, Asia-Pacific, AWS-US) and remembers the right one. You do not have to know your region.

4. Run the experiments (about 3 minutes). It prints a result table at the end:

```
python langsmith_lab.py
```

Short of time? `python langsmith_lab.py --quick` runs only 5 questions. (Those 5 all pass, so v1 and v3 look the same. The differences are in the full run.)

5. In the browser (`https://smith.langchain.com`):
   - Left menu **Datasets & Experiments** → **askit-ops-14** → **Experiments** tab.
   - Tick the **v1** and the **v3** experiment → **Compare**.
   - Look for cells with **0** (a FAIL). Which risk columns changed from v1 to v3? Is it the same table as tab 4?
   - Click one cell with 0 → open its **trace**. Find the model call and the tool call. What went wrong?
6. Answer in your notes: *Did any question get worse from v1 to v3?* Take a screenshot of the Compare screen and save it in the `submission` folder.
7. Stretch: `python langsmith_lab.py --prompts v2`, then compare all three.

**What leaves your computer?** Only the made-up Orbit Corp questions, the answers and the traces go to LangSmith (a company's cloud service). With real company data you would first mask personal data and ask your security team. That is the CISO curveball in the team task.

| | Tab 4 (this app) | LangSmith experiment |
|---|---|---|
| The 5 checks | Yes | **The same code**, same numbers |
| Stored for the whole team | No, your laptop | Yes |
| Compare two runs side by side | A small table | Full screen, click through to the trace |
| Run in a CI pipeline before release | Not easily | Yes, the same command |

## Team task · Tab 8 (Board 5: Ops and FinOps Review)

Follow the 7 steps on the tab, top to bottom (1 team · 2 your numbers · 3 five choices · 4 why and what you rejected · 5 reveal the curveball · 6 create the ADR · 7 pitch for 90 seconds). Click **📝 Create our design decision (ADR)**. The ADR is saved in `teams\<your team>\ADR-AskIT-05.md` with your lab numbers inside. Run **SYNC.bat** afterwards.

---

## What is saved for GitHub (folder `submission`)

| File | What |
|---|---|
| `traces.jsonl` | Every run you made (one line each) |
| `eval_runs.json` | Every exam you ran |
| Compare screenshot | From Part D (LangSmith), if you took one |
| `cost_report.csv` | Your cost table (if you clicked Save) |

Then double-click **SYNC.bat** in `C:\AskIT\dxc-agentic-ai`.

## If something goes wrong

| What you see | What to do |
|---|---|
| "python is not recognized" | Close VS Code, open it again, open the folder again, new terminal. |
| The install did not work | Check your VPN or internet, run `python run.py` again. Still stuck: tell the trainer "install failed". |
| Bedrock shows a problem in the sidebar | Choose **Offline stand-in**. The whole lab works; only tab 5 needs real Bedrock. |
| Port 8501 busy | Another lab app is running. Press Ctrl+C in its terminal, then run again. |
| Langfuse test fails | Skip it. Tell the trainer. The lab works without it. |
| Tab 5 query shows no rows | Wait one minute, run a question in tab 1 with **AWS Bedrock** (not Offline), query again. |
| Tab 5 "could not read the logs" | Use the console steps. Same query. |
| `No LangSmith key found` | Run `python langsmith_setup.py` first. |
| LangSmith "did not accept the key" | Copy the whole key again (starts with `lsv2_`). The script already tries all 4 regions. Still failing: make a new key. |
| Cannot reach smith.langchain.com | Skip Part D and watch the trainer's screen. Tell the trainer. |
| Part D is slow | `python langsmith_lab.py --quick` |

## Files in this folder (you never edit them)

| File | What it does |
|---|---|
| `app.py` | The screen: tabs and buttons |
| `ops_agent.py` | The AskIT agent, with every step traced; the failure switches |
| `ops_trace.py` | The recorder: spans, saving, sending to Langfuse |
| `evals.py` | The 14 test questions and the PASS/FAIL checks |
| `mystery.py` | The four recorded failures |
| `prices.py` | Model prices (with the date they were checked) |
| `langsmith_setup.py` | Part D: saves your LangSmith key and tests it |
| `langsmith_lab.py` | Part D: runs the 14-question exam as LangSmith experiments |
| `model_factory.py` | Gives the app a model: Bedrock, Azure, OpenAI or the Offline stand-in |
| `diagram.py` · `design_decision.py` | Pictures · your team ADR |
| `run.py` · `run.bat` | Start the lab (`python run.py`, or double-click `run.bat`) |

Prices are approximate and were checked on 12 Oct 2026. Always check the vendor's price page before you quote a client.
