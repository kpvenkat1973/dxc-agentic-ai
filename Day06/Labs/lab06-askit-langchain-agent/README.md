# Lab 6: Build the AskIT agent with LangChain

**Session 6 · LangChain, Middleware and Streaming**
Labs 6A, 6B and 6C. About 40 minutes each, all in this folder.

This README is your complete guide. The Day 6 session page shows the same steps, but you can finish everything from this file alone.

---

## STEP 0. Open the right folder (do this first, every time)

**We are doing Lab 6 now (`lab06-askit-langchain-agent`).**

1. Open **VS Code**.
2. Click **File** → **Open Folder**.
3. Paste this path and click **Select Folder**:

```
C:\AskIT\dxc-agentic-ai\Day06\Labs\lab06-askit-langchain-agent
```

4. Open a terminal: click **Terminal** → **New Terminal**.
5. Look at the end of the prompt. It must end with **lab06-askit-langchain-agent**.

Your prompt ends with `C:\Users\...` or something else? You opened the wrong folder. Go back to step 2.

**Install once** (it takes a few minutes, so do it first). Type this line in the terminal and press Enter:

```
python -m pip install -r requirements.txt
```

You should see packages being installed, or the words "already satisfied".

**Check that the AI model is connected.** Type this line and press Enter:

```
python run_6a.py
```

The first line it prints is `Model: ...`.

| It prints | What it means |
|---|---|
| `Model: bedrock (...)` | Good. AWS Bedrock is connected. This is what we use. |
| `Model: openai (...)` | Fine. The backup model is connected. |
| `Model: offline` | No keys found. The lab still runs, but the answers are simpler. Ask the trainer for the keys. |

(Until you finish TODO-1, 2 and 3 the run may print an error or an empty answer. That is normal.)

---

## The big idea (2 minutes)

Yesterday you wrote the agent loop yourself (about 100 lines). Today **LangChain gives you that loop ready made**, so you can spend your time on the interesting parts:

| Day 5 (by hand) | Day 6 (LangChain) |
|---|---|
| Your loop (`while` / `for`) | `create_agent(...)` |
| Your `run_tool` and the TOOLS dictionary | LangChain **tools** |
| Your `give_up` and `is_repeat` checks | **Middleware** (small guards) |
| Waiting for the final answer | **Streaming** (see every step as it happens) |

**Middleware** = small functions that LangChain calls at fixed moments: before every model call, or around every tool call. You write what the guard does. LangChain decides when it runs.

---

## What is in this folder

| File | What you do with it |
|---|---|
| `agent6.py` | **The only file you edit.** Eight places to write (TODO-1 to TODO-8). Everything else is already built. |
| `run_6a.py`, `run_6b.py`, `run_6c.py` | You **run** them, one per lab. |
| `check.py` | You **run** it to test your work (one line per lab, shown below). |
| `model_factory.py` | Talks to the AI model. **Do not edit.** |
| `submission\lab06_notes.md` | **You fill in your answers here** after each lab. |
| `tests\` | The tests that `check.py` runs. |
| `..\..\Hints\lab06_hints.md` | Hints and full answers to copy. Use it when you are stuck. |

**How to paste an answer from the Hints file:** in `agent6.py` press **Ctrl+F**, type the TODO name (for example `TODO-1`) and press Enter. Select the whole old function (from its `def` line down to its last `return` line), delete it, paste the answer block, press **Ctrl+S**.

---

## Lab 6A: Build the agent with LangChain (40 min)

**What we do:** Rebuild AskIT with LangChain in three small functions: wrap the tools, build the agent, ask a question.

**Why:** You see how much of yesterday's loop disappears, and you prove it is the same agent by comparing the tools it uses.

**Outcome:** A working LangChain agent on the small Bedrock Nova model, and a feel for which code you still own.

**Do this:**

1. **Read (5 min).** Open `agent6.py` and read the comment at the top.

2. **TODO-1 `make_tools` (5 min).** Press **Ctrl+F**, type `TODO-1`, press Enter. Wrap the four functions as tools and return them in a list. (Why: the model can only use functions that LangChain knows as tools.)

3. **TODO-2 `build_agent` (5 min).** Press **Ctrl+F**, type `TODO-2`. One call to `create_agent(...)`. (Why: this one call is the whole loop you wrote yesterday.)

4. **TODO-3 `ask` (10 min).** Press **Ctrl+F**, type `TODO-3`. Run the agent, then collect the answer and the names of the tools used. Press **Ctrl+S**.

5. **Run it.** Type each line and press Enter:

```
python run_6a.py
```

```
python run_6a.py "How do I fix VPN error 809?"
```

   The first line asks the airport laptop question. Read `Tools used, in order` and `ANSWER`.

6. **Compare with Day 5 (5 min).** Same question, same tools? Open yesterday's `agent.py` and count the lines of `run_agent`. Count the lines of your `build_agent` today.

7. **Notes and check (5 min).** Fill in the **Lab 6A** lines in `submission\lab06_notes.md`, save, then run:

```
python check.py 6a
```

   You should see **4 passed**. If you see `RESULT: your code is fine. Only your notes are missing.`, finish the notes.

**Optional stretch:** switch the model without touching `agent6.py`. Open `C:\AskIT\dxc-agentic-ai\.env` (File → Open File), add the lines `OPENAI_API_KEY=...` and `ASKIT_MODEL=openai`, save, and run the same question. Compare the tools used. Delete the two lines afterwards.

**Stuck in 6A?**

| Problem | What to do |
|---|---|
| `ImportError` for `langchain` | The install did not finish. Run the install line from Step 0 again. |
| `Model: offline` | The keys are missing. Ask the trainer. Offline is fine for the TODOs. |
| Throttling or rate limit error | Wait 30 seconds and run again. |
| Stuck on a TODO | Hints file, section for that TODO: read the **Hint** first, then the **Answer**. |

---

## Lab 6B: Three guards (middleware) (40 min)

**What we do:** Write the logic of three guards: hide emails and phone numbers, stop the agent at its call limit, and survive a crashing tool.

**Why:** Real agents fail in boring ways: personal data leaks to the model, the cost runs away, a database is down. Guards turn those into controlled outcomes.

**Outcome:** An agent that never shows personal data to the model, always stops, and answers politely when a tool is down.

**Do this:**

1. **See the crash first (2 min).** Type this and press Enter:

```
python run_6b.py --down "What is the status of ticket TKT-0004?"
```

   The ticket database is pretend-"down" and your agent crashes. This is what we fix.

2. **TODO-4 `redact_pii` (8 min).** Press **Ctrl+F**, type `TODO-4`. Two `re.sub` calls: replace emails with `[EMAIL]` and phone numbers with `[PHONE]`. (Why: the AI model should never see personal data.)

3. **TODO-5 `over_budget` (3 min).** Press **Ctrl+F**, type `TODO-5`. One comparison: has the agent used up its model calls? (Why: a limit stops runaway cost.)

4. **TODO-6 `tool_guard` (8 min).** Press **Ctrl+F**, type `TODO-6`. Try to run the tool. If it crashes, return a polite message instead. (Why: one broken tool must not break the whole agent.) The three guards are already connected in `GUARDS`. Press **Ctrl+S**.

5. **Run again (10 min).**

```
python run_6b.py
```

   The question holds an email and a phone number. Read what the model actually received.

```
python run_6b.py --down "What is the status of ticket TKT-0004?"
```

   You should now get a polite answer, not a crash.

6. **Notes and check (9 min).** Fill in the **Lab 6B** lines in `submission\lab06_notes.md`, save, then run:

```
python check.py 6b
```

   You should see **7 passed**.

**Optional stretch:** at the top of `agent6.py` change `MAX_MODEL_CALLS = 6` to `MAX_MODEL_CALLS = 3`, run the airport question from Lab 6A. Does the agent still finish? What does that tell you about choosing the limit? Change it back to `6`.

**Stuck in 6B?**

| Problem | What to do |
|---|---|
| `--down` still crashes | TODO-6 must put `handler(request)` inside `try:` and catch the error with `except Exception as e:`. |
| `IndentationError` | A pasted line moved. Keep the spaces on the left. Paste the whole function again. |
| 6A TODOs not done | Do Lab 6A first. |

---

## Lab 6C: Stream the agent's steps (30 min)

**What we do:** Turn each streamed update into a readable line (TODO-7), then print the lines as they arrive (TODO-8).

**Why:** People accept a 10 second wait when they can see progress. Streamed steps also help you find bugs.

**Outcome:** A live view of the agent: tool requested, tool result, answer. You measure how soon the first line appears.

**Do this:**

1. **TODO-7 `describe_step` (8 min).** Press **Ctrl+F**, type `TODO-7`. One update goes in, a list of text lines comes out. (Why: the raw update is hard to read.)

2. **TODO-8 `stream_answer` (7 min).** Press **Ctrl+F**, type `TODO-8`. Loop over `agent.stream(...)` and print each line at once. (Why: printing as it arrives is what makes it feel fast.) Press **Ctrl+S**.

3. **Run it (5 min).**

```
python run_6c.py
```

```
python run_6c.py "How do I fix VPN error 809?"
```

   Watch the lines appear one by one. The run prints the total time.

4. **Notes and check (5 min).** Fill in the **Lab 6C** lines in `submission\lab06_notes.md`, save, then run:

```
python check.py 6c
```

   You should see **3 passed**.

**Optional stretch (STRETCH-C):** write `stream_tokens` (answer: Hints file) so the answer is typed word by word. Then run:

```
python run_6c.py --tokens
```

```
python check.py stretch
```

**Stuck in 6C?**

| Problem | What to do |
|---|---|
| Nothing prints | `describe_step` still returns an empty list. |
| Lines appear all at once at the end | Use `stream_mode="updates"` and `flush=True` when printing. |

---

## When you are finished

1. Run everything once:

```
python check.py all
```

2. Make sure every `<fill>` in `submission\lab06_notes.md` is replaced with your answer.
3. On the Day 6 session page click the **"I completed"** buttons, then **Day End**.

---

## If something goes wrong

| What you see | What to do |
|---|---|
| Prompt does not end with `lab06-askit-langchain-agent` | Wrong folder. Do **Step 0** again. |
| `No module named ...` or `ImportError` | Run `python -m pip install -r requirements.txt` again. |
| `Model: offline` | The keys are missing. Ask the trainer. |
| Throttling error | Wait 30 seconds and run again. |
| `RESULT: your code is fine. Only your notes are missing.` | Open `submission\lab06_notes.md`, replace every `<fill>`, save, run the check again. |
| A check fails | Read the message under FAILURES. It says what was expected. |
| Still stuck after 10 minutes | Open `Day06\Hints\lab06_hints.md`. It has the full answer. Then ask the trainer. |

---

## What you learned today

- **LangChain gives you the loop:** `create_agent` replaces about 100 lines of yesterday's code.
- **Middleware = guards:** hide personal data, cap the cost, survive a broken tool.
- **Streaming:** show each step as it happens, so the wait feels short.
