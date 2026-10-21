# Lab 15: AskIT Gateway

**Session 11 · One front door for tools: AgentCore Gateway** · about 50 minutes · **no code to write**

| What we do | Why | Outcome | How |
|---|---|---|---|
| Put a small AWS **Lambda** function (ticket tools) behind an **AgentCore Gateway**. The Gateway turns it into **MCP tools**. Then our agent finds the tools and calls them through the Gateway. | Companies have many tools and many agents. A Gateway gives one place for access, logging and rules instead of wiring every agent to every tool. | You can create a Gateway, see tool discovery and a tool call, and explain why a Gateway beats direct calls. | Console clicks (Part A) and one app (Part B). |

**The app has the same instructions in its first tab, 🏁 Start here.**

**Stuck in the console?** Part B works without AWS. Choose **Practice gateway** in the app and you still learn everything.

---

## STEP 0. Open the right folder

**We are doing Lab 15 · AskIT Gateway now (`lab15-askit-gateway`).**

1. **VS Code** → **File** → **Open Folder** → paste:

```
C:\AskIT\dxc-agentic-ai\Day11\Labs\lab15-askit-gateway
```

2. **Terminal** → **New Terminal** (prompt ends with **lab15-askit-gateway**).

## PART A. Create your Gateway (AWS console, region N. Virginia us-east-1)

Console names can differ slightly. Follow the idea, not the exact word.

1. Sign in with your **AWS user** from the trainer. Check top right says **N. Virginia**.
2. Search **Bedrock AgentCore** → left menu **Gateways** → **Create gateway**.
3. **Name:** `askit-gw-user1xx` (your user number). **Inbound auth:** choose **IAM**.
4. **Service role:** choose **Use an existing role** → `askit-gateway-role`.
5. Create it. Wait until status is **Ready**.
6. Open your Gateway → **Targets** → **Add target**.
   - **Target protocol:** MCP target (the default).
   - **Target name:** `askit-lambda` (replace the automatic name).
   - **Target type:** **Lambda ARN** (not "MCP server"). **ARN:** the trainer gives you the ARN of `askit-get-ticket`.
   - **Tool schema:** Inline. Paste the whole content of `tool_schema.json` (in this folder).
7. Save. Copy the **Gateway MCP URL** (ends with `/mcp`). Keep it for Part B.

## PART B. Use it from the app

```
python run.py
```

The browser opens (`http://localhost:8501`).

| Tab | What you do |
|---|---|
| **Connect** | Choose **Practice gateway** or **My AWS gateway**. Paste your MCP URL. Press **Connect**. |
| **Discover** | See the 3 tools the Gateway found. Note the names: `askit-lambda___get_ticket`. |
| **Call a tool** | Call `get_ticket` with `TKT-0004`. Then a wrong id. Read the error hint. |
| **Two doors** | Ask the same question through the Gateway and directly. Compare. |
| **How it works** | Diagram, in/out authentication, products. |
| **Lessons learnt** | Unlocks after the two questions at the bottom of tabs 2 to 4. |

## If something goes wrong

| Error | Fix |
|---|---|
| 403 / AccessDenied | Your user lacks permission, or the region is wrong. Check **us-east-1**. Tell the trainer. |
| 404 | The URL is not the Gateway MCP URL. Copy it again (ends `/mcp`). |
| Tool not found | Target name must be exactly `askit-lambda`. |
| Anything else | Switch to **Practice gateway** and carry on. |

The app does not store your AWS keys in the repo. Never put keys in GitHub, wikis or chat.

## Clean up

**Keep your Gateway.** Session 12 (Labs 16A and 16B) uses it again. The trainer runs the clean-up after Session 12.
