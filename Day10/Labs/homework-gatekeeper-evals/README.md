# Evening Mission: Write 5 pass/fail evals for your Gatekeeper (spec + Copilot)

**After office hours · 45 to 60 minutes · on your VM · you write a spec, Copilot writes the code**

| What we do | Why | Outcome | How |
|---|---|---|---|
| Write 5 small tests (evals) for your Gatekeeper MCP server from Day 9. Each test is a question with a clear PASS or FAIL. | Today you saw that "it seems fine" is not a test. Evals tell you when a change breaks something. | `evals_gatekeeper.py` that prints PASS or FAIL for 5 cases and a final score, plus 3 lines of notes. | One prompt to Copilot, one command to run. |

---

## STEP 0. Open the folder (2 minutes)

1. In File Explorer open `C:\AskIT\dxc-agentic-ai` and double-click **SYNC.bat**.
2. Open **VS Code**. Click **File > Open Folder**, paste this path and click **Select Folder**:

```
C:\AskIT\dxc-agentic-ai\Day10\Labs\homework-gatekeeper-evals
```

3. Open **Copilot Chat** (Ctrl + Shift + I), mode **Agent**.
4. Copy `gatekeeper_server.py` and `gatekeeper.py` from your Day 9 homework `submission` folder into this folder's `submission` folder. No server yet? Tell the trainer, you can use the sample.

## STEP 1. Think first (10 minutes)

Write 5 cases in `submission\my_cases.md`, one line each: the input, and what must be true for a PASS.
Cover these five risks, one case each:

1. A normal ticket goes to the right team.
2. A password reset always needs approval.
3. A VIP user is treated as VIP.
4. A strange or empty ticket does not crash the tool.
5. The same input gives the same answer twice.

## STEP 2. Build it with Copilot (15 minutes)

Send this to Copilot (one block):

```
Read submission/my_cases.md and submission/gatekeeper_server.py. Save the spec below as submission/SPEC.md, then implement submission/evals_gatekeeper.py strictly from it.
Do not change the server. If anything is unclear, ask me before coding.

# SPEC: Gatekeeper evals v1
- Import the functions from gatekeeper.py directly (no network).
- One function per case from my_cases.md. Each returns True (PASS) or False (FAIL) and never raises: wrap each in try/except and count an exception as FAIL.
- Print one line per case: PASS or FAIL, the case name, and the reason on FAIL.
- At the end print "score: X/5" and exit code 0 only if all pass.
- No model calls, no randomness.
```

## STEP 3. Run it (10 minutes)

In the VS Code terminal (prompt must end with **homework-gatekeeper-evals**):

```
python submission/evals_gatekeeper.py
```

All PASS? Now break something on purpose (for example make `needs_approval` return False for a password reset) and run again. One line must turn FAIL. If nothing fails, your test is too weak: fix the test.

## STEP 4. Think like an architect (10 minutes)

Write 3 lines in `submission\my_notes.md`:

1. Which of your 5 cases protects against the most expensive mistake, and why?
2. Which case could NOT be a plain pass/fail and would need a model judge?
3. Where would you run these evals automatically (before every change, nightly, both)?

## STEP 5. Save

Double-click **SYNC.bat** in `C:\AskIT\dxc-agentic-ai`.

## Stretch

Ask Copilot to add a 6th case from a real surprise you saw today (loop, long answer, wrong tool) and to print the cost of the run if it used a model.
