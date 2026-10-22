# Lab 16 · AskIT goes to production (Day 12)

**We are doing Lab 16 · AskIT goes to production now (lab16-askit-enterprise).**
**In VS Code: File > Open Folder > C:\AskIT\dxc-agentic-ai\Day12\Labs\lab16-askit-enterprise**

## Why
For 11 days you built AskIT on your VM. A client's CIO asks: *"Can 50,000 employees use it on Monday, securely, and will you know when it breaks?"*
Today you close the five gaps between a working agent and a production agent, using AWS Bedrock AgentCore:

| Gap | Closed in tab | AgentCore piece | You met the idea on |
|---|---|---|---|
| 🏠 Hosting | 2 | Runtime | Day 5 (agent loop), Day 9 (console Lambda) |
| 👥 Scale & isolation | 3 | Runtime sessions | Day 7 (memory) |
| 🧰 Enterprise tools | 4 | Gateway | Day 9 (MCP), Day 11 (Gateway) |
| 🔎 Troubleshooting | 5 | Observability (CloudWatch) | Day 10 (Langfuse traces) |
| 🛡️ Governance | 5 | Policy (Cedar) | Day 11 (guardrails) |

Tab 6 **Architect it**: design AgentCore for a client (bank, retailer, hospital) and compare with the reference design.

## What you do
You run AskIT on your VM, **deploy it to AWS yourself**, give it company tools (version 2), see an incident in the agent's trace, learn how a policy blocks a risky action, and design AgentCore for a client.

## Outcome
Your own agent on AgentCore Runtime, version 2 with 4 Gateway tools, a client architecture you designed, and a client line for every step (download them in tab 6).

## How

**1.** In VS Code open a terminal: **Terminal > New Terminal**. Type this and press Enter:

```
python run.py
```

**2.** The app opens in your browser. Do the tabs **in order, 1 to 6**. Each tab has a "Predict first" question: answer it, and the steps appear.

**3.** For the console steps, sign in to the AWS console as **your own user** (user101 ... user116). Region: **N. Virginia (us-east-1)**.

### The two console forms (the app shows the same values, with copy buttons)

**Tab 2 · Deploy (version 1).** Bedrock AgentCore > Runtime > **Create runtime**:

| Field | Value |
|---|---|
| Name | `askit_<your user>`, for example `askit_user101` |
| Runtime platform / Compute type | leave V1 / microVMs |
| Agent source | **S3 Source** > **Choose from an existing S3 bucket** (NOT "Start with a template"). S3 URI: shown in the app |
| Agent entry point | `main.py` |
| Python version | shown in the app |
| Permissions | Use an existing service role: `askit-runtime-role` |
| Everything else | leave the default |

Click **Create**. A note "Update your IAM execution role..." is normal. Then click **Check my Runtime** in the app.

**Tab 4 · Version 2.**
1. AgentCore > **Gateways** > `askit-gw-user116` > copy its **Gateway URL** (ends with `/mcp`).
2. AgentCore > **Runtime** > your Runtime > **Update runtime** > **Environment variables** > Add:

| Key | Value |
|---|---|
| `GATEWAY_URL` | the Gateway URL you copied |

Save. Wait for **Ready**. Click **Check version** in the app.

### Before you leave
AgentCore > Runtime > select your Runtime > **Delete**. Then tab 6 > **Check it is deleted**.

## Files (you do not edit any of them)
| File | What it does |
|---|---|
| `app.py` | The screen: 6 tabs |
| `cloud.py` | AWS calls: who am I, find my Runtime, call it |
| `gw_agent.py`, `gw_client.py`, `tools_core.py`, `rag_tool.py` | The agent and tools for tab 1 (your VM) |
| `model_factory.py` | Picks the model (Bedrock Nova) from the course `.env` |
| `run.py` / `run.bat` | Installs what is needed, then starts the app |

The agent code that runs **inside** your Runtime is `main.py`, packed in the S3 zip. It is the same loop as Day 5: ask the model, run the tool it picks, answer.
Version 1 has no tools. Version 2 reads `GATEWAY_URL` and gets its 4 tools from the Gateway.

## Stuck?
- **"No AWS keys"**: your keys are in `C:\AskIT\dxc-agentic-ai\.env`. Tell the trainer.
- **Deploy failed or is slow**: in the app sidebar switch on **"Stuck? Use the class backup Runtime"** and carry on.
- **"No Runtime called askit_userNNN"**: check the name (small letters, underscore) and the region, then **Refresh my Runtime**.
- **Port busy**: press Ctrl+C in the other Streamlit terminal, then run `python run.py` again.
