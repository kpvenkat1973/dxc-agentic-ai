# Evening Mission: Turn your Gatekeeper into an MCP tool (spec + Copilot)

**After office hours · 45 to 60 minutes · on your VM · you write a spec, Copilot writes the code**

| What we do | Why | Outcome | How |
|---|---|---|---|
| Expose your Day 8 `gatekeeper.py` as a small MCP server with 2 tools: `route_ticket` and `needs_approval`. | Today you used a ready-made MCP server. Tonight you BUILD one, so any agent can ask the Gatekeeper instead of copying its code. | A working `gatekeeper_server.py`, a test script that calls it over MCP, and 3 lines of notes. | One prompt to Copilot, one command to check. |

---

## STEP 0. Open the folder (2 minutes)

1. In File Explorer open `C:\AskIT\dxc-agentic-ai` and double-click **SYNC.bat**.
2. Open **VS Code**. Click **File > Open Folder**, paste this path and click **Select Folder**:

```
C:\AskIT\dxc-agentic-ai\Day09\Labs\homework-gatekeeper-mcp
```

3. Open **Copilot Chat** (Ctrl + Shift + I), mode **Agent**.
4. You need your Day 8 file `gatekeeper.py`. If you did not finish it, tell the trainer: you can use the sample.
5. Copy `gatekeeper.py` from `Day08\Labs\homework-askit-gatekeeper\submission` into this folder's `submission` folder.

## STEP 1. Build it with Copilot (15 minutes)

Send this to Copilot (one block):

```
Read submission/gatekeeper.py. Save the spec below as submission/SPEC.md, then implement submission/gatekeeper_server.py strictly from it.
Use the fastmcp library (version 4.1.0). Do not change gatekeeper.py. If anything is unclear, ask me before coding.

# SPEC: Gatekeeper MCP server v1
- Server name: "AskIT Gatekeeper".
- Tool 1: route_ticket(text) calls route() from gatekeeper.py and returns the team name.
- Tool 2: needs_approval(action, is_vip, hour) calls needs_approval() from gatekeeper.py and returns true or false.
  Match the real parameter names and types of the function in gatekeeper.py.
- Every tool has a clear one-sentence description a model can choose by.
- Runs over stdio by default; with the argument --http it runs on port 8778.
- Also write submission/test_gatekeeper_server.py: it starts the server, lists the tools, calls each tool with 3 examples, and prints PASS or FAIL per call.
```

## STEP 2. Check it (10 minutes)

In the VS Code terminal (prompt must end with **homework-gatekeeper-mcp**):

```
python -m pip install fastmcp==4.1.0
```

```
python submission/test_gatekeeper_server.py
```

Every line must say PASS. Not passing? Paste the error into Copilot and ask it to fix the code, not the test.

## STEP 3. Think like an architect (10 minutes)

Write 3 lines in `submission\my_notes.md`:

1. Why is it better to have the Gatekeeper as ONE server than to copy `gatekeeper.py` into every agent?
2. Which of today's controls (log, mask, role, timeout) would you put in front of it, and why?
3. Which home would you choose for it (VM stdio, VM HTTP, AWS Lambda), and why?

## STEP 4. Save

Double-click **SYNC.bat** in `C:\AskIT\dxc-agentic-ai`.

## Stretch

Ask Copilot to add a third tool `safe_to_remember(fact)`. Then ask: should a write-like tool like this ever be callable by a read-only agent?
