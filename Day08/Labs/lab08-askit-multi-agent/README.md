# Lab 8: AskIT Multi-Agent Control Room

**Session 8 · Multi-agent systems and human-in-the-loop** · about 45 minutes · **no code to write**

| What we do | Why | Outcome | How |
|---|---|---|---|
| Send helpdesk tickets to a team of agents (router + specialists). Approve or reject risky actions. Crash the run and resume it. Compare one agent with the team. | Clients ask "who controls the AI?" and "is multi-agent worth it?". This lab gives you the answer and the numbers. | You can explain the router pattern, why a human approves writes, how a checkpointer makes pauses and crashes safe, and the cost of a team. | One command opens an app. Then only buttons, plus one team decision record. |

---

## STEP 0. Open the right folder (do this first)

**We are doing Lab 8 · AskIT Multi-Agent Control Room now (`lab08-askit-multi-agent`).**

1. Open **VS Code**.
2. Click **File** → **Open Folder**.
3. Paste this path and click **Select Folder**:

```
C:\AskIT\dxc-agentic-ai\Day08\Labs\lab08-askit-multi-agent
```

4. Click **Terminal** → **New Terminal**. The prompt must end with **lab08-askit-multi-agent**.

Folder not there? In File Explorer open `C:\AskIT\dxc-agentic-ai` and double-click **SYNC.bat**. Then repeat step 2.

## STEP 1. Start the app

Is the Lab 7 app still running? Click in its terminal and press **Ctrl+C** first.

In the VS Code terminal, type this line and press Enter:

```
python run.py
```

The browser opens the app. If it does not, open this address yourself:

```
http://localhost:8501
```

Keep the terminal open while you work. Leave **1 · Model** in the sidebar on **AWS Bedrock** (or **Offline stand-in** if Bedrock shows a problem).

---

## How the graph works (read once, 2 minutes)

```
Ticket → Router → ONE of: Network / Access / Hardware / General agent → Policy → (Human approval → Act) → Respond
```

1. **Router**: one LLM call picks the team.
2. **Specialist**: a small agent with its own prompt and READ-only tools.
3. **Policy**: plain Python (no LLM) decides if a human must approve. A password reset always needs approval.
4. **Human approval**: the graph **pauses** (`interrupt()`). Nothing runs while it waits.
5. **Act**: the only step that changes data, and only after **Approve**.
6. **Respond**: builds the reply.
7. Under every step, the **checkpointer** saves the state, so the run can pause, crash and resume.

---

## Part 1 · Tab "1 · Route + approve" (20 min)

1. Click **🌐 VPN error 809**, then **▶ Send to AskIT**. In the picture, which specialist is green? Which are marked SKIP?
2. Click **🔐 Locked out, please reset**, then **▶ Send to AskIT**. The **Human approval** box turns amber: the graph is **paused**.
3. Read the yellow card: the action, the user, why a human is needed, the draft reply. Press **✅ Approve**. Read the final reply: the password reset was done.
4. Send the same ticket again. This time press **❌ Reject**. Read the reply now.
5. Try **💻 Laptop blue screen**, **📦 Need Python installed** and **🎣 Suspicious email**. Open **📋 Trace** each time: how many LLM calls, how many tokens?
6. Open **💾 Checkpoints saved**. Each row is a saved snapshot of the run.

## Part 2 · Tab "2 · Crash + resume" (5 min)

1. Press **💥 Run the VPN ticket with a crash**. A red error appears. In the picture: router and specialist are green, Policy is red.
2. Press **🔄 Resume from the last checkpoint**. The run finishes.
3. Look at the trace: the router and the specialist appear **once**. Their work (and tokens) was saved, not repeated.

## Part 3 · Tab "3 · One agent vs a team" (10 min)

1. Press **⚖️ Run 6 tickets: one agent vs the team**. Wait 1–2 minutes.
2. Read the four numbers: right team (one agent vs team), tokens, and **writes with NO human approval**.
3. In the table, find a ticket where the single agent reset a password on its own.

## Part 4 · The client curveball (when the trainer announces it)

1. In the sidebar switch **VIP users always go to a human** ON.
2. Tab 1: click **👑 VIP: CEO email not syncing**, then **▶ Send**. The graph now pauses for a human.
3. Only the **Policy** step changed. No prompt, no model, no retraining.

## Part 5 · Tab "6 · Team design decision" (team task, 10 min + 2-min pitch)

1. Your team meets in its breakout room. One person shares the screen with this app open.
2. Tab 3 must have been run once (⚖️ Run 6 tickets), so your numbers appear.
3. Tab 6: pick your team. Read your **curveball** (each team has a different one) and look at the evidence it points to.
4. Make the 3 choices, write **Why**, the **rejected alternative**, your **curveball answer**, and edit the approval table.
5. Press **📝 Create our design decision (ADR)**. The app writes `C:\AskIT\dxc-agentic-ai\teams\<your team>\ADR-AskIT-01.md`.
6. Run **SYNC.bat**. Pitch it to the board in 2 minutes. The board scores 5 criteria, 0-5 each (shown at the bottom of tab 6).

## Part 6 · Tabs "4 · How it works" and "5 · Questions + takeaway" (5 min)

1. Read tab 4: the code map, the 4 patterns and the frameworks table.
2. Tab 5: answer the 3 questions and press **💾 Save my answers** (`submission\lab08_answers.md`).
3. In File Explorer open `C:\AskIT\dxc-agentic-ai` and double-click **SYNC.bat**.

---

## Which file does what

| File | What it does |
|---|---|
| `run.py` | Installs the packages (first time only) and starts the app. `run.bat` does the same on double-click |
| `app.py` | The screen: tickets, picture, Approve/Reject, crash/resume, compare |
| `design_decision.py` | Tab 6: the team curveballs, the scoring rubric, and the ADR writer |
| `multi_agent.py` | The LangGraph graph: router, 4 specialists, policy, human approval, act, respond. Also the one-agent baseline |
| `model_factory.py` | Picks the model: Bedrock (main), Azure, OpenAI or Offline |
| `diagram.py` | Draws the live picture |
| `..\..\..\askit_core\tools.py` | The helpdesk tools (search_kb, get_ticket, reset_password ...) |

## If something goes wrong

| What you see | What to do |
|---|---|
| `can't open file ... run.py` | You are in the wrong folder. Repeat STEP 0 |
| "Port 8501 is already in use" | The Lab 7 app is still running. Press Ctrl+C in its terminal, then `python run.py` again |
| The browser shows nothing | Open `http://localhost:8501` yourself |
| Sidebar says Bedrock is not ready | Tell the trainer. Meanwhile pick **Offline stand-in** |
| "The run failed: ..." | Often throttling. Press **▶ Send** again |

## Stretch (optional, for those who like code)

1. Open `multi_agent.py`, find `def policy`. Add a rule: tickets that contain the word "admin" need approval too. Save. In the app click **Rerun** at the top right (or press R), then send "I need admin rights on my laptop".
2. Find `ROUTER_PROMPT`. Add a fifth team "Security" for phishing. What else would you need to add for it to work? (Hint: `ROUTES` and `SPECIALISTS`.)

## What you learned

- Go multi-agent only for a reason: confusion, ownership, parallel work or risk.
- The LLM may **route**. Plain-code **policy** decides what needs a human. **Writes** happen only after a YES.
- A **checkpointer** makes long waits and crashes safe: resume, don't repeat.
- A team usually costs a few more tokens than one agent; you buy clean routing and control with them.
