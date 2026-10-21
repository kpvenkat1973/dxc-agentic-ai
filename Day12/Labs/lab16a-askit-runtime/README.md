# Lab 16A: AskIT Runtime Room

**Session 12 · AskIT runs on AWS: AgentCore Runtime** · about 40 minutes · **no code to write**

| What we do | Why | Outcome | How |
|---|---|---|---|
| Talk to the AskIT agent that now **runs on AWS** inside **AgentCore Runtime**. Watch how **sessions** work: a private sandbox per session, a slow first call, a fresh start after quiet time. Then see the same run in the AWS console and work out what it costs. | Until now the agent ran on your VM, so only you could use it. A Runtime lets many people use one agent safely, and you pay for the work done. | You can explain a session and a cold start, find a run in the console, and give a client a first cost estimate. | One app, buttons, and a few console clicks. |

**Stuck with AWS?** Choose **Practice runtime** in the app. It behaves the same way and needs no AWS. You still learn everything.

---

## STEP 0. Open the right folder

**We are doing Lab 16A · AskIT Runtime Room now (`lab16a-askit-runtime`).**

1. **VS Code** → **File** → **Open Folder** → paste:

```
C:\AskIT\dxc-agentic-ai\Day12\Labs\lab16a-askit-runtime
```

2. **Terminal** → **New Terminal** (the prompt ends with **lab16a-askit-runtime**).
3. No folder? Double-click `C:\AskIT\dxc-agentic-ai\SYNC.bat` first.

## PART A. Watch the trainer deploy (5 minutes, no clicking for you)

The trainer puts the AskIT agent on AgentCore Runtime. You will see: the agent file, one deploy command, and the **Runtime ARN** that comes out. Write the ARN down or copy it from the chat. It looks like:

```
arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/askit_agent-xxxxxxxxxx
```

## PART B. Use it from the app

```
python run.py
```

The browser opens (`http://localhost:8501`).

| Tab | What you do |
|---|---|
| **1 · Connect** | Choose **Practice runtime** or **The trainer's Runtime on AWS**. For AWS paste the Runtime ARN. Your Gateway address from yesterday is filled in for you. Press **Say hello (ping)**. |
| **2 · Talk to it** | Ask a question. Read the session boxes: Session, Sandbox (boot id), Turn, Cold start. Also ask the two **knowledge questions** (VPN error, password length): the agent calls `search_kb` (RAG) and you see which article it found and how it matched (`mode`). |
| **3 · Sessions** | Press buttons 1, 2, 3 in order. Compare boot ids and times. |
| **4 · See it in AWS** | Follow the console steps. Find your own session and its trace. |
| **5 · How it works and cost** | Read the diagram and the table. Change the numbers in the cost box. |
| **Lessons learnt** | Unlocks after the two questions at the bottom of tabs 2 to 5. |

## Optional: give YOUR Gateway the knowledge tool (5 minutes, only if you finish early)

The trainer's Gateway already has the `search_kb` tool. To add it to your own Gateway: Console → Bedrock AgentCore → Gateways → your Gateway → target `askit-lambda` → **Edit** → replace the tool schema with the contents of `tool_schema.json` in this folder (it now has 4 tools) → Save. Then paste your Gateway address in tab 1 and ask the VPN question again.
In Lab 16B this tool will be **denied** until you add a permit rule for it (`policies\allow_search_kb.cedar`). That is default deny again.

## If something goes wrong

| Message | Fix |
|---|---|
| AccessDenied on Runtime | Your AWS user may not call the Runtime, or the region is wrong. Check **us-east-1**. Tell the trainer. |
| ResourceNotFound | The ARN is wrong. Copy it again. |
| "could not list tools" | Your Gateway address is empty or wrong. Clear the box to use the trainer's shared Gateway. |
| Knowledge answer shows `mode: keyword (embedding failed ...)` | The Lambda cannot reach Titan Embeddings. Tell the trainer. The answer is still found by word match. |
| Anything else | Switch to **Practice runtime** and carry on. |

The app never stores your AWS keys in the repo. Never put keys in GitHub, wikis or chat.

## Clean up

Nothing to delete for this lab. The trainer removes the Runtime after the session.
