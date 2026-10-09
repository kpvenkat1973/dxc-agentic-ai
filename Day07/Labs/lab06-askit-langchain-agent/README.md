# Lab 6: Build the AskIT agent with LangChain (3 small parts)

**Session 6 · LangChain, Middleware and Streaming**

You will do three small parts. Each part has **one line to write** and two quick experiments. Total time: about 40 minutes.

- **6A** (about 10 min): build the agent. 1 line.
- **6B** (about 15 min): add a safety limit. 1 line.
- **6C** (about 15 min): watch the agent work, step by step. 1 line.

Everything else in the files is already written for you. You only need to read it, run it and change one value.

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

Wrong folder? Go back to step 2.

**Install once** (takes a few minutes). Type this line in the terminal and press Enter:

```
python -m pip install -r requirements.txt
```

---

## Lab 6A: build the agent (TODO-1)

**Why:** yesterday you wrote the agent loop yourself (about 100 lines). LangChain builds the same loop in one call.

**1. Look at the file.** Open `agent6.py` in VS Code. Find `def build_agent`. The line `return None` has a comment saying `TODO-1`.

**2. Write the line.** Replace `return None` with this line (the hint file has the same line):

```
return create_agent(model=model, tools=tools, system_prompt=SYSTEM_PROMPT, middleware=middleware or [])
```

Save the file (**Ctrl+S**).

**3. Check it.** Type this line in the terminal and press Enter:

```
python check.py 6a
```

Green = done for TODO-1. Red = read the message above `RESULT`, then look at the hint.

**4. Run the agent.** Type this line and press Enter:

```
python run_6a.py
```

You will see which tools the agent used, and the answer.

**Quick experiment (2 minutes):** in `agent6.py`, find `SYSTEM_PROMPT`. Change rule 5 from "2-3 short sentences" to "one short sentence". Run `python run_6a.py` again. What changed in the answer? Change the rule back afterwards.

**Stuck?** `Day06\Hints\lab06_hints.md`, section *Lab 6A*.

---

## Lab 6B: a safety limit (TODO-2)

**Why:** an agent can ask for tools again and again and run up the cost. A guard stops it after a fixed number of model calls. The guard code is already written. You write the one comparison it uses.

**1. Find the line.** In `agent6.py`, find `def over_budget`. The line `return False` has a comment saying `TODO-2`.

**2. Write the line.** Replace `return False` with this line:

```
return model_calls >= max_calls
```

Save (**Ctrl+S**).

**3. Check it.**

```
python check.py 6b
```

**4. See the guard work.** Type this and press Enter:

```
python run_6b.py
```

The question contains an email address and a phone number. Look at the line "The question as stored in the conversation". The personal data is replaced with `[EMAIL]` and `[PHONE]`.

**Quick experiment 1 (2 minutes):** in `agent6.py`, change `MAX_MODEL_CALLS = 6` to `MAX_MODEL_CALLS = 3`. Run `python check.py 6b` and the agent again. Does the agent still answer? Change it back to `6` afterwards.

**Quick experiment 2 (2 minutes):** type this and press Enter. It pretends the ticket database is down:

```
python run_6b.py --down
```

Read the answer. The agent should still answer, and say that a human will follow up.

**Stuck?** `Day06\Hints\lab06_hints.md`, section *Lab 6B*.

---

## Lab 6C: watch the agent think (TODO-3)

**Why:** a user waiting at the helpdesk should not stare at a blank screen. Streaming shows each step as it happens.

**1. Find the line.** In `agent6.py`, find `def describe_step`. Look for the `elif` line that is followed by `pass`, with a comment saying `TODO-3`.

**2. Write the line.** Replace the word `pass` with this line (keep the same indent):

```
lines.append(f"✅ answer: {text_of(m)}")
```

Save (**Ctrl+S**).

**3. Check it.**

```
python check.py 6c
```

**4. Watch it stream.** Type this and press Enter:

```
python run_6c.py
```

You will see the steps one by one: the tool request, the tool result, then the answer. The last line shows how long it took to get the first step.

**Quick experiment (2 minutes):** run `python run_6c.py "What is the status of ticket TKT-0004?"`. Which line came first? How long did the first line take compared with the total?

**Stretch (optional, when you are done):** write `stream_tokens` so the answer appears word by word. Hint and answer are in `lab06_hints.md`, section *Stretch C*. Check with `python check.py stretch`.

**Stuck?** `Day06\Hints\lab06_hints.md`, section *Lab 6C*.

---

## When you are finished

1. Open `submission\lab06_notes.md` and answer the **three** questions. Replace each `<fill>` with your answer. Save (**Ctrl+S**).
2. Run everything once:

```
python check.py all
```

Green line at the end = Lab 6 done.

---

## If something goes wrong

| What you see | What to do |
|---|---|
| `No module named langchain` | Run `python -m pip install -r requirements.txt` in the terminal |
| `python: can't open file` | You are in the wrong folder. Repeat STEP 0 |
| `RESULT: your code is fine. Only your notes are missing.` | Fill in the `<fill>` lines in `submission\lab06_notes.md`, save, and run the check again |
| A check is red | Read the message above `RESULT`. Then open the hint file |

---

## What you learned today

- LangChain builds the agent loop for you (`create_agent`, one call).
- Middleware runs small guards around the model and the tools (privacy, limits, errors).
- Streaming shows each step as it happens, so users are not left waiting.
