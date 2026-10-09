# Lab 7: The agent remembers (and what it costs)

**Session 7 · Context, Compaction and Memory**

You will do three small parts. Each part has **one line to write**, a check, and one quick experiment. Total time: about 45 minutes.

- **7A** (about 15 min): watch the context grow, one bar per step. 1 line.
- **7B** (about 15 min): make the agent summarise old messages. 1 line.
- **7C** (about 15 min): save a note and recall it in a brand-new chat. 1 line.

Everything else in the files is already written for you.

---

## STEP 0. Open the right folder (do this first, every time)

**We are doing Lab 7 now (`lab07-askit-memory-context`).**

1. Open **VS Code**.
2. Click **File** → **Open Folder**.
3. Paste this path and click **Select Folder**:

```
C:\AskIT\dxc-agentic-ai\Day07\Labs\lab07-askit-memory-context
```

4. Open a terminal: click **Terminal** → **New Terminal**.
5. Look at the end of the prompt. It must end with **lab07-askit-memory-context**.

Wrong folder? Go back to step 2.

**Install once** (only if you did not do it for Lab 6 in this folder). Type this line and press Enter:

```
python -m pip install -r requirements.txt
```

---

## Lab 7A: watch the context grow (TODO-1)

**Why:** the model is sent the whole chat again at every step. The bigger the chat, the more it costs. The bar shows that.

**1. Find the line.** Open `agent7.py`. Find `def bar`. The line `return ""` has a comment that says `TODO-1`.

**2. Write the line.** Replace `return ""` with this line:

```
return "█" * max(1, tokens // tokens_per_block)
```

Save (**Ctrl+S**).

**3. Check it.**

```
python check.py 7a
```

**4. Run it.**

```
python run_7a.py
```

You will see one bar for each step. Each bar is bigger than the one before.

**Quick experiment (2 minutes):** in `agent7.py`, change `tokens_per_block=500` to `tokens_per_block=250`. Run `python run_7a.py` again. The bars get longer, but the numbers stay the same. Change it back to `500`.

**Stuck?** `Day07\Hints\lab07_hints.md`, section *Lab 7A*.

---

## Lab 7B: summarise the old messages (TODO-2)

**Why:** a long chat costs more and more. Compaction means the agent writes a short summary of the old part, and keeps only the newest messages word for word.

**1. Find the line.** In `agent7.py`, find `def compaction_middleware`. The line `return None` has a comment that says `TODO-2`.

**2. Write the line.** Replace `return None` with this line:

```
return SummarizationMiddleware(model=model, trigger=("tokens", COMPACT_AT_TOKENS), keep=("messages", KEEP_LAST_MESSAGES))
```

Save (**Ctrl+S**).

**3. Check it.**

```
python check.py 7b
```

**4. Run the comparison.**

```
python run_7b.py
```

The run goes through the same six questions twice: first without compaction, then with it. Compare the two totals and the bars. The bars drop when the summary happens.

**Quick experiment (2 minutes):** in `agent7.py`, change `COMPACT_AT_TOKENS = 1500` to `COMPACT_AT_TOKENS = 800`. Run `python run_7b.py` again. The summary happens earlier. Did the last answer change? Change it back to `1500` afterwards.

**Stuck?** `Day07\Hints\lab07_hints.md`, section *Lab 7B*.

---

## Lab 7C: a note that survives a new chat (TODO-3)

**Why:** a new chat starts empty. A note saved in a store is still there in the next chat.

**1. Find the line.** In `agent7.py`, find `def remember`. The line `return None` has a comment that says `TODO-3`.

**2. Write the line.** Replace `return None` with this line:

```
store.put(("memories", user_id), uuid.uuid4().hex, {"text": text})
```

Save (**Ctrl+S**).

**3. Check it.**

```
python check.py 7c
```

**4. Run it.**

```
python run_7c.py
```

Chat 1 saves the laptop model. Chat 2 is a new chat and asks which laptop you have. The answer should mention the Dell.

**Quick experiment (2 minutes):** change the note in `run_7c.py`, for example to "My laptop is a Lenovo T14". Run again. Does chat 2 answer with the new laptop?

**Stuck?** `Day07\Hints\lab07_hints.md`, section *Lab 7C*.

---

## When you are finished

1. Open `submission\lab07_notes.md` and answer the **three** questions. Replace each `<fill>` with your answer. Save (**Ctrl+S**).
2. Run everything once:

```
python check.py all
```

Green line at the end = Lab 7 done.

---

## If something goes wrong

| What you see | What to do |
|---|---|
| `No module named langgraph` or `langchain` | Run `python -m pip install -r requirements.txt` in the terminal |
| `python: can't open file` | You are in the wrong folder. Repeat STEP 0 |
| `RESULT: your code is fine. Only your notes are missing.` | Fill in the `<fill>` lines in `submission\lab07_notes.md`, save, and run the check again |
| A check is red | Read the message above `RESULT`. Then open the hint file |

---

## What you learned today

- The whole chat is sent to the model at every step, so long chats cost more.
- Compaction summarises the old part of a chat and keeps the newest messages word for word.
- A store keeps notes across chats. Use it for facts that must survive a new chat, not for everything.
