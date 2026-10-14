# Lab 9: AskIT MCP Control Room

**Session 9 · MCP: one tool server, many agents, any home** · about 90 minutes in 3 parts · **no code to write**

| What we do | Why | Outcome | How |
|---|---|---|---|
| Connect an agent to a tool server over MCP. Read the real messages. Change the tool descriptions and watch the agent choose differently. Add controls (log, mask, role). Then move the SAME server to AWS Lambda, which you create yourself. | Clients ask "why MCP, not just functions?", "who controls the tools?" and "where does it run?". This lab gives you the answers and the numbers. | You can explain what MCP does, show the messages, run one server on a VM and on AWS, and defend a design decision (ADR). | One command opens an app. Then buttons, plus 8 clicks in the AWS console. |

---

## STEP 0. Open the right folder (do this first)

**We are doing Lab 9 · AskIT MCP Control Room now (`lab09-askit-mcp-control-room`).**

1. Open **VS Code**.
2. Click **File** → **Open Folder**.
3. Paste this path and click **Select Folder**:

```
C:\AskIT\dxc-agentic-ai\Day09\Labs\lab09-askit-mcp-control-room
```

4. Click **Terminal** → **New Terminal**. The prompt must end with **lab09-askit-mcp-control-room**.

Folder not there? In File Explorer open `C:\AskIT\dxc-agentic-ai` and double-click **SYNC.bat**. Then repeat step 2.

## STEP 1. Start the app

Is the Lab 8 app still running? Click in its terminal and press **Ctrl+C** first.

In the VS Code terminal, type this line and press Enter:

```
python run.py
```

The first time it installs packages (a few minutes). The browser opens the app. If it does not, open:

```
http://localhost:8501
```

Keep the terminal open. In the sidebar leave **1 · Model** on **AWS Bedrock** (or **Offline stand-in** if Bedrock shows a problem) and **2 · Where do the tools live?** on **1 · This VM · stdio**.

---

## The big picture (read once, 2 minutes)

```
Agent (LangChain)  ->  MCP client  ->  [stdio | HTTP | HTTPS]  ->  MCP server  ->  the 4 AskIT tools
```

1. **The agent** decides which tool to use, from the tool **names and descriptions**.
2. **The MCP client** asks the server "who are you?" (`server/discover`), "what tools?" (`tools/list`) and then calls tools (`tools/call`). These are JSON messages.
3. **The MCP server** owns the tools. Many agents can share one server.
4. **The home** is where the server runs: a child process on this VM (stdio), a web service on this VM (HTTP), or AWS Lambda (HTTPS). The agent code does not change.

---

## Part A · Tabs 1, 2, 3 (35 min)

**Tab 1 · Meet the server**
1. Press **🔌 Connect and ask: what can you do?** Read the server card and the tools table.
2. Pick tool `get_ticket`, keep `TKT-0001`, press **📞 Call the tool**.
3. Open **🔬 What went over the wire**. These are the real messages in both directions. Find `tools/call` and the answer.
4. Press the raw buttons. They talk to the server with **no MCP library at all**: MCP is only JSON over a pipe or HTTP.

**Tab 2 · Agent on MCP**
1. Pick a question and press **▶ Ask AskIT**. Read the steps: which tool, what arguments, what came back.
2. Press **🔁 Same question on every home**. Compare milliseconds. The answers are the same.

**Tab 3 · Tool descriptions**
1. Choose a description set (good, vague, misleading, too long). Press **▶ Test the 6 questions**.
2. Read the score chart: the agent never sees your code, only the descriptions. Bad words, wrong tool.

## Part B · Tab 4 · Controls (25 min)

1. Set the agent role to **read-only**. Press scenario **B · Reset password EMP-1021**. Read what the pipeline blocked.
2. Switch **VIP block** on. Press scenario **C** (EMP-1001 is a VIP).
3. Switch **Redact** on. Press **B**: the employee's name in the answer is masked. Then switch **strict** on and press **A**: the employee id is masked too. Safer, but the agent may lose the id it needs.
4. Switch **Server asks me to confirm a reset** on. Press **B** and answer Yes, then No.
5. Press **🧪 Agent challenge** and read the full pipeline trace.

## Part C · Tab 5 · Move to AWS (45 min)

The zip holds only the **code**. The data (KB articles, tickets, users) lives in **S3** and the function reads it from there. Follow the steps on screen, in the AWS console, with **your own user name** (for example `user101`).

1. Console sign-in as your user. Region **us-east-1 (N. Virginia)**.
2. **S3**: open bucket `devproacademy-askit-data-868859238853` → **Create folder** `user101` (your name) → open it → **Upload → Add folder** → `C:\AskIT\dxc-agentic-ai\askit_data` → **Upload**. Check `askit_data/` has `tickets.csv`, `users.csv`, `kb/`.
3. **Lambda → Create function → Event function → Author from scratch**. Name `userNNN-askit-mcp`. Runtime **Python 3.13** (the default may say Node.js, change it).
4. **Additional settings → Custom execution role** on → **askit-lambda-role**. Create function.
5. **Code → Upload from → .zip file** (not the S3 location option): `aws\askit-mcp-lambda.zip`. **Save**.
6. **Configuration → Environment variables**: `ASKIT_KEY` = your user name; `ASKIT_BUCKET` = `devproacademy-askit-data-868859238853`; `ASKIT_PREFIX` = `user101/askit_data/` (with the slash at the end).
7. **Configuration → General configuration → Edit**: **Timeout 30 sec**, **Memory 256 MB**. Save.
8. **Configuration → Function URL → Create** with auth **NONE**. Copy the URL.
9. Paste URL and key in tab 5, press **💾 Save**, then **✅ Test my Lambda**. Press **⏱️ Call it 3 times**: the first call is slower (cold start plus the first read from S3). Then **➡️ Use Lambda as my tool home** and repeat tab 2.
10. In AWS open **Monitor → View CloudWatch logs**: the same messages, in the cloud.

**⚡ Fast movers (optional):** open `askit_data\kb\KB-004_vpn_connect.md` on your PC, change a line, save. In S3 upload it again into `user101/askit_data/kb/` (same name). Wait 10 seconds, ask the VPN question again in tab 2 or press **Test my Lambda**. Your change shows up and you never touched the function: data and code are separate.

## Incident · Tab 6 (15 min)

1. Slow server: set **Server is slow by** 6 s, **Client waits at most** 3 s. Press **▶ Call get_ticket**. It fails.
2. Mission: find settings so the call finishes within 8 s while the server **fails the first 2 calls**.
3. For Lambda: set the function's `ASKIT_DELAY` environment variable and **Configuration → General → Timeout**.

## Team task · Tab 9 · ADR-AskIT-02 (20 min + 2-min pitch)

1. Pick your team and read your **curveball**.
2. Make the 3 choices, write **Why**, the **rejected alternative** and your **curveball answer**.
3. Press **📝 Create our design decision (ADR)**. It writes `C:\AskIT\dxc-agentic-ai\teams\<team>\ADR-AskIT-02.md`. Run **SYNC.bat**.

## Tabs 7 and 8 (5 min)

Tab 7 explains how it works (diagram, code map, product choices, client Q&A). Tab 8: answer the questions and press **💾 Save my answers** (`submission\lab09_answers.md`).

## At the end of the day: clean up

In Lambda select your function → **Actions → Delete**. A public URL must not stay open.

---

## Which file does what

| File | What it does |
|---|---|
| `run.py` / `run.bat` | Installs packages (first time only) and starts the app |
| `app.py` | The screen with 9 tabs |
| `askit_server.py` | The MCP server (FastMCP). Used by homes 1 and 2 |
| `mcp_client.py` | The MCP client, the controls pipeline, timing and the raw JSON calls |
| `model_factory.py` | Picks the model: Bedrock, Azure, OpenAI or Offline |
| `diagram.py` | Draws the live pictures |
| `design_decision.py` | Tab 9: curveballs, rubric, ADR writer |
| `Lab09_Participant_Code_Walkthrough.docx` | Read on your own (15 min): what the code does behind each button, with the key line numbers |
| `aws\askit-mcp-lambda.zip` | The Lambda package you upload: code only (same tools, pure Python). The data is in S3 |
| `..\..\..\askit_core\tools.py` | The 4 helpdesk tools |

## If something goes wrong

| What you see | What to do |
|---|---|
| `can't open file ... run.py` | Wrong folder. Repeat STEP 0 |
| "Port 8501 is already in use" | Another lab app is running. Ctrl+C in its terminal |
| Home 2 says the port is busy | Sidebar → 🔧 Local web server → **Stop it** |
| Lambda test says 401 | The key in tab 5 must equal `ASKIT_KEY` in Lambda, exactly |
| Lambda test says 403 | Function URL auth must be **NONE**; tell the trainer |
| Lambda test says 502 | Open CloudWatch logs. A `Status: timeout` line means step 7 (Timeout 30 sec) was missed; otherwise a wrong zip or runtime |
| Tool says `ASKIT_BUCKET is not set` | Add the environment variables in step 6 |
| Tool says `AccessDenied` or `NoSuchKey` / no data | `ASKIT_PREFIX` must be exactly `<your user name>/askit_data/`; check the files are in S3 under that folder |
| Lambda test says 404 | The URL is wrong. Copy it again from Function URL |
| Sidebar says Bedrock is not ready | Pick **Offline stand-in** |

## What you learned

- MCP = a standard way for agents to find and call tools. One server, many agents.
- The agent chooses tools from **descriptions**: they are part of your design.
- Controls (log, mask, role/VIP, timeout/retry) belong **around** the tools, not in every agent.
- The same server runs on a VM or on AWS; only the home and the identity change.
- Write the decision down: an ADR.
