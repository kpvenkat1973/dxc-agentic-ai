# Lab 5: Build the AskIT agent, step by step

**Session 5 · Agents, Tools and Function Calling**
Labs 5A, 5B, 5C and the Incident. About 40 minutes each, all in this folder.

This README is your complete guide. The Day 5 session page shows the same steps, but you can finish everything from this file alone.

---

## STEP 0. Open the right folder (do this first, every time)

**We are doing Lab 5 now (`lab05-askit-agent-loop`).**

1. Open **VS Code**.
2. Click **File** → **Open Folder**.
3. Paste this path and click **Select Folder**:

```
C:\AskIT\dxc-agentic-ai\Day05\Labs\lab05-askit-agent-loop
```

4. Open a terminal: click **Terminal** → **New Terminal**.
5. Look at the end of the prompt. It must end with **lab05-askit-agent-loop**.

Your prompt ends with `C:\Users\...` or something else? You opened the wrong folder. Go back to step 2.

**Install once.** Type this line in the terminal and press Enter:

```
python -m pip install -r requirements.txt
```

You should see packages being installed, or the words "already satisfied".

**Check that the AI model is connected.** Type this line and press Enter:

```
python run_5a.py
```

The first line it prints is `Model: ...`. This is what it means:

| It prints | What it means |
|---|---|
| `Model: bedrock (...)` | Good. AWS Bedrock is connected. This is what we use. |
| `Model: openai (...)` | Fine. The backup model is connected. |
| `Model: offline` | No keys found. The lab still runs, but the answers are simpler. Ask the trainer for the keys. |

---

## The big idea (2 minutes)

An AI model **cannot run anything by itself**. It can only **ask** for something to be run.

```
You ask a question
  -> the model replies "please run the tool get_ticket with ticket_id = TKT-0004"    (a tool REQUEST)
  -> YOUR code runs the tool
  -> you send the tool's answer back to the model
  -> the model reads it and writes the final answer
```

An **agent** is this same round trip **repeated in a loop** until the model has what it needs.

**The story:** Orbit Corp's IT Helpdesk is drowning in tickets. You are building **AskIT**, an AI helpdesk agent that answers, acts and escalates.

**The 4 tools AskIT can use** (already built):

| Tool | What it does | Changes data? |
|---|---|---|
| `search_kb` | Searches the help articles (how-to answers) | No |
| `get_ticket` | Reads one ticket, e.g. TKT-0004 | No |
| `update_ticket` | Adds a note to a ticket | **Yes** |
| `reset_password` | Resets an employee's password | **Yes** |

---

## What is in this folder

| File | What you do with it |
|---|---|
| `agent.py` | **The only file you edit.** Two places to write (TODO-1, TODO-2), one word to change (Incident). Everything else is already built. |
| `run_5a.py` | You **run** it in Lab 5A. |
| `run_agent.py` | You **run** it in Labs 5B, 5C and the Incident. |
| `check.py` | You **run** it to test your work (one line per lab, shown below). |
| `provider.py` | Talks to the AI model. **Do not edit.** |
| `submission\lab05_notes.md` | **You fill in your answers here** after each lab. |
| `tests\` | The tests that `check.py` runs. |
| `..\..\Hints\lab05_hints.md` | Full answers to copy. Use it when you are stuck. |

**The only things you write today**

| Lab | What you do | Where |
|---|---|---|
| 5A | Nothing to write. Read, predict, run. | |
| 5B | **TODO-1**: write the agent loop | `agent.py`, function `run_agent` |
| 5C | **TODO-2**: say which tools need approval | `agent.py`, function `needs_approval` |
| Incident | Change `False` to `True` | `agent.py`, the line `STOP_ON_REPEAT` |

---

## Lab 5A: One tool call, by hand (40 min)

This is a basic agent: it makes **one** tool call, with **no loop** yet.

**What we do:** Ask the model one question. The model asks for a tool. Our code runs the tool and sends the answer back.

**Why:** The model cannot run anything. You will see this once with your own eyes, with nothing hidden. After this lab you know what every agent framework does inside.

**Outcome:** You can read a tool request, and you can explain who runs the tool (your code) and why the ids must match.

**Do this:**

1. **Read the 3 small functions (5 min).** In `agent.py` press **Ctrl+F**, type `LAB 5A` and press Enter. Read `get_tool_requests`, `run_tool` and `make_tool_result`. Each does one job. You do **not** edit them. (They are already built, so you can see how the pieces fit.)

2. **Run the default question (5 min).** Type this and press Enter:

```
python run_5a.py
```

   You should see 4 printed steps: (1) the question, (2) the tool the model asked for, (3) what the tool returned, (4) the final answer.

3. **Guess first, then run (15 min).** For each question below, **write your guess** in `submission\lab05_notes.md` (which tool will the model ask for?). Then run it and compare.

```
python run_5a.py "How do I fix VPN error 809?"
```

```
python run_5a.py "Hi"
```

```
python run_5a.py "Reset the password for EMP-1021"
```

   - The first one should ask for `search_kb`.
   - "Hi" should ask for **no tool** (the model just answers).
   - The last one asks for `reset_password`. **Look at step 3: our code ran it straight away and nobody was asked.** We fix this in Lab 5C.

4. **Fill in the notes (5 min).** Open `submission\lab05_notes.md`, replace every `<fill>` in the **Lab 5A** lines, and save (Ctrl+S).

5. **Run the check (5 min).** Type this and press Enter:

```
python check.py 5a
```

   You should see **4 passed**. If you see `RESULT: your code is fine. Only your notes are missing.`, finish step 4.

**Optional stretch (STRETCH-A):** add a 5th tool, `get_user`. In `agent.py` find `STRETCH-A`, write the body of `get_user` (answer: Hints file, Stretch A), remove the two `#` in front of the two lines below it, then run:

```
python run_5a.py "Who is EMP-1002?"
```

**Stuck in 5A?**

| Problem | What to do |
|---|---|
| `No module named ...` | Run the install line from Step 0 again. |
| `Model: offline` | The keys are missing. Ask the trainer. Offline is fine for this lab. |
| A throttling or rate limit error | Wait 30 seconds and run it again. |

---

## Lab 5B: The agent loop (40 min)

**What we do:** Finish the function `run_agent`. It asks the model, runs the tool the model asked for, gives the answer back, and repeats. You add the exits: the model has the answer, or we run out of steps and hand over to a human.

**Why:** In Lab 5A you did **one** round trip. Real questions need several (find the ticket, then search the help articles, then answer). This loop is what every agent framework does inside. Tomorrow LangChain does it for you. Today you build it.

**Outcome:** A working agent that answers questions using several tools, answers directly when no tool is needed, and stops safely when it cannot finish.

**Do this:**

1. **Go to TODO-1 (2 min).** In `agent.py` press **Ctrl+F**, type `TODO-1` and press Enter. You land inside the function `run_agent`. Read the comment: it lists PART A, PART B and PART C.

2. **Write TODO-1 (20 min).** Two ways, pick one:
   - **Write it yourself** by following the comment. (It shows every line.)
   - **Copy the answer.** Open `Day05\Hints\lab05_hints.md`, find **TODO-1**, copy the whole function. In `agent.py` select the old `run_agent` function (from the line `def run_agent(` down to the line `return result` at the end), delete it, and paste.

   Save (Ctrl+S).

3. **Run three questions (10 min).** Type each line and press Enter:

```
python run_agent.py "Priya left her laptop at the airport (ticket TKT-0046). What should she do and how fast will we respond?"
```

   This question needs **several tools**: watch each step print. At the end it prints the answer, the number of steps and the cost.

```
python run_agent.py "Hi"
```

   This needs **no tool**: it should finish in 1 step.

```
python run_agent.py "What is the status of TKT-9999?"
```

   This ticket does not exist: the tool returns an error, and the agent tells you in one sentence.

4. **Try one experiment (5 min).** At the top of `agent.py` change `MAX_STEPS = 6` to `MAX_STEPS = 2`, save, and run the airport question again. What happens? (The agent runs out of steps and hands over to a human. This is the safety stop.) Then change it back to `6` and save.

5. **Notes and check (5 min).** Fill in the **Lab 5B** lines in `submission\lab05_notes.md`, save, then run:

```
python check.py 5b
```

   You should see **4 passed**.

**Stuck on TODO-1? Use this ladder:**

1. Read the comment under `TODO-1` in `agent.py`. It lists the lines.
2. Check the example below.
3. Open `Day05\Hints\lab05_hints.md`, section **TODO-1**, and copy the full function.

**Example:** after one tool call, the conversation (`messages`) holds 3 things: your question, the model's tool request, and your tool answers. The model then reads all 3 and answers.

| Problem | What to do |
|---|---|
| The agent stops after the first step | The line `break` is still there. Delete it. |
| `IndentationError` | A pasted line moved. Every line inside the function must keep its spaces on the left. Paste the whole function again. |
| Lab 5B check fails | Read the message under FAILURES: it says what the check expected. |

---

## Lab 5C: Ask a human before the agent changes anything (40 min)

**What we do:** Add an approval step for the two tools that **change** data. Then read the raw conversation with the model and look at what one question costs.

**Why:** A helpful agent that can reset passwords is also a risk. The safety check lives **in your code**, between the model's request and the tool, where the model cannot skip it. A sentence in the prompt is not enough.

**Outcome:** An agent that pauses for a human before write tools, runs read tools freely, and you can say how many tokens and how much money one question costs.

**Do this:**

1. **Go to TODO-2 (2 min).** In `agent.py` press **Ctrl+F**, type `TODO-2` and press Enter. You land on the function `needs_approval`.

2. **Write TODO-2 (5 min).** It is one line. Replace `return False` with a line that returns `True` for `update_ticket` and `reset_password`, and `False` for everything else. (Answer: Hints file, section **TODO-2**.) Save (Ctrl+S).

   The function `run_tool_safely` right below is already built. It uses your `needs_approval` to decide whether to ask a human.

3. **Try a tool that changes data (10 min).** Type this and press Enter:

```
python run_agent.py "Reset the password for EMP-1021"
```

   It asks `Approve? [y/N]`. Type `y` and press **Enter**. Then run the same line again and type `n`. What did the agent say the second time?

4. **Try a tool that only reads.** It must **not** ask you anything:

```
python run_agent.py "What is the status of ticket TKT-0004?"
```

5. **Read the raw conversation (10 min).** Type this and press Enter:

```
python run_agent.py --raw "What is the status of ticket TKT-0004?"
```

   Scroll down to the part after `RAW CONVERSATION`. Find the `toolUse` block and the `toolResult` block. Check that their ids are the same.

6. **Notes and check (5 min).** Fill in the **Lab 5C** lines in `submission\lab05_notes.md` (the run prints the tokens and the cost), save, then run:

```
python check.py 5c
```

   You should see **3 passed**.

**Stuck on TODO-2? Use this ladder:**

1. Read the comment under `TODO-2`.
2. Check the example: `needs_approval("reset_password", ...)` must give `True`, and `needs_approval("get_ticket", ...)` must give `False`.
3. Open `Day05\Hints\lab05_hints.md`, section **TODO-2**.

| Problem | What to do |
|---|---|
| It never asks for approval | TODO-2 still says `return False`, or TODO-1 was not pasted completely. |
| Typing `y` does nothing | Press **Enter** after `y`. |

**Optional stretch (STRETCH-B):** rule KB-018 says that for a VIP, AskIT may gather information but must hand over to a human before any action. In `agent.py` find `STRETCH-B` and write `vip_block` (answer: Hints file, Stretch B). Then run:

```
python run_agent.py "Reset the password for EMP-1001"
```

You can also add `OPENAI_API_KEY=...` and `ASKIT_MODEL=openai` to `.env` and run the same question again: same code, different model.

---

## Incident of the day: "AskIT has been working on one ticket for five minutes" (10 min)

**Wait for the trainer to say GO.**

**The story:** The Orbit Corp CIO just messaged: "The bill is climbing and the user still has no answer. Find out why. Fix it."

**What we do:** Switch on a bug on purpose. Run the agent and watch it keep asking the same question. Find the reason. Switch on the fix.

**Why:** Agents fail in loops, quietly and expensively. A step limit stops the loop, but only after every step has been paid for.

**Outcome:** You can say in one sentence why the agent kept repeating, and the agent stops itself after 2 steps.

**Do this:**

1. **Switch the bug on.** In VS Code click **File** → **Open File**, paste this path and press Enter:

```
C:\AskIT\dxc-agentic-ai\.env
```

   Add a new line at the bottom:

```
ASKIT_INCIDENT=loop
```

   Save (Ctrl+S). Close this tab and go back to `agent.py`.

2. **Run this** and count the steps that print:

```
python run_agent.py "What is the status of ticket TKT-0004?"
```

   You should see the same `get_ticket` line again and again, then a hand over to a human after 6 steps.

   **The agent answered after 1 or 2 steps and did not repeat?** Your model was too clever. Add one more line to `.env` (the same file), save, and run again:

```
ASKIT_MODEL=offline
```

3. **Look at the lines printed above and answer in your notes** (the **Incident** lines of `submission\lab05_notes.md`): how many steps? What does the tool keep answering? Why does the agent keep asking again?

4. **Switch the fix on.** In `agent.py` press **Ctrl+F**, type `STOP_ON_REPEAT` and press Enter. Change `False` to `True`, so the line reads:

```
STOP_ON_REPEAT = True
```

   Save (Ctrl+S). (The agent now remembers every call it made. If it is about to make the exact same call again, it stops and hands over to a human.)

5. **Run the same question again.** It should stop after **2 steps**.

6. **Clean up.** Open `.env` again and delete the line `ASKIT_INCIDENT=loop` (and the line `ASKIT_MODEL=offline` if you added it). Save.

7. **Notes and check.** Fill in the rest of the **Incident** lines, save, then run:

```
python check.py incident
```

   You should see **3 passed**.

---

## When you are finished

1. Run everything once:

```
python check.py all
```

2. Make sure every `<fill>` in `submission\lab05_notes.md` is replaced with your answer.
3. On the Day 5 session page click the **"I completed"** buttons, then **Day End**.

---

## If something goes wrong

| What you see | What to do |
|---|---|
| Prompt does not end with `lab05-askit-agent-loop` | Wrong folder. Do **Step 0** again. |
| `No module named ...` | Run `python -m pip install -r requirements.txt` again. |
| `Model: offline` | The keys are missing. Ask the trainer. |
| Throttling error | Wait 30 seconds and run again. |
| `RESULT: your code is fine. Only your notes are missing.` | Open `submission\lab05_notes.md`, replace every `<fill>`, save, run the check again. |
| A check fails | Read the message under FAILURES. It says what was expected. |
| Still stuck after 10 minutes | Open `Day05\Hints\lab05_hints.md`. It has the full answer. Then ask the trainer. |

---

## What you learned today

- **The model asks, your code acts.** Tool request, tool result, matching ids.
- **A loop that always ends:** think, act, observe. It ends with an answer, a step limit, or a handover to a human.
- **Safety lives in code:** approval before write tools, and a stop when the agent repeats itself.

**Tomorrow (Day 6):** a framework, LangChain, builds this loop for you, so you can add the interesting parts: middleware and streaming.
